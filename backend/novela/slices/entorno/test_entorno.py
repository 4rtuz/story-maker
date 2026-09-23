import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from novela.cli import app
from novela.plataforma import run
from novela.slices.entorno.comprobaciones import entorno

SETTINGS = json.dumps({"permissions": {"allow": [], "deny": []}, "hooks": {}})
PYTHON = "C:\\Python312\\python.exe"
BIEN = {"settings": SETTINGS, "local": None, "hook_existe": True, "python": PYTHON}


@pytest.mark.parametrize(
    ("cambio", "hallazgo"),
    [
        ({"settings": "{no es json"}, "settings.json no es JSON válido"),
        ({"settings": None}, "falta .claude/settings.json"),
        (
            {"local": json.dumps({"enabledPlugins": {}, "permissions": {"allow": ["Bash"]}})},
            "settings.local.json: clave no permitida: permissions",
        ),
        ({"local": "{"}, "settings.local.json no es JSON válido"),
        ({"hook_existe": False}, "falta .claude/hooks/denegar-escritura-estado.py"),
        ({"python": None}, "python no resuelve: el hook fallaría abierto"),
        (
            {"python": "C:\\Users\\x\\AppData\\Local\\Microsoft\\windowsapps\\python.exe"},
            "python es el alias de la Microsoft Store: el hook fallaría abierto",
        ),
    ],
)
def test_un_hallazgo_por_condicion(cambio: dict[str, object], hallazgo: str) -> None:
    """CA-17 (RF-28): cada condición de la spec 0003 §5.3, sola, da exactamente su hallazgo."""
    datos = BIEN | cambio
    assert entorno(**datos, sucio=False, limpio=False) == [hallazgo]  # type: ignore[arg-type]


def test_limpio_con_el_arbol_sucio() -> None:
    """--limpio (F-63): el canario no prueba una configuración que no es la commiteada."""
    assert entorno(**BIEN, sucio=True, limpio=True) == [  # type: ignore[arg-type]
        "cambios sin commitear en lo que atribuye el manifiesto"
    ]
    assert entorno(**BIEN, sucio=True, limpio=False) == []  # type: ignore[arg-type]


def test_sin_hallazgos() -> None:
    local = json.dumps({"enabledPlugins": {"langfuse-observability@langfuse-observability": True}})
    assert entorno(**BIEN | {"local": local}, sucio=False, limpio=False) == []  # type: ignore[arg-type]


def test_por_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """La cáscara, sobre un directorio temporal y sin tocar el repo: con un hallazgo sale con 1 y
    lo imprime en una línea; sin ninguno, sale con 0 y no imprime nada."""
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text(SETTINGS, encoding="utf-8")
    monkeypatch.setattr(run, "RAIZ_REPO", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _: PYTHON)

    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert resultado.exit_code == 1
    assert resultado.output.splitlines() == ["falta .claude/hooks/denegar-escritura-estado.py"]

    (tmp_path / ".claude" / "hooks" / "denegar-escritura-estado.py").write_text("", "utf-8")
    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert (resultado.exit_code, resultado.output) == (0, "")
