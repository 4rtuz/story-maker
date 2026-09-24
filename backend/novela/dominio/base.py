"""Lo que comparten las cuatro ramas: el modelo base, la versión de los contratos y el tipo
append-only."""

import re
import unicodedata
from collections.abc import Iterable, Iterator
from types import GenericAlias
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

# Todo documento del workspace lleva su schema_version (RF-26). Un documento con otra versión se
# rechaza en el borde en vez de interpretarse a medias.
SchemaVersion = Literal["1.0.0"]
SCHEMA_VERSION: SchemaVersion = "1.0.0"

# Valores que usan varias ramas; aquí para que ninguna importe de otra.
Nivel = Literal["alta", "media", "baja"]
Tension = Annotated[int, Field(ge=1, le=10)]

_ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """NFC y cada secuencia de espacios en blanco a un espacio. Nada más: ni comillas ni
    mayúsculas, porque una cita que solo casa aflojando la comparación ya no es una cita. La
    usan las citas de `aplicar-delta` y la petición de `novela cambio` (spec 0007, RF-11)."""
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto))


class Modelo(BaseModel):
    """Inmutable y estricto: un campo de más en la salida de un agente se ve en el capítulo 1."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ColeccionAppendOnly[T]:
    """Colección que solo crece (RF-28). Un tipo para las siete: `libro_de_hechos` y las seis del
    canon que `definitions.md` §2 declara append-only.

    No hay método que modifique ni borre, así que el bug no se puede escribir: `añadir` devuelve
    otra colección y `entradas` una tupla, nunca la lista interna. En la rama 4 el trigger lo caza
    igualmente; en el canon, que vive en markdown, este tipo es la única línea de defensa.
    """

    __slots__ = ("_entradas",)

    def __init__(self, entradas: Iterable[T] = ()) -> None:
        self._entradas: tuple[T, ...] = tuple(entradas)

    @property
    def entradas(self) -> tuple[T, ...]:
        return self._entradas

    def añadir(self, entrada: T) -> "ColeccionAppendOnly[T]":
        return ColeccionAppendOnly((*self._entradas, entrada))

    def __iter__(self) -> Iterator[T]:
        return iter(self._entradas)

    def __len__(self) -> int:
        return len(self._entradas)

    def __eq__(self, otra: object) -> bool:
        return isinstance(otra, ColeccionAppendOnly) and self._entradas == otra._entradas

    def __hash__(self) -> int:
        return hash(self._entradas)

    def __repr__(self) -> str:
        return f"ColeccionAppendOnly({list(self._entradas)!r})"

    @classmethod
    def __get_pydantic_core_schema__(cls, fuente: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        # En disco y en JSON es una lista; en memoria, esta clase.
        (item,) = get_args(fuente) or (Any,)
        lista = handler.generate_schema(GenericAlias(list, (item,)))
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.no_info_before_validator_function(
                lambda v: list(v.entradas) if isinstance(v, ColeccionAppendOnly) else v, lista
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda c: list(c.entradas), return_schema=lista, info_arg=False
            ),
        )
