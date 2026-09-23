import pytest
from pydantic import ValidationError

from novela.dominio.estado import Delta
from tests.fixtures import fabrica


def test_delta_valida() -> None:
    """El delta del cronista trae las tres granularidades del resumen; sin ellas no es un delta."""
    ejemplo = fabrica.delta(fabrica.DEMO, 7)
    delta = Delta.model_validate(ejemplo)
    assert set(delta.resumen.escena) == {"esc-07-1", "esc-07-2"}
    assert Delta.model_validate_json(delta.model_dump_json()) == delta
    with pytest.raises(ValidationError, match="resumen"):
        Delta.model_validate({k: v for k, v in ejemplo.items() if k != "resumen"})
    for derivada in ("pistas", "metricas", "tension_real", "cursor"):
        with pytest.raises(ValidationError, match=derivada):
            Delta.model_validate({**ejemplo, derivada: {}})
