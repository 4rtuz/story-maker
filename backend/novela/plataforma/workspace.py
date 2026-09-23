"""`WorkspaceRepository`: el puerto de lectura y escritura de `novelas/<slug>/`.

Uno de los dos únicos puertos del sistema (architecture.md §3.0). Su doble en los tests no es otra
clase: es esta misma apuntada con `NOVELAS_DIR` a un workspace sintético de `tests/fixtures/`.
Todo lo que lee de disco pasa por un modelo de `dominio/` antes de llegar al código.
"""

import os
import re
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ValidationError

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

    def leer_yaml[M: BaseModel](self, ruta: Path, modelo: type[M]) -> M:
        try:
            return modelo.model_validate(yaml.safe_load(ruta.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise WorkspaceInvalido(f"{ruta}: {exc}") from exc

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
