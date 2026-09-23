import re
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import TypeAdapter, ValidationError

from novela.dominio import ids

CASOS: list[tuple[Any, str]] = [
    (ids.PersonajeId, r"per-[a-z0-9-]+"),
    (ids.EscenarioId, r"esc-[a-z][a-z0-9-]*"),
    (ids.EscenaId, r"esc-[0-9]{2,3}-[0-9]+"),
    (ids.PistaId, r"pis-[0-9]{3}"),
    (ids.PistaFalsaId, r"pfa-[0-9]{3}"),
    (ids.RevelacionId, r"rev-[0-9]{3}"),
    (ids.HiloId, r"hil-[0-9]{3}"),
    (ids.ObjetoId, r"obj-[0-9]{3}"),
    (ids.HechoId, r"hec-[0-9]{3}"),
    (ids.CapituloId, r"cap-[0-9]{2,3}"),
    (ids.RunId, r"r-[0-9]{8}-[0-9]{4}"),
    (ids.Slug, r"[a-z0-9-]+"),
]


def _acepta(tipo: Any, valor: str) -> bool:
    try:
        TypeAdapter(tipo).validate_python(valor)
    except ValidationError:
        return False
    return True


@pytest.mark.parametrize(("tipo", "patron"), CASOS)
@given(datos=st.data())
def test_formato_de_cada_prefijo(tipo: Any, patron: str, datos: st.DataObject) -> None:
    valido = datos.draw(st.from_regex(patron, fullmatch=True))
    assert _acepta(tipo, valido)
    cualquiera = datos.draw(st.text(max_size=20) | st.from_regex(patron + r"\n?", fullmatch=True))
    assert _acepta(tipo, cualquiera) == bool(re.fullmatch(patron, cualquiera))


@given(st.from_regex(CASOS[2][1], fullmatch=True), st.from_regex(CASOS[1][1], fullmatch=True))
def test_escena_y_escenario_disjuntos(escena: str, escenario: str) -> None:
    assert not _acepta(ids.EscenarioId, escena)
    assert not _acepta(ids.EscenaId, escenario)


def test_numero_de_capitulo_con_formato_del_workspace() -> None:
    assert ids.nn(7, 24) == "07"
    assert ids.nn(7, 120) == "007"
    for fuera in (0, 25):
        with pytest.raises(ValueError, match="fuera de rango"):
            ids.nn(fuera, 24)
