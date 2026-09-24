import hashlib
import shutil
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from novela.cli import app
from novela.dominio.artefactos import Manifest
from novela.plataforma import run
from novela.plataforma.workspace import CONFIG_DIR, WorkspaceRepository
from tests.test_contratos import CONTRATO

Novelas = Callable[[str], WorkspaceRepository]
LAS_DIEZ = datetime(2026, 9, 23, 10, 0)


def test_manifiesto_y_log(novelas: Novelas) -> None:
    """CA-13: sin run abierto se crea runs/<run_id>/ con manifest.json (sha y recetas), y la línea
    de harness.log está en disco al salir del bloque, no al cerrar el proceso."""
    ws = novelas("demo-24")
    abierto = run.abrir(ws, 8, entorno={}, ahora=LAS_DIEZ)
    assert abierto.id == "r-20260923-1000"
    manifiesto = Manifest.model_validate_json((abierto.dir / "manifest.json").read_bytes())
    assert manifiesto.capitulo == 8
    assert len(manifiesto.sha_commit) == 40
    recetas = hashlib.sha256((CONFIG_DIR / "recipes.yaml").read_bytes()).hexdigest()
    assert manifiesto.version_recetas == recetas

    with abierto.registro("briefing", "08", "escritor"):
        pass
    with open(abierto.dir / "harness.log", encoding="utf-8") as otro_descriptor:
        assert "briefing 08 escritor -> 0" in otro_descriptor.read()

    # El capítulo sigue abierto: un minuto después se reutiliza el mismo run.
    assert run.abrir(ws, 8, entorno={}, ahora=datetime(2026, 9, 23, 10, 7)).id == abierto.id


def test_registro_anota_la_causa_del_fallo(novelas: Novelas) -> None:
    abierto = run.abrir(novelas("demo-24"), 8, entorno={}, ahora=LAS_DIEZ)
    with pytest.raises(ValueError, match="custodia"):
        with abierto.registro("aplicar-delta", "08") as causas:
            causas.append("custodia: el capítulo cambió")
            raise ValueError("custodia rota")
    log = (abierto.dir / "harness.log").read_text(encoding="utf-8")
    assert "aplicar-delta 08 -> error · custodia: el capítulo cambió" in log


def test_run_id_de_entorno(novelas: Novelas) -> None:
    """CA-33: con NOVELA_RUN_ID se usa ese run; con un valor que no casa el formato, se aborta
    sin crear directorio."""
    ws = novelas("demo-24")
    fijado = run.abrir(ws, 8, entorno={"NOVELA_RUN_ID": "r-20260101-0101"}, ahora=LAS_DIEZ)
    assert fijado.dir == ws.raiz / "runs" / "r-20260101-0101"
    antes = sorted((ws.raiz / "runs").iterdir())
    for malo in ("../fuera", "r-2026-01", "r-20260101-0101\n"):
        with pytest.raises(run.RunInvalido):
            run.abrir(ws, 8, entorno={"NOVELA_RUN_ID": malo}, ahora=LAS_DIEZ)
    assert sorted((ws.raiz / "runs").iterdir()) == antes
    assert not (ws.raiz / "fuera").exists()


def test_run_de_arranque(tmp_path: Path) -> None:
    """RF-11: el arranque tiene su run y ningún otro agente lo reutiliza. Sin eso, el capítulo 1
    quedaba atribuido al canon vacío que vio el briefing del arquitecto (spec 0003 §2, hueco 4)."""
    orden = ["nueva", "nuevo", "--idea", "Un faro.", "--capitulos", "3", "--palabras", "900"]
    assert CliRunner().invoke(app, orden, env={"NOVELAS_DIR": str(tmp_path)}).exit_code == 0
    ws = WorkspaceRepository(tmp_path / "nuevo")

    arranque = run.abrir(ws, 1, fase="arranque", entorno={}, ahora=LAS_DIEZ)
    assert run.abrir(ws, 1, fase="arranque", entorno={}, ahora=LAS_DIEZ).id == arranque.id
    manifiesto = Manifest.model_validate_json((arranque.dir / "manifest.json").read_bytes())
    assert manifiesto.fase == "arranque"

    with pytest.raises(run.RunInvalido, match="de otro capítulo o fase"):
        run.abrir(ws, 1, entorno={}, ahora=LAS_DIEZ)  # el minuto ya es del arranque

    capitulo = run.abrir(ws, 1, entorno={}, ahora=datetime(2026, 9, 23, 10, 5))
    assert capitulo.id != arranque.id
    manifiesto = Manifest.model_validate_json((capitulo.dir / "manifest.json").read_bytes())
    assert manifiesto.fase == "capitulo"


GIT = shutil.which("git") or "git"


def _git(repo: Path, *args: str) -> None:
    identidad = ["-c", "user.email=test@example.invalid", "-c", "user.name=test"]
    subprocess.run([GIT, "-C", str(repo), *identidad, *args], check=True, capture_output=True)  # noqa: S603


def test_procedencia(tmp_path: Path) -> None:
    """CA-08 (RF-12, F-04, F-05): un prompt sin commitear deja sucio el manifiesto y cambia su
    hash. CLAUDE.md también, porque se carga en cada subagente. Sin git, sucio."""
    ficheros = {
        ".claude/agents/escritor.md": "Escribes.\n",
        ".claude/commands/novela-nueva.md": "Arrancas.\n",
        "CLAUDE.md": "Convenciones.\n",
    }
    for relativa, texto in ficheros.items():
        (tmp_path / relativa).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relativa).write_text(texto, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "limpio")

    sucio, limpios = run.procedencia(tmp_path)
    assert not sucio
    assert set(limpios) == set(ficheros)

    (tmp_path / ".claude/agents/escritor.md").write_text("Escribes mejor.\n", encoding="utf-8")
    sucio, hashes = run.procedencia(tmp_path)
    assert sucio and hashes[".claude/agents/escritor.md"] != limpios[".claude/agents/escritor.md"]

    _git(tmp_path, "checkout", "-q", "--", ".")
    (tmp_path / "CLAUDE.md").write_text("Otras convenciones.\n", encoding="utf-8")
    sucio, hashes = run.procedencia(tmp_path)
    assert sucio and hashes["CLAUDE.md"] != limpios["CLAUDE.md"]

    assert run.procedencia(tmp_path, git=None)[0]  # D-6: sin git no se afirma que esté limpio


def test_manifiesto_registra_los_prompts(novelas: Novelas) -> None:
    """RF-12 sobre el repo real: el manifiesto lleva el hash de cada agente de CONTRATO y de lo que
    se carga en cada uno."""
    abierto = run.abrir(novelas("demo-24"), 8, entorno={}, ahora=LAS_DIEZ)
    manifiesto = Manifest.model_validate_json((abierto.dir / "manifest.json").read_bytes())
    hashes = manifiesto.hashes_claude
    agentes = {k for k in hashes if k.startswith(".claude/agents/")}
    assert agentes == {f".claude/agents/{rol}.md" for rol in CONTRATO}
    assert {"CLAUDE.md", "AGENTS.md", ".claude/settings.json"} <= set(hashes)
