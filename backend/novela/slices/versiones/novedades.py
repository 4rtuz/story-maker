"""Novedades entre dos versiones (spec 0007, D18): el sha256 del capítulo es la custodia, así que
comparar sellos no añade ninguna fuente nueva."""

from collections.abc import Mapping


def calcular(anterior: Mapping[int, str], actual: Mapping[int, str]) -> list[int]:
    """Los capítulos cerrados en `actual` cuyo hash difiere o falta en `anterior`, ascendentes."""
    return sorted(c for c, sha in actual.items() if anterior.get(c) != sha)
