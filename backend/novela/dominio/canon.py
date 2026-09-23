"""Rama 2: canon (definitions.md §2). Lo que es verdad del mundo, se haya escrito o no.

Cada fichero de `canon/` es markdown con frontmatter YAML: los campos de su modelo arriba, prosa
libre en el cuerpo. Las seis colecciones append-only del canon son `ColeccionAppendOnly`.
"""

from typing import Literal, Self

from pydantic import Field, model_validator

from novela.dominio.base import SCHEMA_VERSION, ColeccionAppendOnly, Modelo, Nivel, SchemaVersion
from novela.dominio.ids import (
    CapituloNum,
    EscenarioId,
    PersonajeId,
    PistaFalsaId,
    PistaId,
    RevelacionId,
)

# --- 2.1 Premisa -----------------------------------------------------------------------------


class Premisa(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    logline: str = Field(min_length=1)
    pregunta_dramatica: str
    tema: str
    promesa_al_lector: str


# --- 2.2 Mundo -------------------------------------------------------------------------------


class Escenario(Modelo):
    id: EscenarioId
    nombre: str
    descripcion: str
    detalle_sensorial: str
    # Material de trama, no metadato: quién puede entrar determina quién pudo hacer qué.
    quien_tiene_acceso: list[PersonajeId] = []


class EpocaYTecnologia(Modelo):
    epoca: str
    existe: list[str] = []
    no_existe: list[str] = []


class Institucion(Modelo):
    nombre: str
    procedimientos: str


class Mundo(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    escenarios: list[Escenario] = Field(min_length=1)
    epoca_y_tecnologia: EpocaYTecnologia
    reglas_del_mundo: list[str] = []
    instituciones: list[Institucion] = []


# --- 2.3 Personajes: canon/personajes/<id>.md (RF-36) ----------------------------------------


class Identidad(Modelo):
    id: PersonajeId
    nombre: str
    alias: list[str] = []
    edad: int | None = None
    rol_narrativo: str


class Voz(Modelo):
    idiolecto: str
    muletillas: list[str] = []
    registro: str
    # Obligatorio: el escritor imita mejor de lo que obedece.
    dialogo_canonico: list[str] = Field(min_length=1)


class Psicologia(Modelo):
    deseo: str
    necesidad: str
    miedo: str
    herida: str


class Secreto(Modelo):
    que_oculta: str
    a_quien: list[str]


class CambioDeArco(Modelo):
    capitulo: CapituloNum
    descripcion: str


class ArcoPrevisto(Modelo):
    estado_inicial: str
    estado_final: str
    cambios: list[CambioDeArco] = []


class RelacionCanon(Modelo):
    """Punto de partida; la evolución vive en `estado.relaciones`, que es otro campo."""

    con: PersonajeId
    tipo: str
    tension: str
    historia_compartida: str


class MomentoPrivado(Modelo):
    momento: str  # texto, como linea_temporal.inicio
    ubicacion: EscenarioId
    detalle: str


class Personaje(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    identidad: Identidad
    fisico: dict[str, str] = {}
    voz: Voz
    psicologia: Psicologia
    # Campos propios, no prosa: es lo que permitirá filtrarlos del briefing (spec 0002).
    secreto: Secreto | None = None
    arco_previsto: ArcoPrevisto | None = None
    relaciones: list[RelacionCanon] = []
    coartada_y_cronologia_privada: list[MomentoPrivado] = []


# --- 2.4 Misterio ----------------------------------------------------------------------------


class MotivoMedioOportunidad(Modelo):
    motivo: str
    medio: str
    oportunidad: str


class Pista(Modelo):
    id: PistaId
    contenido: str
    capitulo_plantado: CapituloNum
    # None es legítimo: una pista plantada y no pagada existe, y es lo que busca `auditar`.
    capitulo_pagado: CapituloNum | None
    quien_la_percibe: list[str] = []
    es_fair_play: bool


class PistaFalsa(Modelo):
    id: PistaFalsaId
    contenido: str
    a_quien_apunta: PersonajeId
    cuando_se_desmonta: CapituloNum | None


class Revelacion(Modelo):
    id: RevelacionId
    contenido: str
    # Mínimo una: una revelación sin pista no se puede ni escribir (fair play como guardarraíl).
    pistas_que_la_pagan: list[PistaId] = Field(min_length=1)
    capitulo_previsto: CapituloNum
    quien_la_recibe: Literal["lector", "personaje", "ambos"]
    impacto: Nivel


class Giro(Revelacion):
    que_creia_el_lector_antes: str = Field(min_length=1)


class Reloj(Modelo):
    descripcion: str
    limite: str


class Misterio(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    verdad_oculta: ColeccionAppendOnly[str]  # párrafos: se amplía, no se reescribe
    culpable_o_amenaza: str
    motivo_medio_oportunidad: MotivoMedioOportunidad
    pistas: ColeccionAppendOnly[Pista]
    pistas_falsas: ColeccionAppendOnly[PistaFalsa]
    revelaciones: ColeccionAppendOnly[Revelacion]
    giros: ColeccionAppendOnly[Giro]
    reloj: Reloj

    @model_validator(mode="after")
    def _referencias(self) -> Self:
        ids = [p.id for p in self.pistas]
        if len(ids) != len(set(ids)):
            raise ValueError("misterio.pistas repite un id")
        for rev in (*self.revelaciones, *self.giros):
            faltan = sorted(set(rev.pistas_que_la_pagan) - set(ids))
            if faltan:
                raise ValueError(f"{rev.id} la pagan pistas que no existen: {', '.join(faltan)}")
        return self


# --- 2.5 Estilo ------------------------------------------------------------------------------


class Ritmo(Modelo):
    """Numérico, no texto: es lo que hace verificable al editor-estilo."""

    longitud_media_frase: float = Field(gt=0)
    proporcion_dialogo: float = Field(ge=0, le=1)
    proporcion_accion: float = Field(ge=0, le=1)
    proporcion_interioridad: float = Field(ge=0, le=1)


class Estilo(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    guia_de_voz_narrativa: str
    ritmo: Ritmo
    # La única del canon que crece durante la ejecución: la amplía el editor-estilo.
    prohibiciones: ColeccionAppendOnly[str]
    parrafos_canonicos: list[str] = Field(min_length=1)
    convenciones_formato: dict[str, str] = {}


class Canon(Modelo):
    """El canon entero, que es lo que describe `canon.schema.json`. En disco son cinco ficheros
    más uno por personaje; cada uno valida contra su submodelo."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    premisa: Premisa
    mundo: Mundo
    personajes: list[Personaje]
    misterio: Misterio
    estilo: Estilo
