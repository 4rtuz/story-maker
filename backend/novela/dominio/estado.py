"""Rama 4: estado narrativo (definitions.md §4). Lo que ya pasó.

Es la vista serializada de `architecture.md` §7.1: lo que devuelven `novela estado --json` y
`GET /novelas/{slug}/estado`, y lo que valida `state.schema.json`. En disco vive en `estado.db`,
una tabla por colección. Los nombres son los de §7.1, sin alias.

Las cinco append-only —`linea_temporal`, `conocimiento`, `libro_de_hechos`, `conocimiento_lector`
y `tension_real`— son `ColeccionAppendOnly`: el tipo evita escribir el bug y el trigger lo caza.
`pistas` y `metricas` son derivadas: se calculan al aplicar el delta, no vienen en él.
"""

from typing import Annotated, Literal, Self, get_args

from pydantic import Field, StringConstraints, field_validator, model_validator

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
    Slug,
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


class CursorDeNovela(Modelo):
    """Una fila de `GET /novelas`: dónde va cada novela del directorio de workspaces."""

    slug: Slug
    cursor: Cursor


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


Via = Literal["origen", "conocimiento", "lector", "cita"]


class UsoDeHecho(Modelo):
    """Una fila de `usos_de_hecho`: el capítulo `capitulo` usa el hecho `hecho` por `via`. Es un
    índice derivado de los deltas y no forma parte de `Estado` (spec 0007, D19)."""

    hecho: HechoId
    capitulo: CapituloNum
    via: Via


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


class Resumen(Modelo):
    """Las tres granularidades de un capítulo, de la más corta a la más fina. `escena` va por id
    de escena y no como prosa: es lo que deja abiertas las capas exacta y léxica del índice
    recuperable (architecture.md §12.4) sin reprocesar capítulos."""

    linea: str = Field(min_length=1)
    parrafo: str = Field(min_length=1)
    escena: dict[EscenaId, str] = Field(min_length=1)


class UsoCitado(Modelo):
    """Un hecho ya afirmado que el capítulo usa sin enseñarlo de nuevo, con la cita literal que
    lo prueba. Es lo que deja rastro en `usos_de_hecho` por la vía `cita` (spec 0007, D4)."""

    hecho: HechoId
    cita: str = Field(min_length=1)


# docs/formal/lean.md: el capítulo y un correlativo, como las escenas.
EventoId = Annotated[str, StringConstraints(pattern=r"^evt-[0-9]{2,3}-[0-9]+$")]


class EventoCronologia(Modelo):
    """Un evento datado: lo que alimenta `novela verificar-lean`. `momento` son minutos desde el
    día 1 a las 00:00; `excluye`, quién sale de la historia en él (muerte o partida definitiva);
    `edades`, las que el texto declara; `tras`, los eventos que el texto sitúa antes."""

    id: EventoId
    momento: int = Field(ge=0)
    duracion_min: int = Field(default=0, ge=0)
    lugar: EscenarioId
    personajes: list[PersonajeId] = []
    excluye: list[PersonajeId] = []
    edades: dict[PersonajeId, int] = {}
    tras: list[EventoId] = []
    cita: str | None = None

    @model_validator(mode="after")
    def _edades_de_presentes(self) -> Self:
        if ausentes := set(self.edades) - set(self.personajes):
            raise ValueError(f"{self.id}: edades de quien no está: {sorted(ausentes)}")
        return self


class Delta(Modelo):
    """`estado/deltas/NN.json`: la salida del cronista y la única entrada de `aplicar-delta`.

    Las append-only traen solo altas; las mutables, el estado nuevo de lo que el capítulo toca.
    `hilos` lleva solo los que se abren o se cierran en el capítulo, y tiene que casar con el
    frontmatter. No vienen `pistas` ni `metricas`, que se derivan, ni `tension_real`, que es
    del lector-suspense, ni el cursor, que avanza `aplicar-delta` desde `capitulo`.
    """

    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: CapituloNum
    linea_temporal: list[EntradaTemporal] = []
    personajes: dict[PersonajeId, EstadoPersonaje] = {}
    conocimiento: dict[PersonajeId, list[EntradaConocimiento]] = {}
    conocimiento_lector: list[EntradaConocimiento] = []
    relaciones: list[Relacion] = []
    objetos: list[Objeto] = []
    libro_de_hechos: list[Hecho] = []
    hechos_usados: list[UsoCitado] = []
    hilos: list[Hilo] = []
    resumen: Resumen
    cronologia: list[EventoCronologia] = []


class Aparicion(Modelo):
    """Una fila de la tabla `apariciones` de `estado.db`: la entidad sale en ese capítulo. Es un
    índice derivado para la ficha del libro, fuera de `Estado` y de `Delta` (spec 0006)."""

    entidad: PersonajeId | EscenarioId
    tipo: Literal["personaje", "escenario"]
    capitulo: CapituloNum

    @model_validator(mode="after")
    def _tipo_del_prefijo(self) -> Self:
        if self.entidad.startswith("per-") != (self.tipo == "personaje"):
            raise ValueError(f"{self.entidad} no es de tipo {self.tipo}")
        return self


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
