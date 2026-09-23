"""Recetas de briefing: el formato de architecture.md §6.2 como modelo, y su carga."""

import hashlib
from typing import Any, Literal

import yaml
from pydantic import Field, TypeAdapter, field_validator

from novela.dominio.base import Modelo
from novela.dominio.ids import Agente, CapituloNum
from novela.plataforma.workspace import CONFIG_DIR

RUTA = CONFIG_DIR / "recipes.yaml"
TECHO_TOKENS = 100_000  # ninguna invocación ensambla más (architecture.md §6.5)

Granularidad = Literal["parrafo", "una_linea"]
SelectorEstado = Literal[
    "personajes",
    "conocimiento",
    "hilos_abiertos",
    "objetos",
    "relaciones",
    "libro_de_hechos",
    "linea_temporal",
    "coartadas",  # de las fichas de canon, no de estado.db
    "pistas",
    "conocimiento_lector",
    "tension_real",
]


class Permanente(Modelo):
    permanente: list[str] = Field(min_length=1)  # rutas del workspace, sin .md; admite `dir/*`


class Personajes(Modelo):
    personajes: Literal["presentes_en_escena", "todos"]


class EstadoFiltrado(Modelo):
    estado: list[SelectorEstado] = Field(min_length=1)


class Inmediata(Modelo):
    inmediata: Literal["capitulo_anterior_completo"]


class Resumenes(Modelo):
    n: int = Field(default=3, ge=1)
    granularidad: Granularidad
    desde: CapituloNum = 1


class Reciente(Modelo):
    reciente: Resumenes


class Remota(Modelo):
    remota: Resumenes


class Plan(Modelo):
    plan: Literal["capitulo_actual"]


class Variacion(Modelo):
    variacion: Literal["restriccion_de_apertura"]


class Objetivo(Modelo):
    objetivo: Literal["capitulo_recien_escrito"]


Capa = (
    Permanente
    | Personajes
    | EstadoFiltrado
    | Inmediata
    | Reciente
    | Remota
    | Plan
    | Variacion
    | Objetivo
)


class Receta(Modelo):
    presupuesto_tokens: int = Field(gt=0, le=TECHO_TOKENS)
    capas: list[Capa] = Field(min_length=1)
    excluir: list[str] = []

    @field_validator("capas", mode="before")
    @classmethod
    def _un_par_por_capa(cls, capas: Any) -> Any:
        if isinstance(capas, list) and any(isinstance(c, dict) and len(c) != 1 for c in capas):
            raise ValueError("cada capa es un mapa de un solo par")
        return capas


_RECETAS = TypeAdapter(dict[Agente, Receta])


def validar(datos: Any) -> dict[Agente, Receta]:
    recetas = _RECETAS.validate_python(datos)
    faltan = sorted(set(Agente) - set(recetas))
    if faltan:
        _RECETAS.validate_python({**datos, **{a.value: "falta la receta" for a in faltan}})
    return recetas


def cargar() -> dict[Agente, Receta]:
    return validar(yaml.safe_load(RUTA.read_text(encoding="utf-8")))


def version() -> str:
    """El identificador de las recetas que se anota en el manifiesto: el hash del fichero."""
    return hashlib.sha256(RUTA.read_bytes()).hexdigest()
