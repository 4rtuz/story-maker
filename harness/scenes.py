"""Marcadores de escena, hashes y verificacion de parches dirigidos (5.2, 9.5).

La comprobacion de hashes es barata y evita la regresion silenciosa, que es el
fallo caracteristico de los bucles de reescritura (9.5).
"""

from __future__ import annotations

import hashlib
import re

SCENE_RE = re.compile(r"<!--\s*ESCENA\s+(\d+)\s*-->", re.I)
END_MARKER = "<!-- FIN -->"
END_RE = re.compile(r"<!--\s*FIN\s*-->", re.I)
TITLE_RE = re.compile(r"^#\s*Cap[íi]tulo\s+(\d+)\s*(?:[-—–]\s*(.*))?$", re.M)


class Chapter:
    """Un capitulo parseado en titulo + escenas numeradas."""

    def __init__(self, text: str):
        self.raw = text
        self.title = ""
        self.number: int | None = None
        m = TITLE_RE.search(text)
        if m:
            self.number = int(m.group(1))
            self.title = (m.group(2) or "").strip()
        self.scenes = self._split(text)

    @staticmethod
    def _split(text: str) -> dict[int, str]:
        marks = list(SCENE_RE.finditer(text))
        scenes: dict[int, str] = {}
        for i, mark in enumerate(marks):
            start = mark.end()
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[start:end]
            body = END_RE.split(body)[0]
            scenes[int(mark.group(1))] = body.strip()
        return scenes

    @property
    def has_end_marker(self) -> bool:
        return bool(END_RE.search(self.raw))

    def hashes(self) -> dict[int, str]:
        """Hash por escena, sobre el texto normalizado en espacios: una diferencia
        de sangrado no debe contar como reescritura, un cambio de palabra si."""
        return {n: hashlib.sha256(" ".join(body.split()).encode("utf-8")).hexdigest()
                for n, body in self.scenes.items()}

    def render(self) -> str:
        title = f"# Capítulo {self.number} — {self.title}".rstrip(" —")
        parts = [title, ""]
        for n in sorted(self.scenes):
            parts += [f"<!-- ESCENA {n} -->", self.scenes[n], ""]
        parts.append(END_MARKER)
        return "\n".join(parts)


def structural_problems(text: str, cfg) -> list[str]:
    """Comprobaciones deterministas previas a gastar cuota en evaluar.

    Detectan truncamiento y formato roto (12), no calidad literaria.
    """
    problems: list[str] = []
    ch = Chapter(text)
    caps = cfg["capitulos"]
    smin, smax = caps["escenas_min"], caps["escenas_max"]

    if ch.number is None:
        problems.append("Falta el encabezado `# Capítulo N — <título>`.")
    if not ch.has_end_marker:
        problems.append(f"Falta el marcador final {END_MARKER} (respuesta truncada).")
    if not ch.scenes:
        problems.append("No hay ningún marcador `<!-- ESCENA n -->`.")
    elif not (smin <= len(ch.scenes) <= smax):
        problems.append(f"{len(ch.scenes)} escenas; el perfil exige entre {smin} y {smax}.")

    expected = sorted(ch.scenes)
    if expected and expected != list(range(1, len(expected) + 1)):
        problems.append(f"Las escenas no están numeradas 1..n: {expected}.")

    from .artifacts import word_count
    words = word_count(text)
    target = caps["palabras_objetivo"]
    tol = caps["tolerancia_palabras"]
    lo, hi = int(target * (1 - tol)), int(target * (1 + tol))
    if not (lo <= words <= hi):
        problems.append(f"{words} palabras; el perfil exige entre {lo} y {hi}.")

    empty = [n for n, body in ch.scenes.items() if len(body.split()) < 5]
    if empty:
        problems.append(f"Escenas prácticamente vacías: {empty}.")

    return problems


# --------------------------------------------------------------------------
# deriva de idioma (12)
# --------------------------------------------------------------------------
SPANISH_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "pero", "que", "qué", "en", "con", "por", "para", "sin", "sobre",
    "su", "sus", "se", "le", "les", "lo", "no", "sí", "más", "como", "cuando",
    "porque", "hasta", "desde", "entre", "era", "fue", "había", "estaba", "ya",
    "muy", "también", "aunque", "mientras", "él", "ella", "ellos", "nada",
}


def spanish_ratio(text: str) -> float:
    """Proporcion de palabras funcionales espanolas. Heuristica de 12."""
    from .artifacts import WORD_RE
    words = [w.lower() for w in WORD_RE.findall(text)]
    if not words:
        return 0.0
    return sum(1 for w in words if w in SPANISH_STOPWORDS) / len(words)


def language_drift(text: str, threshold: float = 0.18) -> bool:
    return spanish_ratio(text) < threshold


# --------------------------------------------------------------------------
# 9.5 aplicacion del parche
# --------------------------------------------------------------------------
def reconcile_patch(original_text: str, patched_text: str,
                    patched_scenes: list[int]) -> tuple[str, list[int]]:
    """Devuelve (texto final, escenas que el modelo alteró sin permiso).

    Las escenas no señaladas que el modelo haya tocado se restauran desde el
    original; solo se conservan las escenas efectivamente parcheadas (9.5).
    """
    original = Chapter(original_text)
    patched = Chapter(patched_text)
    allowed = set(patched_scenes)

    original_hashes = original.hashes()
    patched_hashes = patched.hashes()

    violated = sorted(
        n for n in original.scenes
        if n not in allowed
        and n in patched_hashes
        and patched_hashes[n] != original_hashes[n]
    )

    result = Chapter(patched_text)
    for n in original.scenes:
        if n not in allowed:
            result.scenes[n] = original.scenes[n]
    # una escena que el modelo haya borrado se restaura siempre
    for n, body in original.scenes.items():
        result.scenes.setdefault(n, body)

    if result.number is None:
        result.number = original.number
    if not result.title:
        result.title = original.title

    return result.render(), violated
