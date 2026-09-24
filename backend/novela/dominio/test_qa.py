from typing import Any

import pytest
from pydantic import ValidationError

from novela.dominio.qa import InformeQA

INFORME: dict[str, Any] = {
    "capitulo": 7,
    "agente": "continuista",
    "veredicto": "rechazado",
    "hallazgos": [
        {
            "tipo": "contradiccion_hecho",
            "gravedad": "alta",
            "referencia": "hec-014",
            "ubicacion": "escena esc-07-2, párrafo 4",
            "descripcion": "El faro aparece encendido; el libro de hechos lo da por apagado.",
            "correccion_sugerida": "...",
        }
    ],
}


def test_informe_valida() -> None:
    informe = InformeQA.model_validate(INFORME)
    assert InformeQA.model_validate_json(informe.model_dump_json()) == informe
    assert informe.capitulo_sha256 is None  # ningún agente lo escribe: lo pone novela validar

    desconocido = {**INFORME["hallazgos"][0], "tipo": "me_parece_raro"}
    with pytest.raises(ValidationError):
        InformeQA.model_validate({**INFORME, "hallazgos": [desconocido]})
    with pytest.raises(ValidationError):
        InformeQA.model_validate({**INFORME, "capitulo_sha256": "no-es-un-hash"})


@pytest.mark.parametrize("tipo", ["esquema_invalido", "nombre_mal_escrito", "elemento_sin_cubrir"])
def test_tipos_de_la_spec_0009(tipo: str) -> None:
    hallazgo = {"tipo": tipo, "gravedad": "alta", "descripcion": "d"}
    assert InformeQA.model_validate({**INFORME, "hallazgos": [hallazgo]}).hallazgos[0].tipo == tipo
