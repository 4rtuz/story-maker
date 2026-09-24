import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from novela.dominio.estado import Aparicion, Estado, Hecho, Hilo
from tests import estrategias


@given(estado=estrategias.estados, altas=st.lists(estrategias.hechos, max_size=5))
def test_libro_de_hechos_solo_crece(estado: Estado, altas: list[Hecho]) -> None:
    """validators.md §3.6: len(nuevo.libro_de_hechos) >= len(viejo.libro_de_hechos) para cualquier
    secuencia de operaciones que exponga el tipo, que son solo altas."""
    publicos = {n for n in dir(estado.libro_de_hechos) if not n.startswith("_")}
    assert publicos == {"añadir", "entradas"}
    for hecho in altas:
        nuevo = estado.model_copy(update={"libro_de_hechos": estado.libro_de_hechos.añadir(hecho)})
        assert len(nuevo.libro_de_hechos) >= len(estado.libro_de_hechos)
        assert nuevo.libro_de_hechos.entradas[: len(estado.libro_de_hechos)] == (
            estado.libro_de_hechos.entradas
        )
        estado = nuevo


@given(estrategias.estados)
def test_roundtrip_exacto(estado: Estado) -> None:
    """1.6b: sin exclude_none, `ubicacion: null` sigue siendo null y no «ausente»."""
    assert Estado.model_validate(estado.model_dump()) == estado
    assert Estado.model_validate_json(estado.model_dump_json()) == estado
    for objeto in estado.model_dump(mode="json")["objetos"]:
        assert "ubicacion" in objeto


def test_hilo_cerrado_lleva_capitulo_de_cierre() -> None:
    base = {"id": "hil-001", "abierto_en": 2, "descripcion": "¿quién apagó el faro?"}
    assert Hilo.model_validate({**base, "estado": "abierto"}).cerrado_en is None
    with pytest.raises(ValidationError, match="cerrado_en"):
        Hilo.model_validate({**base, "estado": "cerrado"})
    with pytest.raises(ValidationError, match="cerrado_en"):
        Hilo.model_validate({**base, "estado": "cerrado", "cerrado_en": 1})


@pytest.mark.parametrize(
    ("entidad", "tipo"),
    [("per-elena-vidal", "escenario"), ("esc-01-3", "escenario"), ("esc-puerto", "personaje")],
)
def test_aparicion_casa_tipo_y_prefijo(entidad: str, tipo: str) -> None:
    """VER-5: un personaje no es un lugar, y un id de escena no es un escenario."""
    with pytest.raises(ValidationError):
        Aparicion.model_validate({"entidad": entidad, "tipo": tipo, "capitulo": 1})
    assert Aparicion(entidad="esc-casa-del-faro", tipo="escenario", capitulo=1).capitulo == 1
