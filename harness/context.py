"""Ensamblador de contexto (seccion 7).

Los subagentes no tienen herramientas: no pueden leer archivos. Por tanto todo
el contexto viaja en el mensaje de usuario, y este modulo es quien lo construye.
De ahi que el presupuesto de 16k tokens de 7.4 sea un requisito y no una
recomendacion.

Cada bloque se etiqueta para que el recorte de 7.4 pueda retirarlos por nombre y
en el orden que fija `contexto.orden_de_recorte`.
"""

from __future__ import annotations

import re
from pathlib import Path

from .artifacts import (Card, CharacterState, ClueLedger, Timeline, read,
                        parse_outline, sections, word_count)


class Block:
    def __init__(self, tag: str, heading: str, body: str, droppable: bool = False):
        self.tag = tag
        self.heading = heading
        self.body = (body or "").strip()
        self.droppable = droppable

    def render(self) -> str:
        return f"## {self.heading}\n{self.body}" if self.body else ""

    def words(self) -> int:
        return len(self.body.split())


class Assembly:
    def __init__(self, cfg, role: str, instruction: str, blocks: list[Block]):
        self.cfg = cfg
        self.role = role
        self.instruction = instruction
        self.blocks = [b for b in blocks if b.body]
        self.dropped: list[str] = []
        self._trim()

    # -- 7.4 presupuesto ---------------------------------------------------
    def tokens(self) -> int:
        per_word = self.cfg["contexto"]["tokens_por_palabra"]
        words = len(self.instruction.split()) + sum(b.words() for b in self.blocks)
        return int(words * per_word)

    def _trim(self) -> None:
        budget = self.cfg["contexto"]["presupuesto_tokens_max"]
        order = self.cfg["contexto"]["orden_de_recorte"]
        for tag in order:
            if self.tokens() <= budget:
                return
            for block in list(self.blocks):
                if block.tag == tag and block.droppable:
                    self.blocks.remove(block)
                    self.dropped.append(tag)

    def render(self) -> str:
        parts = [self.instruction.strip(), ""]
        for block in self.blocks:
            parts.append(block.render())
            parts.append("")
        if self.dropped:
            parts.append("## Nota del sistema")
            parts.append("Se han recortado por presupuesto de contexto: "
                         + ", ".join(self.dropped) + ".")
        return "\n".join(parts).rstrip() + "\n"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _present_characters(cfg, entry, extra_text: str = "") -> list[str]:
    """Personajes presentes: el focalizador mas los nombrados en la entrada.

    Sirve para filtrar `personajes.md` y `personajes-estado.md` (7.1, columnas
    "solo presentes"). Si no se reconoce ninguno, se devuelven todos: en una obra
    de 8 personajes como maximo, equivocarse por exceso es barato.
    """
    roster = list(sections(read(cfg.bible_path("personajes.md")), 2))
    if not roster:
        return []
    haystack = f"{getattr(entry, 'body', '')} {getattr(entry, 'pov', '')} {extra_text}"
    haystack = haystack.lower()
    present = []
    for name in roster:
        parts = [p for p in re.split(r"\s+", name.strip()) if len(p) > 2]
        if any(p.lower() in haystack for p in parts):
            present.append(name)
    return present or roster


def _character_sheets(cfg, names: list[str]) -> str:
    text = read(cfg.bible_path("personajes.md"))
    blocks = sections(text, 2)
    wanted = [n for n in blocks if n in set(names)] or list(blocks)
    return "\n\n".join(f"## {n}\n{blocks[n]}" for n in wanted)


def _outline_entries(cfg, numbers: list[int]) -> str:
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    out = [outline[n].render() for n in numbers if n in outline]
    return "\n\n".join(out)


def _clue_table(cfg, ids: list[str] | None = None, live_only: bool = False) -> str:
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    if live_only:
        rows = ledger.live()
    elif ids is None:
        rows = ledger.clues
    else:
        rows = ledger.filtered(ids)
    return ledger.render(rows) if rows else ""


def _full_text_chapters(cfg, next_chapter: int) -> list[int]:
    n = cfg["contexto"]["capitulos_texto_integro"]
    return [c for c in range(max(1, next_chapter - n), next_chapter)]


