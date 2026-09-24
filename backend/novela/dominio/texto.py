"""Qué cuenta como la misma cita: lo comparten el delta del cronista, el brief y la petición de
`novela cambio` (spec 0007, RF-11)."""

import re
import unicodedata

_ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """NFC y cada secuencia de espacios en blanco a un espacio. Nada más: ni comillas ni
    mayúsculas, porque una cita que solo casa aflojando la comparación ya no es una cita."""
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto))
