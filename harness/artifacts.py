"""Lectura y escritura de los artefactos Markdown de la seccion 6.

Los esquemas se respetan byte a byte: el Anexo B.2 punto 3 lo exige, porque una
ejecucion en curso debe poder continuar bajo otro binding.
"""

from __future__ import annotations

import re
from pathlib import Path

CLUE_STATES = {"PLANTADA", "REFORZADA", "RESUELTA", "RED_HERRING", "DESACTIVADA"}
CLUE_HEADER = ("| id | descripción | tipo | estado | plantada en | "
               "tocada por última vez en | resolución prevista |")
CLUE_RULE = ("|----|-------------|------|--------|-------------|"
             "--------------------------|---------------------|")
TIMELINE_HEADER = "| día de ficción | fecha relativa | capítulo(s) | sucesos |"
TIMELINE_RULE = "|----------------|----------------|-------------|---------|"


# --------------------------------------------------------------------------
# utilidades genericas
# --------------------------------------------------------------------------
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def parse_table(text: str) -> list[list[str]]:
    """Filas de datos de la primera tabla Markdown, sin cabecera ni linea de regla."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):   # linea de regla
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def sections(text: str, level: int = 2) -> dict[str, str]:
    """Divide por encabezados del nivel dado. Devuelve {titulo: cuerpo}."""
    marker = "#" * level + " "
    out: dict[str, str] = {}
    current, buf = None, []
    for line in text.splitlines():
        if line.startswith(marker) and not line.startswith(marker + "#"):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current, buf = line[len(marker):].strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip()
    return out


def field(text: str, name: str) -> str:
    """Valor de una linea del tipo `- **Nombre:** valor`."""
    m = re.search(rf"^-\s*\*\*{re.escape(name)}:?\*\*\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def id_list(raw: str) -> list[str]:
    """Convierte `P-01, P-03` o `ninguna` en una lista de ids."""
    raw = raw.strip()
    if not raw or raw.lower() in {"ninguna", "ninguno", "-", "n/a", "none"}:
        return []
    return re.findall(r"P-\d+", raw)


WORD_RE = re.compile(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’-][0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*")


def word_count(text: str) -> int:
    """Palabras del cuerpo, descontando marcadores de escena y encabezados."""
    body = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    body = re.sub(r"^#.*$", " ", body, flags=re.M)
    return len(WORD_RE.findall(body))


# --------------------------------------------------------------------------
# 6.5 escaleta
# --------------------------------------------------------------------------
class OutlineEntry:
    def __init__(self, number: int, body: str):
        self.number = number
        self.body = body
        self.title = field(body, "Título provisional")
        self.pov = field(body, "Focalizador")
        self.day = field(body, "Día de ficción")
        self.location = field(body, "Localización")
        self.plant = id_list(field(body, "Pistas a plantar"))
        self.reinforce = id_list(field(body, "Pistas a reforzar"))
        self.resolve = id_list(field(body, "Pistas a resolver"))
        self.relevant = id_list(field(body, "Pistas relevantes en contexto"))
        self.starts = field(body, "Empieza en")
        self.ends = field(body, "Termina en")

    @property
    def clue_ids(self) -> list[str]:
        """7.3: el Escritor solo ve las pistas nombradas en su propia entrada."""
        seen: set[str] = set()
        out: list[str] = []
        for cid in self.plant + self.reinforce + self.resolve + self.relevant:
            if cid not in seen:
                seen.add(cid)
                out.append(cid)
        return out

    @property
    def day_int(self) -> int | None:
        m = re.search(r"-?\d+", self.day)
        return int(m.group(0)) if m else None

    @property
    def is_flashback(self) -> bool:
        return "flashback" in self.body.lower()

    def render(self) -> str:
        return f"### Capítulo {self.number}\n{self.body}".strip()

    def missing_fields(self) -> list[str]:
        pairs = [("Título provisional", self.title), ("Focalizador", self.pov),
                 ("Día de ficción", self.day), ("Localización", self.location),
                 ("Empieza en", self.starts), ("Termina en", self.ends)]
        missing = [name for name, value in pairs
                   if not value or "por determinar" in value.lower()]
        if not re.search(r"^\s*\d+\.\s+\S", self.body, re.M):
            missing.append("Beats")
        return missing

    def is_complete(self) -> bool:
        return not self.missing_fields()


def parse_outline(text: str) -> dict[int, OutlineEntry]:
    entries: dict[int, OutlineEntry] = {}
    for title, body in sections(text, 3).items():
        m = re.match(r"Capítulo\s+(\d+)", title)
        if m:
            n = int(m.group(1))
            entries[n] = OutlineEntry(n, body.split("\n## ")[0].strip())
    return entries


# --------------------------------------------------------------------------
# 6.6 ledger de pistas
# --------------------------------------------------------------------------
class Clue:
    FIELDS = ("id", "descripcion", "tipo", "estado", "plantada_en",
              "tocada_en", "resolucion_prevista")

    def __init__(self, **kw):
        for f in self.FIELDS:
            setattr(self, f, str(kw.get(f, "")).strip())

    @classmethod
    def from_row(cls, row: list[str]) -> "Clue":
        row = (row + [""] * 7)[:7]
        return cls(**dict(zip(cls.FIELDS, row)))

    def to_row(self) -> str:
        return "| " + " | ".join(getattr(self, f) or "-" for f in self.FIELDS) + " |"

    @property
    def is_red_herring(self) -> bool:
        return self.tipo.strip().lower() == "red_herring"

    @property
    def is_real(self) -> bool:
        return self.tipo.strip().lower() == "real"

    def int_field(self, name: str) -> int | None:
        m = re.search(r"\d+", getattr(self, name, "") or "")
        return int(m.group(0)) if m else None


class ClueLedger:
    def __init__(self, clues: list[Clue], notes: list[str]):
        self.clues = clues
        self.notes = notes

    @classmethod
    def load(cls, path: Path) -> "ClueLedger":
        text = read(path)
        if not text:
            return cls([], [])
        table_part = text.split("## Notas")[0]
        clues = [Clue.from_row(r) for r in parse_table(table_part)
                 if r and r[0] and r[0] != "-"]
        parts = text.split("## Notas", 1)
        notes: list[str] = []
        if len(parts) > 1:
            notes = [l.strip() for l in parts[1].splitlines()
                     if l.strip().startswith("- ") and "(sin notas)" not in l]
        return cls(clues, notes)

    def save(self, path: Path) -> None:
        lines = ["# Ledger de pistas", "", CLUE_HEADER, CLUE_RULE]
        lines += [c.to_row() for c in self.clues]
        lines += ["", "## Notas"]
        lines += self.notes if self.notes else ["- (sin notas)"]
        write(path, "\n".join(lines))

    def by_id(self, cid: str) -> Clue | None:
        return next((c for c in self.clues if c.id == cid), None)

    def filtered(self, ids: list[str]) -> list[Clue]:
        wanted = set(ids)
        return [c for c in self.clues if c.id in wanted]

    def live(self) -> list[Clue]:
        """7.3: el Continuista ve toda pista que no este RESUELTA ni DESACTIVADA."""
        return [c for c in self.clues
                if c.estado.upper() not in {"RESUELTA", "DESACTIVADA"}]

    def upsert(self, cid: str, state: str, chapter: int,
               description: str = "", kind: str = "real") -> Clue:
        clue = self.by_id(cid)
        if clue is None:
            clue = Clue(id=cid,
                        descripcion=description or "(introducida sobre la marcha)",
                        tipo=kind, estado=state, plantada_en=str(chapter),
                        tocada_en=str(chapter), resolucion_prevista="-")
            self.clues.append(clue)
            self.clues.sort(key=lambda c: c.id)
            return clue
        clue.estado = state
        clue.tocada_en = str(chapter)
        if not clue.plantada_en or clue.plantada_en == "-":
            clue.plantada_en = str(chapter)
        # El ciclo de vida de 8.1 es el que manda sobre el tipo: una pista que
        # entra en RED_HERRING o DESACTIVADA es un senuelo, aunque la escaleta
        # no lo dijera al sembrar el ledger.
        if state in {"RED_HERRING", "DESACTIVADA"}:
            clue.tipo = "red_herring"
        return clue

    def render(self, clues: list[Clue] | None = None) -> str:
        rows = self.clues if clues is None else clues
        return "\n".join([CLUE_HEADER, CLUE_RULE] + [c.to_row() for c in rows])


# --------------------------------------------------------------------------
# 6.7 cronologia
# --------------------------------------------------------------------------
class Timeline:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    @classmethod
    def load(cls, path: Path) -> "Timeline":
        rows = []
        for r in parse_table(read(path)):
            r = (r + [""] * 4)[:4]
            if not r[0] or r[0] == "-":
                continue
            rows.append({"dia": r[0].strip(), "fecha": r[1].strip(),
                         "capitulos": r[2].strip(), "sucesos": r[3].strip()})
        return cls(rows)

    def save(self, path: Path) -> None:
        self.rows = self._sorted()
        write(path, "# Cronología\n\n" + self.render())

    def _sorted(self) -> list[dict]:
        def key(r):
            try:
                return (0, int(r["dia"]))
            except (ValueError, TypeError):
                return (1, 0)
        return sorted(self.rows, key=key)

    def add(self, day: int, event: str, chapter: int) -> None:
        for r in self.rows:
            if r["dia"] == str(day):
                if event and event not in r["sucesos"]:
                    r["sucesos"] = f"{r['sucesos']}; {event}".strip("; ")
                caps = [c.strip() for c in r["capitulos"].split(",")
                        if c.strip() and c.strip() != "-"]
                if str(chapter) not in caps:
                    caps.append(str(chapter))
                r["capitulos"] = ", ".join(caps)
                return
        self.rows.append({"dia": str(day), "fecha": "-",
                          "capitulos": str(chapter), "sucesos": event})

    def max_day(self) -> int | None:
        days = []
        for r in self.rows:
            try:
                days.append(int(r["dia"]))
            except (ValueError, TypeError):
                pass
        return max(days) if days else None

    def day_of_chapter(self, chapter: int) -> int | None:
        days = []
        for r in self.rows:
            caps = [c.strip() for c in r["capitulos"].split(",")]
            if str(chapter) in caps:
                try:
                    days.append(int(r["dia"]))
                except (ValueError, TypeError):
                    pass
        return max(days) if days else None

    def last_days(self, n: int) -> list[dict]:
        rows = self._sorted()
        return rows[-n:] if n > 0 else rows

    def render(self, rows: list[dict] | None = None) -> str:
        rows = self._sorted() if rows is None else rows
        lines = [TIMELINE_HEADER, TIMELINE_RULE]
        for r in rows:
            lines.append(f"| {r['dia']} | {r['fecha'] or '-'} | "
                         f"{r['capitulos'] or '-'} | {r['sucesos'] or '-'} |")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# 6.8 estado de personajes
# --------------------------------------------------------------------------
CHAR_FIELDS = ["Última aparición", "Ubicación", "Situación física", "Sabe que",
               "Cree erróneamente que", "Oculta a", "Objetos en su posesión"]

_CHAR_ALIAS = {
    "ultima_aparicion": "Última aparición",
    "ubicacion": "Ubicación",
    "situacion_fisica": "Situación física",
    "sabe_que": "Sabe que",
    "cree_erroneamente_que": "Cree erróneamente que",
    "oculta_a": "Oculta a",
    "objetos": "Objetos en su posesión",
    "objetos_en_su_posesion": "Objetos en su posesión",
}


class CharacterState:
    def __init__(self, chars: dict[str, dict[str, str]]):
        self.chars = chars

    @classmethod
    def load(cls, path: Path) -> "CharacterState":
        chars: dict[str, dict[str, str]] = {}
        for name, body in sections(read(path), 2).items():
            chars[name] = {f: field(body, f) for f in CHAR_FIELDS}
        return cls(chars)

    def save(self, path: Path) -> None:
        write(path, "# Estado de personajes\n\n" + self.render() + "\n")

    def apply(self, name: str, changes: dict, chapter: int) -> None:
        entry = self.chars.setdefault(name, {f: "" for f in CHAR_FIELDS})
        for key, value in (changes or {}).items():
            canonical = _CHAR_ALIAS.get(key.strip().lower().replace(" ", "_"),
                                        key.strip())
            match = next((f for f in CHAR_FIELDS
                          if f.lower() == canonical.lower()), None)
            if match is None:
                continue
            entry[match] = ", ".join(str(v) for v in value) \
                if isinstance(value, list) else str(value)
        entry["Última aparición"] = f"capítulo {chapter}"

    def render(self, names: list[str] | None = None) -> str:
        if names is None:
            selected = sorted(self.chars)
        else:
            wanted = {n.strip().lower() for n in names}
            selected = [n for n in sorted(self.chars)
                        if n.strip().lower() in wanted
                        or any(w in n.strip().lower() for w in wanted)]
        out: list[str] = []
        for name in selected:
            out.append(f"## {name}")
            for f in CHAR_FIELDS:
                out.append(f"- **{f}:** {self.chars[name].get(f, '') or '-'}")
            out.append("")
        return "\n".join(out).strip()

    def knows(self, name: str) -> str:
        return self.chars.get(name, {}).get("Sabe que", "")


# --------------------------------------------------------------------------
# 6.11 ficha de capitulo
# --------------------------------------------------------------------------
def render_card(n: int, ficha: dict, words: int, iterations: int,
                mean: float) -> str:
    present = ficha.get("personajes_presentes", [])
    if isinstance(present, list):
        present = ", ".join(str(p) for p in present)
    return "\n".join([
        f"# Ficha del capítulo {n}",
        f"- **Título:** {ficha.get('titulo', '')}",
        f"- **Focalizador:** {ficha.get('focalizador', '')}",
        f"- **Día de ficción:** {ficha.get('dia_ficcion', '')}",
        f"- **Personajes presentes:** {present}",
        f"- **Gancho final:** {ficha.get('gancho_final', '')}",
        f"- **Palabras:** {words}",
        f"- **Iteraciones consumidas:** {iterations}",
        f"- **Media del Evaluador:** {mean}",
        "",
        "## Resumen (120 palabras)",
        str(ficha.get("resumen_120", "")).strip(),
    ])


class Card:
    def __init__(self, n: int, text: str):
        self.number = n
        self.text = text
        head = text.split("## Resumen")[0]
        self.title = field(head, "Título")
        self.pov = field(head, "Focalizador")
        self.day = field(head, "Día de ficción")
        self.present = field(head, "Personajes presentes")
        self.hook = field(head, "Gancho final")
        parts = text.split("## Resumen (120 palabras)")
        self.summary = parts[1].strip() if len(parts) > 1 else ""

    @classmethod
    def load(cls, path: Path, n: int) -> "Card | None":
        text = read(path)
        return cls(n, text) if text.strip() else None

    def present_list(self) -> list[str]:
        return [p.strip() for p in self.present.split(",") if p.strip()]

    def first_sentence(self) -> str:
        flat = " ".join(self.summary.split())
        m = re.match(r"(.+?[.!?])(\s|$)", flat)
        return m.group(1).strip() if m else flat[:200]
