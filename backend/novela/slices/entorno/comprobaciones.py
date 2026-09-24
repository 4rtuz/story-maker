"""Lo que tiene que estar bien antes de lanzar el bucle o el canario (spec 0003 §5.3): función pura
sobre textos y resultados; no abre nada.

Un fallo aquí no es un gate: es una configuración con la que el hook fallaría abierto, o con la
que la sesión cargaría permisos que CI no ve.
"""

import json
import re
from collections.abc import Mapping

HOOK = ".claude/hooks/denegar-escritura-estado.py"
HOOK_VALIDACION = ".claude/hooks/validar-capitulo.py"  # PostToolUse, spec 0008


def _json(texto: str) -> object:
    try:
        return json.loads(texto)
    except ValueError:
        return None


def entorno(
    settings: str | None,
    local: str | None,
    hook_existe: bool,
    hook_validacion_existe: bool,
    python: str | None,
    sucio: bool,
    limpio: bool,
    env_ignorado: bool | None,
    scores: Mapping[str, str],
) -> list[str]:
    """Un hallazgo por condición. `settings` y `local` son el texto del fichero o None si no
    existe; `python` es lo que resuelve `which`; `env_ignorado`, None si no hay `.env`; `scores`,
    lo que verá el emisor de `checkpoint`. Los hallazgos nombran variables, nunca valores."""
    hallazgos = []
    if settings is None:
        hallazgos.append("falta .claude/settings.json")
    elif not isinstance(_json(settings), dict):
        hallazgos.append("settings.json no es JSON válido")
    # No está versionado, CI no lo ve y el bucle lo carga con --setting-sources project,local.
    if local is not None:
        datos = _json(local)
        if not isinstance(datos, dict):
            hallazgos.append("settings.local.json no es JSON válido")
        else:
            hallazgos += [
                f"settings.local.json: clave no permitida: {k}"
                for k in datos
                if k != "enabledPlugins"
            ]
    if not hook_existe:
        hallazgos.append(f"falta {HOOK}")
    if not hook_validacion_existe:
        hallazgos.append(f"falta {HOOK_VALIDACION}")
    # Con cualquier código distinto de 2, Claude Code deja pasar la acción.
    if python is None:
        hallazgos.append("python no resuelve: el hook fallaría abierto")
    elif "windowsapps" in (s.casefold() for s in re.split(r"[\\/]", python)):
        hallazgos.append("python es el alias de la Microsoft Store: el hook fallaría abierto")
    if limpio and sucio:
        hallazgos.append("cambios sin commitear en lo que atribuye el manifiesto")
    if env_ignorado is False:
        hallazgos.append(".env no está ignorado por git: las claves se versionarían")
    # Sin esto, el sink se queda en no-op sin avisar y el capítulo cierra sin scores (F-54).
    if scores.get("TRACE_TO_LANGFUSE") == "true":
        hallazgos += [
            f"TRACE_TO_LANGFUSE=true sin {k}"
            for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
            if not scores.get(k)
        ]
        if not (scores.get("LANGFUSE_BASE_URL") or scores.get("LANGFUSE_HOST")):
            hallazgos.append("TRACE_TO_LANGFUSE=true sin LANGFUSE_BASE_URL ni LANGFUSE_HOST")
    return hallazgos
