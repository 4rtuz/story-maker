"""Lo que tiene que estar bien antes de lanzar el bucle o el canario (spec 0003 §5.3): función pura
sobre textos y resultados; no abre nada.

Un fallo aquí no es un gate: es una configuración con la que el hook fallaría abierto, o con la
que la sesión cargaría permisos que CI no ve.
"""

import json
import re

HOOK = ".claude/hooks/denegar-escritura-estado.py"


def _json(texto: str) -> object:
    try:
        return json.loads(texto)
    except ValueError:
        return None


def entorno(
    settings: str | None,
    local: str | None,
    hook_existe: bool,
    python: str | None,
    sucio: bool,
    limpio: bool,
) -> list[str]:
    """Un hallazgo por condición. `settings` y `local` son el texto del fichero o None si no
    existe; `python` es lo que resuelve `which`."""
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
    # Con cualquier código distinto de 2, Claude Code deja pasar la acción.
    if python is None:
        hallazgos.append("python no resuelve: el hook fallaría abierto")
    elif "windowsapps" in (s.casefold() for s in re.split(r"[\\/]", python)):
        hallazgos.append("python es el alias de la Microsoft Store: el hook fallaría abierto")
    if limpio and sucio:
        hallazgos.append("cambios sin commitear en lo que atribuye el manifiesto")
    return hallazgos