def _card_chapters(cfg, next_chapter: int) -> list[int]:
    n_full = cfg["contexto"]["capitulos_texto_integro"]
    n_card = cfg["contexto"]["capitulos_ficha_completa"]
    hi = next_chapter - n_full
    return [c for c in range(max(1, hi - n_card), hi)]


def _author_notes(cfg, chapter: int) -> str:
    """Notas vigentes aplicables a este capitulo (6.12)."""
    text = read(cfg.path("notas_autor"))
    if not text:
        return ""
    current = sections(text, 2).get("Vigentes", "")
    keep = []
    for line in current.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        m = re.search(r"\[cap\.\s*(>=|<=|=)?\s*(\d+)\]", line)
        if not m:
            keep.append(line)
            continue
        op, target = m.group(1) or "=", int(m.group(2))
        if (op == ">=" and chapter >= target) or (op == "<=" and chapter <= target) \
                or (op == "=" and chapter == target):
            keep.append(line)
    return "\n".join(keep)


# --------------------------------------------------------------------------
# 7.1 ensamblados por rol
# --------------------------------------------------------------------------
def for_writer(cfg, chapter: int, patches: str = "", draft: str = "") -> Assembly:
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    entry = outline.get(chapter)
    if entry is None:
        raise ValueError(f"La escaleta no tiene entrada para el capítulo {chapter}")

    present = _present_characters(cfg, entry)
    caps = cfg["capitulos"]
    target = caps["palabras_objetivo"]
    tol = caps["tolerancia_palabras"]
    lo, hi = int(target * (1 - tol)), int(target * (1 + tol))

    mode = "PARCHE" if patches else "BORRADOR"
    instruction = (
        f"TAREA: escribe el capítulo {chapter} de la novela. Modo: {mode}.\n"
        f"Focalizador obligatorio: {entry.pov}.\n\n"
        f"EXTENSIÓN DE ESTA EJECUCIÓN (perfil `{cfg.profile_name}`; sustituye a la "
        f"cifra de tu system prompt): entre {lo} y {hi} palabras, objetivo "
        f"{target}, en {caps['escenas_min']} a {caps['escenas_max']} escenas. "
        f"Un capítulo fuera de ese rango se rechaza automáticamente antes de "
        f"evaluarse.\n\n"
        f"Devuelve solo el capítulo, con los marcadores `<!-- ESCENA n -->` y "
        f"terminando en `<!-- FIN -->`."
    )

    blocks = [
        Block("premisa", "Premisa", read(cfg.bible_path("premisa.md"))),
        Block("voz", "Voz y estilo", read(cfg.bible_path("voz-y-estilo.md"))),
        Block("personajes", "Personajes presentes", _character_sheets(cfg, present)),
        Block("escaleta", f"Escaleta — entradas {chapter - 1} a {chapter + 1}",
              _outline_entries(cfg, [chapter - 1, chapter, chapter + 1])),
        Block("pistas", "Pistas relevantes para este capítulo",
              _clue_table(cfg, entry.clue_ids)),
        Block("personajes_estado", "Estado actual de los personajes presentes",
              CharacterState.load(cfg.state_path("personajes-estado.md")).render(present)),
        Block("cronologia", "Cronología reciente",
              Timeline.load(cfg.state_path("cronologia.md")).render(
                  Timeline.load(cfg.state_path("cronologia.md")).last_days(
                      cfg["contexto"]["dias_cronologia_visibles"])),
              droppable=True),
        Block("resumen", "Resumen rodante",
              read(cfg.state_path("resumen-rodante.md"))),
        Block("notas_autor", "Notas del autor vigentes", _author_notes(cfg, chapter)),
    ]

    for n in _card_chapters(cfg, chapter):
        card = Card.load(cfg.card_path(n), n)
        if card:
            blocks.append(Block("fichas_antiguas", f"Ficha del capítulo {n}",
                                card.text, droppable=True))

    full = _full_text_chapters(cfg, chapter)
    for i, n in enumerate(full):
        # el mas lejano (N-2) es el primero en caer si hay que recortar (7.4)
        droppable = (i == 0 and len(full) > 1)
        blocks.append(Block("texto_integro_n_menos_2" if droppable else "texto_integro",
                            f"Texto íntegro del capítulo {n}",
                            read(cfg.chapter_path(n)), droppable=droppable))

    if patches:
        # En modo PARCHE el Escritor tiene que copiar literalmente lo que no parchea:
        # sin el borrador vigente delante no puede hacerlo (9.5).
        blocks.append(Block("borrador_vigente", "Borrador vigente del capítulo", draft))
        blocks.append(Block("parches", "PARCHES SOLICITADOS", patches))

    return Assembly(cfg, "escritor", instruction, blocks)


