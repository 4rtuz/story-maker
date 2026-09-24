"""`WorkspaceRepository`: el puerto de lectura y escritura de `novelas/<slug>/`.

Uno de los dos únicos puertos del sistema (architecture.md §3.0). Su doble en los tests no es otra
clase: es esta misma apuntada con `NOVELAS_DIR` a un workspace sintético de `tests/fixtures/`.
Todo lo que lee de disco pasa por un modelo de `dominio/` antes de llegar al código.
"""

import hashlib
import os
import re
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ValidationError

from novela.dominio import frontmatter
from novela.dominio.artefactos import (
    TOPE_LECTURA_BYTES,
    TOPE_TRAMO_BYTES,
    Checkpoint,
    Manifest,
    TramoDeLog,
    cortar_tramo,
)
from novela.dominio.config import Config
from novela.dominio.ids import SLUG_PATRON, nn
from novela.dominio.plan import Escaleta
from novela.plataforma import atomic, lock

# backend/config/: default.yaml y recipes.yaml, del harness y no del workspace.
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class SlugInvalido(ValueError):
    """El slug no casa `^[a-z0-9-]+$`. Es una cadena de fuera que iba a convertirse en ruta."""


class WorkspaceInvalido(Exception):
    """Falta el workspace o un fichero suyo no valida contra su modelo. Salida 4."""


class FueraDelLog(ValueError):
    """El `desde` pedido pasa del tamaño de `harness.log`: la API lo sirve como 416."""


def validar_slug(slug: str) -> str:
    # fullmatch y no match: con `$`, re.match acepta "demo\n".
    if not re.fullmatch(SLUG_PATRON, slug):
        raise SlugInvalido(f"slug inválido: {slug!r} (se espera {SLUG_PATRON})")
    return slug


def raiz_de_novelas(entorno: Mapping[str, str] = os.environ) -> Path:
    return Path(entorno["NOVELAS_DIR"]) if entorno.get("NOVELAS_DIR") else Path("novelas")


