"""Contratos transversales: esquemas, claves, clientes de modelo, OpenAPI."""

import ast
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import jsonschema
from typer.testing import CliRunner

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
RAICES = ("novela",)


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

    # Proceso limpio: en el de pytest hay módulos que no son del backend.
    codigo = "import sys, " + ", ".join(RAICES) + "; import novela.cli; print(*sys.modules)"
    cargados = subprocess.run(  # noqa: S603
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True, cwd=backend
    ).stdout.split()
    assert [m for m in cargados if _prohibido(m)] == []
