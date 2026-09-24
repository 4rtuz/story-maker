"""La rúbrica de `backend/config/rubrica.yaml` como modelo, y su carga."""

from typing import Self

import yaml
from pydantic import Field, model_validator

from novela.dominio.base import Modelo
from novela.dominio.juicio import CRITERIOS, Criterio
from novela.plataforma.workspace import CONFIG_DIR

RUTA = CONFIG_DIR / "rubrica.yaml"


class DefinicionCriterio(Modelo):
    pregunta: str = Field(min_length=1)
    escala: dict[int, str] = Field(min_length=1)


class Umbral(Modelo):
    media_minima: float = Field(ge=1, le=5)
    minimo_por_criterio: int = Field(ge=1, le=5)


class Rubrica(Modelo):
    version: str = Field(pattern=r"^rubrica-\d+$")
    criterios: dict[Criterio, DefinicionCriterio]
    umbral: Umbral

    @model_validator(mode="after")
    def _criterios_del_modelo(self) -> Self:
        if tuple(self.criterios) != CRITERIOS:
            faltan = [c for c in CRITERIOS if c not in self.criterios]
            raise ValueError(f"los criterios son {CRITERIOS}, en orden; faltan {faltan}")
        return self


def cargar() -> Rubrica:
    return Rubrica.model_validate(yaml.safe_load(RUTA.read_text(encoding="utf-8")))
