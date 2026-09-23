"""El hook PreToolUse de .claude/hooks/ (spec 0003 §5.2), ejecutado como subproceso, igual que lo
ejecuta Claude Code (spec §13). No se importa salvo para comparar su tabla de salidas."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

RAIZ_REPO = Path(__file__).resolve().parents[2]
HOOK = RAIZ_REPO / ".claude" / "hooks" / "denegar-escritura-estado.py"
MOTIVO = "denegar-escritura-estado:"


def _hook(
    entrada: dict[str, Any] | str, cwd: Path, entorno: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Sin NOVELA_SESSION_ID por defecto: si la suite corre desde una shell del bucle, la regla 5
    no puede contaminar los tests de las otras cuatro."""
    datos = entrada if isinstance(entrada, str) else json.dumps(entrada)
    env = {k: v for k, v in os.environ.items() if k != "NOVELA_SESSION_ID"} | (entorno or {})
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)],
        input=datos,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env=env,
        timeout=10,
        check=False,
    )


def _escritura(ruta: str, cwd: Path, agente: str | None = "Explore") -> dict[str, Any]:
    entrada: dict[str, Any] = {
        "tool_name": "Write",
        "tool_input": {"file_path": ruta, "content": "x"},
        "cwd": str(cwd),
    }
    if agente is not None:
        entrada["agent_type"] = agente
    return entrada


def test_falla_cerrado(tmp_path: Path) -> None:
    """CA-04 (RF-06): lo que no entiende lo deniega con 2, porque cualquier otro código deja pasar
    la acción. Una herramienta que el matcher no debería dejar pasar también."""
    for entrada in (
        "esto no es JSON",
        {"tool_name": "Write", "tool_input": {}},
        {"tool_name": "Frobnicate", "tool_input": {"file_path": "README.md"}},
        [],
    ):
        resultado = _hook(entrada, tmp_path)
        assert resultado.returncode == 2, entrada
        assert resultado.stderr.startswith(MOTIVO), resultado.stderr

    permitido = _hook(_escritura("README.md", tmp_path), tmp_path)
    assert (permitido.returncode, permitido.stdout, permitido.stderr) == (0, "", "")
    # D-4: NotebookEdit trae notebook_path, no file_path.
    cuaderno = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "x.ipynb"}}
    assert _hook(cuaderno | {"agent_type": "Explore"}, tmp_path).returncode == 0
