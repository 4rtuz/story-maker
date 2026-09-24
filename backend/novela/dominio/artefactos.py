"""Rama 6: artefactos en disco que no son canon, plan ni estado (definitions.md §6).

El frontmatter del capítulo es contrato del escritor (architecture.md §7.2); el checkpoint lo
escribe `novela checkpoint`. Los dos cruzan del disco al código, así que tienen modelo.
"""

from typing import Literal

from pydantic import Field

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.estado import Cursor, Resumen
from novela.dominio.ids import (
    Agente,
    CapituloNum,
    EscenaId,
    HiloId,
    PersonajeId,
    PistaId,
    RunId,
    Sha256,
)


def contar_palabras(cuerpo: str) -> int:
    """Del cuerpo, no del `palabras` del frontmatter: eso es una declaración del escritor."""
    return len(cuerpo.split())


class FrontmatterCapitulo(Modelo):
    """Cabecera de `capitulos/NN.md`. Es una declaración del escritor, no una prueba: `validar`
    cuenta las palabras del cuerpo en vez de fiarse de `palabras`."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: CapituloNum
    titulo: str = Field(min_length=1)
    pov: PersonajeId
    palabras: int = Field(ge=0)
    escenas: list[EscenaId] = Field(min_length=1)
    pistas_plantadas: list[PistaId] = []
    pistas_pagadas: list[PistaId] = []
    hilos_abiertos: list[HiloId] = []
    hilos_cerrados: list[HiloId] = []
    version_canon: int = Field(ge=1)
    version_plan: int = Field(ge=1)
    run_id: RunId


class Checkpoint(Modelo):
    """`checkpoints/NN.json` y `latest.json`: cursor, versiones y run_id, no la base (RF-20).
    `capitulos_sha256` es el sello de los capítulos cerrados hasta N (RF-35)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: CapituloNum
    cursor: Cursor
    run_id: RunId
    version_canon: Sha256
    version_plan: Sha256
    capitulos_sha256: dict[CapituloNum, Sha256]


class Manifest(Modelo):
    """`runs/<run_id>/manifest.json`: lo que permite atribuir un cambio de calidad a un cambio
    concreto (validators.md §4.7). Las versiones son hashes de contenido, no números. `fase`
    separa el run de arranque —arquitecto y trazador— de los runs de capítulo (spec 0003)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    run_id: RunId
    capitulo: CapituloNum
    fase: Literal["arranque", "capitulo"] = "capitulo"
    creado: str  # ISO 8601 con zona
    sha_commit: str
    version_recetas: Sha256
    version_canon: Sha256
    version_plan: Sha256
    # El sha no basta si el árbol estaba sucio: un prompt sin commitear daría dos ejecuciones
    # con el mismo sha y prompts distintos (RF-12).
    sucio: bool = False
    hashes_claude: dict[str, Sha256] = {}


# El tramo de `harness.log` que sirve la API al panel (spec 0004, D17 y D48).
TOPE_TRAMO_BYTES = 65_536
TOPE_LECTURA_BYTES = 1_048_576


class TramoDeLog(Modelo):
    """Líneas completas de `runs/<run_id>/harness.log` desde el byte `desde`. `hasta` es el
    siguiente `desde`: el cliente encadena sin que el servidor guarde nada. Sin log, `tamano` 0,
    `modificado` None y `hasta` = `desde`. No es documento del workspace: sin schema_version."""

    desde: int = Field(ge=0)
    hasta: int = Field(ge=0)
    tamano: int = Field(ge=0)
    modificado: str | None  # mtime ISO 8601 con zona
    lineas: list[str]


def cortar_tramo(
    ventana: bytes, desde: int, tope: int, *, en_limite: bool, hasta_el_final: bool
) -> tuple[list[str], int]:
    """Las líneas completas de `ventana` —los bytes del log desde `desde`— y el `hasta` absoluto.

    Si `desde` cae a mitad de línea, descarta hasta el primer `\\n`. Corta en el último `\\n` de
    los primeros `tope` bytes, o en el primero si una línea sola pasa del tope. Si ninguna línea
    termina en la ventana, la incompleta del final espera; si la ventana no llega al final, es
    una línea mayor que la lectura y se salta entera (D48). Cortar aquí, en bytes, es lo que
    impide partir un carácter UTF-8 al serializar."""
    inicio = 0 if en_limite else ventana.find(b"\n") + 1
    corte = ventana.rfind(b"\n", inicio, inicio + tope)
    if corte == -1:
        corte = ventana.find(b"\n", inicio)
    if corte == -1:
        return [], desde + (len(ventana) if inicio == 0 and not hasta_el_final else inicio)
    lineas = ventana[inicio:corte].split(b"\n")
    return [linea.removesuffix(b"\r").decode("utf-8", "replace") for linea in lineas], (
        desde + corte + 1
    )


class Memoria(Resumen):
    """`memoria/resumenes/NN.md`, que escribe `aplicar-delta` desde el delta: derivado y
    reconstruible recorriendo `estado/deltas/*.json`. Todo va en el frontmatter."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: CapituloNum


class FrontmatterBriefing(Modelo):
    """Cabecera de `runs/<run_id>/briefings/NN-<agente>.md`. `capitulo_sha256` solo está cuando
    el briefing incrusta `capitulos/NN.md`: es la versión exacta que vio ese agente (RF-30)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    agente: Agente
    capitulo: CapituloNum
    run_id: RunId
    presupuesto_tokens: int
    tokens_estimados: int
    degradacion: list[str] = []
    capitulo_sha256: Sha256 | None = None
