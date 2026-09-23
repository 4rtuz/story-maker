from dataclasses import replace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.estado import Cursor, Estado
from novela.dominio.ids import Agente
from novela.slices.briefing import assemble
from novela.slices.briefing.recipes import Receta
from tests import estrategias

PREMISA = "---\nlogline: x\n---\nUna farera vuelve al pueblo.\n"
MUNDO = "---\nescenarios: []\n---\nUn pueblo de costa.\n"


def receta(presupuesto: int = 60_000, **capas: Any) -> Receta:
    return Receta.model_validate(
        {"presupuesto_tokens": presupuesto, "capas": [{k: v} for k, v in capas.items()]}
    )


def fuentes(**cambios: Any) -> assemble.Fuentes:
    base = assemble.Fuentes(
        agente=Agente.ESCRITOR,
        capitulo=1,
        run_id="r-20260101-0900",
        ficheros={"canon/premisa.md": PREMISA, "canon/mundo.md": MUNDO},
        ficha=None,
        ficha_texto=None,
        misterio=None,
        misterio_texto=None,
        personajes={},
        estado=Estado(cursor=Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=1)),
        capitulo_anterior=None,
        capitulo_actual=None,
        sha_actual=None,
        resumenes={},
    )
    return replace(base, **cambios)


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
