"""Fuentes de ensamblado de ejemplo, compartidas por los tests de briefing."""

from dataclasses import replace
from typing import Any

from novela.dominio.canon import Personaje
from novela.dominio.estado import Cursor, Estado
from novela.dominio.ids import Agente
from novela.dominio.plan import FichaCapitulo
from novela.slices.briefing import assemble
from novela.slices.briefing.recipes import Receta

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
