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
from novela.plataforma import versiones
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


# El sha solo identifica el prompt con el árbol limpio (validators.md §4.7). CLAUDE.md y AGENTS.md
# se cargan en cada subagente y cambian su conducta igual que su prompt (F-05).
RAIZ_REPO = CONFIG_DIR.parent.parent
_VIGILADO = (".claude", "backend/config", "backend/novela", "CLAUDE.md", "AGENTS.md")
_HASHEADO = (
    ".claude/agents/*.md",
    ".claude/commands/*.md",
    ".claude/hooks/*",
    ".claude/settings.json",
    "CLAUDE.md",
    "AGENTS.md",
)


def _sucio(raiz: Path, git: str | None) -> bool:
    """Sin git, o si falla, sucio (D-6): un manifiesto que no puede probar que el árbol estaba
    limpio no lo afirma. Sin @cache, a diferencia de _sha_commit: se llama una vez por run."""
    if git is None:
        return True
    try:
        r = subprocess.run(  # noqa: S603
            [git, "-C", str(raiz), "status", "--porcelain", "--", *_VIGILADO],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    return r.returncode != 0 or bool(r.stdout.strip())


def procedencia(
    raiz: Path = RAIZ_REPO, git: str | None = shutil.which("git")
) -> tuple[bool, dict[str, str]]:
    """`sucio` y el sha256 de cada fichero de .claude/ que cambia la conducta de un agente."""
    hashes = {
        p.relative_to(raiz).as_posix(): sha256(p)
        for patron in _HASHEADO
        for p in sorted(raiz.glob(patron))
        if p.is_file()
    }
    return _sucio(raiz, git), hashes


# Solo la forma canónica, y no uuid.UUID(), que acepta llaves y `urn:`: el valor acaba en una
# línea de log que el procedimiento lee.
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


@dataclass(frozen=True)
class Run:
    dir: Path
    sesion: str | None = None  # NOVELA_SESSION_ID: enlaza cada línea con su traza (RF-21)

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
            # Tras la marca (D-5): la subcadena `<orden> NN -> <código>` que se cuenta no cambia.
            sesion = f" sesion={self.sesion}" if self.sesion else ""
            detalle = f" · {'; '.join(causas)}" if causas else ""
            # Una sola línea aunque la causa traiga saltos, como un ValidationError: el
            # procedimiento decide leyendo la última línea del log (spec 0003 §5.4).
            linea = f"{marca}{sesion} {' '.join(orden)} -> {codigo}{detalle}"
            self.registrar(" ".join(linea.splitlines()))


def _de(
    ws: WorkspaceRepository, directorio: Path, desde: datetime | None
) -> tuple[int, Fase] | Literal["anterior"] | None:
    """`(capitulo, fase)` del run, o None si no tiene manifiesto. Un run anterior a `desde` —el
    último cambio— es de otra versión: devolverlo lo mezclaría con esta (spec 0007, D4)."""
    ruta = directorio / "manifest.json"
    if not ruta.exists():
        return None
    manifiesto = ws.leer_json(ruta, Manifest)
    if desde is not None and datetime.fromisoformat(manifiesto.creado) < desde:
        return "anterior"
    return manifiesto.capitulo, manifiesto.fase


def _run_id(
    ws: WorkspaceRepository, capitulo: int, fase: Fase, entorno: Mapping[str, str], ahora: datetime
) -> str:
    cambio = versiones.ultimo_cambio(ws)
    desde = cambio.creado if cambio else None
    fijado = entorno.get("NOVELA_RUN_ID")
    if fijado is not None:
        if not re.fullmatch(RUN_ID_PATRON, fijado):
            raise RunInvalido(f"NOVELA_RUN_ID={fijado!r} no casa {RUN_ID_PATRON}")
        de = _de(ws, ws.raiz / "runs" / fijado, desde)
        if de == "anterior":
            raise RunInvalido(f"NOVELA_RUN_ID={fijado} es un run de una versión anterior")
        # RF-27: sin esto, la variable mezclaría el arranque con el capítulo 1 por otra vía.
        if de not in (None, (capitulo, fase)):
            raise RunInvalido(f"NOVELA_RUN_ID={fijado} es un run de otro capítulo o fase: {de}")
        return fijado
    punto = ws.ultimo_checkpoint()
    if not (punto and punto.capitulo >= capitulo):
        for directorio in sorted((ws.raiz / "runs").glob("r-*"), reverse=True):
            if _de(ws, directorio, desde) == (capitulo, fase):
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
    """El run abierto del capítulo en esa fase, creándolo con su manifiesto si no lo hay. Un
    NOVELA_SESSION_ID inválido se ignora: a diferencia de NOVELA_RUN_ID, no acaba en una ruta."""
    sesion = entorno.get("NOVELA_SESSION_ID", "")
    run = Run(
        ws.raiz / "runs" / _run_id(ws, capitulo, fase, entorno, ahora or datetime.now()),
        sesion if re.fullmatch(_UUID, sesion) else None,
    )
    ruta = run.dir / "manifest.json"
    if not ruta.exists():
        sucio, hashes = procedencia()
        manifiesto = Manifest(
            run_id=run.id,
            capitulo=capitulo,
            fase=fase,
            sucio=sucio,
            hashes_claude=hashes,
            creado=datetime.now().astimezone().isoformat(timespec="seconds"),
            sha_commit=_sha_commit(),
            version_recetas=sha256(CONFIG_DIR / "recipes.yaml"),
            version_canon=huella(ws.raiz / "canon"),
            version_plan=huella(ws.raiz / "plan"),
        )
        ws.escribir(ruta, manifiesto.model_dump_json(indent=2))
    return run
