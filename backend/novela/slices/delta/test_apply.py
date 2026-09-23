from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.estado import Cursor, Delta, Estado
from novela.slices.delta import apply
from tests import estrategias


@st.composite
def derivados(draw: st.DrawFn, delta: Delta) -> apply.Derivados:
    fm = estrategias.frontmatter_de(delta)
    pistas = draw(st.lists(estrategias.id_("pis"), max_size=4, unique=True))
    plantadas = draw(st.lists(st.sampled_from(pistas), unique=True)) if pistas else []
    pagadas = draw(st.lists(st.sampled_from(pistas), unique=True)) if pistas else []
    return apply.Derivados(
        frontmatter=fm.model_copy(
            update={"pistas_plantadas": plantadas, "pistas_pagadas": pagadas}
        ),
        pago_previsto={p: draw(st.none() | estrategias.capitulo) for p in pistas},
        tension=draw(st.none() | st.integers(1, 10)),
        palabras_totales=draw(st.integers(0, 10**5)),
        palabras_objetivo=draw(st.integers(0, 10**5)),
    )


@given(estrategias.estados, st.data())
def test_idempotencia_property(estado: Estado, datos: st.DataObject) -> None:
    """CA-20, validators.md §3.6: aplicar(aplicar(e, d), d) == aplicar(e, d). Reanudar repite el
    paso entero, y la reanudación es el caso normal en modo desatendido."""
    delta = datos.draw(
        estrategias.deltas(capitulo=datos.draw(st.integers(estado.cursor.capitulo, 30)))
    )
    d = datos.draw(derivados(delta))
    una = apply.aplicar(estado, delta, d)
    assert apply.aplicar(una, delta, d) == una


@given(estrategias.estados, st.data())
def test_append_only_solo_crecen(estado: Estado, datos: st.DataObject) -> None:
    delta = datos.draw(
        estrategias.deltas(capitulo=datos.draw(st.integers(estado.cursor.capitulo, 30)))
    )
    nuevo = apply.aplicar(estado, delta, datos.draw(derivados(delta)))
    for coleccion in ("linea_temporal", "libro_de_hechos", "conocimiento_lector", "tension_real"):
        antes = getattr(estado, coleccion).entradas
        assert getattr(nuevo, coleccion).entradas[: len(antes)] == antes, coleccion
    for personaje, entradas in estado.conocimiento.items():
        assert nuevo.conocimiento[personaje].entradas[: len(entradas)] == entradas.entradas
    assert len(nuevo.tension_real) >= delta.capitulo
    assert nuevo.cursor.capitulo == delta.capitulo


def test_pistas_derivadas_del_frontmatter() -> None:
    """pistas no viene en el delta: sale del frontmatter y del pago previsto en el canon."""
    delta = Delta.model_validate(
        {"capitulo": 3, "resumen": {"linea": "l", "parrafo": "p", "escena": {"esc-03-1": "e"}}}
    )
    fm = estrategias.frontmatter_de(delta).model_copy(
        update={"pistas_plantadas": ["pis-001", "pis-002"], "pistas_pagadas": ["pis-003"]}
    )
    d = apply.Derivados(
        frontmatter=fm,
        pago_previsto={"pis-001": 9, "pis-002": None, "pis-003": 3, "pis-004": 12},
        tension=7,
        palabras_totales=900,
        palabras_objetivo=1000,
    )
    inicial = Estado(cursor=Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=1))
    nuevo = apply.aplicar(inicial, delta, d)
    estados = {p: (e.estado, e.plantada_en, e.pagada_en) for p, e in nuevo.pistas.items()}
    assert estados == {
        "pis-001": ("plantada", 3, None),
        "pis-002": ("huerfana", 3, None),  # plantada y ningún capítulo prevé pagarla
        "pis-003": ("pagada", None, 3),
        "pis-004": ("pendiente", None, None),
    }
    assert nuevo.tension_real.entradas == (None, None, 7)  # huecos, no interpolación
    assert nuevo.metricas.desviacion_vs_plan == -0.1
