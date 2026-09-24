from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.artefactos import Memoria
from novela.dominio.ids import Agente
from novela.slices.briefing import assemble, recipes
from novela.slices.briefing.recipes import Receta
from tests import estrategias
from tests.fuentes import FICHA, MUNDO, PERSONAJE, PREMISA, fuentes, receta


def test_incrusta_contenido_no_rutas() -> None:
    briefing = assemble.ensamblar(receta(permanente=["canon/premisa", "canon/mundo"]), fuentes())
    assert "Una farera vuelve al pueblo." in briefing.cuerpo
    assert "Un pueblo de costa." in briefing.cuerpo
    assert briefing.cuerpo.index("Una farera") < briefing.cuerpo.index("Un pueblo")
    assert briefing.meta.tokens_estimados == assemble.estimar_tokens(briefing.cuerpo)


def test_glob_y_exclusion() -> None:
    ficheros = {"canon/premisa.md": PREMISA, "canon/misterio.md": "---\n---\nsecreto\n"}
    con_glob = receta(permanente=["canon/*"])
    assert "secreto" in assemble.ensamblar(con_glob, fuentes(ficheros=ficheros)).cuerpo
    excluye = con_glob.model_copy(update={"excluir": ["canon/misterio"]})
    assert "secreto" not in assemble.ensamblar(excluye, fuentes(ficheros=ficheros)).cuerpo


def test_ruta_que_falta_falla_explicitamente() -> None:
    with pytest.raises(assemble.FuenteAusente, match="canon/estilo"):
        assemble.ensamblar(receta(permanente=["canon/estilo"]), fuentes())


@given(
    st.dictionaries(st.sampled_from(["premisa", "mundo", "estilo"]), estrategias.frase, min_size=1)
)
def test_toda_capa_permanente_llega_integra(textos: dict[str, str]) -> None:
    ficheros = {f"canon/{k}.md": v for k, v in textos.items()}
    briefing = assemble.ensamblar(
        receta(permanente=[f"canon/{k}" for k in sorted(textos)]), fuentes(ficheros=ficheros)
    )
    for texto in textos.values():
        assert texto.strip() in briefing.cuerpo


def _larga(n: int) -> assemble.Fuentes:
    """Capítulo 8 con siete resúmenes, dos personajes que hablan y uno que no."""
    ficha = FICHA.model_copy(update={"capitulo": 8})
    escena = ficha.escenas[0].model_copy(
        update={"id": "esc-08-1", "personajes": ["per-a", "per-b"], "dialogo": ["per-a"]}
    )
    ficha = ficha.model_copy(update={"escenas": [escena]})
    resumenes = {
        c: Memoria(
            capitulo=c,
            linea=f"Línea del capítulo {c}. " * 3,
            parrafo=f"Párrafo del capítulo {c}. " * 20,
            escena={f"esc-{c:02d}-1": "x"},
        )
        for c in range(1, 8)
    }
    personaje = PERSONAJE
    ficheros = {"canon/premisa.md": PREMISA, "canon/mundo.md": MUNDO, "canon/estilo.md": "Seco."}
    return replace(
        fuentes(),
        capitulo=8,
        ficheros=ficheros,
        ficha=ficha,
        ficha_texto="Ficha del capítulo 8.",
        personajes={"per-a": (personaje, "A habla. " * n), "per-b": (personaje, "B calla. " * n)},
        capitulo_anterior="El capítulo 7 entero.",
        resumenes=resumenes,
    )


ESCRITOR = recipes.cargar()[Agente.ESCRITOR]


def _con_presupuesto(presupuesto: int) -> Receta:
    return ESCRITOR.model_copy(update={"presupuesto_tokens": presupuesto})


def test_orden_de_degradacion() -> None:
    """CA-12: remota recortada, luego reciente a una línea, luego personajes con diálogo; canon y
    estado filtrado llegan íntegros en todos los casos. Si ni así cabe, falla."""
    f = _larga(200)
    completo = assemble.ensamblar(ESCRITOR, f)
    assert completo.meta.degradacion == []
    fijas = [s for s in completo.cuerpo.split("\n## ") if s.startswith(("permanente", "estado"))]

    pasos_vistos = []
    for presupuesto in range(completo.meta.tokens_estimados, 0, -25):
        try:
            briefing = assemble.ensamblar(_con_presupuesto(presupuesto), f)
        except assemble.PresupuestoExcedido:
            break
        assert briefing.meta.tokens_estimados <= presupuesto
        for seccion in fijas:
            assert seccion in briefing.cuerpo
        pasos = [p.split(" ")[0] for p in briefing.meta.degradacion]
        if pasos and pasos not in pasos_vistos:
            pasos_vistos.append(pasos)
    else:
        pytest.fail("con presupuesto 1 tenía que fallar")
    assert pasos_vistos[0] == ["1"]
    assert pasos_vistos[-1] == ["1", "2", "3"]
    assert ["1", "2"] in pasos_vistos


@given(presupuesto=st.integers(1, 12_000), n=st.integers(1, 300))
def test_cabe_o_falla_y_nunca_trunca(presupuesto: int, n: int) -> None:
    f = _larga(n)
    try:
        briefing = assemble.ensamblar(_con_presupuesto(presupuesto), f)
    except assemble.PresupuestoExcedido:
        return
    assert briefing.meta.tokens_estimados <= presupuesto
    for ruta, texto in f.ficheros.items():
        if ruta in ("canon/premisa.md", "canon/mundo.md"):
            assert texto.strip() in briefing.cuerpo


def _novela_entera(n: int = 9) -> assemble.Fuentes:
    resumenes = {
        c: Memoria(
            capitulo=c,
            linea=f"Línea {c}.",
            parrafo=f"Párrafo del capítulo {c}.",
            escena={f"esc-{c:02d}-1": "x"},
        )
        for c in range(1, n + 1)
    }
    capitulos = {c: f"Texto entero del capítulo {c}. " * 200 for c in range(1, n + 1)}
    return replace(
        fuentes(), agente=Agente.JUEZ, capitulo=n, resumenes=resumenes, capitulos=capitulos
    )


def test_obra_entera_o_resumenes_y_muestra() -> None:
    """El juez ve la novela entera si cabe; si no, los resúmenes de todos los capítulos y el
    primero, el central y el último completos. Si ni así cabe, falla: nunca se trunca."""
    f = _novela_entera()
    entera = assemble.ensamblar(receta(100_000, obra={"muestra": 3}), f)
    assert entera.meta.degradacion == []
    for c in range(1, 10):
        assert f.capitulos[c].strip() in entera.cuerpo
    assert "Párrafo del capítulo" not in entera.cuerpo

    muestreada = assemble.ensamblar(
        receta(entera.meta.tokens_estimados - 1, obra={"muestra": 3}), f
    )
    assert [p.split(" ")[0] for p in muestreada.meta.degradacion] == ["4"]
    assert all(f"Párrafo del capítulo {c}." in muestreada.cuerpo for c in range(1, 10))
    completos = [c for c in range(1, 10) if f.capitulos[c].strip() in muestreada.cuerpo]
    assert completos == [1, 5, 9]

    with pytest.raises(assemble.PresupuestoExcedido):
        assemble.ensamblar(receta(1_000, obra={"muestra": 3}), f)


def test_obra_sin_capitulo_falla_explicitamente() -> None:
    f = _novela_entera()
    f = replace(f, capitulos={c: t for c, t in f.capitulos.items() if c != 4})
    with pytest.raises(assemble.FuenteAusente, match="capitulos/04.md"):
        assemble.ensamblar(receta(100_000, obra={"muestra": 3}), f)
