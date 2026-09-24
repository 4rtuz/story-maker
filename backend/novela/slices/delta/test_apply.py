import sqlite3
from collections.abc import Iterable

from hypothesis import given, settings
from hypothesis import strategies as st

from novela.dominio.estado import Aparicion, Cursor, Delta, Estado
from novela.dominio.plan import FichaCapitulo
from novela.plataforma import estado_db
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


def _delta(n: int, **secciones: object) -> Delta:
    resumen = {"linea": "l", "parrafo": "p", "escena": {f"esc-{n:02d}-1": "e"}}
    return Delta.model_validate({"capitulo": n, "resumen": resumen, **secciones})


def _derivados(
    delta: Delta, plantar: list[str], pagar: list[str], **extra: object
) -> apply.Derivados:
    fm = estrategias.frontmatter_de(delta).model_copy(
        update={"pistas_plantadas": plantar, "pistas_pagadas": pagar}
    )
    datos = {"pago_previsto": {"pis-001": 3, "pis-002": 2, "pis-003": 1}, "tension": 5} | extra
    return apply.Derivados(
        frontmatter=fm,
        palabras_totales=int(datos.pop("palabras", 1)),  # type: ignore[call-overload]
        palabras_objetivo=int(datos.pop("objetivo", 3)),  # type: ignore[call-overload]
        **datos,  # type: ignore[arg-type]
    )


def test_dos_capitulos_seguidos() -> None:
    """Casos fijos para la mutación: la propiedad no garantiza generar cada rama."""
    persona = {
        "ubicacion": None,
        "estado_fisico": "f",
        "estado_emocional": "e",
        "condicion": "viva",
        "objetivo_activo": "o",
        "ultima_aparicion": 1,
    }
    objeto = {"poseedor": None, "ubicacion": None, "capitulo_intro": 1, "relevancia": "alta"}
    uno = _delta(
        1,
        personajes={"per-a": persona, "per-b": persona},
        objetos=[objeto | {"id": "obj-001"}, objeto | {"id": "obj-002"}],
        relaciones=[
            {"de": "per-a", "a": "per-b", "tipo": "t", "intensidad": 0.1, "desde": 1},
            {"de": "per-b", "a": "per-a", "tipo": "t", "intensidad": 0.2, "desde": 1},
        ],
        hilos=[
            {"id": "hil-001", "estado": "abierto", "abierto_en": 1, "descripcion": "uno"},
            {"id": "hil-002", "estado": "abierto", "abierto_en": 1, "descripcion": "dos"},
        ],
        libro_de_hechos=[{"id": "hec-001", "texto": "t", "capitulo": 1, "cita": "c"}],
    )
    inicial = Estado(cursor=Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=2))
    e1 = apply.aplicar(inicial, uno, _derivados(uno, ["pis-001", "pis-002"], ["pis-003"]))
    assert [h.id for h in e1.libro_de_hechos] == ["hec-001"]  # las altas nuevas entran
    assert e1.cursor.intento == 2  # mismo capítulo: el intento se conserva
    assert e1.metricas.desviacion_vs_plan == -0.6667
    dos = _delta(
        2,
        personajes={"per-b": persona | {"estado_fisico": "herido"}},
        objetos=[objeto | {"id": "obj-002", "relevancia": "baja"}],
        relaciones=[{"de": "per-a", "a": "per-b", "tipo": "t", "intensidad": 0.9, "desde": 1}],
        hilos=[
            {
                "id": "hil-002",
                "estado": "cerrado",
                "abierto_en": 1,
                "cerrado_en": 2,
                "descripcion": "d",
            }
        ],
    )
    e2 = apply.aplicar(e1, dos, _derivados(dos, [], [], objetivo=0))
    assert e2.cursor.intento == 1  # capítulo nuevo: el intento vuelve a 1
    assert set(e2.personajes) == {"per-a", "per-b"}
    assert e2.personajes["per-b"].estado_fisico == "herido"
    assert [(o.id, o.relevancia) for o in e2.objetos] == [("obj-001", "alta"), ("obj-002", "baja")]
    assert [r.intensidad for r in e2.relaciones] == [0.9, 0.2]
    assert [(h.id, h.estado) for h in e2.hilos] == [("hil-001", "abierto"), ("hil-002", "cerrado")]
    assert e2.pistas["pis-003"].pagada_en == 1  # pagada en el 1, sigue pagada
    # La pista plantada en el 1 sigue plantada en el 2; la que se paga en el 2 según el plan y
    # no se paga, es huérfana justo en su capítulo previsto.
    assert (e2.pistas["pis-001"].estado, e2.pistas["pis-001"].plantada_en) == ("plantada", 1)
    assert (e2.pistas["pis-002"].estado, e2.pistas["pis-002"].plantada_en) == ("huerfana", 1)
    assert e2.metricas.desviacion_vs_plan == 0.0  # sin objetivo no hay desviación
    assert e2.tension_real.entradas == (5, 5)


