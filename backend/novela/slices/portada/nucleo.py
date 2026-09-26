"""El prompt y la URL de la portada (spec 0015 §5.1), sin disco ni red.

La petición sale a un tercero: solo lleva el subgénero y las descripciones de los escenarios, y de
ellas se quitan los nombres de los personajes (RF-02, D3).
"""

import re
import urllib.parse
import zlib
from collections.abc import Iterable

from novela.dominio.config import Subgenero

SERVICIO = "https://image.pollinations.ai/prompt/"
_GENERO: dict[Subgenero, str] = {
    "thriller_psicologico": "psychological thriller",
    "noir": "noir",
    "domestic_suspense": "domestic suspense",
    "procedural": "police procedural",
}
# ponytail: tope fijo para que la URL no pase de lo que acepta el servicio; con más escenarios,
# resumirlos en vez de cortar.
_MAX_ESCENARIOS = 600


def _sin_nombres(texto: str, nombres: Iterable[str]) -> str:
    """Cada palabra con mayúscula de un nombre o alias, como palabra entera: «Elena», no «del»."""
    partes = {p for n in nombres for p in n.split() if len(p) > 2 and p[0].isupper()}
    for parte in sorted(partes, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(parte)}\b", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def prompt(subgenero: Subgenero, escenarios: Iterable[str], nombres: Iterable[str]) -> str:
    lugares = _sin_nombres(" ".join(escenarios), list(nombres))[:_MAX_ESCENARIOS]
    return (
        f"Cinematic book cover illustration for a {_GENERO[subgenero]} suspense novel. "
        f"Setting: {lugares} "
        "Moody atmospheric lighting, deep shadows, dramatic composition, painterly, high detail, "
        "portrait orientation. No text, no letters, no words, no title, no typography."
    )


def url(slug: str, texto: str) -> str:
    # La misma semilla para el mismo slug; Pollinations no admite más de 2^31 - 1.
    semilla = zlib.crc32(slug.encode()) & 0x7FFFFFFF
    consulta = urllib.parse.urlencode(
        {"width": 768, "height": 1152, "seed": semilla, "nologo": "true"}
    )
    return f"{SERVICIO}{urllib.parse.quote(texto, safe='')}?{consulta}"


def es_jpeg(datos: bytes) -> bool:
    return datos.startswith(b"\xff\xd8\xff")
