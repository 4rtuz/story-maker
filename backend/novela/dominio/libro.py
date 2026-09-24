"""El libro de la lectura web (docs/lectura-web.md): portada, índice y ficha, sin el cuerpo.

Es lo mismo que compone el PDF de la spec 0006, servido por `GET /novelas/{slug}/libro`. Del brief
solo sale la dedicatoria; el brief no se sirve (spec 0005, CA-29).
"""

from novela.dominio.base import Modelo
from novela.dominio.brief import Brief, Ocasion

# ponytail: dedicatoria derivada de ocasión y nombre; cuando `Brief` tenga su campo `dedicatoria`
# (spec 0006, T4.1) ese texto literal la sustituye.
_MOTIVO: dict[Ocasion, str] = {
    "hijo": "con todo el cariño",
    "pareja": "con todo mi amor",
    "boda": "en el día de su boda",
    "aniversario": "en nuestro aniversario",
    "jubilacion": "por su jubilación",
}


def dedicatoria(brief: Brief) -> str:
    return f"Para {brief.destinatario.nombre.valor}, {_MOTIVO[brief.ocasion]}."


class EntradaDeIndice(Modelo):
    capitulo: int
    titulo: str


class EntradaDeFicha(Modelo):
    id: str
    nombre: str
    detalle: str | None  # alias unidos por comas, o la descripción del lugar
    capitulos: list[int]  # ascendentes: un enlace por capítulo


class Libro(Modelo):
    titulo: str
    dedicatoria: str | None
    capitulos: list[EntradaDeIndice]  # solo los cerrados
    personajes: list[EntradaDeFicha]
    lugares: list[EntradaDeFicha]
