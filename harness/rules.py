"""Reglas bloqueantes de continuidad (8.2) y auditoria final (8.3).

Las tres primeras reglas de 8.2 son verificables en codigo, sin llamada al
modelo, y la especificacion exige implementarlas asi. La cuarta exige juicio del
modelo y vive en el prompt del Continuista; aqui solo se deja su rastro. La
quinta es aritmetica sobre la cronologia.
"""

from __future__ import annotations

from .artifacts import Card, ClueLedger, Timeline, parse_outline, read


class Violation:
    def __init__(self, rule: str, severity: str, message: str):
        self.rule = rule
        self.severity = severity      # ALTA | MEDIA | BAJA
        self.message = message

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule}: {self.message}"


# --------------------------------------------------------------------------
# 8.2 reglas comprobables en codigo
# --------------------------------------------------------------------------
def rule_1_nothing_resolved_unplanted(ledger: ClueLedger) -> list[Violation]:
    """Nada se resuelve sin haber sido plantado en un capitulo estrictamente anterior."""
    out = []
    for clue in ledger.clues:
        if clue.estado.upper() != "RESUELTA":
            continue
        planted = clue.int_field("plantada_en")
        touched = clue.int_field("tocada_en")
        if planted is None:
            out.append(Violation("no_resolver_sin_plantar", "ALTA",
                                 f"{clue.id} está RESUELTA sin capítulo de plantado."))
        elif touched is not None and planted >= touched:
            out.append(Violation(
                "no_resolver_sin_plantar", "ALTA",
                f"{clue.id} se resuelve en el capítulo {touched} pero se plantó "
                f"en el {planted}: el plantado debe ser estrictamente anterior."))
    return out


def rule_2_every_real_clue_has_resolution(ledger: ClueLedger) -> list[Violation]:
    out = []
    for clue in ledger.clues:
        if not clue.is_real:
            continue
        if clue.estado.upper() == "RESUELTA":
            continue
        if clue.int_field("resolucion_prevista") is None:
            out.append(Violation(
                "toda_pista_real_con_resolucion", "ALTA",
                f"{clue.id} es de tipo real y no tiene capítulo de resolución asignado."))
    return out


def rule_3_every_red_herring_defused(ledger: ClueLedger, total: int,
                                     upcoming_only: bool = True) -> list[Violation]:
    out = []
    for clue in ledger.clues:
        if not clue.is_red_herring:
            continue
        if clue.estado.upper() == "DESACTIVADA":
            continue
        planned = clue.int_field("resolucion_prevista")
        if planned is None:
            out.append(Violation(
                "todo_red_herring_desactivado", "ALTA",
                f"{clue.id} es un red herring sin capítulo de desactivación asignado."))
        elif upcoming_only and planned > total:
            out.append(Violation(
                "todo_red_herring_desactivado", "ALTA",
                f"{clue.id} tiene su desactivación prevista en el capítulo {planned}, "
                f"fuera de los {total} capítulos de la obra."))
    return out


def rule_5_monotonic_timeline(timeline: Timeline, chapter: int, day: int | None,
                              flashback: bool) -> list[Violation]:
    """El dia de ficcion nunca retrocede, salvo flashback marcado en la escaleta."""
    if day is None or flashback:
        return []
    previous = [d for d in (timeline.day_of_chapter(c) for c in range(1, chapter))
                if d is not None]
    if previous and day < max(previous):
        return [Violation(
            "cronologia_monotona", "ALTA",
            f"El capítulo {chapter} transcurre el día {day}, anterior al día "
            f"{max(previous)} ya alcanzado, y la escaleta no lo marca como flashback.")]
    return []


def stale_clues(ledger: ClueLedger, chapter: int, max_gap: int) -> list[Violation]:
    """Pistas plantadas y sin tocar durante demasiados capitulos (5.5, 6.0)."""
    out = []
    for clue in ledger.clues:
        if clue.estado.upper() not in {"PLANTADA", "REFORZADA", "RED_HERRING"}:
            continue
        touched = clue.int_field("tocada_en")
        if touched is not None and chapter - touched > max_gap:
            out.append(Violation(
                "max_capitulos_pista_sin_tocar", "MEDIA",
                f"{clue.id} lleva {chapter - touched} capítulos sin tocarse "
                f"(máximo {max_gap})."))
    return out


def enabled(cfg, name: str) -> bool:
    return bool(cfg["continuidad"]["reglas_bloqueantes"].get(name, True))


