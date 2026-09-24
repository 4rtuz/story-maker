"""Contratos transversales: esquemas, claves, clientes de modelo, OpenAPI."""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import jsonschema
import yaml
from typer.testing import CliRunner

from api.main import app as api
from novela.cli import app
from novela.dominio import esquemas
from novela.plataforma.workspace import WorkspaceRepository

RAIZ_REPO = Path(__file__).resolve().parents[2]
SCHEMAS = RAIZ_REPO / "backend" / "schemas"
# REGENERAR=1 uv run pytest tests/test_contratos.py reescribe los contratos commiteados; el diff del
# commit es la revisión del cambio.
REGENERAR = os.environ.get("REGENERAR") == "1"
GIT = shutil.which("git") or "git"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [GIT, "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def test_sin_claves_versionadas(tmp_path: Path) -> None:
    """CA-32: un fichero versionado con una clave hace fallar el pre-commit."""
    repo = tmp_path / "repo"
    (repo / ".githooks").mkdir(parents=True)
    shutil.copy(RAIZ_REPO / ".githooks" / "pre-commit", repo / ".githooks" / "pre-commit")
    _git(repo, "init", "-q")
    _git(repo, "config", "core.hooksPath", ".githooks")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")

    # Control: sin clave, el commit pasa. Si no pasara, el fallo de abajo no probaría nada.
    (repo / "limpio.md").write_text("Las claves van en `LANGFUSE_SECRET_KEY`, fuera de git.\n")
    _git(repo, "add", "-A")
    assert _git(repo, "commit", "-qm", "limpio").returncode == 0

    # Construida por partes para que este fichero no dispare el hook que lo prueba.
    clave = "LANGFUSE_SECRET_KEY" + "=" + "sk-lf-" + "dummy0000000000"
    (repo / "settings.env").write_text(clave + "\n")
    _git(repo, "add", "-A")
    resultado = _git(repo, "commit", "-qm", "con clave")
    assert resultado.returncode != 0
    assert "clave" in resultado.stderr


def test_state_schema_al_dia() -> None:
    """CA-06 y RF-26: el JSON Schema commiteado es el que genera Pydantic ahora mismo. Si cambias
    un modelo y no regeneras, esto se pone rojo."""
    generados = esquemas.generar()
    if REGENERAR:
        SCHEMAS.mkdir(exist_ok=True)
        for nombre, esquema in generados.items():
            texto = json.dumps(esquema, indent=2, ensure_ascii=False) + "\n"
            (SCHEMAS / nombre).write_bytes(texto.encode("utf-8"))
    commiteados = {p.name for p in SCHEMAS.glob("*.json")}
    assert commiteados == set(generados), "schemas/ tiene ficheros de más o de menos"
    for nombre, esquema in generados.items():
        assert json.loads((SCHEMAS / nombre).read_text(encoding="utf-8")) == esquema, nombre
        assert "schema_version" in esquema["properties"], nombre


def test_estado_json_valida_contra_el_esquema(
    novelas: Callable[[str], WorkspaceRepository],
) -> None:
    """CA-06, la otra mitad: lo que emite `novela estado --json` valida contra el commiteado."""
    novelas("demo-24")
    resultado = CliRunner().invoke(app, ["estado", "demo-24", "--json"])
    assert resultado.exit_code == 0, resultado.output
    esquema = json.loads((SCHEMAS / "state.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads(resultado.stdout), esquema)


# Clientes de proveedores de modelos y gateways: AGENTS.md, «Nunca».
PROHIBIDOS = (
    "anthropic",
    "claude_agent_sdk",
    "openai",
    "google.generativeai",
    "google.genai",
    "mistralai",
    "cohere",
    "ollama",
    "litellm",
    "langchain",
    "openrouter",
)
RAICES = ("novela", "api")


def _prohibido(modulo: str) -> bool:
    return any(modulo == p or modulo.startswith(p + ".") for p in PROHIBIDOS)


def test_sin_clientes_de_modelo() -> None:
    """CA-28: ni un import directo (también los perezosos, dentro de funciones) ni uno transitivo
    de ningún cliente de modelo en el CLI ni en la API."""
    backend = RAIZ_REPO / "backend"
    directos = []
    for raiz in RAICES:
        for fichero in (backend / raiz).rglob("*.py"):
            for nodo in ast.walk(ast.parse(fichero.read_text(encoding="utf-8"))):
                if isinstance(nodo, ast.Import):
                    nombres = [a.name for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                    nombres = [nodo.module]
                else:
                    continue
                directos += [f"{fichero.name}: {n}" for n in nombres if _prohibido(n)]
    assert directos == []

    assert [m for m in _cargados("novela.cli", "api.main") if _prohibido(m)] == []


def _cargados(*modulos: str) -> list[str]:
    """sys.modules tras importar `modulos` en un proceso limpio: en el de pytest hay módulos que
    no son del backend."""
    codigo = f"import sys, {', '.join(modulos)}; print(*sys.modules)"
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        check=True,
        cwd=RAIZ_REPO / "backend",
    ).stdout.split()


def test_openapi_al_dia() -> None:
    """CA-29 (RNF-05): el OpenAPI commiteado es el que genera la app. De él salen los tipos del
    frontend, generados y no escritos a mano, así que no pueden derivar por su cuenta."""
    generado = api.openapi()
    ruta = RAIZ_REPO / "backend" / "api" / "openapi.json"
    if REGENERAR:
        texto = json.dumps(generado, indent=2, ensure_ascii=False) + "\n"
        ruta.write_bytes(texto.encode("utf-8"))
    assert json.loads(ruta.read_text(encoding="utf-8")) == generado


def test_api_no_importa_slices() -> None:
    """La API puede importar dominio/ y la lectura de plataforma/; slices/ es escritura. El
    montaje en solo lectura de test_api cubre el efecto; esto cubre la causa, y nombra el import
    el día que un router tire de delta/apply.py «solo para reutilizar la serialización»."""
    assert [m for m in _cargados("api.main") if m.startswith("novela.slices")] == []


# --- Harness ↔ Claude Code (validators.md §3.8, tercer contrato) -----------------------------

AGENTES_DIR = RAIZ_REPO / ".claude" / "agents"

# spec 0003 §5.1: tools, model y salidas relativas a novelas/<slug>/. El hook lleva su propia
# copia de las salidas (no puede importar backend/); test_hook comprueba que casan.
CONTRATO = {
    "arquitecto": (
        ["Read", "Write"],
        "opus",
        [
            "canon/premisa.md",
            "canon/mundo.md",
            "canon/estilo.md",
            # El deny de Read del misterio también deniega escribirlo: el gate promueve el
            # borrador (spec 0003 v0.5, F-28).
            "canon/misterio.borrador.md",
            "canon/personajes/*.md",
        ],
    ),
    "trazador": (["Read", "Write"], "opus", ["plan/escaleta.md", "plan/capitulos/NN.md"]),
    "escritor": (["Read", "Write"], "opus", ["capitulos/NN.md"]),
    "continuista": (["Read", "Write"], "sonnet", ["qa/NN-continuidad.json"]),
    "editor-estilo": (
        ["Read", "Edit", "Write"],
        "sonnet",
        ["capitulos/NN.md", "qa/NN-estilo.json"],
    ),
    "lector-suspense": (["Read", "Write"], "sonnet", ["qa/NN-suspense.json"]),
    "cronista": (["Read", "Write"], "haiku", ["estado/deltas/NN.json"]),
}
ESQUEMAS = {
    "arquitecto": ["backend/schemas/canon.schema.json"],
    "trazador": [
        "backend/schemas/escaleta.schema.json",
        "backend/schemas/plan-capitulo.schema.json",
    ],
    "escritor": ["backend/schemas/capitulo.schema.json"],
    "continuista": ["backend/schemas/qa-informe.schema.json"],
    "editor-estilo": ["backend/schemas/qa-informe.schema.json"],
    "lector-suspense": ["backend/schemas/qa-informe.schema.json"],
    "cronista": ["backend/schemas/delta.schema.json"],
}
PROHIBIDAS = {"Glob", "Grep", "Bash", "Task", "Agent", "Skill", "WebFetch", "WebSearch"}


def _agente(rol: str) -> tuple[dict[str, str], str]:
    """Frontmatter y cuerpo. No reutiliza dominio/frontmatter.py: ese valida la novela, no el
    harness, y acoplarlos haría que un cambio en uno rompa el otro."""
    _, cabecera, cuerpo = (AGENTES_DIR / f"{rol}.md").read_text(encoding="utf-8").split("---", 2)
    meta: dict[str, str] = yaml.safe_load(cabecera)
    return meta, cuerpo


def test_agentes_de_claude() -> None:
    """CA-01 (RF-01 a RF-03): los siete roles, con name, tools y model de la spec 0003 §5.1."""
    assert {p.stem for p in AGENTES_DIR.glob("*.md")} == set(CONTRATO)
    for rol, (tools, model, _) in CONTRATO.items():
        meta, _ = _agente(rol)
        assert meta["name"] == rol
        declaradas = [t.strip() for t in meta["tools"].split(",")]
        assert set(declaradas) & PROHIBIDAS == set(), f"{rol}: {set(declaradas) & PROHIBIDAS}"
        assert declaradas == tools, rol
        assert meta["model"] == model, rol


def test_agentes_nombran_sus_salidas() -> None:
    """CA-02 (RF-04, RF-24): cada cuerpo nombra sus salidas y su esquema, y todo esquema que se
    cita existe: uno renombrado rompe CI y no el primer capítulo (F-03)."""
    for rol, (_, _, salidas) in CONTRATO.items():
        _, cuerpo = _agente(rol)
        for ruta in salidas + ESQUEMAS[rol]:
            assert ruta in cuerpo, f"{rol} no nombra {ruta}"
        for citado in re.findall(r"backend/schemas/[\w.-]+\.json", cuerpo):
            assert (RAIZ_REPO / citado).is_file(), f"{rol} cita {citado}, que no existe"


SETTINGS = RAIZ_REPO / ".claude" / "settings.json"
DENY = {
    "Read(./novelas/*/canon/misterio.md)",
    "Edit(./novelas/*/estado/estado.db*)",
    "Edit(./novelas/*/estado/state.lock)",
    "Bash(sqlite3:*)",
}
MATCHER = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task"}


def test_settings_de_claude() -> None:
    """CA-06 (RF-08, RF-09, RF-10, RF-20). En -p, un settings.json inválido se ignora sin avisar, y
    con él desaparecerían el deny del misterio y el hook."""
    texto = SETTINGS.read_text(encoding="utf-8")
    settings = json.loads(texto)
    assert set(settings) <= {"permissions", "hooks"}, "ni claves, ni enabledPlugins, ni env"
    assert "bypassPermissions" not in texto
    assert settings["permissions"]["allow"] == ["Agent", "Bash(novela:*)", "Edit(./novelas/**)"]
    assert DENY <= set(settings["permissions"]["deny"])
    [registro] = settings["hooks"]["PreToolUse"]
    assert set(registro["matcher"].split("|")) == MATCHER
    [orden] = [h["command"] for h in registro["hooks"]]
    script = re.search(r"\$CLAUDE_PROJECT_DIR/([^\"\s]+)", orden)
    assert script and (RAIZ_REPO / script[1]).is_file(), orden  # F-10: la ruta existe
    assert orden.startswith("python "), "python3 es el alias de la Store en Windows (E-11)"
