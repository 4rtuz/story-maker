"""Run, manifiesto y `harness.log` (RF-13, RF-27, RF-29).

Un run agrupa los pasos de un capítulo: los briefings de sus agentes, su log y su manifiesto.
`run_id` sale de `NOVELA_RUN_ID` si está definida —validada, porque acaba siendo una ruta— y si
no del reloj; mientras el capítulo no esté cerrado, el run abierto se reutiliza.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Literal

import typer

from novela.dominio.artefactos import Manifest
from novela.dominio.ids import RUN_ID_PATRON
from novela.plataforma.workspace import CONFIG_DIR, WorkspaceRepository, huella, sha256

Fase = Literal["arranque", "capitulo"]


class RunInvalido(ValueError):
    """NOVELA_RUN_ID no casa el formato o es de otro capítulo o fase, o el run del reloj ya es de
    otro. Salida 2."""


@cache
def _sha_commit() -> str:
    git = shutil.which("git")
    if git is None:
        return "desconocido"
    r = subprocess.run(  # noqa: S603
        [git, "-C", str(CONFIG_DIR.parent), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    return r.stdout.strip() if r.returncode == 0 else "desconocido"


@dataclass(frozen=True)
class Run:
    dir: Path

    @property
    def id(self) -> str:
        return self.dir.name

    def registrar(self, linea: str) -> None:
        # La excepción del invariante 6: un log que se lee en vivo no se reescribe entero en cada
        # línea. Se abre, se añade y se cierra: la línea está en disco al volver de aquí.
        with open(self.dir / "harness.log", "a", encoding="utf-8") as log:
            log.write(linea + "\n")

    @contextmanager
    def registro(self, *orden: str) -> Iterator[list[str]]:
        """Una línea por subcomando al terminar, con su código de salida y la causa si falla."""
        causas: list[str] = []
        codigo: int | str = 0
        try:
            yield causas
        except typer.Exit as exc:
            codigo = exc.exit_code
            raise
        except Exception as exc:
            codigo = "error"
            causas.append(f"{type(exc).__name__}: {exc}")
            raise
        finally:
            marca = datetime.now().astimezone().isoformat(timespec="seconds")
            detalle = f" · {'; '.join(causas)}" if causas else ""
            self.registrar(f"{marca} {' '.join(orden)} -> {codigo}{detalle}")


def _de(ws: WorkspaceRepository, directorio: Path) -> tuple[int, Fase] | None:
    ruta = directorio / "manifest.json"
    if not ruta.exists():
        return None
    manifiesto = ws.leer_json(ruta, Manifest)
    return manifiesto.capitulo, manifiesto.fase


def _run_id(
    ws: WorkspaceRepository, capitulo: int, fase: Fase, entorno: Mapping[str, str], ahora: datetime
) -> str:
    fijado = entorno.get("NOVELA_RUN_ID")
    if fijado is not None:
        if not re.fullmatch(RUN_ID_PATRON, fijado):
            raise RunInvalido(f"NOVELA_RUN_ID={fijado!r} no casa {RUN_ID_PATRON}")
        # RF-27: sin esto, la variable mezclaría el arranque con el capítulo 1 por otra vía.
        if (de := _de(ws, ws.raiz / "runs" / fijado)) not in (None, (capitulo, fase)):
            raise RunInvalido(f"NOVELA_RUN_ID={fijado} es un run de otro capítulo o fase: {de}")
        return fijado
    punto = ws.ultimo_checkpoint()
    if not (punto and punto.capitulo >= capitulo):
        for directorio in sorted((ws.raiz / "runs").glob("r-*"), reverse=True):
            if _de(ws, directorio) == (capitulo, fase):
                return directorio.name
    nuevo = ahora.strftime("r-%Y%m%d-%H%M")
    if (ws.raiz / "runs" / nuevo).exists():
        raise RunInvalido(f"el run {nuevo} ya es de otro capítulo o fase; fija NOVELA_RUN_ID")
    return nuevo


def abrir(
    ws: WorkspaceRepository,
    capitulo: int,
    fase: Fase = "capitulo",
    entorno: Mapping[str, str] = os.environ,
    ahora: datetime | None = None,
) -> Run:
    """El run abierto del capítulo en esa fase, creándolo con su manifiesto si no lo hay."""
    run = Run(ws.raiz / "runs" / _run_id(ws, capitulo, fase, entorno, ahora or datetime.now()))
    ruta = run.dir / "manifest.json"
    if not ruta.exists():
        manifiesto = Manifest(
            run_id=run.id,
            capitulo=capitulo,
            fase=fase,
            creado=datetime.now().astimezone().isoformat(timespec="seconds"),
            sha_commit=_sha_commit(),
            version_recetas=sha256(CONFIG_DIR / "recipes.yaml"),
            version_canon=huella(ws.raiz / "canon"),
            version_plan=huella(ws.raiz / "plan"),
        )
        ws.escribir(ruta, manifiesto.model_dump_json(indent=2))
    return run
