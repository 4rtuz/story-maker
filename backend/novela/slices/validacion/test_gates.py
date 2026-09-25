import json
from dataclasses import replace
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from novela.dominio import frontmatter
from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.config import PalabrasPorCapitulo
from novela.dominio.plan import FichaCapitulo
from novela.dominio.prohibidas import Termino
from novela.slices.checkpoint import cmd as checkpoint
from novela.slices.validacion import gates
from tests import estrategias
from tests.fixtures import fabrica

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


def _contrato(
    pistas: tuple[list[str], list[str]], hilos: tuple[list[str], list[str]]
) -> FrontmatterCapitulo:
    meta = _caso()[0] | {
        "pistas_plantadas": pistas[0],
        "pistas_pagadas": pistas[1],
        "hilos_abiertos": hilos[0],
        "hilos_cerrados": hilos[1],
    }
    return FrontmatterCapitulo.model_validate(meta)


_pistas, _hilos = (st.lists(st.sampled_from(ids), unique=True) for ids in (PISTAS, HILOS))
_conjuntos = st.tuples(_pistas, _pistas, _hilos, _hilos)


@settings(max_examples=200)
@given(_conjuntos, _conjuntos, st.booleans())
def test_regeneracion_altera_contrato_property(
    ahora: tuple[list[str], ...], antes: tuple[list[str], ...], iguales: bool
) -> None:
    """RF-31: un hallazgo por cada id que difiere en alguno de los cuatro conjuntos entre el
    capítulo regenerado y el de la versión anterior, y ninguno si son iguales."""
    antes = ahora if iguales else antes
    fm = _contrato((ahora[0], ahora[1]), (ahora[2], ahora[3]))
    anterior = _contrato((antes[0], antes[1]), (antes[2], antes[3]))
    esperados = sorted(id_ for a, b in zip(ahora, antes, strict=True) for id_ in set(a) ^ set(b))
    hallazgos = gates.regeneracion_altera_contrato(fm, anterior)
    assert sorted(h.referencia or "" for h in hallazgos) == esperados
    assert all((h.tipo, h.gravedad) == ("regeneracion_altera_contrato", "alta") for h in hallazgos)


# --- vp_nombres (spec 0009) --------------------------------------------------------------------

TILDE = dict(zip("aeiounAEIOUNáéíóúñÁÉÍÓÚÑ", "áéíóúñÁÉÍÓÚÑaeiounAEIOUN", strict=True))


def _personaje(referencia: str, texto: str) -> gates.FormaCanonica:
    return gates.FormaCanonica(referencia, texto, f"canon/personajes/{referencia}.md")


def _variante(token: str, cambio: str, posicion: int) -> str:
    if cambio == "minuscula":
        return token[0].lower() + token[1:]
    if cambio == "mayusculas":
        return token.upper()
    con_tilde = [i for i, c in enumerate(token) if c in TILDE]
    if cambio == "tilde" and con_tilde:
        i = con_tilde[posicion % len(con_tilde)]
        return token[:i] + TILDE[token[i]] + token[i + 1 :]
    i = 1 + posicion % (len(token) - 1)  # caja de una letra que no es la inicial
    return token[:i] + token[i].swapcase() + token[i + 1 :]


@given(
    estrategias.nombres_en_cuerpo(),
    st.sampled_from(["nada", "tilde", "caja", "minuscula", "mayusculas"]),
    st.data(),
)
def test_nombres_property(
    caso: tuple[list[tuple[str, str]], list[list[str]]], cambio: str, datos: st.DataObject
) -> None:
    """CA-06: las formas exactas nunca dan hallazgo; una variante, exactamente uno, con la
    referencia de su forma y su línea; una variante en minúscula o gritada, ninguno."""
    textos, lineas = caso
    formas = [_personaje(r, t) for r, t in textos]
    de = {token: r for r, t in textos for token in t.split()}
    if cambio != "nada":
        linea, j = datos.draw(
            st.sampled_from(
                [(n, j) for n, ws in enumerate(lineas) for j, w in enumerate(ws) if w in de]
            )
        )
        original = lineas[linea][j]
        lineas = [list(ws) for ws in lineas]
        lineas[linea][j] = _variante(original, cambio, datos.draw(st.integers(0, 20)))
    hallazgos = gates.nombres("\n".join(" ".join(ws) for ws in lineas), formas)
    if cambio in ("nada", "minuscula", "mayusculas"):
        assert hallazgos == []
    else:
        assert [(h.tipo, h.referencia, h.ubicacion) for h in hallazgos] == [
            ("nombre_mal_escrito", de[original], f"línea {linea + 1}")
        ]