def _registrar_en_memoria(*tandas: Iterable[Aparicion]) -> list[Aparicion]:
    """La tabla real: el INSERT OR IGNORE de la base es lo que acumula."""
    conn = sqlite3.connect(":memory:", isolation_level=None)
    estado_db.inicializar(conn)
    for tanda in tandas:
        with estado_db.transaccion(conn):
            estado_db.registrar_apariciones(conn, tanda)
    return estado_db.apariciones(conn, 999)


@settings(max_examples=200)
@given(st.data())
def test_apariciones_property(datos: st.DataObject) -> None:
    """CA-20 (RF-19, RF-20), VER-7: registrar dos veces el mismo capítulo es registrarlo una; el
    pov está siempre; los capítulos anteriores no cambian."""
    n = datos.draw(st.integers(2, 30))
    delta = datos.draw(estrategias.deltas(capitulo=n))
    ficha = datos.draw(estrategias.fichas_de(n))
    declaradas = datos.draw(st.lists(st.sampled_from([e.id for e in ficha.escenas]), min_size=1))
    fm = estrategias.frontmatter_de(delta).model_copy(
        update={"pov": ficha.pov, "escenas": declaradas}
    )
    anteriores = datos.draw(
        st.lists(
            st.builds(
                Aparicion,
                entidad=estrategias.personaje_id,
                tipo=st.just("personaje"),
                capitulo=st.integers(1, n - 1),
            ),
            unique_by=lambda a: (a.entidad, a.capitulo),
        )
    )
    filas = apply.apariciones(n, fm, ficha, delta)
    assert len({f.entidad for f in filas}) == len(filas)  # sin duplicados
    assert filas[0].entidad == fm.pov and all(f.capitulo == n for f in filas)
    una = _registrar_en_memoria(anteriores, filas)
    assert _registrar_en_memoria(anteriores, filas, filas) == una
    assert [a for a in una if a.capitulo < n] == sorted(
        anteriores, key=lambda a: (a.entidad, a.capitulo)
    )


def _aparicion_persona(ubicacion: str | None, ultima: int) -> dict[str, object]:
    return {
        "ubicacion": ubicacion,
        "estado_fisico": "f",
        "estado_emocional": "e",
        "condicion": "viva",
        "objetivo_activo": "o",
        "ultima_aparicion": ultima,
    }


def test_apariciones_en_orden() -> None:
    """VER-7 y spec §9: pov, personajes y lugar de cada escena declarada, y lo del delta de este
    capítulo con su ubicación. La escena no declarada, la que no está en la ficha, la ubicación
    nula y el personaje de otro capítulo no cuentan."""
    elena, tomas, ines, bruno = "per-elena", "per-tomas", "per-ines", "per-bruno"
    ficha = FichaCapitulo.model_validate(
        {
            "capitulo": 4,
            "pov": elena,
            "objetivo_dramatico": "o",
            "escenas": [
                {
                    "id": f"esc-04-{k}",
                    "lugar": lugar,
                    "tiempo_diegetico": "t",
                    "personajes": gente,
                    "beat": "b",
                    "conflicto": "c",
                }
                for k, lugar, gente in ((1, "esc-faro", [elena, tomas]), (2, "esc-cueva", [ines]))
            ],
            "gancho_final": "amenaza",
            "restriccion_de_apertura": "r",
        }
    )
    delta = _delta(
        4,
        personajes={
            tomas: _aparicion_persona("esc-puerto", 4),
            bruno: _aparicion_persona(None, 4),
            ines: _aparicion_persona("esc-cueva", 3),
        },
    )
    fm = estrategias.frontmatter_de(delta).model_copy(
        update={"pov": elena, "escenas": ["esc-04-1", "esc-04-9"]}
    )
    filas = apply.apariciones(4, fm, ficha, delta)
    assert [(f.entidad, f.tipo) for f in filas] == [
        (elena, "personaje"),
        (tomas, "personaje"),
        ("esc-faro", "escenario"),
        ("esc-puerto", "escenario"),
        (bruno, "personaje"),
    ]
