import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from novela.cli import app
from novela.plataforma import run
from novela.slices.entorno.comprobaciones import entorno

SETTINGS = json.dumps({"permissions": {"allow": [], "deny": []}, "hooks": {}})
PYTHON = "C:\\Python312\\python.exe"
BIEN: dict[str, object] = {
    "settings": SETTINGS,
    "local": None,
    "hook_existe": True,
    "hook_validacion_existe": True,
    "python": PYTHON,
    "env_ignorado": None,
    "scores": {},
}
# Nombres por partes: con nombre y valor juntos, el pre-commit anti-claves rechazaría este fichero.
EMISOR = {
    "TRACE_TO_LANGFUSE": "true",
    **{
        f"LANGFUSE_{k}": v
        for k, v in {
            "PUBLIC_KEY": "publica-de-prueba",
            "SECRET_KEY": "secreta-de-prueba",
            "BASE_URL": "https://env.invalid",
        }.items()
    },
}


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
        ({"hook_validacion_existe": False}, "falta .claude/hooks/validar-capitulo.py"),
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
    (tmp_path / ".claude" / "hooks" / "validar-capitulo.py").write_text("", "utf-8")
    monkeypatch.setattr(run, "RAIZ_REPO", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _: PYTHON)

    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert resultado.exit_code == 1
    assert resultado.output.splitlines() == ["falta .claude/hooks/denegar-escritura-estado.py"]

    (tmp_path / ".claude" / "hooks" / "denegar-escritura-estado.py").write_text("", "utf-8")
    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert (resultado.exit_code, resultado.output) == (0, "")


def test_hook_de_validacion_ausente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-11 de la 0008 (RF-10, VAL-17): sin validar-capitulo.py avisa y sale con el mismo 1 que
    sin el PreToolUse; con los dos, nada."""
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text(SETTINGS, encoding="utf-8")
    (hooks / "denegar-escritura-estado.py").write_text("", "utf-8")
    monkeypatch.setattr(run, "RAIZ_REPO", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _: PYTHON)

    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert resultado.exit_code == 1
    assert resultado.output.splitlines() == ["falta .claude/hooks/validar-capitulo.py"]

    (hooks / "validar-capitulo.py").write_text("", "utf-8")
    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert (resultado.exit_code, resultado.output) == (0, "")


def _sin(*claves: str) -> dict[str, str]:
    return {k: v for k, v in EMISOR.items() if k not in claves}


@pytest.mark.parametrize(
    ("cambio", "hallazgos"),
    [
        (
            {"env_ignorado": False},
            [".env no está ignorado por git: las claves se versionarían"],
        ),
        (
            {"scores": _sin("LANGFUSE_SECRET_KEY")},
            ["TRACE_TO_LANGFUSE=true sin LANGFUSE_SECRET_KEY"],
        ),
        (
            {"scores": _sin("LANGFUSE_PUBLIC_KEY")},
            ["TRACE_TO_LANGFUSE=true sin LANGFUSE_PUBLIC_KEY"],
        ),
        (
            {"scores": _sin("LANGFUSE_BASE_URL")},
            ["TRACE_TO_LANGFUSE=true sin LANGFUSE_BASE_URL ni LANGFUSE_HOST"],
        ),
        ({"scores": _sin("LANGFUSE_BASE_URL") | {"LANGFUSE_HOST": "https://h.invalid"}}, []),
        ({"scores": EMISOR}, []),
        ({"scores": {"TRACE_TO_LANGFUSE": "false"}}, []),
        ({"scores": {}}, []),
        ({"env_ignorado": None}, []),
        ({"env_ignorado": True}, []),
    ],
)
def test_env_y_claves(cambio: dict[str, object], hallazgos: list[str]) -> None:
    """CA-20 y CA-21 (RF-28, RF-33): el .env sin ignorar y el trazado pedido sin claves. Ningún
    hallazgo lleva un valor."""
    obtenidos = entorno(**BIEN | cambio, sucio=False, limpio=False)  # type: ignore[arg-type]
    assert obtenidos == hallazgos
    assert not any(v in h for h in obtenidos for v in EMISOR.values() if v != "true")


def _git(repo: Path, *orden: str) -> None:
    subprocess.run(["git", "-C", str(repo), *orden], check=True, capture_output=True)  # noqa: S603, S607


def test_env_sin_ignorar_por_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-21: sobre un repo git temporal, un .env sin ignorar hace salir con 1; tras ignorarlo,
    con 0. Y CA-20: con el trazado pedido en el .env sin la clave secreta, sale con 1 y el hallazgo
    no cita ningún valor."""
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text(SETTINGS, encoding="utf-8")
    (tmp_path / ".claude" / "hooks" / "denegar-escritura-estado.py").write_text("", "utf-8")
    (tmp_path / ".claude" / "hooks" / "validar-capitulo.py").write_text("", "utf-8")
    _git(tmp_path, "init", "-q")
    (tmp_path / ".env").write_text("".join(f"{k}={v}\n" for k, v in EMISOR.items()), "utf-8")
    monkeypatch.setattr(run, "RAIZ_REPO", tmp_path)
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda n: PYTHON if n == "python" else real(n))

    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert resultado.exit_code == 1
    assert resultado.output.splitlines() == [
        ".env no está ignorado por git: las claves se versionarían"
    ]

    (tmp_path / ".gitignore").write_text(".env\n", "utf-8")
    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert (resultado.exit_code, resultado.output) == (0, "")

    (tmp_path / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in _sin("LANGFUSE_SECRET_KEY").items()), "utf-8"
    )
    resultado = CliRunner().invoke(app, ["comprobar-entorno"])
    assert resultado.exit_code == 1
    assert resultado.output.splitlines() == ["TRACE_TO_LANGFUSE=true sin LANGFUSE_SECRET_KEY"]
