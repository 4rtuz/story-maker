"""Las reglas de `novela lint-prosa`: deterministas, sin modelo, sobre el cuerpo de un capítulo.

Heurísticas de superficie, no análisis sintáctico: sirven para señalar dónde mirar, no para
aprobar ni rechazar un capítulo (docs/linters-prosa.md). Las listas viven en
`backend/config/prosa.yaml`, versionadas con el harness.
"""

import re
from collections import Counter
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

import yaml

from novela.dominio.base import Modelo
from novela.plataforma.workspace import CONFIG_DIR

Regla = Literal["repeticiones", "legibilidad", "lexico", "estilo"]
REGLAS: tuple[Regla, ...] = ("repeticiones", "legibilidad", "lexico", "estilo")

_PALABRA = re.compile(r"[a-záéíóúüñ]+")
_VOCAL, _FUERTE = set("aeiouáéíóúü"), set("aeoáéíóú")
# Por debajo de estas palabras la fórmula de legibilidad es ruido.
_MIN_PALABRAS_LEGIBILIDAD = 20


class Hallazgo(Modelo):
    regla: Regla
    codigo: str
    # Párrafo de prosa, desde 1, sin contar títulos; None si el hallazgo es del capítulo entero.
    parrafo: int | None
    evidencia: str


class Analisis(Modelo):
    hallazgos: list[Hallazgo]
    # prosa_<regla>: 1 − párrafos con hallazgo de la regla / párrafos, con suelo 0.
    scores: dict[str, float]


@dataclass(frozen=True)
class Contexto:
    punto_de_vista: str
    tiempo_verbal: str
    # Del brief de una novela de regalo, si lo hay: bajan los umbrales de la regla 2.
    edad: int | None = None
    tono: str | None = None

    @property
    def max_palabras_frase(self) -> int:
        if self.edad is not None and self.edad < 12:
            return 20
        if self.edad is not None and self.edad < 16:
            return 25
        return 35

    @property
    def min_legibilidad(self) -> float:
        """Fernández-Huerta: 80 es fácil, 70 bastante fácil, 60 normal, 50 algo difícil."""
        if self.edad is not None and self.edad < 12:
            return 80
        if self.edad is not None and self.edad < 16:
            return 70
        return 65 if self.tono in ("ligero", "tierno") else 55


@cache
def listas() -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load((CONFIG_DIR / "prosa.yaml").read_text("utf-8"))
    return datos


def parrafos(cuerpo: str) -> list[str]:
    bloques = (b.strip() for b in re.split(r"\n\s*\n", cuerpo))
    return [b for b in bloques if b and not b.startswith("#")]


def _palabras(texto: str) -> list[str]:
    return _PALABRA.findall(texto.lower())


def _repeticiones(n: int, parrafo: str) -> list[Hallazgo]:
    cfg = listas()
    funcionales = set(cfg["funcionales"])
    cuenta = Counter(p for p in _palabras(parrafo) if len(p) >= 4 and p not in funcionales)
    hallazgos = [
        Hallazgo(regla="repeticiones", codigo="palabra_repetida", parrafo=n, evidencia=f"{p} ×{c}")
        for p, c in cuenta.items()
        if c >= cfg["repeticion_minima"]
    ]
    bajo = parrafo.lower()
    for muletilla in cfg["muletillas"]:
        c = len(re.findall(rf"\b{re.escape(muletilla)}\b", bajo))
        if c >= 2:
            hallazgos.append(
                Hallazgo(
                    regla="repeticiones",
                    codigo="muletilla",
                    parrafo=n,
                    evidencia=f"{muletilla} ×{c}",
                )
            )
    return hallazgos


def silabas(palabra: str) -> int:
    """Núcleos vocálicos: dos vocales seguidas son una sílaba salvo que las dos sean fuertes (o
    una débil acentuada). Aproximación: no ve la «u» muda de que/gui ni la «y» vocal final."""
    n, previa = 0, ""
    for c in palabra:
        if c in _VOCAL and (previa not in _VOCAL or (previa in _FUERTE and c in _FUERTE)):
            n += 1
        previa = c
    return max(1, n)


def fernandez_huerta(texto: str) -> float:
    """206,84 − 60·(sílabas/palabra) − 1,02·(palabras/frase), la forma corregida de la fórmula."""
    frases = [f for f in re.split(r"[.!?…]+", texto) if _palabras(f)]
    palabras = _palabras(texto)
    total = sum(silabas(p) for p in palabras)
    return 206.84 - 60 * total / len(palabras) - 1.02 * len(palabras) / max(1, len(frases))


def _legibilidad(n: int, parrafo: str, ctx: Contexto) -> list[Hallazgo]:
    hallazgos = []
    for frase in re.split(r"(?<=[.!?…])\s+", parrafo):
        largo = len(_palabras(frase))
        if largo > ctx.max_palabras_frase:
            inicio = " ".join(frase.split()[:6])
            evidencia = f"{largo} palabras (máx. {ctx.max_palabras_frase}): {inicio}…"
            hallazgos.append(
                Hallazgo(regla="legibilidad", codigo="frase_larga", parrafo=n, evidencia=evidencia)
            )
    if len(_palabras(parrafo)) >= _MIN_PALABRAS_LEGIBILIDAD:
        indice = fernandez_huerta(parrafo)
        if indice < ctx.min_legibilidad:
            evidencia = f"Fernández-Huerta {indice:.1f} (mín. {ctx.min_legibilidad})"
            hallazgos.append(
                Hallazgo(
                    regla="legibilidad", codigo="legibilidad_baja", parrafo=n, evidencia=evidencia
                )
            )
    return hallazgos


