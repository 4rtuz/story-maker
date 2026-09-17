"""Descubrimiento, alta y lectura de ejecuciones (puertos P2 y P3, solo lectura).

Todo lo que se lee sale de `harness.config.Config`: es quien sabe donde vive cada
artefacto. Construir aqui las rutas a mano repetiria la tabla `rutas` de
config.json y se romperia en cuanto un perfil la cambiara.

La ejecucion de la raiz del repo se llama `novela`; las demas viven en
`runs/<slug>/` y se recorren con el flag `--root` que el nucleo ya trae.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from harness.artifacts import Card, field, parse_outline, read, word_count, write
from harness.config import Config, load
from harness.scenes import Chapter

# Identificador de ejecucion: minusculas, digitos y guiones. Es ademas el unico
# filtro entre la URL y el sistema de archivos, asi que no se relaja.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
ROOT_SLUG = "novela"
RUNS_DIR = "runs"
LOG_NAME = "panel-run.jsonl"
IDEA_NAME = "idea.md"


# --------------------------------------------------------------------------
# resolucion de rutas
# --------------------------------------------------------------------------
def slugify(raw: str) -> str:
    """Convierte un titulo libre en un identificador aceptable."""
    s = raw.strip().lower()
    for a, b in zip("áéíóúüñ", "aeiouun"):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:40].strip("-")


def root_for(repo: Path, slug: str) -> Path:
    """Raiz del `--root` de esa ejecucion. Frontera de confianza: valida el slug
    y comprueba que la ruta resuelta no se sale de `runs/`."""
    if slug == ROOT_SLUG:
        return repo
    if not SLUG_RE.match(slug):
        raise ValueError(f"Identificador no válido: {slug!r}")
    base = (repo / RUNS_DIR).resolve()
    root = (base / slug).resolve()
    if root.parent != base:
        raise ValueError(f"Identificador no válido: {slug!r}")
    return root


def load_cfg(repo: Path, slug: str) -> Config:
    return load(root_for(repo, slug))


def _read_state(cfg: Config) -> dict:
    path = cfg.path("archivo_estado")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Escritura a medias es imposible (os.replace es atomico), pero un
        # archivo editado a mano si puede quedar roto: no tumbes el panel.
        return {}


def exists(repo: Path, slug: str) -> bool:
    try:
        return (root_for(repo, slug) / "novela" / "config.json").exists()
    except ValueError:
        return False


def discover(repo: Path) -> list[str]:
    """Slugs de todas las ejecuciones, la de la raiz primero."""
    slugs = [ROOT_SLUG] if exists(repo, ROOT_SLUG) else []
    base = repo / RUNS_DIR
    if base.is_dir():
        slugs += sorted(d.name for d in base.iterdir()
                        if d.is_dir() and SLUG_RE.match(d.name) and exists(repo, d.name))
    return slugs


# --------------------------------------------------------------------------
# lectura de una ejecucion
# --------------------------------------------------------------------------
def title_of(cfg: Config) -> str:
    """Logline de la premisa; si aun no hay biblia, el titulo del capitulo 1."""
    from harness.artifacts import sections
    logline = sections(read(cfg.bible_path("premisa.md")), 2).get("Logline", "")
    logline = logline.strip().splitlines()[0].strip() if logline.strip() else ""
    if logline:
        return logline
    first = cfg.chapter_path(1)
    return Chapter(read(first)).title if first.exists() else ""


def summary(repo: Path, slug: str) -> dict:
    """Ficha corta para la lista de ejecuciones."""
    cfg = load_cfg(repo, slug)
    state = _read_state(cfg)
    return {
        "slug": slug,
        "ruta": ROOT_SLUG + "/" if slug == ROOT_SLUG else f"{RUNS_DIR}/{slug}/",
        "titulo": title_of(cfg),
        "perfil": state.get("perfil", cfg.profile_name),
        "estado": state.get("estado", "INIT"),
        "puerta_pendiente": state.get("puerta_pendiente"),
        "total": cfg.total_chapters,
        "aceptados": state.get("capitulos_aceptados", []),
        "con_deuda": _chapters_in_debt(cfg),
    }


def _chapters_in_debt(cfg: Config) -> list[int]:
    text = read(cfg.state_path("deuda-narrativa.md"))
    return [int(m) for m in re.findall(r"^##\s*Cap[íi]tulo\s+(\d+)", text, re.M)]


# Subpaso del ciclo, derivado de que archivos existen en `.intentos/`. Es la
# misma senal que usa `harness next`, pero aqui es solo para mostrar: la orden
# `next` tiene efectos laterales (puede pasar a CUOTA_PAUSADA o GATE_BLOQUEO) y
# por eso el sondeo no la ejecuta. Quien decide sigue siendo el nucleo.
EN_CICLO = {"ESCRIBIENDO", "EVALUANDO", "PARCHEANDO", "ACEPTANDO"}


def _substep(cfg: Config, chapter: int, iteration: int) -> str:
    intentos = cfg.path("intentos")
    if not cfg.attempt_path(chapter, iteration).exists():
        return "escribir"
    if not (intentos / f"{chapter:02d}-i{iteration}-eval.json").exists():
        return "evaluar"
    if not (intentos / f"{chapter:02d}-i{iteration}-cont.json").exists():
        return "verificar"
    return "decidir"


def snapshot(repo: Path, slug: str, log_limit: int = 60) -> dict:
    """Todo lo que la vista de progreso sondea. Lectura pura: no transiciona."""
    cfg = load_cfg(repo, slug)
    state = _read_state(cfg)
    n = state.get("capitulo_actual", 1)
    data = {
        "slug": slug,
        "titulo": title_of(cfg),
        "estado": state.get("estado", "INIT"),
        "capitulo_actual": n,
        "acto_actual": state.get("acto_actual", 1),
        "iteracion": state.get("iteracion", 0),
        "intentos": state.get("intentos", []),
        "capitulos_aceptados": state.get("capitulos_aceptados", []),
        "puerta_pendiente": state.get("puerta_pendiente"),
        "cuota": state.get("cuota", {}),
        "perfil": state.get("perfil", cfg.profile_name),
        "total": cfg.total_chapters,
        "umbral": cfg["evaluacion"]["umbral_media"],
        "umbral_bloqueante": cfg["evaluacion"]["umbral_criterio_bloqueante"],
        "criterios_bloqueantes": cfg["evaluacion"]["criterios_bloqueantes"],
        "max_reescrituras": cfg["evaluacion"]["max_reescrituras"],
        # solo dentro del ciclo de escritura: en INIT o en una puerta no
        # significa nada y confunde
        "paso": (_substep(cfg, n, state.get("iteracion", 0))
                 if state.get("estado") in EN_CICLO and n <= cfg.total_chapters else ""),
        "espera_respuesta": _awaiting_answer(cfg),
        "archivos": _scratch(cfg),
        "eventos": events(cfg, log_limit),
        "pistas": _clues(cfg),
        "historial": _attempt_history(cfg),
    }
    return data


# `estado.json` solo guarda los intentos del capitulo en curso: al cerrarlo,
# `reset_chapter_scratch()` los borra (§9.4). Los `-eval.json` de `.intentos/`,
# en cambio, siguen en disco, y son la unica memoria de los capitulos ya
# aceptados. Lectura pura: si un archivo esta roto, ese intento no sale.
EVAL_RE = re.compile(r"^(\d+)-i(\d+)-eval\.json$")


def _attempt_history(cfg: Config) -> list[dict]:
    intentos = cfg.path("intentos")
    if not intentos.is_dir():
        return []
    out = []
    for path in intentos.iterdir():
        m = EVAL_RE.match(path.name)
        if not m:
            continue
        try:
            ev = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        notas = ev.get("puntuaciones") or {}
        out.append({
            "capitulo": int(m.group(1)),
            "iteracion": int(m.group(2)),
            "media": ev.get("media"),
            "puntuaciones": notas,
            "ruta": f"{m.group(1)}-i{m.group(2)}.md",
        })
    out.sort(key=lambda a: (a["capitulo"], a["iteracion"]))
    return out


def _scratch(cfg: Config, limit: int = 14) -> list[dict]:
    """Los archivos de `.intentos/` por fecha. Su mtime es el unico reloj que
    tiene el harness: dice cuando se lanzo cada subagente."""
    intentos = cfg.path("intentos")
    if not intentos.is_dir():
        return []
    files = [p for p in intentos.iterdir() if p.is_file() and p.name != LOG_NAME]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"nombre": p.name, "ts": p.stat().st_mtime, "bytes": p.stat().st_size}
            for p in files[:limit]]


# Fase A de la skill: el Arquitecto pregunto, el turno se acabo y las lineas
# `**Respuesta:**` siguen vacias. No mueve `estado.json` —por eso el panel no
# puede deducirlo de la firma— y es el unico momento en que el autor tiene que
# escribir algo que no es una puerta del nucleo.
VACIA_RE = re.compile(r"^\*\*Respuesta:\*\*\s*$", re.M)


def _awaiting_answer(cfg: Config) -> bool:
    return bool(VACIA_RE.search(read(cfg.bible_path("entrevista.md"))))


def _clues(cfg: Config) -> list[dict]:
    from harness.artifacts import ClueLedger
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    return [{"id": c.id, "tipo": c.tipo, "estado": c.estado,
             "tocada": c.tocada_en, "descripcion": c.descripcion}
            for c in ledger.clues]


# --------------------------------------------------------------------------
# eventos del orquestador (propuesta nueva: ver docs/anexo-c-panel-web.md)
# --------------------------------------------------------------------------
def log_path(cfg: Config) -> Path:
    return cfg.path("intentos") / LOG_NAME


def events(cfg: Config, limit: int = 60) -> list[dict]:
    """Cola de `panel-run.jsonl`, el stream del orquestador ya aplanado.

    El formato de `claude --output-format stream-json` no es un contrato: si una
    linea no encaja, se ignora en vez de romper la vista.
    """
    path = log_path(cfg)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[dict] = []
    for line in lines[-400:]:
        line = line.strip()
        if not line:
            continue
        try:
            out += _flatten(json.loads(line))
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    return out[-limit:]


AGENTS = {"arquitecto", "escritor", "evaluador", "continuista", "editor-acto"}

# Subtipos de `system` que dicen algo. El resto —thinking_tokens, hooks,
# tool_progress, rate_limit_event— es ruido de transporte y se tira.
SHELLS = ("Bash", "PowerShell")

# Una orden del nucleo dentro de un comando de shell. La usa tambien
# `panel.tracing` para nombrar la herramienta en la traza.
CORE_CMD = re.compile(r"-m\s+harness\s+(?:--root\s+\S+\s+)?([a-z-]+(?:\s+[a-z]+)?)")


def _flatten(obj: dict) -> list[dict]:
    """Una linea del stream -> 0..n eventos `{tipo, texto, agente}`."""
    kind = obj.get("type")

    if kind == "system":
        sub = obj.get("subtype")
        if sub == "init":
            return [{"tipo": "sistema", "texto": "orquestador listo"}]
        if sub == "task_started":
            # Aqui viene el subagente, no en el bloque `tool_use` de Task.
            agent = str(obj.get("subagent_type", "")).strip()
            desc = str(obj.get("description", "")).strip()
            return [{"tipo": "agente", "agente": agent if agent in AGENTS else "",
                     "texto": f"▸ {agent or 'subagente'}{f' · {desc}' if desc else ''}"}]
        if sub == "permission_denied":
            return [{"tipo": "aviso",
                     "texto": f"permiso denegado: {obj.get('tool_name', '?')}"}]
        return []

    if kind == "result":
        ok = obj.get("subtype") == "success"
        return [{"tipo": "fin" if ok else "error",
                 "texto": "orquestador terminado" if ok else str(obj.get("subtype"))}]

    if kind != "assistant":
        return []

    message = obj.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    out: list[dict] = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and str(block.get("text", "")).strip():
            # Generoso a proposito: las preguntas de la entrevista son el unico
            # sitio del panel donde el autor lee lo que le pregunta el
            # orquestador, y a 400 caracteres se cortaban por la mitad.
            out.append({"tipo": "texto", "texto": str(block["text"]).strip()[:4000]})
        elif block.get("type") == "tool_use":
            out.append(_tool_event(block))
    return [e for e in out if e]


def _tool_event(block: dict) -> dict | None:
    name = block.get("name", "")
    args = block.get("input", {}) or {}
    if name in SHELLS:
        cmd = " ".join(str(args.get("command", "")).split())
        # las ordenes del nucleo se destacan; el resto es ruido de shell
        m = CORE_CMD.search(cmd)
        if m:
            return {"tipo": "nucleo", "texto": f"harness {m.group(1)}"}
        return {"tipo": "shell", "texto": cmd[:110]}
    if name in ("Write", "Read"):
        return {"tipo": "io", "texto": f"{name} {Path(str(args.get('file_path', ''))).name}"}
    return None


# Un subagente sigue vivo mientras no haya pasado nada detras suyo: en cuanto el
# orquestador vuelve a escribir, a leer o a llamar al nucleo, es que ya respondio.
CIERRAN = {"nucleo", "io", "texto", "fin", "error"}


def running_agent(evs: list[dict]) -> str:
    for ev in reversed(evs):
        if ev.get("tipo") in CIERRAN:
            return ""
        if ev.get("tipo") == "agente" and ev.get("agente"):
            return ev["agente"]
    return ""


# --------------------------------------------------------------------------
# lectura de capitulos (puerto P2)
# --------------------------------------------------------------------------
def chapters(repo: Path, slug: str) -> list[dict]:
    """Los capitulos del perfil: los escritos desde `capitulos/`, los que faltan
    desde la escaleta. Nunca se escribe nada aqui."""
    cfg = load_cfg(repo, slug)
    state = _read_state(cfg)
    outline = parse_outline(read(cfg.bible_path("escaleta.md")))
    debt = _chapters_in_debt(cfg)
    accepted = state.get("capitulos_aceptados", [])

    out = []
    for n in range(1, cfg.total_chapters + 1):
        path = cfg.chapter_path(n)
        entry = {"numero": n, "acto": cfg.act_of(n), "escrito": path.exists(),
                 "aceptado": n in accepted, "deuda": n in debt,
                 "titulo": "", "escenas": 0, "palabras": 0, "media": None}
        if path.exists():
            text = read(path)
            ch = Chapter(text)
            entry["titulo"] = ch.title
            entry["escenas"] = len(ch.scenes)
            entry["palabras"] = word_count(text)
            card = Card.load(cfg.card_path(n), n)
            if card:
                entry["media"] = _as_float(field(card.text, "Media del Evaluador"))
                entry["gancho"] = card.hook
                entry["focalizador"] = card.pov
        elif n in outline:
            entry["titulo"] = outline[n].title
            entry["focalizador"] = outline[n].pov
        out.append(entry)
    return out


def chapter(repo: Path, slug: str, n: int) -> dict | None:
    """Un capitulo con sus escenas separadas, o None si aun no esta escrito."""
    cfg = load_cfg(repo, slug)
    if not 1 <= n <= cfg.total_chapters:
        return None
    path = cfg.chapter_path(n)
    if not path.exists():
        return None
    text = read(path)
    ch = Chapter(text)
    card = Card.load(cfg.card_path(n), n)
    return {
        "numero": n,
        "acto": cfg.act_of(n),
        "titulo": ch.title,
        "palabras": word_count(text),
        "markdown": text,
        "escenas": [{"n": k, "texto": ch.scenes[k]} for k in sorted(ch.scenes)],
        "ficha": {
            "focalizador": card.pov if card else "",
            "dia": card.day if card else "",
            "presentes": card.present if card else "",
            "gancho": card.hook if card else "",
            "resumen": card.summary if card else "",
            "media": _as_float(field(card.text, "Media del Evaluador")) if card else None,
        },
    }


def _as_float(raw: str):
    try:
        return float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# alta de una ejecucion nueva
# --------------------------------------------------------------------------
def cli(repo: Path, root: Path, *args: str) -> tuple[int, str]:
    """Invoca el nucleo. El panel nunca reimplementa una orden del CLI."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "harness", "--root", str(root), *args],
        cwd=str(repo), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def create(repo: Path, slug: str, idea: str = "", profile: str = "") -> dict:
    """Crea `runs/<slug>/` y deja el nucleo inicializarlo.

    Nunca sobrescribe: si la carpeta ya existe, falla. `novela/` es intocable.
    """
    if slug == ROOT_SLUG:
        raise ValueError("`novela` es la ejecución de la raíz: no se puede recrear.")
    root = root_for(repo, slug)
    if root.exists():
        raise ValueError(f"`{RUNS_DIR}/{slug}/` ya existe.")

    source = repo / "novela" / "config.json"
    if not source.exists():
        raise ValueError("No hay `novela/config.json` del que partir.")

    raw = json.loads(source.read_text(encoding="utf-8"))
    if profile:
        if profile not in raw.get("perfiles", {}):
            raise ValueError(f"Perfil desconocido: {profile!r}")
        raw["perfil_activo"] = profile

    (root / "novela").mkdir(parents=True)
    (root / "novela" / "config.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rc, out = cli(repo, root, "init")
    if rc != 0:
        shutil.rmtree(root, ignore_errors=True)
        raise RuntimeError(f"`harness init` falló: {out.strip()}")

    if idea.strip():
        cfg = load(root)
        write(cfg.path("intentos") / IDEA_NAME, idea.strip())

    return {"slug": slug, "salida": out.strip()}


# --------------------------------------------------------------------------
# autocomprobacion: python -m panel.runs
# --------------------------------------------------------------------------
if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent

    assert slugify("El Buzón de la Planta Baja") == "el-buzon-de-la-planta-baja"
    assert slugify("  ¿¿??  ") == ""
    assert slugify("a" * 60) == "a" * 40

    assert root_for(repo, ROOT_SLUG) == repo
    assert root_for(repo, "casa-vacia") == (repo / RUNS_DIR / "casa-vacia").resolve()
    for bad in ("../etc", "a/b", "Mayus", "-guion", "", "a" * 41, "con espacio"):
        try:
            root_for(repo, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"slug aceptado y no debería: {bad!r}")

    assert VACIA_RE.search("**Respuesta:**")
    assert not VACIA_RE.search("**Respuesta:** (A) Una vecina")

    assert _as_float("3,5") == 3.5 and _as_float("4.0") == 4.0 and _as_float("") is None

    for shell in ("Bash", "PowerShell"):
        ev = _tool_event({"name": shell, "input": {"command": "python -m harness --root runs/x next"}})
        assert ev == {"tipo": "nucleo", "texto": "harness next"}, ev
    assert _tool_event({"name": "Bash", "input": {"command": "ls -la"}})["tipo"] == "shell"
    assert _tool_event({"name": "Glob", "input": {}}) is None

    # formas reales observadas en el stream de `claude --output-format stream-json`
    assert _flatten({"type": "system", "subtype": "thinking_tokens"}) == []
    assert _flatten({"type": "system", "subtype": "task_started",
                     "subagent_type": "arquitecto", "description": "Entrevista"})[0]["agente"] == "arquitecto"
    assert _flatten({"type": "system", "subtype": "permission_denied",
                     "tool_name": "PowerShell"})[0]["tipo"] == "aviso"
    assert _flatten({"type": "assistant", "message": {"content": "texto suelto"}}) == []
    assert _flatten({"type": "rate_limit_event"}) == []

    assert running_agent([{"tipo": "agente", "agente": "evaluador"}]) == "evaluador"
    assert running_agent([{"tipo": "agente", "agente": "escritor"},
                          {"tipo": "io", "texto": "Write raw.md"}]) == ""

    debt = "# Deuda narrativa\n\n## Capítulo 3 — aceptado con 2.8 tras 2 iteraciones\n"
    assert re.findall(r"^##\s*Cap[íi]tulo\s+(\d+)", debt, re.M) == ["3"]

    assert discover(repo)[0] == ROOT_SLUG
    caps = chapters(repo, ROOT_SLUG)
    assert len(caps) == 3 and caps[0]["titulo"] == "El recibo que seguía vivo", caps
    assert all(c["escrito"] and c["aceptado"] and not c["deuda"] for c in caps), caps
    assert caps[2]["media"] == 3.67, caps[2]
    assert chapter(repo, ROOT_SLUG, 1)["escenas"][0]["n"] == 1
    assert chapter(repo, ROOT_SLUG, 99) is None
    assert snapshot(repo, ROOT_SLUG)["estado"] == "COMPLETADO"

    print("panel.runs: comprobaciones correctas.")
