import json
from itertools import product
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from novela.dominio.brief import (
    CODIGOS,
    OBJETIVO,
    BorradorBrief,
    Brief,
    CodigoHallazgo,
    Fuente,
    Hallazgo,
    InformeBrief,
    TipoHallazgo,
    idea_semilla,
)

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "brief"


def _json(nombre: str) -> dict[str, Any]:
    datos: dict[str, Any] = json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))
    return datos


def test_brief_ata_entradas() -> None:
    """CA-24: el brief lleva la ocasión y cada entrada usada con su tipo y su sha256."""
    brief = Brief.model_validate(_json("brief-completo.json"))
    assert brief.ocasion == "boda"
    assert [(e.id, e.tipo) for e in brief.entradas] == [
        ("ent-01", "respuesta"),
        ("ent-02", "texto_libre"),
    ]
    assert all(len(e.sha256) == 64 for e in brief.entradas)


def test_idea_semilla_determinista() -> None:
    """CA-27: igual byte a byte al golden, dos veces, y conserva el orden del brief."""
    brief = Brief.model_validate(_json("brief-completo.json"))
    golden = (FIXTURES / "golden" / "idea-semilla.txt").read_bytes().decode("utf-8")
    assert idea_semilla(brief) == idea_semilla(brief) == golden

    datos = _json("brief-completo.json")
    datos["destinatario"]["rasgos"].reverse()
    otra = idea_semilla(Brief.model_validate(datos))
    assert "Rasgos: «paciente», «valiente»" in otra


def test_extension_a_palabras() -> None:
    assert OBJETIVO == {"corta": 1000, "media": 1250, "larga": 1500}


def test_limites() -> None:
    borrador = _json("borrador-completo.json")
    BorradorBrief.model_validate(borrador)
    for cambio in (
        {"preguntas": ["x"] * 9},
        {"recuerdos": [{"entrada": "ent-01", "cita": "x"}] * 21},
        {"prohibidos": {"terminos": ["x"] * 31, "fuente": {"entrada": "ent-01", "cita": "x"}}},
    ):
        with pytest.raises(ValidationError):
            BorradorBrief.model_validate(borrador | cambio)
    with pytest.raises(ValidationError):
        Fuente(entrada="ent-01", cita="x" * 601)
    with pytest.raises(ValidationError):  # [0-9] y no \d: Python y JSON Schema dicen lo mismo
        Fuente(entrada="ent-١٢", cita="x")
    # El brief exige lo que el borrador puede dejar a medias.
    with pytest.raises(ValidationError):
        Brief.model_validate(_json("brief-completo.json") | {"recuerdos": []})


def test_hallazgo_tipo_y_codigo_casan() -> None:
    """Solo los 11 pares de la tabla de §8.3."""
    assert {c for cs in CODIGOS.values() for c in cs} == set(get_args(CodigoHallazgo))
    validos = 0
    for tipo, codigo in product(get_args(TipoHallazgo), get_args(CodigoHallazgo)):
        try:
            Hallazgo(tipo=tipo, codigo=codigo)
            validos += 1
        except ValidationError:
            pass
    assert validos == 11


def test_informe_valido_sii_sin_hallazgos() -> None:
    hallazgo = Hallazgo(tipo="faltante", codigo="falta_campo", campos=["tono"])
    InformeBrief(valido=True, hallazgos=[])
    InformeBrief(valido=False, hallazgos=[hallazgo])
    with pytest.raises(ValidationError):
        InformeBrief(valido=True, hallazgos=[hallazgo])
    with pytest.raises(ValidationError):
        InformeBrief(valido=False, hallazgos=[])


def test_idea_semilla_declara_datos_ficticios() -> None:
    """Una novela de ejemplo o de evaluación: el arquitecto sabe que el destinatario no existe y
    no lo anonimiza. Sin la marca, la semilla no cambia (el golden de arriba lo fija)."""
    datos = _json("brief-completo.json") | {"ficticio": True}
    semilla = idea_semilla(Brief.model_validate(datos))
    assert semilla.splitlines()[2].startswith("Datos ficticios")
    assert "ficticio" not in idea_semilla(Brief.model_validate(_json("brief-completo.json")))