@cache
def _cliches() -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(c, re.IGNORECASE) for c in listas()["cliches"])


def _lexico(n: int, parrafo: str) -> list[Hallazgo]:
    cfg = listas()
    no_adverbios = set(cfg["no_adverbios"])
    adverbios = [p for p in _palabras(parrafo) if p.endswith("mente") and p not in no_adverbios]
    hallazgos = []
    if len(adverbios) >= cfg["adverbios_mente_por_parrafo"]:
        evidencia = ", ".join(adverbios)
        hallazgos.append(
            Hallazgo(regla="lexico", codigo="adverbios_mente", parrafo=n, evidencia=evidencia)
        )
    for patron in _cliches():
        hallazgos += [
            Hallazgo(regla="lexico", codigo="cliche", parrafo=n, evidencia=m.group(0).lower())
            for m in patron.finditer(parrafo)
        ]
    return hallazgos


_CITA = re.compile(r"«[^»]*»|“[^”]*”|\"[^\"]*\"")
_TU, _USTED = frozenset({"tú", "ti", "te", "contigo", "tu", "tus"}), frozenset({"usted"})
# Narración mínima para juzgar el narrador del capítulo entero.
_MIN_PALABRAS_NARRADOR = 30


def partir_dialogo(parrafo: str) -> tuple[str, str]:
    """(narración, diálogo). Raya al inicio: los tramos entre rayas alternan diálogo e inciso del
    narrador. Fuera de eso, lo que va entre comillas es diálogo."""
    if parrafo.startswith(("—", "-")):
        tramos = re.split(r"—|(?<!\w)-|-(?!\w)", parrafo)
        return " ".join(tramos[2::2]), " ".join(tramos[1::2])
    citas = _CITA.findall(parrafo)
    return _CITA.sub(" ", parrafo), " ".join(citas)


def _tiempos(palabras: list[str]) -> tuple[int, int]:
    cfg = listas()
    formas, presente = set(cfg["pasado_formas"]), set(cfg["presente_formas"])
    terminaciones, excepciones = tuple(cfg["pasado_terminaciones"]), set(cfg["no_pasado"])
    pasado = sum(
        p in formas or (len(p) >= 5 and p.endswith(terminaciones) and p not in excepciones)
        for p in palabras
    )
    return pasado, sum(p in presente for p in palabras)


def _estilo(bloques: list[str], ctx: Contexto) -> list[Hallazgo]:
    primera = set(listas()["primera_persona"])
    hallazgos = []
    narrado: list[str] = []
    for n, parrafo in enumerate(bloques, start=1):
        narracion, dialogo = partir_dialogo(parrafo)
        palabras = _palabras(narracion)
        narrado += palabras
        marcas = [p for p in palabras if p in primera]
        if ctx.punto_de_vista == "tercera_limitada" and marcas:
            hallazgos.append(
                Hallazgo(
                    regla="estilo",
                    codigo="narrador_primera_persona",
                    parrafo=n,
                    evidencia=", ".join(marcas),
                )
            )
        pasado, presente = _tiempos(palabras)
        dominante = "pasado" if pasado > presente else "presente"
        if abs(pasado - presente) >= 2 and dominante != ctx.tiempo_verbal:
            evidencia = f"pasado {pasado}, presente {presente} (config: {ctx.tiempo_verbal})"
            hallazgos.append(
                Hallazgo(regla="estilo", codigo="tiempo_verbal", parrafo=n, evidencia=evidencia)
            )
        habla = set(_palabras(dialogo))
        if habla & _TU and habla & _USTED:
            evidencia = ", ".join(sorted(habla & (_TU | _USTED)))
            hallazgos.append(
                Hallazgo(regla="estilo", codigo="tratamiento_mixto", parrafo=n, evidencia=evidencia)
            )
    marcas_capitulo = sum(p in primera for p in narrado)
    if (
        ctx.punto_de_vista == "primera_persona"
        and len(narrado) >= _MIN_PALABRAS_NARRADOR
        and marcas_capitulo * 100 < len(narrado)
    ):
        evidencia = f"{marcas_capitulo} marcas de primera persona en {len(narrado)} palabras"
        hallazgos.append(
            Hallazgo(
                regla="estilo", codigo="narrador_tercera_persona", parrafo=None, evidencia=evidencia
            )
        )
    return hallazgos


def analizar(cuerpo: str, ctx: Contexto) -> Analisis:
    bloques = parrafos(cuerpo)
    hallazgos: list[Hallazgo] = []
    for n, parrafo in enumerate(bloques, start=1):
        hallazgos += _repeticiones(n, parrafo)
        hallazgos += _legibilidad(n, parrafo, ctx)
        hallazgos += _lexico(n, parrafo)
    hallazgos += _estilo(bloques, ctx)
    scores = {}
    for regla in REGLAS:
        tocados = {h.parrafo for h in hallazgos if h.regla == regla}
        scores[f"prosa_{regla}"] = round(max(0.0, 1 - len(tocados) / max(1, len(bloques))), 4)
    return Analisis(hallazgos=hallazgos, scores=scores)
