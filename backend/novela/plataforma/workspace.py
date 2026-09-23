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
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ValidationError

from novela.dominio import frontmatter
from novela.dominio.artefactos import Checkpoint
from novela.dominio.config import Config
from novela.dominio.ids import SLUG_PATRON, nn
from novela.plataforma import atomic, lock

# backend/config/: default.yaml y recipes.yaml, del harness y no del workspace.
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class SlugInvalido(ValueError):
    """El slug no casa `^[a-z0-9-]+$`. Es una cadena de fuera que iba a convertirse en ruta."""


class WorkspaceInvalido(Exception):
    """Falta el workspace o un fichero suyo no valida contra su modelo. Salida 4."""


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
        except ValueError as exc:  # ValidationError, o frontmatter mal formado
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
