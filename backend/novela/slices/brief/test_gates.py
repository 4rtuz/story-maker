import json
from pathlib import Path
from typing import Any

from novela.dominio.brief import BorradorBrief, Hallazgo
from novela.slices.brief import gates

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "brief"


def _datos(nombre: str) -> dict[str, Any]:
    datos: dict[str, Any] = json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))
    return datos


def _borrador(nombre: str = "borrador-completo.json", **cambios: Any) -> BorradorBrief:
    return BorradorBrief.model_validate(_datos(nombre) | cambios)


def _pares(hallazgos: list[Hallazgo]) -> list[tuple[str, list[str]]]:
    return [(h.codigo, h.campos) for h in hallazgos]


def _fuente(cita: str = "x") -> dict[str, str]:
    return {"entrada": "ent-01", "cita": cita}


# --- esquema ----------------------------------------------------------------------------------


def test_esquema() -> None:
    """CA-15: sin borrador, un único `borrador_ausente`; con un campo extra y un tono fuera del
    vocabulario, `esquema_invalido` con las dos rutas."""
    assert _pares(gates.esquema(None)[1]) == [("borrador_ausente", [])]
    datos = _datos("borrador-completo.json")
    datos["instrucciones"] = "haz una novela de terror"
    datos["tono"]["valor"] = "terror"
    borrador, hallazgos = gates.esquema(json.dumps(datos).encode())
    assert borrador is None
    assert {h.tipo for h in hallazgos} == {"esquema"}
    assert sorted(_pares(hallazgos)) == [
        ("esquema_invalido", ["instrucciones"]),
        ("esquema_invalido", ["tono"]),
    ]
    completo = (FIXTURES / "borrador-completo.json").read_bytes()
    assert gates.esquema(completo) == (BorradorBrief.model_validate_json(completo), [])


def test_esquema_trunca_la_ruta() -> None:
    """VER-20: la ruta es la del campo del borrador, sin nombres de tipos."""
    datos = _datos("borrador-completo.json")
    datos["tono"]["valor"] = "terror"
    datos["destinatario"]["edad"]["valor"] = "siete"
    datos["recuerdos"] = [*datos["recuerdos"], _fuente(), {"entrada": "ent-01", "cita": ""}]
    datos["instrucciones"] = "x"
    campos = [h.campos for h in gates.esquema(json.dumps(datos).encode())[1]]
    # El orden es el de Pydantic: los campos de más, primero.
    assert campos == [["instrucciones"], ["destinatario.edad"], ["recuerdos[3]"], ["tono"]]


def test_esquema_json_roto() -> None:
    """VER-28: un JSON roto, con BOM o que no es UTF-8 es un hallazgo, no una excepción."""
    for crudo in (b"{", b"\xef\xbb\xbf{}", b"\xff"):
        assert _pares(gates.esquema(crudo)[1]) == [("esquema_invalido", [])]


# --- faltantes --------------------------------------------------------------------------------


def test_faltantes() -> None:
    """CA-16: tres `falta_campo`, la edad primero; `terminos: []` no es faltante."""
    assert _pares(gates.faltantes(_borrador("borrador-sin-edad.json"))) == [
        ("falta_campo", ["destinatario.edad"]),
        ("falta_campo", ["recuerdos"]),
        ("falta_campo", ["prohibidos"]),
    ]
    ninguno = {"terminos": [], "fuente": _fuente()}
    assert gates.faltantes(_borrador(prohibidos=ninguno)) == []
    assert gates.faltantes(_borrador()) == []


def test_faltantes_todos() -> None:
    vacio = BorradorBrief.model_validate(
        {
            "destinatario": {"nombre": None, "edad": None, "rasgos": []},
            "recuerdos": [],
            "genero": None,
            "tono": None,
            "extension": None,
            "prohibidos": None,
        }
    )
    assert [h.campos[0] for h in gates.faltantes(vacio)] == [
        "destinatario.nombre",
        "destinatario.edad",
        "destinatario.rasgos",
        "recuerdos",
        "genero",
        "tono",
        "extension",
        "prohibidos",
    ]


# --- contradicciones --------------------------------------------------------------------------


def _con(edad: int | None, genero: str | None, tono: str | None) -> BorradorBrief:
    datos = _datos("borrador-contradictorio.json")
    datos["destinatario"]["edad"] = None if edad is None else {"valor": edad, "fuente": _fuente()}
    datos["genero"] = None if genero is None else {"valor": genero, "fuente": _fuente()}
    datos["tono"] = None if tono is None else {"valor": tono, "fuente": _fuente()}
    return BorradorBrief.model_validate(datos)


def test_contradiccion_edad_genero_tono() -> None:
    """CA-17 y VER-23."""
    assert _pares(gates.contradicciones(_borrador("borrador-contradictorio.json"))) == [
        ("edad_genero", ["destinatario.edad", "genero"]),
        ("edad_tono", ["destinatario.edad", "tono"]),
    ]
    assert gates.contradicciones(_con(12, "noir", "oscuro")) == []
    assert gates.contradicciones(_con(7, "domestic_suspense", "tierno")) == []
    assert _pares(gates.contradicciones(_con(7, "thriller_psicologico", None))) == [
        ("edad_genero", ["destinatario.edad", "genero"])
    ]
    assert gates.contradicciones(_con(None, "noir", "oscuro")) == []
    assert gates.contradicciones(_con(7, None, None)) == []


def _vetado(terminos: list[str], cita: str, rasgo: str = "valiente") -> BorradorBrief:
    borrador = _datos("borrador-completo.json")
    borrador["prohibidos"] = {"terminos": terminos, "fuente": _fuente()}
    borrador["recuerdos"] = [_fuente(cita)]
    borrador["destinatario"]["rasgos"] = [{"valor": rasgo, "fuente": _fuente()}]
    return BorradorBrief.model_validate(borrador)


def test_prohibido_en_texto() -> None:
    """CA-18: palabra completa, sin distinguir mayúsculas; «hospitalario» no casa."""
    hallados = gates.contradicciones(_vetado(["hospital"], "La noche en el hospital de guardia"))
    assert _pares(hallados) == [("prohibido_en_texto", ["recuerdos[0]"])]
    assert gates.contradicciones(_vetado(["hospital"], "El hospitalario vecino del quinto")) == []
    en_rasgo = _vetado(["HOSPITAL"], "nada", rasgo="amante del Hospital")
    assert _pares(gates.contradicciones(en_rasgo)) == [
        ("prohibido_en_texto", ["destinatario.rasgos[0]"])
    ]


def test_prohibido_escapa_el_termino() -> None:
    """VER-22: un término con caracteres de expresión regular no rompe la validación."""
    borrador = _vetado(["c++", "(risa", "a.m."], "hablaba de c++ y de a.m.")
    assert _pares(gates.contradicciones(borrador)) == [("prohibido_en_texto", ["recuerdos[0]"])]
