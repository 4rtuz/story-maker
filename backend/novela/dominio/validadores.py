"""Catálogo de validadores programáticos (spec 0009 §8.4): nombre estable, dónde corre, dónde
bloquea, qué tipos de hallazgo produce y cómo se puntúa. Lo leen validar, checkpoint y auditar;
`docs/validators.md` §3.10 lo describe y un test comprueba que coinciden."""

from dataclasses import dataclass
from typing import Literal

from novela.dominio.qa import TipoHallazgo

NombreValidador = Literal[
    "vp_schema", "vp_longitud", "vp_pistas", "vp_hilos", "vp_ids", "vp_nombres", "vp_cobertura"
]
Punto = Literal["validar", "checkpoint", "auditar"]


@dataclass(frozen=True)
class Validador:
    nombre: NombreValidador
    puntos: tuple[Punto, ...]
    bloquea_en: Punto
    tipos: tuple[TipoHallazgo, ...]
    valor: Literal["binario", "fraccion"]


VALIDADORES: tuple[Validador, ...] = (
    Validador(
        "vp_schema",
        ("validar", "checkpoint"),
        "checkpoint",
        ("frontmatter_invalido", "esquema_invalido"),
        "binario",
    ),
    Validador("vp_longitud", ("validar",), "validar", ("longitud_fuera_de_rango",), "binario"),
    Validador("vp_pistas", ("validar",), "validar", ("pista_ausente",), "binario"),
    Validador("vp_hilos", ("validar",), "validar", ("hilo_cerrado_sin_abrir",), "binario"),
    Validador("vp_ids", ("validar",), "validar", ("id_inexistente",), "binario"),
    Validador("vp_nombres", ("validar",), "validar", ("nombre_mal_escrito",), "binario"),
    Validador(
        "vp_cobertura", ("checkpoint", "auditar"), "auditar", ("elemento_sin_cubrir",), "fraccion"
    ),
)


def validador_de(tipo: TipoHallazgo) -> NombreValidador | None:
    return next((v.nombre for v in VALIDADORES if tipo in v.tipos), None)
