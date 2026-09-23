from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.config import PalabrasPorCapitulo
from novela.dominio.plan import FichaCapitulo
from novela.slices.validacion import gates

PISTAS = [f"pis-{i:03d}" for i in range(1, 7)]
HILOS = [f"hil-{i:03d}" for i in range(1, 7)]


def _ficha(plantar: list[str], pagar: list[str]) -> FichaCapitulo:
    return FichaCapitulo.model_validate(
        {
            "capitulo": 5,
            "pov": "per-elena",
            "objetivo_dramatico": "o",
            "escenas": [
                {
                    "id": "esc-05-1",
                    "lugar": "esc-faro",
                    "tiempo_diegetico": "t",
                    "personajes": ["per-elena"],
                    "beat": "b",
                    "conflicto": "c",
                }
            ],
            "pistas_a_plantar": plantar,
            "pistas_a_pagar": pagar,
            "gancho_final": "amenaza",
            "restriccion_de_apertura": "r",
        }
    )


Caso = tuple[dict[str, Any], str, gates.Contexto]


def _caso(
    rango: tuple[int, int, int] = (10, 12, 20),
    plantar: tuple[list[str], list[str]] = (["pis-001"], ["pis-004"]),
    hilos: tuple[list[str], list[str], list[str]] = (["hil-001"], ["hil-004"], ["hil-001"]),
    palabras: int = 12,
) -> Caso:
    minimo, objetivo, maximo = rango
    (plantadas, pagadas), (abiertos_antes, abre, cierra) = plantar, hilos
    meta = {
        "capitulo": 5,
        "titulo": "t",
        "pov": "per-elena",
        "palabras": 0,
        "escenas": ["esc-05-1"],
        "pistas_plantadas": plantadas,
        "pistas_pagadas": pagadas,
        "hilos_abiertos": abre,
        "hilos_cerrados": cierra,
        "version_canon": 1,
        "version_plan": 1,
        "run_id": "r-20260101-0900",
    }
    contexto = gates.Contexto(
        capitulo=5,
        palabras=PalabrasPorCapitulo(objetivo=objetivo, min=minimo, max=maximo),
        ficha=_ficha(plantadas, pagadas),
        personajes=frozenset({"per-elena"}),
        pistas=frozenset(PISTAS),
        hilos_abiertos=frozenset(abiertos_antes),
    )
    return meta, "palabra " * palabras, contexto


@st.composite
def capitulos_validos(draw: st.DrawFn) -> Caso:
    minimo = draw(st.integers(5, 200))
    maximo = minimo + draw(st.integers(0, 100))
    objetivo = draw(st.integers(minimo, maximo))
    plantar = draw(st.lists(st.sampled_from(PISTAS[:3]), unique=True))
    pagar = draw(st.lists(st.sampled_from(PISTAS[3:]), unique=True))
    abiertos_antes = draw(st.lists(st.sampled_from(HILOS[:3]), unique=True))
    abre = draw(st.lists(st.sampled_from(HILOS[3:]), unique=True))
    cerrables = abiertos_antes + abre
    cierra = draw(st.lists(st.sampled_from(cerrables), unique=True)) if cerrables else []
    palabras = draw(st.integers(minimo, maximo))
    return _caso(
        (minimo, objetivo, maximo), (plantar, pagar), (abiertos_antes, abre, cierra), palabras
    )


@given(capitulos_validos(), st.sampled_from(["pista", "hilo", "corto", "largo", "nada"]), st.data())
def test_gates_property(caso: Caso, defecto: str, datos: st.DataObject) -> None:
    """CA-14: una pista del plan ausente, un hilo cerrado sin abrir o unas palabras fuera de
    rango nunca pasan; el mismo capítulo sin el defecto, sí."""
    meta, cuerpo, ctx = caso
    esperado = None
    if defecto == "pista" and (meta["pistas_plantadas"] or meta["pistas_pagadas"]):
        campo = "pistas_plantadas" if meta["pistas_plantadas"] else "pistas_pagadas"
        meta = {**meta, campo: meta[campo][1:]}
        esperado = "pista_ausente"
    elif defecto == "hilo":
        meta = {**meta, "hilos_cerrados": [*meta["hilos_cerrados"], "hil-999"]}
        esperado = "hilo_cerrado_sin_abrir"
    elif defecto == "corto":
        cuerpo = "palabra " * datos.draw(st.integers(0, ctx.palabras.min - 1))
        esperado = "longitud_fuera_de_rango"
    elif defecto == "largo":
        cuerpo = "palabra " * datos.draw(st.integers(ctx.palabras.max + 1, ctx.palabras.max + 50))
        esperado = "longitud_fuera_de_rango"
    tipos = [h.tipo for h in gates.validar(meta, cuerpo, ctx)]
    assert tipos == [] if esperado is None else esperado in tipos


