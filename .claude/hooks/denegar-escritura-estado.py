"""PreToolUse del harness (spec 0003 §5.2).

Deniega con exit 2 y el motivo en stderr; permite con exit 0 y sin salida. Falla cerrado: lo que
no entiende también sale con 2, porque cualquier otro código Claude Code lo trata como no
bloqueante y la acción seguiría adelante. Solo stdlib: corre en cada llamada de herramienta,
fuera del venv de backend/, y no puede importarlo.
"""

import json
import os
import sys
from collections.abc import Mapping
from typing import Any

MOTIVO = "denegar-escritura-estado:"  # prefijo de todo motivo; el canario lo busca en el transcript

# Solo estos campos, nunca tool_input entero (regla 7): una regla sobre todo el tool_input
# bloqueó en el experimento un Agent cuyo prompt mencionaba la ruta prohibida.
_CAMPO = {
    "Write": "file_path",
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",  # D-4
    "Bash": "command",
    "PowerShell": "command",
}


def decidir(entrada: dict[str, Any], entorno: Mapping[str, str]) -> str | None:
    """None si se permite; el motivo si se deniega. Lanza ante lo que no entiende."""
    tool = entrada["tool_name"]
    if tool in ("Agent", "Task"):
        return None
    valor = entrada["tool_input"][_CAMPO[tool]]
    if not isinstance(valor, str) or not valor:
        raise ValueError(f"{_CAMPO[tool]} vacío o no es texto")
    return None


def main() -> int:
    try:
        # Bytes y no sys.stdin: en Windows la página de códigos rompería una ruta con tildes.
        motivo = decidir(json.loads(sys.stdin.buffer.read()), os.environ)
    except Exception as exc:  # falla cerrado (RF-06)
        motivo = f"entrada no interpretable: {exc!r}"
    if motivo is None:
        return 0
    sys.stderr.buffer.write(f"{MOTIVO} {motivo}\n".encode())
    return 2


if __name__ == "__main__":
    sys.exit(main())
