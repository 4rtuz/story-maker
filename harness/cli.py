"""Interfaz de linea de ordenes del nucleo.

Es lo que invoca la skill orquestadora para todo lo que la especificacion marca
como determinista (Anexo A.5: pasos 5, 7, 13, 14, 15, 16, 17, 19 y 21). La skill
solo se reserva lo que exige juicio —lanzar subagentes y presentar puertas— mas
los pasos que el runtime hace mejor.

Todas las ordenes son idempotentes respecto al estado: nada se aplica hasta que
la respuesta se ha parseado con exito (10.2).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import context as ctx
from . import deltas as D
from . import rules
from . import summary as S
from .artifacts import (Card, ClueLedger, Clue, Timeline, parse_outline, read,
                        sections, word_count, write)
from .config import Config, load
from .scenes import (Chapter, language_drift, reconcile_patch, spanish_ratio,
                     structural_problems)
from .state import State

OK, FAIL = 0, 1

# La salida la lee la skill orquestadora, no una consola: se fuerza UTF-8 para
# que los acentos no dependan de la codepage de Windows.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def _out(*lines: str) -> None:
    for line in lines:
        print(line)


def _cfg_state(args) -> tuple[Config, State]:
    cfg = load(Path(args.root) if args.root else None)
    return cfg, State(cfg)


def _report_path(cfg: Config, chapter: int, iteration: int, kind: str) -> Path:
    return cfg.path("intentos") / f"{chapter:02d}-i{iteration}-{kind}.json"


# ==========================================================================
# init
# ==========================================================================
SEED = {
    "estado/pistas.md": None,            # se escribe con ClueLedger
    "estado/cronologia.md": None,        # se escribe con Timeline
    "estado/personajes-estado.md": "# Estado de personajes\n",
    "estado/deuda-narrativa.md": "# Deuda narrativa\n",
    "estado/resumen-rodante.md": "# Resumen rodante\n",
}

NOTES_SEED = """# Notas del autor

## Vigentes
- (ninguna)