def check_state(cfg, chapter: int) -> list[Violation]:
    """Reglas 1, 2, 3 y 5 contra el estado en disco, mas pistas rancias."""
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    timeline = Timeline.load(cfg.state_path("cronologia.md"))
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    entry = outline.get(chapter)

    out: list[Violation] = []
    if enabled(cfg, "no_resolver_sin_plantar"):
        out += rule_1_nothing_resolved_unplanted(ledger)
    if enabled(cfg, "toda_pista_real_con_resolucion"):
        out += rule_2_every_real_clue_has_resolution(ledger)
    if enabled(cfg, "todo_red_herring_desactivado"):
        out += rule_3_every_red_herring_defused(ledger, cfg.total_chapters)
    if enabled(cfg, "cronologia_monotona") and entry is not None:
        out += rule_5_monotonic_timeline(timeline, chapter, entry.day_int,
                                         entry.is_flashback)
    out += stale_clues(ledger, chapter,
                       cfg["continuidad"]["max_capitulos_pista_sin_tocar"])
    return out


# --------------------------------------------------------------------------
# 8.3 auditoria previa al ultimo capitulo
# --------------------------------------------------------------------------
def final_audit(cfg) -> list[Violation]:
    """Ninguna pista real sin resolver, ningun red herring sin desactivar.

    Es el unico punto en el que el sistema puede negarse a continuar por
    razones de trama: una novela de suspense que termina con cabos sueltos ha
    fracasado, por bien escrito que este cada capitulo (8.3).
    """
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    last = cfg.total_chapters
    out: list[Violation] = []

    for clue in ledger.clues:
        state = clue.estado.upper()
        if state in {"RESUELTA", "DESACTIVADA"}:
            continue                      # cerrada por cualquiera de las dos vías de 8.1
        if clue.is_real and state != "RESUELTA":
            planned = clue.int_field("resolucion_prevista")
            if planned is None or planned < last:
                out.append(Violation(
                    "auditoria_final", "ALTA",
                    f"{clue.id} ({clue.descripcion}) es una pista real sin resolver "
                    f"y sin resolución prevista en el capítulo {last}."))
        if clue.is_red_herring and state != "DESACTIVADA":
            planned = clue.int_field("resolucion_prevista")
            if planned is None or planned < last:
                out.append(Violation(
                    "auditoria_final", "ALTA",
                    f"{clue.id} ({clue.descripcion}) es un red herring todavía vivo "
                    f"y sin desactivación prevista en el capítulo {last}."))

    out += rule_1_nothing_resolved_unplanted(ledger)
    return out


# --------------------------------------------------------------------------
# validacion de esquema de la biblia (Puerta 1, fase F2)
# --------------------------------------------------------------------------
REQUIRED_SECTIONS = {
    "premisa.md": ["Logline", "Situación de partida", "El secreto", "La revelación",
                   "Pistas que sostienen la revelación", "Apuesta temática", "Final"],
    "voz-y-estilo.md": ["Parámetros fijos", "Reglas positivas", "Reglas negativas",
                        "Pasaje ancla"],
}


def validate_bible(cfg) -> list[Violation]:
    from .artifacts import sections

    out: list[Violation] = []
    for filename, required in REQUIRED_SECTIONS.items():
        text = read(cfg.bible_path(filename))
        if not text.strip():
            out.append(Violation("esquema", "ALTA", f"{filename} no existe o está vacío."))
            continue
        present = set(sections(text, 2))
        for heading in required:
            if heading not in present:
                out.append(Violation("esquema", "ALTA",
                                     f"{filename}: falta la sección `## {heading}`."))

    chars = read(cfg.bible_path("personajes.md"))
    if not chars.strip():
        out.append(Violation("esquema", "ALTA", "personajes.md no existe o está vacío."))
    else:
        from .artifacts import sections as _s
        names = list(_s(chars, 2))
        limit = cfg["obra"]["personajes_max"]
        if not names:
            out.append(Violation("esquema", "ALTA", "personajes.md no declara personajes."))
        elif len(names) > limit:
            out.append(Violation("esquema", "ALTA",
                                 f"personajes.md declara {len(names)} personajes; "
                                 f"el perfil permite {limit}."))

    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    total = cfg.total_chapters
    if len(outline) != total:
        out.append(Violation("esquema", "ALTA",
                             f"La escaleta tiene {len(outline)} entradas; se esperan {total}."))
    for n in range(1, total + 1):
        entry = outline.get(n)
        if entry is None:
            out.append(Violation("esquema", "ALTA", f"Falta la entrada del capítulo {n}."))
        else:
            missing = entry.missing_fields()
            if missing:
                out.append(Violation("esquema", "ALTA",
                                     f"Capítulo {n}: campos vacíos o por determinar: "
                                     f"{', '.join(missing)}."))
    return out
