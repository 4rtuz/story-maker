from typing import Any

import pytest
from pydantic import ValidationError

from novela.dominio.plan import Escaleta, FichaCapitulo

ESCALETA: dict[str, Any] = {
    "actos": [{"numero": 1, "funcion_dramatica": "planteamiento", "capitulos": [1, 2, 3]}],
    "puntos_de_giro": {"detonante": 1, "punto_medio": 2, "crisis": 2, "climax": 3, "resolucion": 3},
    "curva_tension_objetivo": [3, 6, 9],
}

FICHA: dict[str, Any] = {
    "capitulo": 7,
    "pov": "per-elena-vidal",
    "objetivo_dramatico": "Elena descubre que la puerta fue forzada desde dentro",
    "escenas": [
        {
            "id": "esc-07-1",
            "lugar": "esc-casa-del-faro",
            "tiempo_diegetico": "dia 3, 21:40",
            "personajes": ["per-elena-vidal", "per-tomas-reyes"],
            "dialogo": ["per-tomas-reyes"],
            "beat": "Tomás aparece sin avisar",
            "conflicto": "Elena no puede echarle sin revelar lo que sabe",
        }
    ],
    "pistas_a_plantar": ["pis-009"],
    "pistas_a_pagar": ["pis-004"],
    "hilos_que_abre": ["hil-007"],
    "hilos_que_cierra": ["hil-002"],
    "gancho_final": "amenaza",
    "restriccion_de_apertura": "Empieza con una frase de diálogo, sin acotación",
}


def test_curva_tension_cuadra_con_num_capitulos() -> None:
    contexto = {"num_capitulos": 3}
    assert Escaleta.model_validate(ESCALETA, context=contexto).curva_tension_objetivo == [3, 6, 9]
    with pytest.raises(ValidationError, match="num_capitulos"):
        Escaleta.model_validate({**ESCALETA, "curva_tension_objetivo": [3, 6]}, context=contexto)
    with pytest.raises(ValidationError):
        Escaleta.model_validate(
            {**ESCALETA, "curva_tension_objetivo": [3, 6, 11]}, context=contexto
        )
    with pytest.raises(ValidationError, match="contexto"):
        Escaleta.model_validate(ESCALETA)


def test_ficha_escenas_del_propio_capitulo() -> None:
    assert FichaCapitulo.model_validate(FICHA).gancho_final == "amenaza"
    ajena = {**FICHA["escenas"][0], "id": "esc-08-1"}
    with pytest.raises(ValidationError, match="esc-08-1"):
        FichaCapitulo.model_validate({**FICHA, "escenas": [ajena]})
    muda = {**FICHA["escenas"][0], "dialogo": ["per-ausente"]}
    with pytest.raises(ValidationError, match="per-ausente"):
        FichaCapitulo.model_validate({**FICHA, "escenas": [muda]})
    with pytest.raises(ValidationError):
        FichaCapitulo.model_validate({**FICHA, "gancho_final": "un final muy intenso"})
