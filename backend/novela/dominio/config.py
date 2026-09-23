"""Rama 1: configuración de ejecución (definitions.md §1). Todo INMUTABLE tras el arranque."""

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.ids import Agente

Subgenero = Literal["thriller_psicologico", "noir", "domestic_suspense", "procedural"]
PuntoDeVista = Literal["primera_persona", "tercera_limitada", "multiple", "narrador_no_fiable"]
TiempoVerbal = Literal["presente", "pasado"]
ModeloDeAgente = Literal["opus", "sonnet", "haiku", "inherit"]

# Rango derivado alrededor del objetivo. El gate de longitud compara contra min y max, nunca
# contra el objetivo: exigir un número exacto degrada la prosa.
_TOLERANCIA = 0.2


class PalabrasPorCapitulo(Modelo):
    objetivo: int = Field(gt=0)
    min: int = Field(gt=0)
    max: int = Field(gt=0)

    @model_validator(mode="after")
    def _ordenada(self) -> Self:
        if not self.min <= self.objetivo <= self.max:
            raise ValueError("palabras_por_capitulo exige min <= objetivo <= max")
        return self


class ParametrosObra(Modelo):
    longitud_total_palabras: int = Field(gt=0)
    num_capitulos: int = Field(ge=1, le=999)
    palabras_por_capitulo: PalabrasPorCapitulo
    subgenero: Subgenero
    punto_de_vista: PuntoDeVista
    tiempo_verbal: TiempoVerbal
    idioma: str = "es"
    restricciones_contenido: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _derivar_terna(cls, datos: Any) -> Any:
        if not isinstance(datos, dict) or datos.get("palabras_por_capitulo") is not None:
            return datos
        total, num = datos.get("longitud_total_palabras"), datos.get("num_capitulos")
        if not isinstance(total, int) or not isinstance(num, int) or num < 1:
            raise ValueError(
                "palabras_por_capitulo no se puede derivar: fija longitud_total_palabras y "
                "num_capitulos, o la terna explícita (si falta uno, lo propone el trazador)"
            )
        objetivo = total // num
        terna = {
            "objetivo": objetivo,
            "min": round(objetivo * (1 - _TOLERANCIA)),
            "max": round(objetivo * (1 + _TOLERANCIA)),
        }
        return {**datos, "palabras_por_capitulo": terna}


class Presupuesto(Modelo):
    requests_dia: int = Field(gt=0)
    tokens_por_llamada: int = Field(gt=0)
    tokens_contexto_por_agente: int = Field(gt=0)


class PoliticaReintentos(Modelo):
    # Tres intentos por gate: el fallo del tercero escribe intervencion.md y para.
    max_intentos: int = Field(default=3, ge=1, le=3)
    entrada_del_reintento: Literal["informe_qa"] = "informe_qa"


class ParametrosSistema(Modelo):
    modelo_por_agente: dict[Agente, ModeloDeAgente]
    # Inerte: la temperatura exige API directa y la suscripción no la da (definitions.md §1).
    # Se modela porque el campo existe en la ontología; nada lo consume.
    temperatura_por_agente: dict[Agente, float] = {}
    presupuesto: Presupuesto
    politica_reintentos: PoliticaReintentos = PoliticaReintentos()
    politica_checkpoint: Literal["por_capitulo"] = "por_capitulo"


class Config(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    idea_semilla: str = Field(min_length=1)
    parametros_obra: ParametrosObra
    parametros_sistema: ParametrosSistema
