"""Los contratos del workspace como JSON Schema, generados desde los modelos (RF-26).

`backend/schemas/` es la copia commiteada; `tests/test_contratos.py` falla si difiere de esto, y
con `REGENERAR=1` la reescribe. Un contrato por documento que cruza de un agente o del disco.
"""

from typing import Any

from pydantic import BaseModel

from novela.dominio.canon import Canon
from novela.dominio.config import Config
from novela.dominio.estado import Estado
from novela.dominio.plan import Escaleta, FichaCapitulo
from novela.dominio.qa import InformeQA

MODELOS: dict[str, type[BaseModel]] = {
    "config.schema.json": Config,
    "state.schema.json": Estado,
    "canon.schema.json": Canon,
    "escaleta.schema.json": Escaleta,
    "plan-capitulo.schema.json": FichaCapitulo,
    "qa-informe.schema.json": InformeQA,
}


def generar() -> dict[str, dict[str, Any]]:
    return {
        nombre: {"$schema": "https://json-schema.org/draft/2020-12/schema"}
        | modelo.model_json_schema()
        for nombre, modelo in MODELOS.items()
    }
