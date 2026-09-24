from typing import Any

import pytest
from pydantic import ValidationError

from novela.dominio.juicio import CRITERIOS, Juicio


def _valoracion(puntuacion: int = 4) -> dict[str, Any]:
    return {
        "puntuacion": puntuacion,
        "justificacion": "El faro se apaga y se enciende según lo pactado.",
        "citas": [{"capitulo": 3, "texto": "La luz volvió a girar sobre el agua."}],
    }


def juicio(**cambios: Any) -> dict[str, Any]:
    return {
        "rubrica_version": "rubrica-1",
        "evaluador": "juez",
        "criterios": {c: _valoracion() for c in CRITERIOS},
    } | cambios


def test_juicio_valida() -> None:
    hecho = Juicio.model_validate(juicio())
    assert Juicio.model_validate_json(hecho.model_dump_json()) == hecho
    assert (
        set(hecho.criterios)
        == set(CRITERIOS)
        == {
            "continuidad",
            "tono",
            "arco",
            "personajes",
            "ritmo",
            "personalizacion",
        }
    )


@pytest.mark.parametrize("puntuacion", [0, 6])
def test_escala_de_1_a_5(puntuacion: int) -> None:
    criterios = {c: _valoracion() for c in CRITERIOS} | {"tono": _valoracion(puntuacion)}
    with pytest.raises(ValidationError):
        Juicio.model_validate(juicio(criterios=criterios))


def test_todos_los_criterios_y_con_cita() -> None:
    sin_tono = {c: _valoracion() for c in CRITERIOS if c != "tono"}
    with pytest.raises(ValidationError, match="tono"):
        Juicio.model_validate(juicio(criterios=sin_tono))
    sin_cita = {c: _valoracion() for c in CRITERIOS} | {"arco": _valoracion() | {"citas": []}}
    with pytest.raises(ValidationError):
        Juicio.model_validate(juicio(criterios=sin_cita))
    with pytest.raises(ValidationError):
        Juicio.model_validate(juicio(evaluador="otro"))
