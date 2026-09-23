from dataclasses import replace

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from novela.dominio import frontmatter
from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.canon import Misterio, Personaje
from novela.dominio.ids import Agente
from novela.dominio.plan import FichaCapitulo
from novela.slices.briefing import assemble, recipes
from novela.slices.briefing.test_assemble import fuentes
from tests import estrategias

RECETAS = recipes.cargar()
PERSONAJE = Personaje.model_validate(
    {
        "identidad": {"id": "per-a", "nombre": "A", "rol_narrativo": "testigo"},
        "voz": {"idiolecto": "seco", "registro": "llano", "dialogo_canonico": ["No."]},
        "psicologia": {"deseo": "d", "necesidad": "n", "miedo": "m", "herida": "h"},
    }
)
FICHA = FichaCapitulo.model_validate(
    {
        "capitulo": 1,
        "pov": "per-a",
        "objetivo_dramatico": "o",
        "escenas": [
            {
                "id": "esc-01-1",
                "lugar": "esc-faro",
                "tiempo_diegetico": "t",
                "personajes": ["per-a"],
                "beat": "b",
                "conflicto": "c",
            }
        ],
        "gancho_final": "amenaza",
        "restriccion_de_apertura": "Empieza con un diálogo.",
    }
)
# Qué capas recibe cada agente que excluye el misterio: ahí es donde se puede colar.
CAPAS = {
    Agente.ESCRITOR: ["premisa", "estilo", "ficha", "personaje"],
    Agente.EDITOR_ESTILO: ["estilo", "personaje", "capitulo"],
    Agente.CRONISTA: ["capitulo"],
}


def _fuentes_con(misterio: Misterio, agente: Agente, **textos: str) -> assemble.Fuentes:
    ficheros = {
        "canon/premisa.md": textos.get("premisa", "Premisa sin secretos."),
        "canon/mundo.md": "Un pueblo.",
        "canon/estilo.md": textos.get("estilo", "Seco."),
        "canon/misterio.md": frontmatter.unir(misterio.model_dump(mode="json"), ""),
    }
    return replace(
        fuentes(),
        agente=agente,
        ficheros=ficheros,
        misterio=misterio,
        misterio_texto=ficheros["canon/misterio.md"],
        ficha=FICHA,
        ficha_texto=textos.get("ficha", "La ficha de este capítulo."),
        personajes={"per-a": (PERSONAJE, textos.get("personaje", "Ficha de A."))},
        capitulo_actual=textos.get("capitulo", "El capítulo recién escrito."),
    )


@given(
    misterio=estrategias.misterios(),
    agente=st.sampled_from(sorted(CAPAS)),
    inyectar=st.booleans(),
    datos=st.data(),
)
def test_misterio_nunca_en_briefing(
    misterio: Misterio, agente: Agente, inyectar: bool, datos: st.DataObject
) -> None:
    """CA-09: para cualquier canon, lo que viene de canon/misterio.md no entra en el briefing de
    quien lo excluye. Si otra capa lo trae, el ensamblado aborta en vez de devolver nada."""
    fuga = datos.draw(st.sampled_from(misterio.verdad_oculta.entradas))
    assume(len(fuga) >= assemble.MIN_FRAGMENTO)
    donde = datos.draw(st.sampled_from(CAPAS[agente]))
    textos = {donde: f"Relleno. {fuga} Más relleno."} if inyectar else {}
    f = _fuentes_con(misterio, agente, **textos)
    if inyectar:
        with pytest.raises(assemble.FugaDelSecreto):
            assemble.ensamblar(RECETAS[agente], f)
        return
    cuerpo = assemble.ensamblar(RECETAS[agente], f).cuerpo
    assert f.ficheros["canon/misterio.md"].strip() not in cuerpo
    assert all(p not in cuerpo for p in misterio.verdad_oculta if len(p) >= assemble.MIN_FRAGMENTO)


@given(misterio=estrategias.misterios())
def test_misterio_incrustado(misterio: Misterio) -> None:
    """CA-10: el continuista y el lector-suspense reciben el misterio literal, incrustado."""
    for agente in (Agente.CONTINUISTA, Agente.LECTOR_SUSPENSE):
        f = _fuentes_con(misterio, agente)
        ficheros = dict(f.ficheros) | {"plan/escaleta.md": "La escaleta."}
        cuerpo = assemble.ensamblar(RECETAS[agente], replace(f, ficheros=ficheros)).cuerpo
        assert f.ficheros["canon/misterio.md"].strip() in cuerpo


@given(misterio=estrategias.misterios())
def test_el_error_no_repite_el_secreto(misterio: Misterio) -> None:
    """El mensaje del aborto llega al orquestador: nombra la capa, no el texto filtrado."""
    secreto = "Tomás apagó el faro con la llave que nunca devolvió."
    misterio = misterio.model_copy(update={"verdad_oculta": ColeccionAppendOnly([secreto])})
    f = _fuentes_con(misterio, Agente.EDITOR_ESTILO, estilo=secreto)
    with pytest.raises(assemble.FugaDelSecreto) as error:
        assemble.ensamblar(RECETAS[Agente.EDITOR_ESTILO], f)
    assert "canon/estilo.md" in str(error.value)
    assert secreto not in str(error.value)
