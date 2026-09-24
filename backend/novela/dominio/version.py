"""Versiones de la novela (spec 0007 §8.3): la petición de cambio, su plan y el registro.

Son contratos entre subcomandos del CLI —`cambio`, `aplicar-delta --reaplicar`, `versiones`— y no
los produce ningún agente, así que no se exportan a `backend/schemas/` (spec 0007, D7). Validan
todo lo que se lee de `cambios/` y `versiones/`.
"""

from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from novela.dominio.base import SCHEMA_VERSION, ColeccionAppendOnly, Modelo, SchemaVersion
from novela.dominio.ids import CambioId, CapituloNum, HechoId, Sha256


class PlanDeRegeneracion(Modelo):
    """Qué capítulos se regeneran y cuáles se reaplican. `requeridos` solo lleva los capítulos
    que tienen alguno: los hechos que el capítulo introduce y un capítulo posterior usa."""

    regenerar: list[CapituloNum] = Field(min_length=1)
    reaplicar: list[CapituloNum]
    origen: CapituloNum
    requeridos: dict[CapituloNum, list[HechoId]]


class PeticionDeCambio(Modelo):
    """`cambios/cam-NNN.json`. `preparando` hace de diario de la preparación (spec 0007, D9)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    id: CambioId
    hecho: HechoId
    texto_anterior: str
    texto: str = Field(min_length=1, max_length=500)
    motivo: str | None = Field(default=None, max_length=500)
    hecho_nuevo: HechoId
    version_base: int = Field(ge=1)
    version_nueva: int
    plan: PlanDeRegeneracion
    estado: Literal["preparando", "en_curso"]
    creado: AwareDatetime  # lo compara run._run_id con el `creado` de cada manifiesto


class Version(Modelo):
    """`versiones/vN/version.json`: el sha256 de cada fichero copiado, por ruta relativa a
    `vN/`, y el sello de capítulos del último checkpoint."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    numero: int = Field(ge=1)
    creada: datetime
    cambio: CambioId | None
    capitulos_sha256: dict[CapituloNum, Sha256]
    ficheros: dict[str, Sha256]


class VersionRegistrada(Modelo):
    numero: int = Field(ge=1)
    cambio: CambioId | None  # None: la original
    creada: datetime


class RegistroDeVersiones(Modelo):
    """`versiones/versiones.json`. Solo crece: `ColeccionAppendOnly` no tiene con qué reescribir
    una entrada, y el validador exige los números 1..n en orden."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    versiones: ColeccionAppendOnly[VersionRegistrada] = ColeccionAppendOnly()

    @model_validator(mode="after")
    def _numeradas_desde_uno(self) -> Self:
        numeros = [v.numero for v in self.versiones]
        if numeros != list(range(1, len(numeros) + 1)):
            raise ValueError(f"versiones sin numerar desde 1 en orden: {numeros}")
        return self


class CapituloCambiado(Modelo):
    """Una línea de las novedades: capítulo cerrado cuyo sha256 difiere de la versión anterior."""

    capitulo: CapituloNum
    titulo: str
    cambio: CambioId