def sha256(ruta: Path) -> str:
    """De los bytes en disco, sin normalizar: la custodia compara exactamente esto."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def huella(directorio: Path) -> str:
    """Versión de contenido de un directorio: rutas relativas y bytes, en orden."""
    resumen = hashlib.sha256()
    for fichero in sorted(p for p in directorio.rglob("*") if p.is_file()):
        if fichero.suffix == ".tmp":
            continue
        resumen.update(fichero.relative_to(directorio).as_posix().encode() + b"\0")
        resumen.update(fichero.read_bytes() + b"\0")
    return resumen.hexdigest()


@dataclass(frozen=True)
class WorkspaceRepository:
    raiz: Path

    @classmethod
    def resolver(cls, slug: str, entorno: Mapping[str, str] = os.environ) -> Self:
        return cls(raiz_de_novelas(entorno) / validar_slug(slug))

    @property
    def slug(self) -> str:
        return self.raiz.name

    # --- rutas -------------------------------------------------------------------------------

    @property
    def config_yaml(self) -> Path:
        return self.raiz / "config.yaml"

    @property
    def estado_db(self) -> Path:
        return self.raiz / "estado" / "estado.db"

    @property
    def lock(self) -> Path:
        return self.raiz / "estado" / "state.lock"

    def nn(self, capitulo: int) -> str:
        return nn(capitulo, self.config().parametros_obra.num_capitulos)

    # --- lectura -----------------------------------------------------------------------------

    def existe(self) -> bool:
        return self.config_yaml.is_file()

    def config(self) -> Config:
        return self.leer_yaml(self.config_yaml, Config)

    def ultimo_checkpoint(self) -> Checkpoint | None:
        ruta = self.raiz / "checkpoints" / "latest.json"
        return self.leer_json(ruta, Checkpoint) if ruta.exists() else None

    def escaleta(self) -> Escaleta:
        """`plan/escaleta.md`, validada con el num_capitulos de la obra: `modelo_de_md` no pasa
        contexto y sin él el validador de `Escaleta` rechaza siempre."""
        ruta = self.raiz / "plan" / "escaleta.md"
        contexto = {"num_capitulos": self.config().parametros_obra.num_capitulos}
        try:
            meta = frontmatter.partir(ruta.read_text(encoding="utf-8"))[0]
            return Escaleta.model_validate(meta, context=contexto)
        except (OSError, yaml.YAMLError, ValueError) as exc:  # ValueError: ValidationError incluido
            raise WorkspaceInvalido(f"{ruta}: {exc}") from exc

    def manifiestos(self) -> list[Manifest]:
        rutas = (self.raiz / "runs").glob("*/manifest.json")
        return sorted((self.leer_json(r, Manifest) for r in rutas), key=lambda m: m.run_id)

    def tramo_de_log(self, run_id: str, desde: int) -> TramoDeLog:
        """Salta a `desde` y lee como mucho 1 MiB, más el byte anterior para saber si `desde` es
        límite de línea: nunca desde el principio (RNF-17). Tampoco pasa del tamaño del `stat`,
        aunque el CLI escriba mientras tanto (VER-5)."""
        try:
            with open(self.raiz / "runs" / run_id / "harness.log", "rb") as log:
                info = os.fstat(log.fileno())
                if desde > info.st_size:
                    raise FueraDelLog(f"desde {desde} pasa del tamaño del log ({info.st_size})")
                log.seek(max(desde - 1, 0))
                en_limite = desde == 0 or log.read(1) == b"\n"
                ventana = log.read(min(TOPE_LECTURA_BYTES, info.st_size - desde))
        except FileNotFoundError:
            return TramoDeLog(desde=desde, hasta=desde, tamano=0, modificado=None, lineas=[])
        lineas, hasta = cortar_tramo(
            ventana,
            desde,
            TOPE_TRAMO_BYTES,
            en_limite=en_limite,
            hasta_el_final=desde + len(ventana) >= info.st_size,
        )
        modificado = datetime.fromtimestamp(info.st_mtime).astimezone()
        return TramoDeLog(
            desde=desde,
            hasta=hasta,
            tamano=info.st_size,
            modificado=modificado.isoformat(timespec="seconds"),
            lineas=lineas,
        )

    def exigir(self) -> Self:
        if not self.existe():
            raise WorkspaceInvalido(f"{self.raiz}: no hay workspace (falta config.yaml)")
        return self

    def leer_yaml[M: BaseModel](self, ruta: Path, modelo: type[M]) -> M:
        try:
            return modelo.model_validate(yaml.safe_load(ruta.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise WorkspaceInvalido(f"{ruta}: {exc}") from exc

    @staticmethod
    def modelo_de_md[M: BaseModel](ruta: Path, texto: str, modelo: type[M]) -> M:
        """El frontmatter de un markdown ya leído, validado contra su modelo."""
        try:
            return modelo.model_validate(frontmatter.partir(texto)[0])
        except (ValueError, yaml.YAMLError) as exc:  # ValidationError, o frontmatter mal formado
            raise WorkspaceInvalido(f"{ruta}: {exc}") from exc

    def leer_md[M: BaseModel](self, ruta: Path, modelo: type[M]) -> M:
        try:
            texto = ruta.read_text(encoding="utf-8")
        except OSError as exc:
            raise WorkspaceInvalido(f"{ruta}: {exc}") from exc
        return self.modelo_de_md(ruta, texto, modelo)

    def leer_json[M: BaseModel](self, ruta: Path, modelo: type[M]) -> M:
        try:
            return modelo.model_validate_json(ruta.read_bytes())
        except (OSError, ValidationError) as exc:
            raise WorkspaceInvalido(f"{ruta}: {exc}") from exc

    # --- escritura ---------------------------------------------------------------------------

    def escribir(self, ruta: Path, contenido: str | bytes) -> None:
        atomic.escribir(ruta, contenido)

    def bloquear(self) -> AbstractContextManager[None]:
        return lock.bloquear(self.lock)