## Aplicadas
- (ninguna)
"""


def cmd_init(args) -> int:
    cfg = load(Path(args.root) if args.root else None)
    for key in ("biblia", "estado", "capitulos", "intentos", "informes"):
        cfg.path(key).mkdir(parents=True, exist_ok=True)

    for rel, seed in SEED.items():
        path = cfg.state_path(rel.split("/", 1)[1])
        if path.exists() and not args.force:
            continue
        if seed is None:
            if "pistas" in rel:
                ClueLedger([], []).save(path)
            else:
                Timeline([]).save(path)
        else:
            write(path, seed)

    notes = cfg.path("notas_autor")
    if not notes.exists() or args.force:
        write(notes, NOTES_SEED)

    state = State(cfg)
    if not state.path.exists() or args.force:
        state.data = state._initial()
        state.save()

    _out(f"Estructura creada bajo `{cfg['rutas']['raiz']}/` "
         f"con el perfil `{cfg.profile_name}` "
         f"({cfg.total_chapters} capítulos de {cfg['capitulos']['palabras_objetivo']} "
         f"palabras).",
         f"Estado: {state.name}.")
    return OK


# ==========================================================================
# status / next
# ==========================================================================
def cmd_status(args) -> int:
    cfg, state = _cfg_state(args)
    state.roll_quota_day()
    q = state["cuota"]
    _out(
        "# Estado de la ejecución",
        f"- Perfil activo: `{cfg.profile_name}` "
        f"({cfg.total_chapters} capítulos, {cfg['capitulos']['palabras_objetivo']} palabras)",
        f"- Estado: **{state.name}**",
        f"- Capítulo actual: {state['capitulo_actual']} (acto {state['acto_actual']})",
        f"- Iteración: {state['iteracion']} de {cfg['evaluacion']['max_reescrituras']}",
        f"- Capítulos aceptados: {state['capitulos_aceptados'] or '(ninguno)'}",
        f"- Puerta pendiente: {state['puerta_pendiente'] or '(ninguna)'}",
        f"- Cuota: {q['llamadas_hoy']}/{q['limite_diario']} llamadas lógicas hoy "
        f"({q['fecha_utc']} UTC), quedan {state.quota_left()}",
        f"- Intentos del capítulo en curso: {state['intentos'] or '(ninguno)'}",
    )
    if state["ultimo_error"]:
        _out(f"- Último error: {state['ultimo_error']}")
    return OK


ACTIONS = {
    "GATE_PLAN": "presentar_puerta_plan",
    "GATE_ACTO": "presentar_puerta_acto",
    "GATE_FINAL": "presentar_puerta_final",
    "GATE_BLOQUEO": "presentar_puerta_bloqueo",
}


def cmd_next(args) -> int:
    """Dice a la skill que hacer a continuacion. Unica fuente de decision del bucle."""
    cfg, state = _cfg_state(args)
    state.roll_quota_day()
    n = state["capitulo_actual"]

    if state.at_gate():
        _out(f"ACCION: {ACTIONS[state.name]}",
             f"PUERTA: {state.name}",
             f"CAPITULO: {n}")
        return OK

    if state.name == "COMPLETADO":
        _out("ACCION: nada", "MOTIVO: la novela está completa.")
        return OK

    if state.name in {"INIT", "ENTREVISTA", "GENERANDO_BIBLIA"}:
        _out(f"ACCION: planificar", f"ESTADO: {state.name}",
             "MOTIVO: la biblia todavía no ha superado la Puerta 1.")
        return OK

    if not state.chapter_fits():
        state.transition("CUOTA_PAUSADA")
        _out("ACCION: parar",
             f"MOTIVO: cuota agotada ({state['cuota']['llamadas_hoy']}/"
             f"{state['cuota']['limite_diario']}). Se reanuda solo en el próximo día UTC.")
        return OK

    if state.name == "CUOTA_PAUSADA":
        state.transition("ESCRIBIENDO")

    if state.name == "EDITANDO_ACTO":
        # el acto que acaba de cerrarse es el del ultimo capitulo aceptado,
        # no `acto_actual`, que `accept` ya ha movido al capitulo siguiente.
        _out("ACCION: editar_acto", f"ACTO: {cfg.act_of(max(n - 1, 1))}")
        return OK

    if state.name == "AUDITORIA_FINAL" or n > cfg.total_chapters:
        state.transition("AUDITORIA_FINAL")
        _out("ACCION: auditoria_final")
        return OK

    # auditoria previa al ultimo capitulo (8.3)
    audit_before = cfg["continuidad"]["auditoria_antes_de_capitulo"]
    if n == audit_before and not args.skip_audit:
        violations = rules.final_audit(cfg)
        if violations:
            _out("ACCION: parar",
                 f"MOTIVO: la auditoría previa al capítulo {n} ha fallado. "
                 "No se escribe el último capítulo con cabos sueltos conocidos.")
            for v in violations:
                _out(f"  - {v}")
            state.transition("GATE_BLOQUEO", puerta_pendiente="auditoria_previa")
            return FAIL

    eval_path = _report_path(cfg, n, state["iteracion"], "eval")
    cont_path = _report_path(cfg, n, state["iteracion"], "cont")
    attempt = cfg.attempt_path(n, state["iteracion"])

    if not attempt.exists():
        _out("ACCION: escribir", f"CAPITULO: {n}",
             f"ITERACION: {state['iteracion']}")
    elif not eval_path.exists():
        _out("ACCION: evaluar", f"CAPITULO: {n}",
             f"ITERACION: {state['iteracion']}")
    elif not cont_path.exists():
        _out("ACCION: verificar", f"CAPITULO: {n}",
             f"ITERACION: {state['iteracion']}")
    else:
        _out("ACCION: decidir", f"CAPITULO: {n}",
             f"ITERACION: {state['iteracion']}")
    return OK


# ==========================================================================
# prompt: ensamblado de contexto (paso 5)
# ==========================================================================
SCHEMAS = Path(__file__).parent / "schemas"


def cmd_prompt(args) -> int:
    cfg, state = _cfg_state(args)
    n = args.chapter or state["capitulo_actual"]

    if args.role == "escritor":
        patches = read(Path(args.patches)) if args.patches else ""
        draft = ""
        if patches:
            prev = cfg.attempt_path(n, state["iteracion"] - 1)
            draft = read(prev) if prev.exists() else ""
        assembly = ctx.for_writer(cfg, n, patches, draft)
    elif args.role == "evaluador":
        assembly = ctx.for_evaluator(cfg, n, read(Path(args.draft)))
    elif args.role == "continuista":
        assembly = ctx.for_continuity(cfg, n, read(Path(args.draft)))
    elif args.role == "editor_acto":
        assembly = ctx.for_act_editor(cfg, args.act or state["acto_actual"])
    elif args.role == "arquitecto":
        schema = read(SCHEMAS / f"{args.schema}.md") if args.schema else ""
        extra = read(Path(args.extra)) if args.extra else ""
        assembly = ctx.for_architect(cfg, args.task or "[ESCALETA]", schema, extra)
    else:
        _out(f"Rol desconocido: {args.role}")
        return FAIL

    budget = cfg["contexto"]["presupuesto_tokens_max"]
    tokens = assembly.tokens()
    text = assembly.render()

    if args.output:
        write(Path(args.output), text)
        _out(f"Contexto de `{args.role}` escrito en {args.output}: "
             f"~{tokens} tokens de {budget}"
             + (f" (recortado: {', '.join(assembly.dropped)})"
                if assembly.dropped else ""))
    else:
        print(text)
    if tokens > budget:
        _out(f"AVISO: el contexto supera el presupuesto ({tokens} > {budget}) "
             f"incluso tras el recorte.")
    return OK


# ==========================================================================
# guardado y comprobacion del borrador (pasos 7 y 10)
# ==========================================================================
def cmd_save_attempt(args) -> int:
    cfg, state = _cfg_state(args)
    n = args.chapter or state["capitulo_actual"]
    i = args.iteration if args.iteration is not None else state["iteracion"]

    text = read(Path(args.file))
    if not text.strip():
        _out("El borrador está vacío.")
        return FAIL

    target = cfg.attempt_path(n, i)

    if i > 0 and args.patched_scenes:
        original = read(cfg.attempt_path(n, i - 1))
        scenes = [int(s) for s in str(args.patched_scenes).split(",") if s.strip()]
        text, violated = reconcile_patch(original, text, scenes)
        if violated:
            _out(f"AVISO (9.5): el modelo alteró escenas no señaladas {violated}. "
                 f"Se han restaurado desde `{cfg.attempt_path(n, i - 1).name}`.")
        else:
            _out("Verificación de hashes correcta: las escenas no señaladas "
                 "no han cambiado.")

    write(target, text)
    state.record_usage(1)

    problems = structural_problems(text, cfg)
    ratio = spanish_ratio(text)
    if language_drift(text):
        problems.append(f"Deriva de idioma: solo {ratio:.0%} de palabras "
                        f"funcionales españolas.")

    state.transition("EVALUANDO", iteracion=i)
    _out(f"Borrador guardado en `{target.as_posix()}` "
         f"({word_count(text)} palabras, {len(Chapter(text).scenes)} escenas).")
    if problems:
        _out("PROBLEMAS_ESTRUCTURALES:")
        for p in problems:
            _out(f"  - {p}")
        return FAIL
    _out("PROBLEMAS_ESTRUCTURALES: ninguno")
    return OK


# ==========================================================================
# registro de informes (pasos 8 y 9)
# ==========================================================================
def cmd_record(args) -> int:
    cfg, state = _cfg_state(args)
    n = args.chapter or state["capitulo_actual"]
    i = args.iteration if args.iteration is not None else state["iteracion"]
    raw = read(Path(args.file))

    try:
        obj = D.extract_json(raw)
    except ValueError as exc:
        _out(f"JSON_INVALIDO: {exc}")
        return FAIL

    if args.kind == "eval":
        problems = D.validate_evaluation(obj, cfg)
        if problems:
            _out("JSON_INVALIDO:")
            for p in problems:
                _out(f"  - {p}")
            return FAIL
        mean = D.computed_mean(obj)
        obj["media_calculada"] = mean
        obj["aprobado_por_regla"] = D.accepts(obj, cfg)
        write(_report_path(cfg, n, i, "eval"),
              json.dumps(obj, ensure_ascii=False, indent=2))
        state.record_attempt(i, mean, cfg.attempt_path(n, i).as_posix())
        state.record_usage(1)
        _out(f"Evaluador: media calculada {mean} "
             f"(umbral {cfg['evaluacion']['umbral_media']}), "
             f"veredicto del modelo `{obj.get('veredicto')}`, "
             f"regla del runtime: "
             f"{'APROBADO' if obj['aprobado_por_regla'] else 'CORREGIR'}.")
        if obj.get("veredicto") == "APROBADO" and not obj["aprobado_por_regla"]:
            _out("AVISO: el modelo dijo APROBADO pero no cumple la regla de 9.2. "
                 "Manda la regla.")
    else:
        problems = D.validate_continuity(obj)
        if problems:
            _out("JSON_INVALIDO:")
            for p in problems:
                _out(f"  - {p}")
            return FAIL
        write(_report_path(cfg, n, i, "cont"),
              json.dumps(obj, ensure_ascii=False, indent=2))
        state.record_usage(1)
        _out(f"Continuista: veredicto `{obj.get('veredicto')}`, "
             f"{len(obj.get('contradicciones') or [])} contradicciones.")
    return OK


# ==========================================================================
# decision del bucle (pasos 9 a 12)
# ==========================================================================
def cmd_decide(args) -> int:
    cfg, state = _cfg_state(args)
    n = args.chapter or state["capitulo_actual"]
    i = state["iteracion"]
    ev = json.loads(read(_report_path(cfg, n, i, "eval")) or "{}")
    cont = json.loads(read(_report_path(cfg, n, i, "cont")) or "{}")

    if not ev or not cont:
        _out("Faltan informes para decidir. Ejecuta `evaluar` y `verificar` primero.")
        return FAIL

    approved = ev.get("aprobado_por_regla", False)
    verdict = cont.get("veredicto")

    if verdict == "BLOQUEO":
        state.transition("GATE_BLOQUEO", puerta_pendiente="bloqueo_continuidad")
        _out("DECISION: puerta_bloqueo",
             "MOTIVO: el Continuista exige cambiar capítulos ya aceptados o la escaleta.")
        for c in cont.get("contradicciones") or []:
            _out(f"  - escena {c.get('escena')}: {c.get('descripcion')} "
                 f"(evidencia: {c.get('evidencia')})")
        return OK

    if approved and verdict == "OK":
        state.transition("ACEPTANDO")
        _out("DECISION: aceptar",
             f"MOTIVO: media {ev['media_calculada']} y continuidad OK.")
        return OK

    if i < cfg["evaluacion"]["max_reescrituras"]:
        state.transition("PARCHEANDO", iteracion=i + 1)
        _out("DECISION: parchear", f"ITERACION_NUEVA: {i + 1}",
             f"MOTIVO: media {ev.get('media_calculada')} "
             f"(umbral {cfg['evaluacion']['umbral_media']}), continuidad `{verdict}`.")
        return OK

    best = state.best_attempt()
    state.transition("ACEPTANDO", aceptar_con_deuda=True)
    _out("DECISION: aceptar_con_deuda",
         f"MEJOR_INTENTO: i{best['iteracion']} con media {best['media']}",
         "MOTIVO: iteraciones agotadas (9.4). La ejecución continúa.")
    return OK


def cmd_patch_plan(args) -> int:
    """Fusiona parches del Evaluador y contradicciones del Continuista (9.5)."""
    cfg, state = _cfg_state(args)
    n = args.chapter or state["capitulo_actual"]
    source = state["iteracion"] - 1 if state.name == "PARCHEANDO" else state["iteracion"]
    ev = json.loads(read(_report_path(cfg, n, source, "eval")) or "{}")
    cont = json.loads(read(_report_path(cfg, n, source, "cont")) or "{}")

    by_scene: dict[int, list[str]] = {}
    for p in ev.get("parches") or []:
        by_scene.setdefault(int(p.get("escena", 0)), []).append(
            f"- [{p.get('criterio')}] {p.get('problema')} "
            f"→ {p.get('correccion')}")
    for c in cont.get("contradicciones") or []:
        by_scene.setdefault(int(c.get("escena", 0)), []).append(
            f"- [continuidad/{c.get('tipo')}] {c.get('descripcion')} "
            f"(establecido en: {c.get('evidencia')}) → {c.get('correccion')}")

    if not by_scene:
        _out("No hay parches que aplicar.")
        return FAIL

    lines = ["Reescribe ÚNICAMENTE las escenas listadas. Copia literalmente el "
             "resto del capítulo, sin un solo cambio.", ""]
    for scene in sorted(by_scene):
        lines.append(f"### Escena {scene}")
        lines += by_scene[scene]
        lines.append("")

    out = Path(args.output) if args.output else \
        cfg.path("intentos") / f"{n:02d}-i{state['iteracion']}-parches.md"
    write(out, "\n".join(lines))
    _out(f"PARCHES: {out.as_posix()}",
         f"ESCENAS: {','.join(str(s) for s in sorted(by_scene))}")
    return OK


# ==========================================================================
# aceptacion (pasos 13 a 19)
# ==========================================================================
def cmd_accept(args) -> int:
    cfg, state = _cfg_state(args)
    n = args.chapter or state["capitulo_actual"]

    best = state.best_attempt()
    if best is None:
        _out("No hay ningún intento registrado para este capítulo.")
        return FAIL
    iteration = best["iteracion"]
    chapter_text = read(cfg.attempt_path(n, iteration))
    ev = json.loads(read(_report_path(cfg, n, iteration, "eval")) or "{}")
    cont = json.loads(read(_report_path(cfg, n, iteration, "cont")) or "{}")
    with_debt = not ev.get("aprobado_por_regla", False) or \
        cont.get("veredicto") != "OK"

    # 13: promocion
    write(cfg.chapter_path(n), chapter_text)

    # 14: deltas
    ficha = (cont.get("deltas") or {}).get("ficha") or {}
    applied = D.apply_deltas(cfg, n, cont.get("deltas") or {})

    # 15: ficha
    if not ficha:
        ficha = {"titulo": Chapter(chapter_text).title,
                 "focalizador": "(no extraído)", "dia_ficcion": "",
                 "resumen_120": "(el Continuista no emitió deltas: "
                                "capítulo aceptado con deuda)",
                 "personajes_presentes": [], "gancho_final": ""}
    D.write_card(cfg, n, ficha, chapter_text, iteration, best["media"])

    # 9.4: deuda
    if with_debt:
        D.append_debt(cfg, n, best["media"], iteration, ev)

    # 17: notas del autor
    moved = D.promote_author_notes(cfg, n)

    # 19: avance de estado
    accepted = sorted(set(state["capitulos_aceptados"] + [n]))
    state["capitulos_aceptados"] = accepted
    state["capitulo_actual"] = n + 1
    state["acto_actual"] = cfg.act_of(min(n + 1, cfg.total_chapters))
    state.reset_chapter_scratch()

    # 16: resumen rodante, tras mover el puntero
    S.write_rolling_summary(cfg, n + 1)

    # comprobaciones deterministas de 8.2 sobre el estado ya actualizado
    violations = rules.check_state(cfg, n)

    if cfg.is_act_end(n):
        state.transition("EDITANDO_ACTO")
        siguiente = "editar_acto"
    elif n >= cfg.total_chapters:
        state.transition("AUDITORIA_FINAL")
        siguiente = "auditoria_final"
    else:
        state.transition("ESCRIBIENDO")
        siguiente = "escribir"

    _out(f"Capítulo {n} aceptado desde el intento i{iteration} "
         f"(media {best['media']}){' CON DEUDA' if with_debt else ''}.",
         f"- Promovido a `{cfg.chapter_path(n).as_posix()}`",
         f"- Ficha en `{cfg.card_path(n).as_posix()}`",
         f"- Deltas aplicados: {len(applied)}")
    for a in applied:
        _out(f"    · {a}")
    if moved:
        _out(f"- Notas del autor aplicadas: {len(moved)}")
    if violations:
        _out("- AVISOS de reglas bloqueantes (8.2):")
        for v in violations:
            _out(f"    · {v}")
    _out(f"SIGUIENTE: {siguiente}")
    return OK


# ==========================================================================
# actos, auditoria y puertas
# ==========================================================================
def cmd_save_report(args) -> int:
    cfg, state = _cfg_state(args)
    act = args.act or state["acto_actual"]
    text = read(Path(args.file))
    if not text.strip():
        _out("El informe está vacío.")
        return FAIL
    write(cfg.report_path(act), text)
    state.record_usage(1)
    state.transition("GATE_ACTO", puerta_pendiente=f"acto_{act}")
    _out(f"Informe del acto {act} guardado en `{cfg.report_path(act).as_posix()}`.",
         "ACCION: presentar_puerta_acto")
    return OK


def cmd_audit(args) -> int:
    cfg, state = _cfg_state(args)
    violations = rules.final_audit(cfg) if args.final \
        else rules.check_state(cfg, args.chapter or state["capitulo_actual"])
    if not violations:
        _out("AUDITORIA: sin incidencias.")
        if args.final:
            state.transition("GATE_FINAL", puerta_pendiente="final")
        return OK
    _out(f"AUDITORIA: {len(violations)} incidencias.")
    for v in violations:
        _out(f"  - {v}")
    return FAIL if args.final else OK


def cmd_validate_bible(args) -> int:
    cfg, _ = _cfg_state(args)
    violations = rules.validate_bible(cfg)
    if not violations:
        _out("BIBLIA: los cuatro artefactos cumplen su esquema.")
        return OK
    _out(f"BIBLIA: {len(violations)} problemas de esquema.")
    for v in violations:
        _out(f"  - {v}")
    return FAIL


def cmd_gate(args) -> int:
    cfg, state = _cfg_state(args)
    answer = (args.answer or "").strip().lower()
    gate = state.name

    if gate == "GATE_PLAN":
        if answer in {"aprobar", "approve"}:
            problems = rules.validate_bible(cfg)
            if problems and not args.force:
                _out("No se puede aprobar el plan: la biblia no cumple su esquema.")
                for p in problems:
                    _out(f"  - {p}")
                return FAIL
            cmd_seed_clues(args)
            S.write_rolling_summary(cfg, 1)
            state.transition("ESCRIBIENDO", puerta_pendiente=None,
                             capitulo_actual=1, acto_actual=1)
            _out("Plan aprobado. Estado: ESCRIBIENDO, capítulo 1.")
            return OK
        if answer.startswith("rehacer") or answer.startswith("redo"):
            state.transition("GENERANDO_BIBLIA", puerta_pendiente=None)
            _out("Vuelta a GENERANDO_BIBLIA: regenera solo el artefacto indicado.")
            return OK
        if answer in {"editar", "edit"}:
            _out("Pausa para edición manual. Al reanudar, ejecuta "
                 "`validar-biblia` antes de aprobar.")
            return OK

    elif gate == "GATE_ACTO":
        if answer in {"continuar", "continue"}:
            n = state["capitulo_actual"]
            if n > cfg.total_chapters:
                state.transition("AUDITORIA_FINAL", puerta_pendiente=None)
                _out("Último acto cerrado. ACCION: auditoria_final")
            else:
                state.transition("ESCRIBIENDO", puerta_pendiente=None)
                _out(f"Continuando con la escaleta vigente. Capítulo {n}.")
            return OK
        if answer.startswith("ajustar") or answer.startswith("adjust"):
            state.transition("REVISANDO_ESCALETA", puerta_pendiente=None)
            _out("Estado: REVISANDO_ESCALETA. Lanza al Arquitecto con "
                 "[REVISION_ESCALETA].")
            return OK
        if answer in {"parar", "stop"}:
            state.save()
            _out("Estado persistido. Puedes cerrar la sesión.")
            return OK

    elif gate == "GATE_BLOQUEO":
        if answer in {"forzar", "force"}:
            state.transition("ACEPTANDO", puerta_pendiente=None)
            _out("Bloqueo forzado: el capítulo se aceptará con deuda. "
                 "Ejecuta `aceptar`.")
            return OK
        if answer.startswith("reescribir") or answer.startswith("rewrite"):
            state.transition("PARCHEANDO", puerta_pendiente=None,
                             iteracion=state["iteracion"] + 1)
            _out(f"Vuelta al Escritor en la iteración {state['iteracion']}.")
            return OK
        if answer in {"parar", "stop"}:
            state.save()
            _out("Estado persistido.")
            return OK

    elif gate == "GATE_FINAL":
        if answer in {"aceptar", "accept", "aprobar"}:
            state.transition("COMPLETADO", puerta_pendiente=None)
            _out("Novela completada.")
            return OK

    _out(f"Respuesta `{args.answer}` no válida para la puerta {gate}.")
    return FAIL


def cmd_seed_clues(args) -> int:
    """Crea `pistas.md` a partir de la escaleta aprobada (6.6)."""
    cfg, _ = _cfg_state(args)
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))

    premise = read(cfg.bible_path("premisa.md"))
    descriptions: dict[str, str] = {}
    for line in premise.splitlines():
        m = __import__("re").match(r"\s*[-*]\s*(P-\d+)\s*[·:—-]\s*(.+)", line)
        if m:
            descriptions[m.group(1)] = m.group(2).strip()

    planned_resolution: dict[str, int] = {}
    kinds: dict[str, str] = {}
    first_plant: dict[str, int] = {}
    for n in sorted(outline):
        entry = outline[n]
        for cid in entry.plant:
            first_plant.setdefault(cid, n)
        for cid in entry.resolve:
            planned_resolution.setdefault(cid, n)

    for n in sorted(outline):
        body = outline[n].body.lower()
        for cid in outline[n].clue_ids:
            if "red herring" in body or "red_herring" in body:
                kinds.setdefault(cid, "red_herring")

    created = 0
    for cid in sorted(set(first_plant) | set(planned_resolution)
                      | {c for e in outline.values() for c in e.clue_ids}):
        if ledger.by_id(cid):
            continue
        ledger.clues.append(Clue(
            id=cid,
            descripcion=descriptions.get(cid, "(descrita en la premisa)"),
            tipo=kinds.get(cid, "real"),
            estado="PREVISTA",
            plantada_en=str(first_plant.get(cid, "-")),
            tocada_en="-",
            resolucion_prevista=str(planned_resolution.get(cid, "-")),
        ))
        created += 1
    ledger.clues.sort(key=lambda c: c.id)
    ledger.save(cfg.state_path("pistas.md"))
    _out(f"Ledger de pistas sembrado desde la escaleta: {created} pistas nuevas, "
         f"{len(ledger.clues)} en total.")
    return OK


def cmd_save_bible(args) -> int:
    cfg, state = _cfg_state(args)
    text = read(Path(args.file))
    if not text.strip():
        _out("El artefacto está vacío.")
        return FAIL
    target = cfg.bible_path(args.name)
    write(target, text)
    state.record_usage(1)
    _out(f"Guardado `{target.as_posix()}` ({word_count(text)} palabras).")
    if args.gate:
        state.transition("GATE_PLAN", puerta_pendiente="plan")
        _out("ACCION: presentar_puerta_plan")
    return OK


def cmd_commit(args) -> int:
    cfg, state = _cfg_state(args)
    n = args.chapter or (state["capitulo_actual"] - 1)
    if not cfg["ejecucion"].get("commit_por_capitulo", True):
        _out("commit_por_capitulo está desactivado en config.json.")
        return OK
    card = Card.load(cfg.card_path(n), n)
    title = (card.title if card else "") or f"capítulo {n}"
    message = f"feat(novela): capítulo {n:02d} — {title}"
    paths = [cfg["rutas"]["capitulos"], cfg["rutas"]["estado"],
             cfg["rutas"]["archivo_estado"], cfg["rutas"]["notas_autor"],
             cfg["rutas"]["informes"]]
    try:
        subprocess.run(["git", "add", *paths], cwd=cfg.root, check=True,
                       capture_output=True)
        result = subprocess.run(["git", "commit", "-m", message], cwd=cfg.root,
                                capture_output=True, text=True)
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            _out(f"git commit falló: {result.stdout}{result.stderr}")
            return FAIL
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        _out(f"No se pudo commitear (puerto P5 es opcional, Anexo B.1): {exc}")
        return OK
    _out(f"Commit: {message}")
    return OK


# ==========================================================================
# parser
# ==========================================================================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m harness",
                                description="Núcleo determinista del harness de novela.")
    p.add_argument("--root", help="Raíz del repositorio (por defecto, el cwd).")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="Crea la estructura de novela/ y estado.json.")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("status", help="Imprime el estado actual.")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("next", help="Dice qué acción toca a continuación.")
    s.add_argument("--skip-audit", action="store_true")
    s.set_defaults(func=cmd_next)

    s = sub.add_parser("prompt", help="Ensambla el contexto de un rol (§7).")
    s.add_argument("role", choices=["escritor", "evaluador", "continuista",
                                    "editor_acto", "arquitecto"])
    s.add_argument("--chapter", type=int)
    s.add_argument("--act", type=int)
    s.add_argument("--draft", help="Archivo con el borrador a juzgar.")
    s.add_argument("--patches", help="Archivo con el bloque PARCHES SOLICITADOS.")
    s.add_argument("--task", help="Tarea del Arquitecto, p. ej. [ESCALETA].")
    s.add_argument("--schema", help="Nombre del esquema en harness/schemas/.")
    s.add_argument("--extra", help="Archivo con material de partida.")
    s.add_argument("--output", "-o", help="Escribe el contexto en este archivo.")
    s.set_defaults(func=cmd_prompt)

    s = sub.add_parser("save-attempt", help="Guarda un borrador en .intentos/.")
    s.add_argument("--file", required=True)
    s.add_argument("--chapter", type=int)
    s.add_argument("--iteration", type=int)
    s.add_argument("--patched-scenes", help="Escenas autorizadas, p. ej. 1,3.")
    s.set_defaults(func=cmd_save_attempt)

    s = sub.add_parser("record", help="Registra el informe de un juez.")
    s.add_argument("kind", choices=["eval", "cont"])
    s.add_argument("--file", required=True)
    s.add_argument("--chapter", type=int)
    s.add_argument("--iteration", type=int)
    s.set_defaults(func=cmd_record)

    s = sub.add_parser("decide", help="Aplica la condición de aceptación (§9.2).")
    s.add_argument("--chapter", type=int)
    s.set_defaults(func=cmd_decide)

    s = sub.add_parser("patch-plan", help="Fusiona parches y contradicciones.")
    s.add_argument("--chapter", type=int)
    s.add_argument("--output", "-o")
    s.set_defaults(func=cmd_patch_plan)

    s = sub.add_parser("accept", help="Promueve, aplica deltas y regenera estado.")
    s.add_argument("--chapter", type=int)
    s.set_defaults(func=cmd_accept)

    s = sub.add_parser("save-report", help="Guarda el informe del Editor de acto.")
    s.add_argument("--file", required=True)
    s.add_argument("--act", type=int)
    s.set_defaults(func=cmd_save_report)

    s = sub.add_parser("save-bible", help="Guarda un artefacto de la biblia.")
    s.add_argument("--name", required=True,
                   help="entrevista.md | premisa.md | personajes.md | "
                        "voz-y-estilo.md | escaleta.md")
    s.add_argument("--file", required=True)
    s.add_argument("--gate", action="store_true",
                   help="Tras guardar, abre la Puerta 1.")
    s.set_defaults(func=cmd_save_bible)

    s = sub.add_parser("seed-clues", help="Siembra pistas.md desde la escaleta.")
    s.set_defaults(func=cmd_seed_clues)

    s = sub.add_parser("audit", help="Reglas de §8.2 o auditoría final de §8.3.")
    s.add_argument("--final", action="store_true")
    s.add_argument("--chapter", type=int)
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("validate-bible", help="Valida los esquemas de §6.")
    s.set_defaults(func=cmd_validate_bible)

    s = sub.add_parser("gate", help="Responde a una puerta humana (§11).")
    s.add_argument("--answer", required=True)
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_gate)

    s = sub.add_parser("commit", help="Commit del capítulo aceptado (puerto P5).")
    s.add_argument("--chapter", type=int)
    s.set_defaults(func=cmd_commit)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:                      # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return FAIL


if __name__ == "__main__":
    sys.exit(main())
