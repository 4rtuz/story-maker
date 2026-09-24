import pytest
import yaml
from pydantic import ValidationError

from novela.dominio.juicio import CRITERIOS
from novela.slices.juicio import rubrica


def test_rubrica_versionada_con_los_criterios_del_modelo() -> None:
    cargada = rubrica.cargar()
    assert cargada.version.startswith("rubrica-")
    assert tuple(cargada.criterios) == CRITERIOS
    assert all({1, 3, 5} <= set(c.escala) for c in cargada.criterios.values())
    assert (cargada.umbral.media_minima, cargada.umbral.minimo_por_criterio) == (3, 2)

    datos = yaml.safe_load(rubrica.RUTA.read_text(encoding="utf-8"))
    del datos["criterios"]["ritmo"]
    with pytest.raises(ValidationError, match="ritmo"):
        rubrica.Rubrica.model_validate(datos)
