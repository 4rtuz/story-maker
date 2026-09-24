"""Identificadores del workspace como tipos con validador de formato.

Las expresiones son las de `architecture.md` §5 con `[0-9]` donde allí pone `\\d`: en Python `\\d`
acepta cualquier dígito Unicode y en JSON Schema solo ASCII, y los dos lados tienen que decir lo
mismo. Escenario y escena comparten prefijo y son disjuntas: escenario exige letra tras el guion.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

PersonajeId = Annotated[str, StringConstraints(pattern=r"^per-[a-z0-9-]+$")]
EscenarioId = Annotated[str, StringConstraints(pattern=r"^esc-[a-z][a-z0-9-]*$")]
EscenaId = Annotated[str, StringConstraints(pattern=r"^esc-[0-9]{2,3}-[0-9]+$")]
PistaId = Annotated[str, StringConstraints(pattern=r"^pis-[0-9]{3}$")]
PistaFalsaId = Annotated[str, StringConstraints(pattern=r"^pfa-[0-9]{3}$")]
RevelacionId = Annotated[str, StringConstraints(pattern=r"^rev-[0-9]{3}$")]
HiloId = Annotated[str, StringConstraints(pattern=r"^hil-[0-9]{3}$")]
ObjetoId = Annotated[str, StringConstraints(pattern=r"^obj-[0-9]{3}$")]
HechoId = Annotated[str, StringConstraints(pattern=r"^hec-[0-9]{3}$")]
CapituloId = Annotated[str, StringConstraints(pattern=r"^cap-[0-9]{2,3}$")]
CambioId = Annotated[str, StringConstraints(pattern=r"^cam-[0-9]{3}$")]  # spec 0007, D22

# Dos cadenas de fuera del proceso que acaban siendo rutas: el slug (CLI y API) y el run_id
# (NOVELA_RUN_ID y API). Una sola copia de cada regex: dos copias de una regla de seguridad
# acaban divergiendo.
SLUG_PATRON = r"^[a-z0-9-]+$"
RUN_ID_PATRON = r"^r-[0-9]{8}-[0-9]{4}$"
Slug = Annotated[str, StringConstraints(pattern=SLUG_PATRON)]
RunId = Annotated[str, StringConstraints(pattern=RUN_ID_PATRON)]

# Hash de los bytes en disco, sin normalizar: la custodia del capítulo (RF-30 a RF-32).
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

# Número de capítulo: el rango real (1..num_capitulos) depende de config.yaml; el tipo fija el
# techo absoluto y `nn` el formato, que es uno solo para todo el workspace.
CapituloNum = Annotated[int, Field(ge=1, le=999)]


def nn(capitulo: int, num_capitulos: int) -> str:
    """`07` hasta 99 capítulos, `007` si la novela pasa de 99 (architecture.md §5)."""
    if not 1 <= capitulo <= num_capitulos:
        raise ValueError(f"capítulo {capitulo} fuera de rango 1..{num_capitulos}")
    return f"{capitulo:0{3 if num_capitulos > 99 else 2}d}"


class Agente(StrEnum):
    ARQUITECTO = "arquitecto"
    TRAZADOR = "trazador"
    ESCRITOR = "escritor"
    CONTINUISTA = "continuista"
    EDITOR_ESTILO = "editor-estilo"
    LECTOR_SUSPENSE = "lector-suspense"
    CRONISTA = "cronista"
