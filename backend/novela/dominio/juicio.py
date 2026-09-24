"""Juicio de la novela completa con la rúbrica de `backend/config/rubrica.yaml`
(docs/evaluacion/juez.md). Un solo modelo para el `juez` y para la revisión humana: lo único que
cambia es `evaluador`, y así `novela comparar-juicios` compara criterio a criterio.
"""

from typing import Literal, Self, get_args

from pydantic import Field, model_validator

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.ids import CapituloNum

# Calidad narrativa va desglosada en tres: arco, personajes y ritmo entre capítulos.
Criterio = Literal["continuidad", "tono", "arco", "personajes", "ritmo", "personalizacion"]
CRITERIOS: tuple[Criterio, ...] = get_args(Criterio)
Evaluador = Literal["juez", "humano"]


class Cita(Modelo):
    capitulo: CapituloNum
    texto: str = Field(min_length=1, max_length=400)


class Valoracion(Modelo):
    puntuacion: int = Field(ge=1, le=5)
    justificacion: str = Field(min_length=1, max_length=1500)
    citas: list[Cita] = Field(min_length=1, max_length=5)


class Juicio(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    rubrica_version: str = Field(min_length=1)
    evaluador: Evaluador
    criterios: dict[Criterio, Valoracion]

    @model_validator(mode="after")
    def _todos_los_criterios(self) -> Self:
        if faltan := [c for c in CRITERIOS if c not in self.criterios]:
            raise ValueError(f"faltan criterios: {', '.join(faltan)}")
        return self
