"""Rama 3: plan (definitions.md §3). Lo que debería pasar.

`plan/escaleta.md` lleva la escaleta macro en su frontmatter y `plan/capitulos/NN.md` la ficha de
cada capítulo, que es el prompt de trabajo del escritor. Ojo: el plan dice `pistas_a_plantar` y el
capítulo escrito `pistas_plantadas`. Son contratos distintos, de entrada y de salida.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, ValidationInfo, model_validator

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.ids import CapituloNum, EscenaId, EscenarioId, HiloId, PersonajeId, PistaId

# Se especifica el tipo de cliffhanger, no su texto, para no encorsetar al escritor.
GanchoFinal = Literal[
    "pregunta_abierta", "revelacion", "amenaza", "decision_pendiente", "giro", "calma_inquietante"
]
Tension = Annotated[int, Field(ge=1, le=10)]


class Acto(Modelo):
    numero: int = Field(ge=1)
    funcion_dramatica: str
    capitulos: list[CapituloNum] = Field(min_length=1)


class PuntosDeGiro(Modelo):
    """Claves fijas, cada una anclada a un capítulo. No es una lista."""

    detonante: CapituloNum
    punto_medio: CapituloNum
    crisis: CapituloNum
    climax: CapituloNum
    resolucion: CapituloNum


class Escaleta(Modelo):
    """Se valida con `context={"num_capitulos": N}`: la curva tiene un valor por capítulo."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    actos: list[Acto] = Field(min_length=1)
    puntos_de_giro: PuntosDeGiro
    curva_tension_objetivo: list[Tension]

    @model_validator(mode="after")
    def _cuadra_con_la_obra(self, info: ValidationInfo) -> Self:
        num = (info.context or {}).get("num_capitulos")
        if not isinstance(num, int):
            raise ValueError("la escaleta se valida con num_capitulos en el contexto")
        if len(self.curva_tension_objetivo) != num:
            raise ValueError(
                f"curva_tension_objetivo tiene {len(self.curva_tension_objetivo)} valores y "
                f"num_capitulos es {num}"
            )
        for nombre, cap in self.puntos_de_giro:
            if cap > num:
                raise ValueError(f"puntos_de_giro.{nombre} = {cap} pasa de num_capitulos")
        return self


class EscenaPlan(Modelo):
    id: EscenaId
    lugar: EscenarioId
    tiempo_diegetico: str
    personajes: list[PersonajeId] = Field(min_length=1)
    # Quién habla. Es lo que usa el paso 3 de degradación del briefing (architecture.md §6.5).
    dialogo: list[PersonajeId] = []
    beat: str
    conflicto: str

    @model_validator(mode="after")
    def _hablan_los_presentes(self) -> Self:
        ausentes = sorted(set(self.dialogo) - set(self.personajes))
        if ausentes:
            raise ValueError(f"{self.id}: hablan personajes que no están: {', '.join(ausentes)}")
        return self


class FichaCapitulo(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: CapituloNum
    pov: PersonajeId
    objetivo_dramatico: str
    escenas: list[EscenaPlan] = Field(min_length=1)
    # Referencias a canon.misterio.pistas: el escritor recibe el contenido de estas y de nada más.
    pistas_a_plantar: list[PistaId] = []
    pistas_a_pagar: list[PistaId] = []
    hilos_que_abre: list[HiloId] = []
    hilos_que_cierra: list[HiloId] = []
    gancho_final: GanchoFinal
    # Distinta por capítulo: sin temperatura, es lo que evita que 24 capítulos abran igual.
    restriccion_de_apertura: str
    dependencias: list[CapituloNum] = []

    @model_validator(mode="after")
    def _escenas_propias(self) -> Self:
        for escena in self.escenas:
            if int(escena.id.split("-")[1]) != self.capitulo:
                raise ValueError(f"{escena.id} no es una escena del capítulo {self.capitulo}")
        return self
