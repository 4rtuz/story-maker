"""El hook PreToolUse de .claude/hooks/ (spec 0003 §5.2), ejecutado como subproceso, igual que lo
ejecuta Claude Code (spec §13). No se importa salvo para comparar su tabla de salidas."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

RAIZ_REPO = Path(__file__).resolve().parents[2]
HOOK = RAIZ_REPO / ".claude" / "hooks" / "denegar-escritura-estado.py"
MOTIVO = "denegar-escritura-estado:"


def _hook(
    entrada: object, cwd: Path, entorno: dict[str, str] | None = None
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
    entradas: list[object] = [
        "esto no es JSON",
        {"tool_name": "Write", "tool_input": {}},
        {"tool_name": "Frobnicate", "tool_input": {"file_path": "README.md"}},
        [],
    ]
    for entrada in entradas:
        resultado = _hook(entrada, tmp_path)
        assert resultado.returncode == 2, entrada
        assert resultado.stderr.startswith(MOTIVO), resultado.stderr

    permitido = _hook(_escritura("README.md", tmp_path), tmp_path)
    assert (permitido.returncode, permitido.stdout, permitido.stderr) == (0, "", "")
    # D-4: NotebookEdit trae notebook_path, no file_path.
    cuaderno = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "x.ipynb"}}
    assert _hook(cuaderno | {"agent_type": "Explore"}, tmp_path).returncode == 0


# --- Regla 1: nada bajo estado/ salvo estado/deltas/NN.json ----------------------------------

slugs = st.from_regex(r"[a-z0-9][a-z0-9-]{0,10}", fullmatch=True)
delta_valido = st.from_regex(r"\d{2,3}", fullmatch=True).map(lambda n: f"deltas/{n}.json")
bajo_estado = st.one_of(
    st.sampled_from(["estado.db", "estado.db-wal", "state.lock", "deltas/07.json.tmp", "deltas"]),
    st.from_regex(r"\d|\d{4}", fullmatch=True).map(lambda n: f"deltas/{n}.json"),
    st.from_regex(r"[a-z0-9_-][a-z0-9._-]{0,11}", fullmatch=True),  # cualquier nombre
)


@st.composite
def variante(draw: st.DrawFn, segmentos: list[str], cwd: Path) -> str:
    """La misma ruta escrita como la escribiría Win32 o un modelo descuidado."""
    segmentos = [s + draw(st.sampled_from(["", "", ".", " ", ". .", " ."])) for s in segmentos]
    if draw(st.booleans()):
        i = draw(st.integers(0, len(segmentos) - 1))
        segmentos[i:i] = ["x", ".."]
    ruta = segmentos[0]
    for s in segmentos[1:]:
        ruta += draw(st.sampled_from(["/", "\\"])) + s
    if draw(st.booleans()):
        ruta = str(cwd) + "\\" + ruta
        if draw(st.booleans()):
            ruta = "\\\\?\\" + ruta
    return "".join(c.upper() if draw(st.booleans()) else c for c in ruta)


@settings(max_examples=60, deadline=None)  # cada ejemplo es un proceso
@given(slug=slugs, sufijo=bajo_estado | delta_valido, datos=st.data())
def test_estado_denegado_salvo_delta(slug: str, sufijo: str, datos: st.DataObject) -> None:
    """CA-03 (RF-05). Con agent_type Explore para aislar la regla 1: sin él aplicaría también la
    regla 3, que deniega el delta a la sesión principal (CA-14)."""
    cwd = Path(tempfile.gettempdir())
    ruta = datos.draw(variante(["novelas", slug, "estado", *sufijo.split("/")], cwd))
    esperado = 0 if re.fullmatch(r"deltas/\d{2,3}\.json", sufijo) else 2
    resultado = _hook(_escritura(ruta, cwd), cwd)
    assert resultado.returncode == esperado, (ruta, resultado.stderr)


def test_estado_rutas_no_normalizables(tmp_path: Path) -> None:
    """CA-03, la frontera: un flujo alternativo o un segmento de puntos no se sabe normalizar, y
    se deniega dentro o fuera de estado/. `.. ` es `..` para Win32: sin denegarlo, saldría de
    capitulos/ a estado/ sin que la regla 1 lo viera."""
    for ruta in (
        "novelas/x/estado/estado.db:secreto",
        "novelas/x/capitulos/01.md:x",
        "novelas/x/.../estado.db",
        "novelas/x/capitulos/.. /estado/estado.db",
        "C:novelas/x/estado/estado.db",
    ):
        assert _hook(_escritura(ruta, tmp_path), tmp_path).returncode == 2, ruta
    assert _hook(_escritura("novelas/x/capitulos/01.md", tmp_path), tmp_path).returncode == 0
