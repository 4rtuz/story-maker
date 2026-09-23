import sqlite3
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from novela.cli import app
from novela.dominio.base import SCHEMA_VERSION
from novela.dominio.config import Config

ARBOL = [
    "canon/personajes",
    "plan/capitulos",
    "estado/deltas",
    "memoria/resumenes",
    "capitulos",
    "qa",
    "checkpoints",
    "runs",
    "export",
]
ORDEN = ["nueva", "demo", "--idea", "x", "--capitulos", "3", "--palabras", "9000"]


def _huella(raiz: Path) -> dict[Path, int]:
    return {p: p.stat().st_mtime_ns for p in raiz.rglob("*")}


def test_crea_arbol_y_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-01: crea el árbol de architecture.md §4 y estado.db con meta.schema_version; repetido
    sobre el mismo slug sale con 1 y no modifica ningún fichero."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    resultado = CliRunner().invoke(app, ORDEN)
    assert resultado.exit_code == 0, resultado.output
    raiz = tmp_path / "demo"
    for directorio in ARBOL:
        assert (raiz / directorio).is_dir(), directorio
    config = Config.model_validate(yaml.safe_load((raiz / "config.yaml").read_text("utf-8")))
    assert config.idea_semilla == "x"
    assert config.parametros_obra.palabras_por_capitulo.objetivo == 3000
    with sqlite3.connect(raiz / "estado" / "estado.db") as conn:
        fila = conn.execute("SELECT valor FROM meta WHERE clave = 'schema_version'").fetchone()
    assert fila == (SCHEMA_VERSION,)

    antes = _huella(raiz)
    repetido = CliRunner().invoke(app, ORDEN)
    assert repetido.exit_code == 1
    assert _huella(raiz) == antes


@pytest.mark.parametrize("slug", ["../fuera", "Demo", "_cola"])
def test_slug_invalido_no_toca_disco(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, slug: str
) -> None:
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path / "novelas"))
    resultado = CliRunner().invoke(app, ["nueva", slug, "--idea", "x"])
    assert resultado.exit_code == 2
    assert not (tmp_path / "novelas").exists()
    assert not (tmp_path / "fuera").exists()


def test_parametros_imposibles_son_uso_incorrecto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    resultado = CliRunner().invoke(app, ["nueva", "demo", "--idea", "x", "--capitulos", "0"])
    assert resultado.exit_code == 2
    assert not (tmp_path / "demo").exists()
