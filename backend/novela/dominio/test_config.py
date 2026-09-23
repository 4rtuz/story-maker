from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from novela.dominio.config import Config

DEFAULT = Path(__file__).resolve().parents[2] / "config" / "default.yaml"


def _config(**obra: Any) -> dict[str, Any]:
    base: dict[str, Any] = yaml.safe_load(DEFAULT.read_text(encoding="utf-8"))
    base["idea_semilla"] = "Un faro que lleva nueve años apagado."
    base["parametros_obra"] = {k: v for k, v in base["parametros_obra"].items() if k not in obra}
    base["parametros_obra"].update({k: v for k, v in obra.items() if v is not None})
    return base


def test_deriva_palabras_por_capitulo() -> None:
    obra = Config.model_validate(
        _config(longitud_total_palabras=9000, num_capitulos=3)
    ).parametros_obra
    assert obra.palabras_por_capitulo.model_dump() == {"objetivo": 3000, "min": 2400, "max": 3600}


def test_sin_longitud_ni_numero_falla_explicitamente() -> None:
    sin_nada = _config(longitud_total_palabras=None, num_capitulos=None, palabras_por_capitulo=None)
    with pytest.raises(ValidationError, match="palabras_por_capitulo no se puede derivar"):
        Config.model_validate(sin_nada)


def test_terna_incoherente_se_rechaza() -> None:
    terna = {"objetivo": 100, "min": 200, "max": 300}
    with pytest.raises(ValidationError, match="min <= objetivo <= max"):
        Config.model_validate(_config(palabras_por_capitulo=terna))


def test_subgenero_es_enum() -> None:
    with pytest.raises(ValidationError):
        Config.model_validate(_config(subgenero="romantica"))
