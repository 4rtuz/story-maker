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


def tool_names(block: dict) -> list[str]:
    """Nombres estables y de baja cardinalidad para una llamada a herramienta.

    Langfuse trata los nombres como una API: los evaluadores y los paneles
    filtran por ellos, asi que no puede entrar el comando concreto.

    Devuelve uno por cada orden del nucleo que lleve el comando. El orquestador
    encadena ordenes con `;`, y quedandose con la primera —lo que se hacia antes—
    `harness decide`, que es la orden que aplica §9.2, no aparecia nunca en la
    traza aunque se ejecutase en cada iteracion.
    """
    name = block.get("name", "")
    if name not in runs.SHELLS:
        return [TOOL_NAMES.get(name, name or "herramienta")]
    cmd = " ".join(str((block.get("input") or {}).get("command", "")).split())
    ordenes = [f"harness-{m.group(1).replace(' ', '-')}"
               for m in runs.CORE_CMD.finditer(cmd)]
    return ordenes or ["shell"]


def _usage(raw: dict | None, salida: bool = True) -> dict | None:
    """Los cubos de uso de Langfuse a partir de la `usage` de Anthropic.

    `salida=False` para el uso por turno: el stream trae el `output_tokens` del
    `message_start`, que vale 1, y nunca reemite el definitivo. Contarlo es peor
    que no contarlo —en una traza real sumaba 789 tokens de salida cuando los
    reales eran 42.501—, asi que el turno declara solo lo que sabe y el total
    bueno se pone en la raiz desde el `result`.
    """
    if not isinstance(raw, dict):
        return None
    keys = USAGE_KEYS if salida else {k: v for k, v in USAGE_KEYS.items() if k != "output"}
    out = {k: raw[v] for k, v in keys.items() if isinstance(raw.get(v), int)}
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

    def __init__(self, lf, slug: str, cfg: Config | None, prompt: str = "",
                 replay: bool = False):
        self.lf = lf
        self.slug = slug
        self.cfg = cfg
        self.prompt = prompt
        self.replay = replay
        self.root = None
        self.gens = 0
        self.tools: dict[str, list] = {}       # tool_use_id -> observaciones
        self.agents: dict[str, object] = {}    # task_id -> observacion
        self.msgs: dict[str, list] = {}        # message.id -> [observacion, bloques]
        self.pending: list[dict] = []          # lo que el modelo vio desde su ultimo turno
        self.cuota: list[dict] = []            # utilizacion de las ventanas, primera y ultima
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
            self.msgs = {}
            self.cuota = []
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
            elif kind == "rate_limit_event":
                self._rate_limit(obj)
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

        # Claude Code emite un evento `assistant` por bloque de contenido del
        # mismo mensaje: el `text` y el `tool_use` llegan por separado, con el
        # mismo `message.id` y la misma `usage`. Es un turno, no dos. Emitirlos
        # como dos generations duplicaba el coste (10 de 62 en una traza real).
        mid = str(msg.get("id") or "") or f"sin-id-{self.gens}"
        previo = self.msgs.get(mid)
        if previo is not None:
            previo[1] += _blocks(content)
            previo[0].update(output=previo[1])
        else:
            # Lo que el modelo vio desde su turno anterior; en el primero, el
            # prompt de arranque. Sin esto la entrada del primer turno saldria
            # vacia y no se podria saber con que contexto decidio.
            entrada = self.pending or (_clip(self.prompt) if not self.gens else None)
            bloques = _blocks(content)
            gen = self.root.start_observation(
                name="turno-orquestador", as_type="generation",
                model=msg.get("model"),
                input=entrada or None,
                output=bloques,
                usage_details=_usage(msg.get("usage"), salida=False),
                metadata={"stop_reason": msg.get("stop_reason"),
                          "request_id": obj.get("request_id")},
            )
            gen.end()
            self.msgs[mid] = [gen, bloques]
            self.gens += 1
            self.pending = []

        # Las herramientas cuelgan de la raiz, hermanas de la generation que las
        # pidio: asi se ve a que paso pertenece cada accion. Un comando que
        # encadena varias ordenes del nucleo emite una observacion por orden; la
        # salida no se puede repartir entre ellas, asi que la reciben todas.
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") in SKIP_TOOLS:
                continue
            nombres = tool_names(block)
            self.tools[str(block.get("id"))] = [
                self.root.start_observation(
                    name=nombre, as_type="tool",
                    input=block.get("input"),
                    metadata={"herramienta": block.get("name"),
                              "ordenes_encadenadas": len(nombres) if len(nombres) > 1 else None},
                )
                for nombre in nombres
            ]

    def _user(self, obj: dict) -> None:
        msg = obj.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            self.pending.append({"role": "user", "content": [block]})
            failed = bool(block.get("is_error"))
            for obs in self.tools.pop(str(block.get("tool_use_id")), []):
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

    def _rate_limit(self, obj: dict) -> None:
        """La utilizacion de las ventanas de cuota. Es la senal de §4.5 y el
        stream la regala: entre la primera y la ultima esta lo que cuesta un
        capitulo en cuota, que es la pregunta que decide si la obra cabe."""
        ventanas = ((obj.get("rate_limit_info") or {}).get("unifiedWindows") or {})
        uso = {k: v.get("utilization") for k, v in ventanas.items()
               if isinstance(v, dict) and v.get("utilization") is not None}
        if not uso:
            return
        self.cuota = [self.cuota[0] if self.cuota else uso, uso]

    def _result(self, obj: dict) -> None:
        # El uso de verdad solo existe aqui: los turnos traen el `output_tokens`
        # del `message_start` y no el definitivo (ver `_usage`). Va como
        # `usage_details` de la raiz, no solo a metadatos, para que la suma de la
        # traza coincida con lo que se pago.
        usage = obj.get("usage") or {}
        coste = obj.get("total_cost_usd")
        self.root.update(
            output=_clip(obj.get("result")),
            level="ERROR" if obj.get("is_error") else None,
            usage_details=_usage(usage),
            cost_details={"total": coste} if isinstance(coste, (int, float)) else None,
            metadata={
                "coste_usd": coste,
                "turnos": obj.get("num_turns"),
                "duracion_ms": obj.get("duration_ms"),
                "subagentes": (obj.get("subagent_stats") or {}).get("spawned"),
                "motivo_fin": obj.get("terminal_reason"),
                "cuota_inicial": self.cuota[0] if self.cuota else None,
                "cuota_final": self.cuota[1] if self.cuota else None,
            },
        )
        self._scores()
        self.close()

    # ------------------------------------------------------------------
    def _scores(self) -> None:
        """La nota del Evaluador y el veredicto del Continuista, del informe mas
        reciente de `.intentos/`. Son la senal de calidad del harness: sin ellas
        la traza dice lo que costo el capitulo, pero no si salio bien."""
        if self.cfg is None or self.replay:
            return   # reproduciendo, el informe de disco es el de ahora, no el de entonces
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
            abiertas = [o for lista in self.tools.values() for o in lista]
            for obs in abiertas + list(self.agents.values()):
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


