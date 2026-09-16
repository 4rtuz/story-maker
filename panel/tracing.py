"""Traza en Langfuse lo que hace el orquestador (Anexo C, binding secundario).

El harness no llama nunca a un modelo desde Python: quien llama es el binding de
Claude Code, que el panel arranca como subproceso y cuyo stream ya vuelca a
`.intentos/panel-run.jsonl`. Ese stream trae todo lo que Langfuse necesita
—modelo, tokens, subagentes, herramientas, coste— asi que aqui solo se traduce.

Reparto (ver CLAUDE.md): esto vive en `panel/` porque menciona identificadores de
modelo y el runtime. El nucleo (`harness/`) no se entera de que existe Langfuse.

Alcance de una traza: una invocacion del orquestador, que por 7.5 es un capitulo.
Las trazas de una misma novela se agrupan por `session_id` = slug de la ejecucion.

Arbol que se emite:

    agent  orquestar-capitulo          <- raiz, input = prompt de arranque
    |- generation  turno-orquestador   <- cada mensaje del orquestador
    |- tool  harness-next              <- hermana de la generation que la pidio
    |- agent  escritor                 <- el subagente, con su prompt y su salida
    +- event  permiso-denegado

Si falta el SDK o las claves, `Tracer` se queda mudo: el panel funciona igual y
sigue siendo stdlib puro. Tampoco se deja reventar el hilo de volcado: cualquier
error de trazado se traga en `feed`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from harness.artifacts import read
from harness.config import Config

from . import runs

# Recorte de cortesia: el prompt del Escritor son 16k tokens y eso se manda
# entero a proposito (es el contexto con el que decidio), pero un volcado
# accidental de medio repositorio no.
MAX_TEXT = 200_000

# El `Task` que lanza un subagente no se emite como herramienta: ya esta
# representado por su propia observacion `agent`, y duplicarlo ensucia el grafo.
SKIP_TOOLS = {"Task", "Agent"}

TOOL_NAMES = {"Write": "escribir-archivo", "Read": "leer-archivo"}

# Claves de uso de Anthropic -> cubos de Langfuse. Son excluyentes entre si
# (`input_tokens` ya no incluye cache), que es justo lo que Langfuse espera.
USAGE_KEYS = {
    "input": "input_tokens",
    "output": "output_tokens",
    "cache_creation_input_tokens": "cache_creation_input_tokens",
    "cache_read_input_tokens": "cache_read_input_tokens",
}


def load_env(repo: Path) -> None:
    """Mete el `.env` del repositorio en el entorno. Sin dependencias: son tres
    lineas y `python-dotenv` no aporta nada aqui. Lo ya definido manda."""
    path = repo / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def client(repo: Path):
    """El cliente de Langfuse, o None si no se puede trazar. Nunca lanza: el
    trazado es accesorio y jamas debe impedir que se escriba la novela."""
    load_env(repo)
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import Langfuse
        return Langfuse(
            base_url=os.environ.get("LANGFUSE_BASE_URL") or os.environ.get("LANGFUSE_HOST"),
            environment=os.environ.get("LANGFUSE_TRACING_ENVIRONMENT", "development"),
        )
    except Exception:
        return None


def tool_name(block: dict) -> str:
    """Nombre estable y de baja cardinalidad para una llamada a herramienta.

    Langfuse trata los nombres como una API: los evaluadores y los paneles
    filtran por ellos, asi que no puede entrar el comando concreto.
    """
    name = block.get("name", "")
    if name in runs.SHELLS:
        cmd = " ".join(str((block.get("input") or {}).get("command", "")).split())
        m = runs.CORE_CMD.search(cmd)
        return f"harness-{m.group(1).replace(' ', '-')}" if m else "shell"
    return TOOL_NAMES.get(name, name or "herramienta")


def _usage(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    out = {k: raw[v] for k, v in USAGE_KEYS.items() if isinstance(raw.get(v), int)}
    return out or None


def _blocks(content) -> list[dict]:
    """Los bloques de un mensaje del orquestador, sin la firma del razonamiento:
    son varios kB de base64 opaco por bloque y no dicen nada a quien lee la traza."""
    out = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "thinking":
            out.append({"type": "thinking", "thinking": block.get("thinking", "")})
        else:
            out.append(block)
    return out


def _clip(value):
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f"\n[... recortado, {len(value)} caracteres]"
    return value


class Tracer:
    """Traduce el stream de una ejecucion del orquestador a una traza.

    Con `lf=None` todos los metodos son un no-op, que es el caso cuando no hay
    SDK ni claves.
    """

    def __init__(self, lf, slug: str, cfg: Config | None, prompt: str = ""):
        self.lf = lf
        self.slug = slug
        self.cfg = cfg
        self.prompt = prompt
        self.root = None
        self.gens = 0
        self.tools: dict[str, object] = {}     # tool_use_id -> observacion
        self.agents: dict[str, object] = {}    # task_id -> observacion
        self.pending: list[dict] = []          # lo que el modelo vio desde su ultimo turno
        self._open()

    def _open(self) -> None:
        """Abre la traza de una invocacion del orquestador, que por 7.5 es un
        capitulo. Se vuelve a llamar si un mismo log trae varias: una traza por
        unidad de trabajo, no una por archivo."""
        if self.lf is None or self.root is not None:
            return
        try:
            from langfuse import propagate_attributes
            state = runs._read_state(self.cfg) if self.cfg else {}
            # Los atributos de traza se fijan al crear la raiz: es ella quien
            # define la traza. Los hijos llegan luego, desde el hilo de volcado.
            with propagate_attributes(
                session_id=self.slug,
                trace_name="orquestar-capitulo",
                metadata={
                    "ejecucion": self.slug,
                    "perfil": state.get("perfil", ""),
                    "capitulo": state.get("capitulo_actual", 0),
                    "acto": state.get("acto_actual", 0),
                    "iteracion": state.get("iteracion", 0),
                    "estado_inicial": state.get("estado", ""),
                },
            ):
                self.root = self.lf.start_observation(
                    name="orquestar-capitulo", as_type="agent",
                    input=_clip(self.prompt) or None,
                )
            self.gens = 0
            self.pending = []   # el contexto de la invocacion anterior no cruza
        except Exception:
            self.lf = self.root = None

    # ------------------------------------------------------------------
    def feed(self, line: str) -> None:
        """Una linea cruda del stream. No propaga nunca: el hilo que vuelca el
        log no puede morir porque Langfuse tenga un mal dia."""
        if self.lf is None:
            return
        try:
            obj = json.loads(line)
            kind = obj.get("type")
            if kind == "system" and obj.get("subtype") == "init":
                self._open()   # el log se acumula: un `init` abre otra traza
            if self.root is None:
                return
            if kind == "assistant":
                self._assistant(obj)
            elif kind == "user":
                self._user(obj)
            elif kind == "system":
                self._system(obj)
            elif kind == "result":
                self._result(obj)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _assistant(self, obj: dict) -> None:
        msg = obj.get("message")
        if not isinstance(msg, dict):
            return
        content = msg.get("content")
        content = content if isinstance(content, list) else []

        # Lo que el modelo vio desde su turno anterior; en el primero, el prompt
        # de arranque. Sin esto la entrada del primer turno saldria vacia y no se
        # podria saber con que contexto decidio.
        entrada = self.pending or (_clip(self.prompt) if not self.gens else None)

        gen = self.root.start_observation(
            name="turno-orquestador", as_type="generation",
            model=msg.get("model"),
            input=entrada or None,
            output=_blocks(content),
            usage_details=_usage(msg.get("usage")),
            metadata={"stop_reason": msg.get("stop_reason"),
                      "request_id": obj.get("request_id")},
        )
        gen.end()
        self.gens += 1
        self.pending = []

        # Las herramientas cuelgan de la raiz, hermanas de la generation que las
        # pidio: asi se ve a que paso pertenece cada accion.
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") in SKIP_TOOLS:
                continue
            obs = self.root.start_observation(
                name=tool_name(block), as_type="tool",
                input=block.get("input"),
                metadata={"herramienta": block.get("name")},
            )
            self.tools[str(block.get("id"))] = obs

    def _user(self, obj: dict) -> None:
        msg = obj.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            self.pending.append({"role": "user", "content": [block]})
            obs = self.tools.pop(str(block.get("tool_use_id")), None)
            if obs is None:
                continue
            failed = bool(block.get("is_error"))
            obs.update(output=_clip(block.get("content")),
                       level="ERROR" if failed else None)
            obs.end()

    def _system(self, obj: dict) -> None:
        sub = obj.get("subtype")
        if sub == "init":
            # Del `init` solo interesa con que se arranco. El resto del bloque
            # son rutas de la maquina, plugins y sockets: ni util ni prudente.
            self.root.update(metadata={
                "modelo_sesion": obj.get("model"),
                "sesion_claude": obj.get("session_id"),
                "version_claude": obj.get("claude_code_version"),
            })
        elif sub == "task_started":
            # El subagente se emite como `agent`, no como `tool`: es lo que lo
            # convierte en un nodo propio del grafo de agentes.
            role = str(obj.get("subagent_type") or "subagente")
            obs = self.root.start_observation(
                name=role, as_type="agent",
                input=_clip(obj.get("prompt")),
                metadata={"descripcion": obj.get("description"),
                          "profundidad": obj.get("spawn_depth")},
            )
            self.agents[str(obj.get("task_id"))] = obs
        elif sub == "task_notification":
            obs = self.agents.pop(str(obj.get("task_id")), None)
            if obs is None:
                return
            usage = obj.get("usage") or {}
            # El stream da un unico `total_tokens` del subagente, sin repartir
            # entre entrada y salida y sin decir con que modelo corrio. Langfuse
            # ignora un `total` suelto (no es un cubo, es la suma de los cubos) y
            # sin modelo tampoco podria costearlo, asi que va a metadatos: mejor
            # un dato honesto en el sitio pobre que uno inventado en el bueno.
            obs.update(
                output=_clip(obj.get("summary")),
                level=None if obj.get("status") == "completed" else "ERROR",
                metadata={"tokens_totales": usage.get("total_tokens"),
                          "duracion_ms": usage.get("duration_ms"),
                          "estado": obj.get("status")},
            )
            obs.end()
        elif sub == "permission_denied":
            self.root.create_event(name="permiso-denegado", level="WARNING",
                                   input={"herramienta": obj.get("tool_name")})

    def _result(self, obj: dict) -> None:
        usage = obj.get("usage") or {}
        self.root.update(
            output=_clip(obj.get("result")),
            level="ERROR" if obj.get("is_error") else None,
            metadata={
                "coste_usd": obj.get("total_cost_usd"),
                "turnos": obj.get("num_turns"),
                "duracion_ms": obj.get("duration_ms"),
                "subagentes": (obj.get("subagent_stats") or {}).get("spawned"),
                "motivo_fin": obj.get("terminal_reason"),
                "uso_total": {k: usage[v] for k, v in USAGE_KEYS.items()
                              if isinstance(usage.get(v), int)},
            },
        )
        self._scores()
        self.close()

    # ------------------------------------------------------------------
    def _scores(self) -> None:
        """La nota del Evaluador y el veredicto del Continuista, del informe mas
        reciente de `.intentos/`. Son la senal de calidad del harness: sin ellas
        la traza dice lo que costo el capitulo, pero no si salio bien."""
        if self.cfg is None:
            return
        ev = _latest_report(self.cfg, "eval")
        if ev:
            media = ev.get("media_calculada")
            if isinstance(media, (int, float)):
                self.root.score_trace(
                    name="media-evaluador", value=float(media), data_type="NUMERIC",
                    comment=f"veredicto del modelo: {ev.get('veredicto')}",
                    metadata=ev.get("puntuaciones"))
            self.root.score_trace(
                name="aprobado-por-regla",
                value=1 if ev.get("aprobado_por_regla") else 0, data_type="BOOLEAN")
        cont = _latest_report(self.cfg, "cont")
        if cont and cont.get("veredicto"):
            self.root.score_trace(name="continuidad", value=str(cont["veredicto"]),
                                  data_type="CATEGORICAL")

    def close(self) -> None:
        """Cierra lo que quedara abierto (el orquestador pudo morir a medias) y
        vacia la cola: el panel es un proceso largo, pero el subproceso no."""
        if self.root is None:
            return
        try:
            for obs in list(self.tools.values()) + list(self.agents.values()):
                obs.update(level="WARNING", status_message="sin cerrar: el orquestador terminó antes")
                obs.end()
            self.tools.clear()
            self.agents.clear()
            self.root.end()
            self.lf.flush()
        except Exception:
            pass
        finally:
            self.root = None


def _latest_report(cfg: Config, kind: str) -> dict:
    """El informe `*-<kind>.json` mas reciente. El mtime de `.intentos/` es el
    unico reloj del harness, y `panel.runs` ya lo usa como tal."""
    intentos = cfg.path("intentos")
    if not intentos.is_dir():
        return {}
    files = sorted(intentos.glob(f"*-{kind}.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        return {}
    try:
        return json.loads(read(files[-1]) or "{}")
    except json.JSONDecodeError:
        return {}


def start(repo: Path, slug: str, prompt: str) -> Tracer:
    """Un trazador para esta ejecucion. Siempre devuelve un objeto usable."""
    try:
        cfg = runs.load_cfg(repo, slug)
    except Exception:
        cfg = None
    return Tracer(client(repo), slug, cfg, prompt)


# --------------------------------------------------------------------------
# autocomprobacion y reproduccion: python -m panel.tracing [log.jsonl]
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    repo = Path(__file__).resolve().parent.parent

    assert tool_name({"name": "Bash", "input": {"command": "python -m harness --root runs/x next"}}) == "harness-next"
    assert tool_name({"name": "PowerShell", "input": {"command": "python -m harness save-attempt"}}) == "harness-save-attempt"
    assert tool_name({"name": "Bash", "input": {"command": "ls -la"}}) == "shell"
    assert tool_name({"name": "Write", "input": {}}) == "escribir-archivo"

    assert _usage({"input_tokens": 2, "output_tokens": 1, "cache_read_input_tokens": 7}) == {
        "input": 2, "output": 1, "cache_read_input_tokens": 7}
    assert _usage(None) is None and _usage({}) is None

    assert _clip("a" * 10) == "a" * 10
    assert len(_clip("a" * (MAX_TEXT + 50))) < MAX_TEXT + 60

    # Un Tracer mudo acepta todo el stream sin quejarse ni emitir nada.
    mute = Tracer(None, "novela", None, "/novela")
    for line in ('{"type":"assistant"}', "no es json", '{"type":"result"}'):
        mute.feed(line)
    mute.close()

    if len(sys.argv) > 1:
        # Reproduce un log real contra Langfuse. Las marcas de tiempo son las de
        # ahora, no las del run: sirve para revisar la forma del arbol, no para
        # medir latencias.
        log = Path(sys.argv[1])
        slug = log.parent.parent.parent.name
        tracer = start(repo, slug if runs.exists(repo, slug) else runs.ROOT_SLUG, f"reproducción de {log.name}")
        if tracer.root is None:
            print("Sin cliente de Langfuse: revisa el `.env`.")
            raise SystemExit(1)
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                tracer.feed(line)
        tracer.close()
        print(f"panel.tracing: {log.name} reproducido en Langfuse.")
    else:
        print("panel.tracing: comprobaciones correctas.")
