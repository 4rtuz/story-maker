"""El lanzamiento de una novela desde el panel: lo que pide y lo que `novela producir` informa.

No es una rama de contexto: vive en `novelas/.lanzador/`, fuera de todo workspace, y solo dice qué
proceso corre y por dónde va. Lo escrito sigue saliendo de `estado.db` y de `checkpoints/`.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from novela.dominio.base import Modelo
from novela.dominio.ids import Slug

EstadoDeLanzamiento = Literal["en_marcha", "terminado", "fallido", "detenido", "interrumpido"]


class PeticionDeLanzamiento(Modelo):
    """Los argumentos de `/novela-nueva`, con los mismos límites que el formulario del panel."""

    slug: Slug
    idea: Annotated[str, StringConstraints(max_length=4000, pattern=r"\S")]
    capitulos: Annotated[int, Field(ge=1, le=999)] | None = None
    palabras: Annotated[int, Field(ge=1, le=2_000_000)] | None = None

    @field_validator("idea")
    @classmethod
    def _sin_controles(cls, idea: str) -> str:
        # Un NUL rompe el argv, y los demás no tienen sitio en una idea.
        if any(ord(c) < 32 and c not in "\n\r\t" for c in idea):
            raise ValueError("la idea lleva caracteres de control")
        return idea


class Lanzamiento(Modelo):
    slug: Slug
    estado: EstadoDeLanzamiento
    paso: str
    detalle: str
    actualizado: datetime
    detener_pedido: bool = False
    # Las últimas líneas de la salida de las sesiones; solo en la respuesta de la API.
    registro: list[str] = []
