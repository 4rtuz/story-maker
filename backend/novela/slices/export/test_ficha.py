import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from novela.dominio.estado import Aparicion
from novela.slices.export import ficha

ids_personaje = st.integers(0, 14).map(lambda i: f"per-p{i:02d}")
ids_escenario = st.integers(0, 14).map(lambda i: f"esc-e{i:02d}")


def _aparicion(entidad: str, capitulo: int) -> Aparicion:
    tipo = "personaje" if entidad.startswith("per-") else "escenario"
    return Aparicion(entidad=entidad, tipo=tipo, capitulo=capitulo)


def _canon(
    entidades: set[str],
) -> tuple[dict[str, tuple[str, tuple[str, ...]]], dict[str, tuple[str, str]]]:
    alias: tuple[str, ...] = ("alias",)
    personajes = {e: (f"Nombre {e}", alias) for e in entidades if e.startswith("per-")}
    escenarios = {e: (f"Lugar {e}", f"Descripción {e}") for e in entidades if e.startswith("esc-")}
    return personajes, escenarios


@settings(max_examples=200)
@given(
    st.lists(
        st.tuples(ids_personaje | ids_escenario, st.integers(1, 20)),
        min_size=1,
        max_size=60,
    )
)
def test_un_enlace_por_aparicion(pares: list[tuple[str, int]]) -> None:
    """CA-27 (RF-26, RF-27), parte pura: un capítulo por par distinto, ascendentes, y solo las
    entidades con alguna aparición."""
    filas = [_aparicion(e, c) for e, c in pares]
    personajes, escenarios = _canon({e for e, _ in pares})
    personajes["per-nunca"] = ("Nadie", ())  # canon sin aparición: no sale
    f = ficha.construir(filas, personajes, escenarios)
    entradas = [*f.personajes, *f.lugares]
    assert sum(len(e.capitulos) for e in entradas) == len(set(pares))
    assert all(list(e.capitulos) == sorted(set(e.capitulos)) for e in entradas)
    assert {e.id for e in entradas} == {e for e, _ in pares}
    assert all(e.id.startswith("per-") for e in f.personajes)
    assert all(e.id.startswith("esc-") for e in f.lugares)


def test_orden() -> None:
    """CA-30 (RF-30), VAL-32: personajes y luego lugares, cada grupo por primer capítulo y id."""
    pares = [("per-b", 1), ("per-a", 2), ("esc-z", 1), ("per-c", 2), ("esc-a", 3), ("per-a", 5)]
    personajes, escenarios = _canon({e for e, _ in pares})
    f = ficha.construir([_aparicion(e, c) for e, c in pares], personajes, escenarios)
    assert [e.id for e in f.personajes] == ["per-b", "per-a", "per-c"]
    assert [e.id for e in f.lugares] == ["esc-z", "esc-a"]
    assert f.personajes[1].capitulos == (2, 5)


def test_detalle() -> None:
    """RF-26: de un personaje, sus alias; de un lugar, su descripción; nada más del canon."""
    f = ficha.construir(
        [_aparicion("per-a", 1), _aparicion("per-b", 1), _aparicion("esc-a", 1)],
        {"per-a": ("Ana", ("la farera", "Anita")), "per-b": ("Beto", ())},
        {"esc-a": ("El faro", "Un faro en el cabo")},
    )
    assert [(e.nombre, e.detalle) for e in f.personajes] == [
        ("Ana", "la farera, Anita"),
        ("Beto", None),
    ]
    assert [(e.nombre, e.detalle) for e in f.lugares] == [("El faro", "Un faro en el cabo")]


def test_ids_sin_canon() -> None:
    """RF-29, VER-14: la excepción nombra todos los ids sin canon."""
    filas = [
        _aparicion("per-ines-mar", 1),
        _aparicion("per-tomas-reyes", 2),
        _aparicion("esc-x", 1),
    ]
    with pytest.raises(ficha.SinCanon) as exc:
        ficha.construir(filas, {}, {"esc-x": ("X", "x")})
    assert exc.value.ids == ("per-ines-mar", "per-tomas-reyes")
    assert "per-ines-mar" in str(exc.value) and "per-tomas-reyes" in str(exc.value)
