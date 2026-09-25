"""Ficha de personajes y lugares del libro (spec 0006, RF-26 a RF-30): función pura.

Recibe del canon solo nombre, alias y descripción, nunca el modelo entero: así ningún cambio aquí
puede volcar al libro un secreto, una coartada o un detalle sensorial (RF-28).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from novela.dominio.estado import Aparicion


@dataclass(frozen=True)
class EntradaFicha:
    id: str
    nombre: str
    detalle: str | None  # alias unidos por comas, o la descripción del lugar
    capitulos: tuple[int, ...]  # ascendentes: un enlace por capítulo


@dataclass(frozen=True)
class Ficha:
    personajes: tuple[EntradaFicha, ...]
    lugares: tuple[EntradaFicha, ...]


class SinCanon(ValueError):
    """Entidades con aparición y sin ficha en el canon. Salida 4."""

    def __init__(self, ids: tuple[str, ...]) -> None:
        super().__init__(f"sin ficha en el canon: {', '.join(ids)}")
        self.ids = ids


def construir(
    apariciones: Iterable[Aparicion],
    personajes: Mapping[str, tuple[str, tuple[str, ...]]],  # id → (nombre, alias)
    escenarios: Mapping[str, tuple[str, str | None]],  # id → (nombre, descripcion)
) -> Ficha:
    capitulos: dict[str, set[int]] = {}
    for a in apariciones:
        capitulos.setdefault(a.entidad, set()).add(a.capitulo)
    ausentes = tuple(sorted(e for e in capitulos if e.startswith("per-") and e not in personajes))
    if ausentes:
        raise SinCanon(ausentes)
    # Un lugar sin ficha (un id que el cronista inventó y la story bible, append-only, ya guarda)
    # sale con el nombre de su id y sin descripción: el nombre de un personaje ha de ser exacto,
    # el de un lugar no. `aplicar-delta` rechaza hoy esos ids (violaciones.py).
    escenarios = {
        **{
            e: (e.removeprefix("esc-").replace("-", " ").capitalize(), None)
            for e in capitulos
            if not e.startswith("per-")
        },
        **escenarios,
    }
    orden = sorted(capitulos, key=lambda e: (min(capitulos[e]), e))
    return Ficha(
        personajes=tuple(
            EntradaFicha(
                e,
                personajes[e][0],
                ", ".join(personajes[e][1]) or None,
                tuple(sorted(capitulos[e])),
            )
            for e in orden
            if e in personajes
        ),
        lugares=tuple(
            EntradaFicha(e, escenarios[e][0], escenarios[e][1], tuple(sorted(capitulos[e])))
            for e in orden
            if e in escenarios
        ),
    )
