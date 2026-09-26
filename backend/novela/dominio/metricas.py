"""`metricas.json`: el informe de `novela costes <slug> --guardar`, servido por `GET
/novelas/{slug}/metricas` (spec 0015 §5.2). La forma es la de `costes.agregar` más la hora."""

from datetime import datetime

from novela.dominio.base import Modelo


class Consumo(Modelo):
    llamadas: int
    tokens_entrada: int  # incluye la caché leída
    tokens_salida: int
    tokens_cache_lectura: int
    coste_usd: float  # el `totalCost` que calcula Langfuse, sumado
    latencia_media_llamada_s: float


class ConsumoDePaso(Consumo):
    paso: str  # `nueva`, `capitulo NN`, `auditoria` o `sesión <id>`
    latencia_s: float  # tiempo de pared de las trazas del paso, sin los huecos
    roles: dict[str, Consumo]


class TotalDeCostes(Consumo):
    latencia_s: float  # la suma de la de sus pasos


class InformeDeCostes(Modelo):
    slug: str
    sesion: str  # la sesión de Langfuse de la novela
    generado: datetime
    pasos: list[ConsumoDePaso]
    total: TotalDeCostes
