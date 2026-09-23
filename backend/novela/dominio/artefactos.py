"""Rama 6: artefactos en disco que no son canon, plan ni estado (definitions.md §6).

El frontmatter del capítulo es contrato del escritor (architecture.md §7.2); el checkpoint lo
escribe `novela checkpoint`. Los dos cruzan del disco al código, así que tienen modelo.
"""

from pydantic import Field

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.estado import Cursor
from novela.dominio.ids import CapituloNum, EscenaId, HiloId, PersonajeId, PistaId, RunId, Sha256


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