def for_evaluator(cfg, chapter: int, draft: str) -> Assembly:
    ev = cfg["evaluacion"]
    instruction = (
        f"TAREA: evalúa el capítulo {chapter}.\n"
        f"Umbral de aprobación vigente en este perfil: media >= {ev['umbral_media']}, "
        f"y {' y '.join(ev['criterios_bloqueantes'])} >= "
        f"{ev['umbral_criterio_bloqueante']}.\n"
        f"Máximo {ev['max_parches_por_iteracion']} parches. "
        f"Devuelve solo el objeto JSON."
    )
    blocks = [
        Block("voz", "Voz y estilo", read(cfg.bible_path("voz-y-estilo.md"))),
        Block("escaleta", f"Entrada de escaleta del capítulo {chapter}",
              _outline_entries(cfg, [chapter])),
        Block("capitulo", "Capítulo a evaluar", draft),
    ]
    previous = chapter - 1
    if previous >= 1:
        card = Card.load(cfg.card_path(previous), previous)
        if card:
            blocks.insert(2, Block("ficha_anterior",
                                   f"Ficha del capítulo {previous}", card.text))
    return Assembly(cfg, "evaluador", instruction, blocks)


def for_continuity(cfg, chapter: int, draft: str) -> Assembly:
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    entry = outline.get(chapter)
    present = _present_characters(cfg, entry, draft) if entry else []

    instruction = (
        f"TAREA: verifica la continuidad del capítulo {chapter} y, si el veredicto "
        f"es OK, extrae los deltas de estado.\n"
        f"El resumen de la ficha debe tener exactamente "
        f"{cfg['contexto']['palabras_ficha']} palabras.\n"
        f"Devuelve solo el objeto JSON."
    )
    blocks = [
        Block("escaleta", f"Entrada de escaleta del capítulo {chapter}",
              _outline_entries(cfg, [chapter])),
        Block("resumen", "Resumen rodante", read(cfg.state_path("resumen-rodante.md"))),
        Block("pistas", "Pistas vivas (ni resueltas ni desactivadas)",
              _clue_table(cfg, live_only=True)),
        Block("cronologia", "Cronología completa",
              Timeline.load(cfg.state_path("cronologia.md")).render()),
        Block("personajes_estado", "Estado de personajes",
              CharacterState.load(cfg.state_path("personajes-estado.md")).render()),
        Block("personajes", "Fichas de los personajes presentes",
              _character_sheets(cfg, present)),
        Block("capitulo", "Capítulo a verificar", draft),
    ]
    previous = chapter - 1
    if previous >= 1:
        blocks.insert(1, Block("texto_integro",
                               f"Texto íntegro del capítulo {previous}",
                               read(cfg.chapter_path(previous))))
    return Assembly(cfg, "continuista", instruction, blocks)


def for_act_editor(cfg, act_number: int) -> Assembly:
    act = next(a for a in cfg["actos"] if a["numero"] == act_number)
    numbers = list(range(act["desde"], act["hasta"] + 1))

    instruction = (
        f"TAREA: emite el informe de cierre del Acto {act_number} "
        f"(capítulos {act['desde']}-{act['hasta']}).\n"
        f"La obra tiene {cfg.total_chapters} capítulos en total. "
        f"Propón correcciones solo sobre capítulos aún no escritos.\n"
        f"Devuelve solo el informe en Markdown."
    )
    blocks = [
        Block("escaleta", f"Escaleta del Acto {act_number}",
              _outline_entries(cfg, numbers)),
        Block("pistas", "Ledger de pistas completo", _clue_table(cfg)),
        Block("cronologia", "Cronología",
              Timeline.load(cfg.state_path("cronologia.md")).render()),
    ]
    for n in numbers:
        card = Card.load(cfg.card_path(n), n)
        if card:
            blocks.append(Block("fichas", f"Ficha del capítulo {n}", card.text))
    return Assembly(cfg, "editor_acto", instruction, blocks)