def test_rango_es_cerrado_en_los_dos_extremos() -> None:
    """Para la mutación (CA-15): min y max pasan; min-1 y max+1 no. Contra el objetivo, nunca."""
    meta, _, ctx = _caso(rango=(10, 12, 20))
    for palabras, pasa in ((9, False), (10, True), (12, True), (20, True), (21, False)):
        tipos = [h.tipo for h in gates.validar(meta, "x " * palabras, ctx)]
        assert ("longitud_fuera_de_rango" not in tipos) is pasa, palabras


def test_frontmatter_invalido_para_en_el_primer_gate() -> None:
    meta, cuerpo, ctx = _caso()
    hallazgos = gates.validar({**meta, "pov": "Elena"}, cuerpo, ctx)
    assert [h.tipo for h in hallazgos] == ["frontmatter_invalido"]
    assert gates.validar(None, cuerpo, ctx)[0].tipo == "frontmatter_invalido"
    ajeno = gates.validar({**meta, "capitulo": 6}, cuerpo, ctx)
    assert [h.tipo for h in ajeno] == ["frontmatter_invalido"]


def test_ids_citados_existen() -> None:
    meta, cuerpo, ctx = _caso()
    hallazgos = gates.validar(
        {**meta, "pov": "per-nadie", "escenas": ["esc-05-9"], "pistas_plantadas": ["pis-900"]},
        cuerpo,
        ctx,
    )
    referencias = {h.referencia for h in hallazgos if h.tipo == "id_inexistente"}
    assert {"per-nadie", "esc-05-9", "pis-900"} <= referencias


def test_casos_fijos_de_cada_gate() -> None:
    """Casos deterministas: la propiedad de arriba es aleatoria y una ejecución de mutmut puede no
    generar el ejemplo que mata a un mutante. Estos corren siempre."""
    meta, cuerpo, ctx = _caso()
    assert gates.validar(meta, cuerpo, ctx) == []

    sin_plantar = gates.validar({**meta, "pistas_plantadas": []}, cuerpo, ctx)
    assert [(h.tipo, h.referencia) for h in sin_plantar] == [("pista_ausente", "pis-001")]
    sin_pagar = gates.validar({**meta, "pistas_pagadas": []}, cuerpo, ctx)
    assert [(h.tipo, h.referencia) for h in sin_pagar] == [("pista_ausente", "pis-004")]

    cierra_nuevo = gates.validar({**meta, "hilos_cerrados": ["hil-004"]}, cuerpo, ctx)
    assert cierra_nuevo == []  # se abre y se cierra en el mismo capítulo
    cierra_ajeno = gates.validar({**meta, "hilos_cerrados": ["hil-002"]}, cuerpo, ctx)
    assert [(h.tipo, h.referencia) for h in cierra_ajeno] == [("hilo_cerrado_sin_abrir", "hil-002")]

    pagada_ajena = gates.validar({**meta, "pistas_pagadas": ["pis-004", "pis-900"]}, cuerpo, ctx)
    assert [(h.tipo, h.referencia) for h in pagada_ajena] == [("id_inexistente", "pis-900")]
    escena_ajena = gates.validar({**meta, "escenas": ["esc-05-1", "esc-05-7"]}, cuerpo, ctx)
    assert [(h.tipo, h.referencia) for h in escena_ajena] == [("id_inexistente", "esc-05-7")]
