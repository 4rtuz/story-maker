"""Rama 4: estado narrativo (definitions.md §4). Lo que ya pasó.

Es la vista serializada de `architecture.md` §7.1: lo que devuelven `novela estado --json` y
`GET /novelas/{slug}/estado`, y lo que valida `state.schema.json`. En disco vive en `estado.db`,
una tabla por colección. Los nombres son los de §7.1, sin alias.

Las cinco append-only —`linea_temporal`, `conocimiento`, `libro_de_hechos`, `conocimiento_lector`
y `tension_real`— son `ColeccionAppendOnly`: el tipo evita escribir el bug y el trigger lo caza.
`pistas` y `metricas` son derivadas: se calculan al aplicar el delta, no vienen en él.
"""

from typing import Literal, Self, get_args

from pydantic import Field, field_validator, model_validator

from novela.dominio.base import (
    SCHEMA_VERSION,
    ColeccionAppendOnly,
    Modelo,
    Nivel,
    SchemaVersion,
    Tension,
)
from novela.dominio.ids import (
    CapituloNum,
    EscenaId,
    EscenarioId,
    HechoId,
    HiloId,
    ObjetoId,
    PersonajeId,
    PistaId,
)

# Los cuatro tramos y los nueve pasos del bucle de architecture.md §2.1.
Fase = Literal["escritura", "revision", "registro", "cerrado"]
Paso = Literal[
    "briefing",
    "escritor",
    "validar",
    "continuista",
    "editor-estilo",
    "lector-suspense",
    "cronista",
    "aplicar-delta",
    "checkpoint",
]
FASES: tuple[Fase, ...] = get_args(Fase)
PASOS: tuple[Paso, ...] = get_args(Paso)
Condicion = Literal["viva", "muerta", "desaparecida"]
EstadoDePista = Literal["plantada", "pagada", "pendiente", "huerfana"]


class Cursor(Modelo):
    capitulo: CapituloNum
    fase: Fase
    ultimo_paso: Paso | None  # None: todavía no se ha dado ningún paso de la novela
    # Se persiste porque la parada al tercer intento depende de él.
    intento: int = Field(ge=1, le=3)


class EntradaTemporal(Modelo):
    escena: EscenaId
    capitulo: CapituloNum
    inicio: str
    duracion_min: int = Field(ge=0)
    cita: str | None = None


class EstadoPersonaje(Modelo):
    ubicacion: EscenarioId | None
    estado_fisico: str
    estado_emocional: str
    condicion: Condicion
    objetivo_activo: str
    ultima_aparicion: CapituloNum


class EntradaConocimiento(Modelo):
    """Misma entrada para `conocimiento` (por personaje) y `conocimiento_lector` (plana)."""

    hecho: HechoId
    desde_capitulo: CapituloNum
    cita: str | None = None


class Relacion(Modelo):
    """Arista de la evolución; `intensidad` es cuantitativa y no es la `tension` del canon."""

    de: PersonajeId
    a: PersonajeId
    tipo: str
    intensidad: float = Field(ge=0, le=1)
    desde: CapituloNum


class Objeto(Modelo):
    id: ObjetoId
    poseedor: PersonajeId | None
    # Obligatorio aunque admita null: un objeto en manos de alguien no tiene lugar fijo, y eso
    # no es lo mismo que no saber dónde está.
    ubicacion: EscenarioId | None
    capitulo_intro: CapituloNum
    relevancia: Nivel


class Hecho(Modelo):
    id: HechoId
    texto: str
    capitulo: CapituloNum
    cita: str


class Hilo(Modelo):
    id: HiloId
    estado: Literal["abierto", "cerrado"]
    abierto_en: CapituloNum
    cerrado_en: CapituloNum | None = None
    descripcion: str

    @model_validator(mode="after")
    def _cierre_coherente(self) -> Self:
        if (self.estado == "cerrado") != (self.cerrado_en is not None):
            raise ValueError(f"{self.id}: un hilo cerrado lleva cerrado_en y uno abierto no")
        if self.cerrado_en is not None and self.cerrado_en < self.abierto_en:
            raise ValueError(f"{self.id}: cerrado_en anterior a abierto_en")
        return self


class EstadoPista(Modelo):
    estado: EstadoDePista
    plantada_en: CapituloNum | None
    pagada_en: CapituloNum | None


class Metricas(Modelo):
    palabras_totales: int = Field(ge=0)
    desviacion_vs_plan: float = Field(allow_inf_nan=False)  # fracción con signo, no porcentaje


class Estado(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    cursor: Cursor
    linea_temporal: ColeccionAppendOnly[EntradaTemporal] = ColeccionAppendOnly()
    personajes: dict[PersonajeId, EstadoPersonaje] = {}
    conocimiento: dict[PersonajeId, ColeccionAppendOnly[EntradaConocimiento]] = {}
    relaciones: list[Relacion] = []
    objetos: list[Objeto] = []
    libro_de_hechos: ColeccionAppendOnly[Hecho] = ColeccionAppendOnly()
    hilos: list[Hilo] = []
    pistas: dict[PistaId, EstadoPista] = {}
    conocimiento_lector: ColeccionAppendOnly[EntradaConocimiento] = ColeccionAppendOnly()
    # El índice es el capítulo; no lleva número dentro. La puntúa el lector-suspense y la registra
    # aplicar-delta, una entrada por capítulo; null es un hueco (sin puntuación), no se interpola.
    tension_real: ColeccionAppendOnly[Tension | None] = ColeccionAppendOnly()
    metricas: Metricas = Metricas(palabras_totales=0, desviacion_vs_plan=0.0)

    @field_validator("conocimiento")
    @classmethod
    def _sin_personajes_vacios(
        cls, valor: dict[str, ColeccionAppendOnly[EntradaConocimiento]]
    ) -> dict[str, ColeccionAppendOnly[EntradaConocimiento]]:
        # Un personaje que no sabe nada no tiene filas: {per-a: []} y {} son el mismo estado.
        return {personaje: c for personaje, c in valor.items() if len(c)}
