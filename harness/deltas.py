"""Aplicacion de los deltas del Continuista y promocion del capitulo aceptado.

Cubre los pasos 13 a 17 del Anexo A.5, todos deterministas: promocion del
borrador, aplicacion de deltas sobre pistas/cronologia/personajes, escritura de
la ficha, y traslado de las notas del autor ya aplicadas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .artifacts import (CharacterState, ClueLedger, Timeline, CLUE_STATES,
                        parse_outline, read, render_card, sections, word_count,
                        write)


# --------------------------------------------------------------------------
# 12: extraccion tolerante de JSON
# --------------------------------------------------------------------------
def extract_json(text: str) -> dict:
    """Primer objeto JSON balanceado del texto.

    Los modelos `:free` envuelven el JSON en vallas de codigo o lo preceden de
    cortesias. Eso no es un fallo recuperable con reintento: es formato, y se
    resuelve aqui sin gastar cuota.
    """
    if text is None:
        raise ValueError("Respuesta vacía")
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip(),
                     flags=re.M)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    depth, start, in_string, escape = 0, None, False, False
    for i, ch in enumerate(cleaned):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = cleaned[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None
    raise ValueError("No se ha encontrado ningún objeto JSON balanceado en la respuesta")


def validate_evaluation(obj: dict, cfg) -> list[str]:
    criteria = ["tension", "escaleta", "voz", "caracterizacion", "ritmo", "prosa"]
    problems = []
    scores = obj.get("puntuaciones")
    if not isinstance(scores, dict):
        return ["Falta el objeto `puntuaciones`."]
    for c in criteria:
        v = scores.get(c)
        if not isinstance(v, int) or not (1 <= v <= cfg["evaluacion"]["escala_max"]):
            problems.append(f"`puntuaciones.{c}` no es un entero de 1 a "
                            f"{cfg['evaluacion']['escala_max']}: {v!r}.")
    if obj.get("veredicto") not in {"APROBADO", "CORREGIR"}:
        problems.append(f"`veredicto` inválido: {obj.get('veredicto')!r}.")
    return problems


def computed_mean(obj: dict) -> float:
    scores = obj.get("puntuaciones", {})
    values = [v for v in scores.values() if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 2) if values else 0.0


def accepts(obj: dict, cfg) -> bool:
    """9.2: la regla la aplica el runtime, no se confia en el veredicto del modelo."""
    ev = cfg["evaluacion"]
    scores = obj.get("puntuaciones", {})
    if computed_mean(obj) < ev["umbral_media"]:
        return False
    return all(scores.get(c, 0) >= ev["umbral_criterio_bloqueante"]
               for c in ev["criterios_bloqueantes"])


def validate_continuity(obj: dict) -> list[str]:
    problems = []
    if obj.get("veredicto") not in {"OK", "CORREGIR", "BLOQUEO"}:
        problems.append(f"`veredicto` inválido: {obj.get('veredicto')!r}.")
    if obj.get("veredicto") == "OK":
        deltas = obj.get("deltas")
        if not isinstance(deltas, dict):
            problems.append("Veredicto OK sin objeto `deltas`.")
        elif not isinstance(deltas.get("ficha"), dict):
            problems.append("`deltas.ficha` ausente o no es un objeto.")
        else:
            ficha = deltas["ficha"]
            for key in ("titulo", "focalizador", "resumen_120"):
                if not str(ficha.get(key, "")).strip():
                    problems.append(f"`deltas.ficha.{key}` está vacío.")
    return problems


# --------------------------------------------------------------------------
# paso 14: aplicacion de deltas
# --------------------------------------------------------------------------
def apply_deltas(cfg, chapter: int, deltas: dict) -> list[str]:
    """Escribe los deltas sobre pistas, cronologia y estado de personajes.

    Devuelve la lista de cambios aplicados, para que el orquestador la muestre
    sin tener que releer los archivos.
    """
    applied: list[str] = []
    deltas = deltas or {}

    # -- pistas ----------------------------------------------------------
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    entry = outline.get(chapter)
    for item in deltas.get("pistas") or []:
        cid = str(item.get("id", "")).strip()
        state = str(item.get("nuevo_estado", "")).strip().upper()
        if not cid:
            continue
        if state not in CLUE_STATES:
            applied.append(f"pista {cid}: estado `{state}` no válido, ignorado")
            continue
        existed = ledger.by_id(cid) is not None
        kind = "red_herring" if state in {"RED_HERRING", "DESACTIVADA"} else "real"
        ledger.upsert(cid, state, chapter,
                      description=str(item.get("nota", "")).strip(), kind=kind)
        note = str(item.get("nota", "")).strip()
        if note:
            ledger.notes.append(f"- {cid} · cap. {chapter} · {note}")
        applied.append(f"pista {cid} -> {state}"
                       + ("" if existed else " (creada sobre la marcha)"))
    ledger.save(cfg.state_path("pistas.md"))

    # -- cronologia ------------------------------------------------------
    timeline = Timeline.load(cfg.state_path("cronologia.md"))
    for item in deltas.get("cronologia") or []:
        day = item.get("dia_ficcion")
        event = str(item.get("suceso", "")).strip()
        if day is None:
            continue
        try:
            day = int(day)
        except (TypeError, ValueError):
            continue
        timeline.add(day, event, chapter)
        applied.append(f"cronología día {day}: {event[:60]}")
    ficha = deltas.get("ficha") or {}
    if not (deltas.get("cronologia") or []) and ficha.get("dia_ficcion") is not None:
        try:
            timeline.add(int(ficha["dia_ficcion"]),
                         str(ficha.get("gancho_final", "")).strip(), chapter)
            applied.append(f"cronología día {ficha['dia_ficcion']} (desde la ficha)")
        except (TypeError, ValueError):
            pass
    timeline.save(cfg.state_path("cronologia.md"))

    # -- personajes ------------------------------------------------------
    chars = CharacterState.load(cfg.state_path("personajes-estado.md"))
    for item in deltas.get("personajes") or []:
        name = str(item.get("nombre", "")).strip()
        if not name:
            continue
        chars.apply(name, item.get("cambios") or {}, chapter)
        applied.append(f"personaje {name}: "
                       f"{', '.join((item.get('cambios') or {}).keys())}")
    for name in ficha.get("personajes_presentes") or []:
        name = str(name).strip()
        if name and name not in chars.chars:
            chars.apply(name, {}, chapter)
    chars.save(cfg.state_path("personajes-estado.md"))

    return applied


# --------------------------------------------------------------------------
# paso 15: ficha del capitulo
# --------------------------------------------------------------------------
def write_card(cfg, chapter: int, ficha: dict, chapter_text: str,
               iterations: int, mean: float) -> Path:
    path = cfg.card_path(chapter)
    write(path, render_card(chapter, ficha, word_count(chapter_text),
                            iterations, mean))
    return path


# --------------------------------------------------------------------------
# 6.10 deuda narrativa
# --------------------------------------------------------------------------
def append_debt(cfg, chapter: int, mean: float, iterations: int,
                evaluation: dict) -> None:
    path = cfg.state_path("deuda-narrativa.md")
    text = read(path) or "# Deuda narrativa\n"
    scores = evaluation.get("puntuaciones", {})
    worst = min(scores, key=lambda k: scores[k]) if scores else "desconocido"
    patches = evaluation.get("parches") or []
    problem = patches[0].get("problema", "") if patches else \
        evaluation.get("observaciones", "")
    fix = patches[0].get("correccion", "") if patches else ""

    entry = "\n".join([
        "",
        f"## Capítulo {chapter} — aceptado con {mean} tras {iterations} iteraciones",
        f"- **Criterio fallido:** {worst} ({scores.get(worst, '-')})",
        f"- **Problema:** {problem or '(no reportado)'}",
        f"- **Corrección propuesta y no aplicada:** {fix or '(no reportada)'}",
        f"- **Riesgo si no se corrige:** arrastra el defecto al contexto de los "
        f"capítulos siguientes, que leen este capítulo como precedente.",
    ])
    write(path, text.rstrip() + "\n" + entry)


# --------------------------------------------------------------------------
# paso 17: notas del autor aplicadas
# --------------------------------------------------------------------------
def promote_author_notes(cfg, chapter: int) -> list[str]:
    path = cfg.path("notas_autor")
    text = read(path)
    if not text:
        return []
    blocks = sections(text, 2)
    current = blocks.get("Vigentes", "")
    done = blocks.get("Aplicadas", "")

    keep, moved = [], []
    for line in current.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            if stripped:
                keep.append(line)
            continue
        m = re.search(r"\[cap\.\s*(>=|<=|=)?\s*(\d+)\]", stripped)
        if m and (m.group(1) or "=") == "=" and int(m.group(2)) == chapter:
            moved.append(f"{stripped} — aplicada en cap. {chapter}")
        else:
            keep.append(line)

    if not moved:
        return []

    body = "\n".join([
        "# Notas del autor",
        "",
        "## Vigentes",
        "\n".join(keep).strip() or "- (ninguna)",
        "",
        "## Aplicadas",
        (done.strip() + "\n" if done.strip() else "") + "\n".join(moved),
    ])
    write(path, body)
    return moved
