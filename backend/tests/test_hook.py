"""El hook PreToolUse de .claude/hooks/ (spec 0003 §5.2), ejecutado como subproceso, igual que lo
ejecuta Claude Code (spec §13). No se importa salvo para comparar su tabla de salidas."""

import importlib.util
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.test_contratos import CONTRATO

RAIZ_REPO = Path(__file__).resolve().parents[2]
HOOK = RAIZ_REPO / ".claude" / "hooks" / "denegar-escritura-estado.py"
MOTIVO = "denegar-escritura-estado:"


def _hook(
    entrada: object, cwd: Path, entorno: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Sin NOVELA_SESSION_ID por defecto: si la suite corre desde una shell del bucle, la regla 5
    no puede contaminar los tests de las otras cuatro."""
    datos = entrada if isinstance(entrada, str) else json.dumps(entrada)
    env = {k: v for k, v in os.environ.items() if k != "NOVELA_SESSION_ID"}
    # El log de auditoría sin workspace va a CLAUDE_PROJECT_DIR: el de cada test, no el del repo.
    env |= {"CLAUDE_PROJECT_DIR": str(cwd)} | (entorno or {})
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


# --- Regla 2: cada rol, solo en sus salidas --------------------------------------------------

FUERA = [".claude/agents/escritor.md", "backend/x.py", "README.md"]


def _instancia(patron: str) -> st.SearchStrategy[str]:
    """Una ruta concreta de un patrón de CONTRATO: NN de 2 o 3 dígitos, `*` un nombre."""
    nn = st.from_regex(r"\d{2,3}", fullmatch=True)
    nombre = st.from_regex(r"per-[a-z]{1,8}", fullmatch=True)
    return st.tuples(nn, nombre).map(lambda t: patron.replace("NN", t[0]).replace("*", t[1]))


@settings(max_examples=60, deadline=None)
@given(rol=st.sampled_from(sorted(CONTRATO)), datos=st.data())
def test_salidas_por_rol(rol: str, datos: st.DataObject) -> None:
    """CA-05 (RF-07): un rol escribe en sus salidas y en nada más. capitulos/NN.md es de escritor
    y de editor-estilo: no es «de otra fila» para ninguno de los dos."""
    cwd = Path(tempfile.gettempdir())
    propias = CONTRATO[rol][2]
    ajenas = sorted({p for _, _, ps in CONTRATO.values() for p in ps} - set(propias))
    suya = datos.draw(st.sampled_from(propias).flatmap(_instancia))
    ajena = datos.draw(st.sampled_from(ajenas).flatmap(_instancia))
    for ruta, esperado in (
        (f"novelas/demo/{suya}", 0),
        (f"novelas/demo/{ajena}", 2),
        (datos.draw(st.sampled_from(FUERA)), 2),
    ):
        resultado = _hook(_escritura(ruta, cwd, agente=rol), cwd)
        assert resultado.returncode == esperado, (rol, ruta, resultado.stderr)


def test_arquitecto_escribe_el_borrador(tmp_path: Path) -> None:
    """CA-27 (RF-37, F-28): el arquitecto escribe el borrador del misterio, no el misterio, que
    solo escribe el CLI al promoverlo. Sin esto, el deny y el hook dirían cosas distintas."""
    for ruta, esperado in (
        ("novelas/demo/canon/misterio.borrador.md", 0),
        ("novelas/demo/canon/misterio.md", 2),
    ):
        resultado = _hook(_escritura(ruta, tmp_path, agente="arquitecto"), tmp_path)
        assert resultado.returncode == esperado, (ruta, resultado.stderr)


def test_sin_rol_fuera_del_workspace(tmp_path: Path) -> None:
    """CA-05, la otra mitad: los agentes de desarrollo y la sesión principal escriben en el repo."""
    for agente in ("Explore", None):
        for ruta in FUERA:
            assert _hook(_escritura(ruta, tmp_path, agente), tmp_path).returncode == 0


def test_salidas_casan_el_contrato() -> None:
    """D-2 (F-16): la tabla del hook es una copia vigilada de CONTRATO. El hook no puede importar
    backend/, así que el que compara es este test."""
    spec = importlib.util.spec_from_file_location("hook", HOOK)
    assert spec is not None and spec.loader is not None
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    assert set(hook.ROLES) == set(CONTRATO) == set(hook.SALIDAS)
    for rol, (_, _, salidas) in CONTRATO.items():
        rutas = [p.replace("NN", "07").replace("*", "x") for p in salidas]
        for ruta in rutas:  # cada salida del contrato la permite algún patrón del hook
            assert any(re.fullmatch(r, ruta) for r in hook.SALIDAS[rol]), (rol, ruta)
        for r in hook.SALIDAS[rol]:  # y ningún patrón del hook sobra
            assert any(re.fullmatch(r, ruta) for ruta in rutas), (rol, r)


def test_entrevistador_solo_borrador(tmp_path: Path) -> None:
    """CA-03 (RF-03) y VER-32: el entrevistador escribe su borrador y nada más, tampoco el brief
    que valida el CLI ni una ruta que solo empieza como la suya."""
    for ruta, esperado in (
        ("novelas/boda-prueba/brief/borrador.json", 0),
        ("novelas/boda-prueba/./brief/borrador.json", 0),
        ("novelas/boda-prueba/brief/brief.json", 2),
        ("novelas/boda-prueba/brief/informe.json", 2),
        ("novelas/boda-prueba/brief/entradas/ent-01.md", 2),
        ("novelas/boda-prueba/brief/borrador.json.bak", 2),
        ("novelas/boda-prueba/brief/borrador.json/../../config.yaml", 2),
        ("novelas/boda-prueba/config.yaml", 2),
        ("novelas/boda-prueba/canon/premisa.md", 2),
    ):
        resultado = _hook(_escritura(ruta, tmp_path, agente="entrevistador"), tmp_path)
        assert resultado.returncode == esperado, (ruta, resultado.stderr)


# --- Regla 3: la sesión principal no escribe en el workspace ---------------------------------


def test_sesion_principal(tmp_path: Path) -> None:
    """CA-14 (RF-25): sin agent_type, en novelas/ solo runs/*/intervencion.md. El orquestador no
    escribe el capítulo, el delta ni un qa/ «para ahorrar una llamada»."""
    for ruta, esperado in (
        ("novelas/x/capitulos/07.md", 2),
        ("novelas/x/qa/07-continuidad.json", 2),
        ("novelas/x/estado/deltas/07.json", 2),  # la regla 1 lo permitiría; la 3, no
        ("novelas/x/runs/r-20260101-0000/intervencion.md", 0),
        ("novelas/x/runs/r-20260101-0000/manifest.json", 2),
        ("README.md", 0),
        ("docs/specs/0003-contencion-y-bucle-en-claude.md", 0),
    ):
        resultado = _hook(_escritura(ruta, tmp_path, agente=None), tmp_path)
        assert resultado.returncode == esperado, (ruta, resultado.stderr)


def test_versiones_y_cambios_denegados(tmp_path: Path) -> None:
    """CA-21 (RF-23): versiones/ y cambios/ solo los escribe `novela cambio`; ningún rol ni la
    sesión principal."""
    for agente in (*sorted(CONTRATO), None):
        for ruta in (
            "novelas/demo/versiones/v1/capitulos/01.md",
            "novelas/demo/cambios/cam-001.json",
        ):
            resultado = _hook(_escritura(ruta, tmp_path, agente=agente), tmp_path)
            assert resultado.returncode == 2, (agente, ruta, resultado.stderr)


# --- Regla 4: órdenes Bash y PowerShell ------------------------------------------------------


def test_ordenes(tmp_path: Path) -> None:
    """CA-11 (RF-20): una regla de texto sobre la orden. La barra tras canon es la que deja pasar
    un slug con «misterio»."""
    for tool, orden, esperado in (
        ("Bash", "cat novelas/x/canon/misterio.md", 2),
        ("Bash", r"type novelas\x\CANON\Misterio.md", 2),
        ("Bash", "sqlite3 novelas/x/estado/estado.db", 2),
        ("PowerShell", r"Get-Content novelas\x\CANON\Misterio.md", 2),
        ("PowerShell", "Remove-Item novelas/x/estado/estado.db", 2),
        ("Bash", "novela estado el-misterio-del-faro --breve", 0),
        ("Bash", "novela briefing el-misterio-del-faro 3 escritor", 0),
    ):
        entrada = {"tool_name": tool, "tool_input": {"command": orden}, "cwd": str(tmp_path)}
        assert _hook(entrada, tmp_path).returncode == esperado, orden


# --- Regla 5: solo los roles, en una sesión del harness --------------------------------------

SESION = {"NOVELA_SESSION_ID": "0f8fad5b-d9cb-469f-a165-70867728950e"}


def test_subagentes(tmp_path: Path) -> None:
    """CA-15 (RF-26), la parte estática: fija el entorno del subproceso. Que Claude Code se lo pase
    al hook lo prueba el quinto intento del canario. Sin la variable, Agent no se examina: una
    sesión de desarrollo no depende de la forma de su entrada."""
    for entorno, tool, tipo, esperado in (
        (SESION, "Agent", "general-purpose", 2),
        (SESION, "Task", None, 2),
        (SESION, "Agent", "escritor", 0),
        (SESION, "Agent", "canario", 0),
        (SESION, "Agent", "entrevistador", 0),
        ({}, "Agent", "general-purpose", 0),
        ({}, "Agent", None, 0),
    ):
        datos = {"prompt": "x"} | ({"subagent_type": tipo} if tipo else {})
        entrada = {"tool_name": tool, "tool_input": datos, "cwd": str(tmp_path)}
        assert _hook(entrada, tmp_path, entorno).returncode == esperado, (entorno, tool, tipo)


def test_rendimiento(tmp_path: Path) -> None:
    """RNF-01 (F-18): corre en cada escritura, orden e invocación. Mediana por debajo de 300 ms."""
    tiempos = []
    for _ in range(10):
        inicio = time.perf_counter()
        assert _hook(_escritura("novelas/x/capitulos/01.md", tmp_path), tmp_path).returncode == 0
        tiempos.append(time.perf_counter() - inicio)
    assert statistics.median(tiempos) < 0.3


# --- Auditoría de las decisiones (docs/guardrails.md) ----------------------------------------


def _log(ruta: Path) -> list[dict[str, Any]]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]


def test_denegacion_al_log_del_workspace(tmp_path: Path) -> None:
    """Cada denegación, una línea JSON en novelas/<slug>/auditoria/policy.jsonl; lo permitido no
    deja rastro."""
    (tmp_path / "novelas" / "demo").mkdir(parents=True)
    ruta = "novelas/demo/estado/estado.db"
    assert _hook(_escritura(ruta, tmp_path), tmp_path).returncode == 2
    assert _hook(_escritura("novelas/demo/capitulos/01.md", tmp_path), tmp_path).returncode == 0
    [entrada] = _log(tmp_path / "novelas" / "demo" / "auditoria" / "policy.jsonl")
    assert entrada["decision"] == "denegar"
    assert (entrada["herramienta"], entrada["agente"]) == ("Write", "Explore")
    assert entrada["motivo"] == f"escritura bajo estado/ denegada: {ruta}"
    assert entrada["momento"]


def test_sin_workspace_al_log_del_proyecto(tmp_path: Path) -> None:
    """Una orden, o una ruta cuyo workspace no existe: al log de .claude/logs/ del proyecto, sin
    crear el workspace."""
    orden = {"tool_name": "Bash", "tool_input": {"command": "rm estado.db"}, "cwd": str(tmp_path)}
    assert _hook(orden, tmp_path).returncode == 2
    assert _hook(_escritura("novelas/nada/estado/x", tmp_path), tmp_path).returncode == 2
    assert _hook("esto no es JSON", tmp_path).returncode == 2
    lineas = _log(tmp_path / ".claude" / "logs" / "policy.jsonl")
    assert [e["herramienta"] for e in lineas] == ["Bash", "Write", None]
    assert not (tmp_path / "novelas" / "nada").exists()


def test_log_inescribible_no_cambia_la_decision(tmp_path: Path) -> None:
    """Sin poder escribir el log, el hook decide igual: ni falla ni deja pasar."""
    (tmp_path / "novelas" / "demo").mkdir(parents=True)
    (tmp_path / "novelas" / "demo" / "auditoria").write_text("un fichero, no un directorio")
    (tmp_path / ".claude").write_text("tampoco")
    resultado = _hook(_escritura("novelas/demo/estado/estado.db", tmp_path), tmp_path)
    assert resultado.returncode == 2
    assert resultado.stderr.startswith(f"{MOTIVO} escritura bajo estado/")
    orden = {"tool_name": "Bash", "tool_input": {"command": "cat estado.db"}, "cwd": str(tmp_path)}
    assert _hook(orden, tmp_path).returncode == 2
