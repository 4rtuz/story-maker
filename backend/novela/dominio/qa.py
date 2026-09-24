"""Informe de QA (architecture.md §7.3): un solo modelo para los cuatro productores —continuista,
editor-estilo, lector-suspense y el propio `novela validar`— y para `novela auditar`.

Es lo único que recibe el escritor en un reintento, así que es estructurado y el tipo de hallazgo
es un vocabulario cerrado: un hallazgo con tipo libre es uno que el reintento no sabe leer.
"""

from typing import Literal

from pydantic import Field

from novela.dominio.base import SCHEMA_VERSION, Modelo, Nivel, SchemaVersion
from novela.dominio.ids import CapituloNum, Sha256

Productor = Literal["validar", "continuista", "editor-estilo", "lector-suspense", "auditar"]
Veredicto = Literal["aprobado", "rechazado", "aprobado_con_reservas"]
TipoHallazgo = Literal[
    # novela validar
    "frontmatter_invalido",
    "longitud_fuera_de_rango",
    "pista_ausente",
    "hilo_cerrado_sin_abrir",
    "id_inexistente",
    "nombre_mal_escrito",
    # novela validar, con un cambio en curso (spec 0007, RF-31)
    "regeneracion_altera_contrato",
    # novela validar (frontmatter) y novela checkpoint (el resto de artefactos)
    "esquema_invalido",
    # continuista
    "contradiccion_hecho",
    "contradiccion_temporal",
    "contradiccion_personaje",
    "contradiccion_canon",
    # editor-estilo
    "prohibicion_estilo",
    "desviacion_ritmo",
    "voz_de_personaje",
    # lector-suspense
    "tension_insuficiente",
    "fair_play",
    "previsibilidad",
    "gancho_debil",
    # novela auditar
    "pista_huerfana",
    "hilo_sin_cerrar",
    "pista_falsa_sin_desmontar",
    "revelacion_sin_pista",
    "elemento_sin_cubrir",
]
# Lo que puntúa el lector-suspense; checkpoint lo emite como scores (RF-21).
Puntuacion = Literal["tension", "fair_play", "coherencia", "previsibilidad"]


class Hallazgo(Modelo):
    tipo: TipoHallazgo
    gravedad: Nivel
    referencia: str | None = None  # id afectado: hec-014, pis-007…
    ubicacion: str | None = None
    descripcion: str
    correccion_sugerida: str | None = None


class InformeQA(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: CapituloNum
    agente: Productor
    veredicto: Veredicto
    hallazgos: list[Hallazgo] = []
    puntuaciones: dict[Puntuacion, float] = Field(default={})
    # Solo lo escribe el CLI: un modelo no calcula un sha256, lo inventaría.
    capitulo_sha256: Sha256 | None = None
