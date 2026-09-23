"""PreToolUse del harness (spec 0003 §5.2).

Deniega con exit 2 y el motivo en stderr; permite con exit 0 y sin salida. Falla cerrado: lo que
no entiende también sale con 2, porque cualquier otro código Claude Code lo trata como no
bloqueante y la acción seguiría adelante. Solo stdlib: corre en cada llamada de herramienta,
fuera del venv de backend/, y no puede importarlo.
"""

import json
import os
import re
import sys
from collections.abc import Mapping
from typing import Any

MOTIVO = "denegar-escritura-estado:"  # prefijo de todo motivo; el canario lo busca en el transcript
_DELTA = r"estado/deltas/\d{2,3}\.json"
_PREFIJO_WIN32 = re.compile(r"^(\\\\|//)[?.][\\/]")  # \\?\  \\.\


class RutaNoNormalizable(ValueError):
    """Lo que Win32 resolvería de una forma que el hook no puede reproducir sin tocar el disco."""


def _normalizar(ruta: str, cwd: str) -> str:
    """Absoluta, con `/`, sin `..` y sin mayúsculas (D-3), deshaciendo lo que Win32 normaliza al
    escribir. ponytail: no resuelve enlaces, uniones ni nombres 8.3; eso exigiría tocar el disco
    en cada llamada (validators.md §5.14), y debajo quedan los triggers de estado.db."""
    ruta = _PREFIJO_WIN32.sub("", ruta)
    if re.match(r"[a-zA-Z]:(?![\\/])", ruta):
        raise RutaNoNormalizable(f"ruta relativa a una unidad: {ruta}")
    if ":" in re.sub(r"^[a-zA-Z]:", "", ruta):
        raise RutaNoNormalizable(f"flujo alternativo de NTFS: {ruta}")
    segmentos = re.split(r"[\\/]", ruta)
    limpios = [s if s in ("", ".", "..") else s.rstrip(". ") for s in segmentos]
    # Win32 quita puntos y espacios finales: `estado./` es `estado/`, pero `.. ` es `..` y `...`
    # no se sabe qué es. Un segmento que se queda sin nada no se interpreta.
    if "" in (limpio for s, limpio in zip(segmentos, limpios, strict=True) if s):
        raise RutaNoNormalizable(f"segmento de puntos o espacios: {ruta}")
    absoluta = os.path.normpath(os.path.join(cwd, "/".join(limpios)))
    return absoluta.replace("\\", "/").casefold()


def _relativas(ruta: str) -> list[str]:
    """La ruta relativa a cada `novelas/<slug>/` que contenga. Por segmento y no por prefijo, para
    que valga con NOVELAS_DIR fuera del repo. Todas, no la primera: un antecesor que se llame
    novelas/ no puede esconder el estado. ponytail: ese mismo antecesor hace que la sesión
    principal vea el repo entero como workspace; se mueve el repo si llega a pasar."""
    s = ruta.split("/")
    return ["/".join(s[i + 2 :]) for i in range(len(s) - 2) if s[i] == "novelas" and s[i + 1]]

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
    if _CAMPO[tool] == "command":
        return None
    try:
        relativas = _relativas(_normalizar(valor, entrada.get("cwd") or os.getcwd()))
    except RutaNoNormalizable as exc:
        return str(exc)
    # Regla 1, para todos.
    if any(r.split("/")[0] == "estado" and not re.fullmatch(_DELTA, r) for r in relativas):
        return f"escritura bajo estado/ denegada: {valor}"
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
