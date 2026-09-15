"""Regeneracion del resumen rodante (6.9, paso 16 del Anexo A.5).

Determinista y sin ninguna llamada al modelo: es una recomposicion de fichas ya
escritas, no un acto de juicio. Delegarla quemaria cuota y anadiria una fuente
de alucinacion donde hoy no la hay.
"""

from __future__ import annotations

from .artifacts import Card, write, WORD_RE


def _bands(cfg, next_chapter: int) -> tuple[list[int], list[int], list[int]]:
    """Reparte los capitulos ya aceptados en las tres bandas de granularidad de 7.2.

    Devuelve (texto_integro, ficha_completa, una_linea) para el capitulo que se
    va a escribir. La banda de texto integro no se copia al resumen: la inyecta
    el ensamblador directamente desde `capitulos/`.
    """
    ctx = cfg["contexto"]
    n_full = ctx["capitulos_texto_integro"]
    n_card = ctx["capitulos_ficha_completa"]

    written = list(range(1, next_chapter))
    full = written[-n_full:] if n_full else []
    rest = written[:-n_full] if n_full else written
    cards = rest[-n_card:] if n_card else []
    lines = rest[:-n_card] if n_card else rest
    return full, cards, lines


def _closed_acts(cfg, next_chapter: int) -> list[dict]:
    out = []
    for act in cfg["actos"]:
        if act["hasta"] < next_chapter:
            out.append(act)
    return out


def _truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(",;: ") + "…"


def _load_cards(cfg, numbers: list[int]) -> dict[int, Card]:
    cards: dict[int, Card] = {}
    for n in numbers:
        card = Card.load(cfg.card_path(n), n)
        if card is not None:
            cards[n] = card
    return cards


def regenerate(cfg, next_chapter: int) -> str:
    """Construye el resumen rodante para el capitulo `next_chapter`."""
    ctx = cfg["contexto"]
    full, card_band, line_band = _bands(cfg, next_chapter)
    closed = _closed_acts(cfg, next_chapter)
    closed_numbers = {n for act in closed
                      for n in range(act["desde"], act["hasta"] + 1)}

    all_cards = _load_cards(cfg, list(range(1, next_chapter)))
    parts = ["# Resumen rodante", ""]

    # -- actos cerrados: un parrafo por acto ------------------------------
    parts.append("## Actos cerrados")
    if not closed:
        parts.append("(ninguno todavía)")
    for act in closed:
        rng = range(act["desde"], act["hasta"] + 1)
        sentences = [all_cards[n].first_sentence() for n in rng if n in all_cards]
        paragraph = " ".join(s.rstrip() for s in sentences if s)
        parts.append(f"### Acto {act['numero']} "
                     f"(capítulos {act['desde']}-{act['hasta']})")
        parts.append(_truncate_words(paragraph, ctx["palabras_resumen_acto"])
                     or "(sin fichas registradas)")
    parts.append("")

    # -- una linea por capitulo antiguo del acto en curso -----------------
    open_lines = [n for n in line_band if n not in closed_numbers]
    label_lo = open_lines[0] if open_lines else "-"
    label_hi = open_lines[-1] if open_lines else "-"
    parts.append(f"## Capítulos {label_lo}..{label_hi} — una línea cada uno")
    if not open_lines:
        parts.append("(ninguno todavía)")
    for n in open_lines:
        card = all_cards.get(n)
        parts.append(f"- **Cap. {n}:** "
                     f"{card.first_sentence() if card else '(sin ficha)'}")
    parts.append("")

    # -- ficha completa ---------------------------------------------------
    band_lo = card_band[0] if card_band else "-"
    band_hi = card_band[-1] if card_band else "-"
    parts.append(f"## Capítulos {band_lo}..{band_hi} — ficha completa")
    if not card_band:
        parts.append("(ninguno todavía)")
    for n in card_band:
        card = all_cards.get(n)
        if card is None:
            parts.append(f"### Cap. {n}\n(sin ficha)")
            continue
        parts.append(f"### Cap. {n} — {card.title}")
        parts.append(f"- **Focalizador:** {card.pov} · **Día de ficción:** {card.day}")
        parts.append(f"- **Gancho final:** {card.hook}")
        parts.append(card.summary)
    parts.append("")

    # -- texto integro: se inyecta aparte, no se copia aqui ---------------
    label = ", ".join(str(n) for n in full) if full else "-"
    parts.append(f"## Capítulos {label}")
    parts.append("(el texto íntegro se inyecta directamente desde `capitulos/`; "
                 "no se copia aquí)")

    return "\n".join(parts).rstrip() + "\n"


def write_rolling_summary(cfg, next_chapter: int) -> str:
    text = regenerate(cfg, next_chapter)
    write(cfg.state_path("resumen-rodante.md"), text)
    return text
