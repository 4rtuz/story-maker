"""Markdown con cabecera YAML: capítulos, fichas de canon y de plan, briefings, resúmenes.

Solo parte y une texto; no sabe de disco. Lo que devuelve `partir` es un dict sin validar, así que
quien lo llama lo pasa por un modelo antes de usarlo.
"""

from typing import Any

import yaml

_ABRE = "---\n"
_CIERRA = "\n---\n"


def partir(texto: str) -> tuple[dict[str, Any], str]:
    if not texto.startswith(_ABRE):
        raise ValueError("falta el frontmatter: el fichero no empieza por ---")
    fin = texto.find(_CIERRA, len(_ABRE) - 1)
    if fin == -1:
        if not texto.endswith("\n---"):
            raise ValueError("frontmatter sin cerrar")
        fin, cuerpo = len(texto) - 4, ""
    else:
        cuerpo = texto[fin + len(_CIERRA) :]
    meta = yaml.safe_load(texto[len(_ABRE) : fin]) if fin >= len(_ABRE) else None
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise ValueError("el frontmatter no es un mapa YAML")
    return meta, cuerpo


def unir(meta: dict[str, Any], cuerpo: str) -> str:
    return _ABRE + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n" + cuerpo
