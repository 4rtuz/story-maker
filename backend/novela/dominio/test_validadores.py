from typing import get_args

from novela.dominio.qa import TipoHallazgo
from novela.dominio.validadores import VALIDADORES, validador_de

ASIGNADOS = {
    "frontmatter_invalido": "vp_schema",
    "esquema_invalido": "vp_schema",
    "longitud_fuera_de_rango": "vp_longitud",
    "pista_ausente": "vp_pistas",
    "hilo_cerrado_sin_abrir": "vp_hilos",
    "id_inexistente": "vp_ids",
    "nombre_mal_escrito": "vp_nombres",
    "elemento_sin_cubrir": "vp_cobertura",
}


def test_catalogo() -> None:
    """CA-01: siete validadores sin repetir; bloquean en uno de sus puntos; binarios salvo la
    cobertura."""
    nombres = [v.nombre for v in VALIDADORES]
    assert nombres == [
        "vp_schema",
        "vp_longitud",
        "vp_pistas",
        "vp_hilos",
        "vp_ids",
        "vp_nombres",
        "vp_cobertura",
    ]
    for v in VALIDADORES:
        assert v.puntos and v.bloquea_en in v.puntos
        assert v.valor == ("fraccion" if v.nombre == "vp_cobertura" else "binario")


def test_tipos_asignados_una_vez() -> None:
    """CA-02: los ocho tipos de RF-02 en su validador, ninguno en dos, el resto en ninguno."""
    tipos = [t for v in VALIDADORES for t in v.tipos]
    assert len(tipos) == len(set(tipos))
    for tipo in get_args(TipoHallazgo):
        assert validador_de(tipo) == ASIGNADOS.get(tipo), tipo