@given(
    estrategias.nombres_en_cuerpo(),
    st.sampled_from(["tilde", "caja"]),
    st.data(),
)
def test_erratas_property(
    caso: tuple[list[tuple[str, str]], list[list[str]]], cambio: str, datos: st.DataObject
) -> None:
    """Para el LSP: cada variante sale con su línea y columna exactas, y `nombres` la agrupa."""
    textos, lineas = caso
    formas = [_personaje(r, t) for r, t in textos]
    de = {token: r for r, t in textos for token in t.split()}
    linea, j = datos.draw(
        st.sampled_from(
            [(n, j) for n, ws in enumerate(lineas) for j, w in enumerate(ws) if w in de]
        )
    )
    original = lineas[linea][j]
    lineas = [list(ws) for ws in lineas]
    lineas[linea][j] = _variante(original, cambio, datos.draw(st.integers(0, 20)))
    cuerpo = "\n".join(" ".join(ws) for ws in lineas)
    columna = len(" ".join(lineas[linea][:j])) + (1 if j else 0)
    [e] = gates.erratas(cuerpo, formas)
    assert (e.token, e.linea, e.columna, e.referencia) == (
        lineas[linea][j],
        linea + 1,
        columna,
        de[original],
    )
    assert e.canonico == original


def test_nombres_casos_fijos() -> None:
    """CA-07 (gate) y los límites de la regla, para la mutación."""
    formas = [_personaje("per-elena-vidal", "Elena Vidal"), _personaje("per-munoz", "Muñoz")]
    cuerpo = "Elena Vídal llegó.\nMunoz calló.\nelena\n¡ELENA!\nElena Vidal"
    hallazgos = gates.nombres(cuerpo, formas)
    assert [(h.tipo, h.gravedad, h.referencia, h.ubicacion) for h in hallazgos] == [
        ("nombre_mal_escrito", "alta", "per-elena-vidal", "línea 1"),
        ("nombre_mal_escrito", "alta", "per-munoz", "línea 2"),
    ]
    assert hallazgos[0].descripcion == "«Vídal» no es la grafía de per-elena-vidal: «Vidal»"

    # Una fila por variante, con sus líneas sin repetir; otra variante del mismo nombre, otra fila.
    repetida = gates.nombres("Vídal y Vídal\nnada\nVídal\nVIdal", formas)
    assert [(h.referencia, h.ubicacion) for h in repetida] == [
        ("per-elena-vidal", "línea 1, 3"),
        ("per-elena-vidal", "línea 4"),
    ]
    # Tres letras cuentan; dos, no.
    cortos = [_personaje("per-ana", "Ana"), _personaje("per-li", "Li")]
    assert [h.referencia for h in gates.nombres("Ána y Lí", cortos)] == ["per-ana"]
    # Un alias en minúscula no da tokens canónicos.
    assert gates.nombres("La Jefa", [_personaje("per-j", "la jefa")]) == []
    # Dos personajes que difieren en una tilde: las dos grafías son exactas.
    tilde = [_personaje("per-a", "Martín"), _personaje("per-b", "Martin")]
    assert gates.nombres("Martín y Martin", tilde) == []
    # Mismo apellido en dos formas: la variante se atribuye a la primera (plan P5).
    apellido = [_personaje("per-a", "Ana Muñoz"), _personaje("per-b", "Luis Muñoz")]
    assert [h.referencia for h in gates.nombres("Munoz", apellido)] == ["per-a"]
    assert gates.nombres("", formas) == [] and gates.nombres("Munoz", []) == []


def test_nombres_conflicto_canon() -> None:
    """CA-08: el canon escribe el nombre del destinatario con otra grafía."""
    brief = gates.FormaCanonica("destinatario", "Aurora Ficticia", "brief/brief.json")
    distinto = [_personaje("per-aurora", "Aurora Fictícia"), brief]
    hallazgos = gates.nombres("Nadie la nombra.", distinto)
    assert [(h.tipo, h.referencia, h.ubicacion) for h in hallazgos] == [
        ("nombre_mal_escrito", "per-aurora", "canon/personajes/per-aurora.md")
    ]
    assert gates.nombres("Nadie.", [_personaje("per-aurora", "Aurora Ficticia"), brief]) == []
    # Solo contra el brief: dos personajes que difieren en una tilde no son conflicto.
    assert gates.nombres("", [_personaje("per-a", "Martín"), _personaje("per-b", "Martin")]) == []
    # Un token gritado en el canon no es variante.
    assert gates.nombres("", [_personaje("per-aurora", "AURORA"), brief]) == []


# --- vp_schema (spec 0009) ---------------------------------------------------------------------

CONTEXTO = {"num_capitulos": fabrica.DEMO.num_capitulos}


def _documentos() -> dict[str, tuple[type[BaseModel], object | None, bool]]:
    """Las salidas reales del agente falso para el capítulo 8 de DEMO: todas validan."""
    textos = (
        fabrica.canon(fabrica.DEMO) | fabrica.plan(fabrica.DEMO) | fabrica.informes(fabrica.DEMO, 8)
    )
    textos |= {
        "capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8),
        "qa/08-validacion.json": fabrica.informe(8, "validar"),
        "estado/deltas/08.json": json.dumps(fabrica.delta(fabrica.DEMO, 8)),
    }
    personajes = [r.removeprefix("canon/personajes/") for r in textos if "personajes/" in r]
    return {
        ruta: (
            modelo,
            frontmatter.partir(textos[ruta])[0]
            if ruta.endswith(".md")
            else json.loads(textos[ruta]),
            obligatorio,
        )
        for ruta, (modelo, obligatorio) in checkpoint.artefactos("08", personajes).items()
    }


