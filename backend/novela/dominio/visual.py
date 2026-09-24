"""El informe de la validación visual de la lectura web: `qa/visual.json`.

Ver docs/validacion-visual.md.

Cada comprobación que falla nombra el rol al que se devuelve: `escritor` si falta contenido en la
novela (un personaje sin capítulo, un título vacío), `exportacion` si el libro que sirve el backend
está mal armado (la dedicatoria, la ficha), `frontend` si el dato llega y no se pinta o no navega.
"""

from typing import Literal, Self

from pydantic import Field, model_validator

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.ids import Slug

IdComprobacion = Literal["portada", "dedicatoria", "indice", "navegacion", "ficha"]
Responsable = Literal["escritor", "exportacion", "frontend"]


class Comprobacion(Modelo):
    id: IdComprobacion
    ok: bool
    detalle: str = Field(default="", max_length=500)
    responsable: Responsable | None = None

    @model_validator(mode="after")
    def _responsable_si_falla(self) -> Self:
        if self.ok != (self.responsable is None):
            raise ValueError("una comprobación fallida lleva responsable, y una correcta no")
        return self


class InformeVisual(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    slug: Slug
    herramienta: Literal["playwright-mcp", "playwright-test"]
    comprobaciones: list[Comprobacion] = Field(min_length=1)
    capturas: list[str] = []  # rutas relativas al repo, p. ej. docs/img/lectura-portada.png

    @property
    def score(self) -> float:
        return sum(c.ok for c in self.comprobaciones) / len(self.comprobaciones)

    @property
    def devolver_a(self) -> list[tuple[Responsable, IdComprobacion]]:
        return sorted((c.responsable, c.id) for c in self.comprobaciones if c.responsable)
