"""Guardrail de palabras prohibidas: qué cuenta como el mismo término (docs/guardrails.md).

Se compara por palabra completa y en forma normalizada: sin caja, sin tildes (la ñ se conserva:
«año» no es «ano») y reducida a una raíz que iguala plural, género y diminutivo. Una frase casa
si sus raíces aparecen seguidas, aunque crucen un salto de línea.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

Nivel = Literal["global", "cliente", "novela"]
NIVELES: tuple[Nivel, ...] = ("global", "cliente", "novela")

_LETRAS = re.compile(r"[^\W\d_]+")
_DIMINUTIVOS = ("ito", "ita", "illo", "illa")


@dataclass(frozen=True)
class Termino:
    texto: str
    nivel: Nivel


@dataclass(frozen=True)
class Coincidencia:
    termino: Termino
    forma: str  # tal como aparece en el texto
    linea: int  # de su primera palabra


def _plegar(palabra: str) -> str:
    """Sin caja ni marcas combinantes, salvo la virgulilla de la ñ."""
    nfd = unicodedata.normalize("NFD", palabra.casefold())
    return "".join(
        c
        for i, c in enumerate(nfd)
        if not unicodedata.combining(c) or (c == "̃" and i and nfd[i - 1] == "n")
    )


def raiz(palabra: str) -> str:
    """ponytail: heurística de sufijos, no un lematizador; «bonito» y «bono» comparten raíz. Un
    stemmer de verdad (Snowball) si los falsos positivos llegan a pesar."""
    w = _plegar(palabra)
    if w.endswith("es") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("s") and len(w) > 3:
        w = w[:-1]
    for sufijo in _DIMINUTIVOS:
        if w.endswith(sufijo) and len(w) > len(sufijo) + 2:
            return w[: -len(sufijo)]
    return w[:-1] if w[-1:] in ("o", "a", "e") and len(w) > 3 else w


def clave(texto: str) -> tuple[str, ...]:
    """Lo que identifica un término: dos textos con la misma clave son el mismo."""
    return tuple(raiz(t) for t in _LETRAS.findall(unicodedata.normalize("NFC", texto)))


def buscar(cuerpo: str, terminos: Iterable[Termino]) -> list[Coincidencia]:
    """Cada aparición de cada término, en orden de término y de texto."""
    palabras = [
        (m.group(), n)
        for n, linea in enumerate(unicodedata.normalize("NFC", cuerpo).splitlines(), 1)
        for m in _LETRAS.finditer(linea)
    ]
    raices = [raiz(p) for p, _ in palabras]
    coincidencias = []
    for termino in terminos:
        k = clave(termino.texto)
        if not k:
            continue
        for i in range(len(raices) - len(k) + 1):
            if tuple(raices[i : i + len(k)]) == k:
                forma = " ".join(p for p, _ in palabras[i : i + len(k)])
                coincidencias.append(Coincidencia(termino, forma, palabras[i][1]))
    return coincidencias