@given(st.data())
def test_esquemas_property(datos: st.DataObject) -> None:
    """CA-03: los documentos válidos no dan hallazgo; un campo extra, uno obligatorio borrado o
    uno de otro tipo, exactamente uno, sobre el documento mutado."""
    documentos = _documentos()
    assert gates.esquemas(documentos, CONTEXTO) == []
    ruta = datos.draw(st.sampled_from(sorted(documentos)))
    modelo, original, obligatorio = documentos[ruta]
    assert isinstance(original, dict)
    requeridos = sorted(
        k for k, f in modelo.model_fields.items() if f.is_required() and k in original
    )
    cambio = datos.draw(st.sampled_from(["extra", "borrar", "tipo"] if requeridos else ["extra"]))
    campo = datos.draw(st.sampled_from(requeridos or ["campo_extra"]))
    if cambio == "extra":
        mutado = {**original, "campo_extra": 1}
    elif cambio == "borrar":
        mutado = {k: v for k, v in original.items() if k != campo}
    else:
        mutado = {**original, campo: [[None]]}  # ni texto, ni número, ni mapa, ni modelo
    hallazgos = gates.esquemas({**documentos, ruta: (modelo, mutado, obligatorio)}, CONTEXTO)
    assert [(h.tipo, h.referencia) for h in hallazgos] == [("esquema_invalido", ruta)]


def test_esquemas_casos_fijos() -> None:
    """Ausente, ilegible y la forma del hallazgo (VER-9, VER-10), para la mutación."""
    documentos = _documentos()
    ruta = "qa/08-estilo.json"
    modelo, informe, _ = documentos[ruta]
    assert isinstance(informe, dict)
    assert gates.esquemas({**documentos, ruta: (modelo, None, False)}, CONTEXTO) == []
    ausente = gates.esquemas({**documentos, ruta: (modelo, None, True)}, CONTEXTO)
    assert [(h.referencia, h.ubicacion, h.gravedad) for h in ausente] == [
        (ruta, "(ausente)", "alta")
    ]
    roto = gates.esquemas({ruta: (modelo, "{roto", True)})
    assert [(h.referencia, h.ubicacion) for h in roto] == [(ruta, "(raíz)")]

    # Cada loc unido por «.», los errores por «, »; ningún valor del documento en el hallazgo.
    sin_veredicto = {k: v for k, v in informe.items() if k != "veredicto"}
    malo = {**sin_veredicto, "agente": "Aurora Ficticia", "hallazgos": [{"tipo": "x"}]}
    (hallazgo,) = gates.esquemas({ruta: (modelo, malo, True)})
    assert hallazgo.ubicacion is not None and hallazgo.ubicacion.startswith(
        "agente, veredicto, hallazgos.0."
    )
    assert "Aurora" not in hallazgo.model_dump_json()

    # La escaleta necesita el contexto: sin él, rechaza siempre.
    escaleta = {"plan/escaleta.md": documentos["plan/escaleta.md"]}
    assert gates.esquemas(escaleta, CONTEXTO) == []
    assert [h.referencia for h in gates.esquemas(escaleta)] == ["plan/escaleta.md"]
    # Varios documentos, en su orden.
    dos = {"b": (modelo, None, True), "a": (modelo, None, True)}
    assert [h.referencia for h in gates.esquemas(dos)] == ["b", "a"]


# --- vp_prohibidas (docs/guardrails.md) ---------------------------------------------------------

PROHIBIDOS = (
    Termino("gilipollas", "global"),
    Termino("Villa Rosa", "cliente"),
    Termino("tonto", "novela"),
)


@given(capitulos_validos(), st.sampled_from(PROHIBIDOS), st.data())
def test_prohibidas_property(caso: Caso, termino: Termino, datos: st.DataObject) -> None:
    """Un capítulo válido con un término prohibido de cualquier nivel, en mayúsculas, deja un
    solo hallazgo que dice qué término, de qué nivel y en qué línea; sin él, ninguno."""
    meta, cuerpo, ctx = caso
    ctx = replace(ctx, prohibidos=PROHIBIDOS)
    assert gates.validar(meta, cuerpo, ctx) == []
    lineas = cuerpo.split(" ")
    linea = datos.draw(st.integers(1, len(lineas)))
    lineas[linea - 1] = termino.texto.upper()
    sucio = "\n".join(lineas)
    ctx = replace(ctx, palabras=ctx.palabras.model_copy(update={"max": ctx.palabras.max + 2}))
    [h] = gates.validar(meta, sucio, ctx)
    assert (h.tipo, h.referencia, h.ubicacion) == (
        "termino_prohibido",
        termino.nivel,
        f"línea {linea}",
    )
    assert f"«{termino.texto}»" in h.descripcion and termino.texto.upper() in h.descripcion
