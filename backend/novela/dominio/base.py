"""Lo que comparten las cuatro ramas: el modelo base y la versión de los contratos."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

# Todo documento del workspace lleva su schema_version (RF-26). Un documento con otra versión se
# rechaza en el borde en vez de interpretarse a medias.
SchemaVersion = Literal["1.0.0"]
SCHEMA_VERSION: SchemaVersion = "1.0.0"


class Modelo(BaseModel):
    """Inmutable y estricto: un campo de más en la salida de un agente se ve en el capítulo 1."""

    model_config = ConfigDict(frozen=True, extra="forbid")