def start(repo: Path, slug: str, prompt: str, replay: bool = False) -> Tracer:
    """Un trazador para esta ejecucion. Siempre devuelve un objeto usable.

    `replay=True` manda la traza a otro entorno de Langfuse. Una reproduccion
    emite las marcas de tiempo de ahora y no las del run, asi que mezclada con
    las reales estropea cualquier media de latencia o de coste del proyecto: un
    log acumulado de cuatro sesiones se reproducia como cuatro trazas con todas
    sus observaciones en el mismo milisegundo.
    """
    if replay:
        os.environ["LANGFUSE_TRACING_ENVIRONMENT"] = "replay"
    try:
        cfg = runs.load_cfg(repo, slug)
    except Exception:
        cfg = None
    return Tracer(client(repo), slug, cfg, prompt, replay=replay)


# --------------------------------------------------------------------------
# autocomprobacion y reproduccion: python -m panel.tracing [log.jsonl]
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    repo = Path(__file__).resolve().parent.parent

    assert tool_names({"name": "Bash", "input": {"command": "python -m harness --root runs/x next"}}) == ["harness-next"]
    assert tool_names({"name": "PowerShell", "input": {"command": "python -m harness save-attempt"}}) == ["harness-save-attempt"]
    assert tool_names({"name": "Bash", "input": {"command": "ls -la"}}) == ["shell"]
    assert tool_names({"name": "Write", "input": {}}) == ["escribir-archivo"]

    # Una cadena con `;` emite una observacion por orden del nucleo: sin esto
    # `harness decide` no aparecia en ninguna traza.
    cadena = ("python -m harness --root runs/x record cont --file a.json; "
              "python -m harness --root runs/x decide")
    assert tool_names({"name": "Bash", "input": {"command": cadena}}) == [
        "harness-record-cont", "harness-decide"]

    assert _usage({"input_tokens": 2, "output_tokens": 1, "cache_read_input_tokens": 7}) == {
        "input": 2, "output": 1, "cache_read_input_tokens": 7}
    # El uso por turno no declara salida: el stream solo da el placeholder.
    assert _usage({"input_tokens": 2, "output_tokens": 1}, salida=False) == {"input": 2}
    assert _usage(None) is None and _usage({}) is None

    assert _clip("a" * 10) == "a" * 10
    assert len(_clip("a" * (MAX_TEXT + 50))) < MAX_TEXT + 60

    # Un Tracer mudo acepta todo el stream sin quejarse ni emitir nada.
    mute = Tracer(None, "novela", None, "/novela")
    for line in ('{"type":"assistant"}', "no es json", '{"type":"result"}'):
        mute.feed(line)
    mute.close()

    # Un mensaje que llega partido en dos eventos es un turno, no dos. Es el
    # fallo que inflaba el coste un 19 %, asi que se comprueba con un doble.
    class _Obs:
        def __init__(self, sink, name):
            self.sink, self.name = sink, name
            sink.append(name)
        def start_observation(self, name, as_type=None, **kw):
            return _Obs(self.sink, f"{as_type}:{name}")
        def update(self, **kw): pass
        def end(self): pass
        def create_event(self, name, **kw): self.sink.append(f"event:{name}")
        def score_trace(self, **kw): pass

    class _LF:
        def __init__(self, sink): self.sink = sink
        def start_observation(self, name, as_type=None, **kw):
            return _Obs(self.sink, f"{as_type}:{name}")
        def flush(self): pass

    emitido: list[str] = []
    t = Tracer(_LF(emitido), "novela", None, "/novela")
    turno = ('{"type":"assistant","message":{"id":"msg_1","model":"m",'
             '"usage":{"input_tokens":2,"output_tokens":1},"content":[%s]}}')
    t.feed(turno % '{"type":"text","text":"voy"}')
    t.feed(turno % '{"type":"tool_use","id":"tu_1","name":"Bash",'
                   '"input":{"command":"python -m harness next; python -m harness decide"}}')
    assert emitido.count("generation:turno-orquestador") == 1, emitido
    assert emitido.count("tool:harness-next") == 1 and emitido.count("tool:harness-decide") == 1, emitido
    t.feed('{"type":"rate_limit_event","rate_limit_info":'
           '{"unifiedWindows":{"five_hour":{"utilization":0.19}}}}')
    t.feed('{"type":"rate_limit_event","rate_limit_info":'
           '{"unifiedWindows":{"five_hour":{"utilization":0.24}}}}')
    assert t.cuota == [{"five_hour": 0.19}, {"five_hour": 0.24}], t.cuota

    if len(sys.argv) > 1:
        # Reproduce un log real contra Langfuse. Las marcas de tiempo son las de
        # ahora, no las del run: sirve para revisar la forma del arbol, no para
        # medir latencias. Por eso va al entorno `replay` y no al de las trazas
        # buenas, donde falsearia las medias de coste y de latencia.
        log = Path(sys.argv[1])
        slug = log.parent.parent.parent.name
        tracer = start(repo, slug if runs.exists(repo, slug) else runs.ROOT_SLUG,
                       f"reproducción de {log.name}", replay=True)
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