def _outline_schema_for_profile(cfg, schema: str) -> str:
    """Reescribe las cabeceras de acto del esquema 6.5 con los actos del perfil.

    El esquema de la especificacion trae los actos de la obra completa (1-8,
    9-22, 23-30). En el perfil `poc` los actos son otros, y un esquema que dice
    "Capítulos 1-8" cuando la obra tiene 3 induce al Arquitecto a error.
    """
    entry_tpl = ""
    m = re.search(r"### Capítulo 1\n(.*?)(?=\n## )", schema, re.S)
    if m:
        entry_tpl = m.group(1).rstrip()
    if not entry_tpl:
        return schema

    parts = ["# Escaleta", ""]
    for act in cfg["actos"]:
        parts.append(f"## Acto {act['numero']} — "
                     f"Capítulos {act['desde']}-{act['hasta']}")
        parts.append("")
        for n in range(act["desde"], act["hasta"] + 1):
            parts.append(f"### Capítulo {n}")
            parts.append(entry_tpl)
            parts.append("")
    parts += ["## Cambios", "- <fecha> · cap. <N> · <qué cambió> · <motivo>"]
    return "\n".join(parts)


def for_architect(cfg, task: str, schema: str, extra: str = "") -> Assembly:
    """`task` es una de [ENTREVISTA] [PREMISA] [PERSONAJES] [VOZ] [ESCALETA]
    [REVISION_ESCALETA]; `schema` es el esquema literal de la seccion 6."""
    if task.startswith("[ESCALETA]") or task.startswith("[REVISION_ESCALETA]"):
        schema = _outline_schema_for_profile(cfg, schema)
    obra = cfg["obra"]
    caps = cfg["capitulos"]
    actos = " · ".join(f"Acto {a['numero']} = capítulos {a['desde']}-{a['hasta']}"
                       for a in cfg["actos"])
    instruction = (
        f"{task}\n\n"
        f"PARÁMETROS DE ESTA EJECUCIÓN (perfil `{cfg.profile_name}`; tienen "
        f"prioridad sobre cualquier cifra de tu system prompt):\n"
        f"- Capítulos totales: {caps['total']}.\n"
        f"- Palabras por capítulo: {caps['palabras_objetivo']}.\n"
        f"- Escenas por capítulo: "
        + (f"{caps['escenas_min']}.\n" if caps['escenas_min'] == caps['escenas_max']
           else f"entre {caps['escenas_min']} y {caps['escenas_max']}.\n") +
        f"- Actos: {actos}.\n"
        f"- Máximo {obra['personajes_max']} personajes con nombre, "
        f"{obra['focalizadores_max']} focalizadores.\n"
        f"- Rondas de entrevista: {cfg['entrevista']['rondas']}.\n"
        f"Emite las {caps['total']} entradas si la tarea es [ESCALETA]."
    )
    blocks = [Block("esquema", "Esquema obligatorio del artefacto", schema)]
    if extra:
        blocks.append(Block("extra", "Material de partida", extra))
    for name, heading in (("premisa.md", "Premisa"),
                          ("personajes.md", "Personajes"),
                          ("voz-y-estilo.md", "Voz y estilo"),
                          ("entrevista.md", "Entrevista")):
        body = read(cfg.bible_path(name))
        if body:
            blocks.append(Block("biblia", heading, body))
    if task.startswith("[REVISION_ESCALETA]"):
        blocks.append(Block("escaleta", "Escaleta vigente",
                            read(cfg.bible_path("escaleta.md"))))
        blocks.append(Block("resumen", "Resumen rodante",
                            read(cfg.state_path("resumen-rodante.md"))))
        blocks.append(Block("pistas", "Ledger de pistas", _clue_table(cfg)))
        blocks.append(Block("notas_autor", "Notas del autor",
                            read(cfg.path("notas_autor"))))
    return Assembly(cfg, "arquitecto", instruction, blocks)
