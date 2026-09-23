"""Contratos transversales: esquemas, claves, clientes de modelo, OpenAPI."""

import shutil
import subprocess
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
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
