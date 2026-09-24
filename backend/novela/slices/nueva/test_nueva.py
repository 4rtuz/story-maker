import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from api.main import app as api
from novela.cli import app
from novela.dominio.base import SCHEMA_VERSION
from novela.dominio.brief import Brief, idea_semilla
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


# --- spec 0005: novela nueva --brief -----------------------------------------------------------

BRIEF = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "brief"


def _brief_valido(base: Path, slug: str = "boda-prueba") -> Path:
    """Un workspace con brief/brief.json escrito por `novela brief validar`, no a mano."""
    cli = CliRunner()
    assert cli.invoke(app, ["brief", "iniciar", slug, "--ocasion", "boda"]).exit_code == 0
    fichero = str(BRIEF / "respuestas-completas.md")
    orden = ["brief", "entrada", slug, "--tipo", "respuesta", "--fichero", fichero]
    assert cli.invoke(app, orden).exit_code == 0
    raiz = base / slug
    (raiz / "brief" / "borrador.json").write_bytes((BRIEF / "borrador-completo.json").read_bytes())
    assert cli.invoke(app, ["brief", "validar", slug]).exit_code == 0
    return raiz


def test_nueva_desde_brief(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-25: 10 capítulos, la terna de la extensión, el género y los vetos, estado.db con el
    cursor inicial, y GET /novelas lo lista."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    raiz = _brief_valido(tmp_path)
    resultado = CliRunner().invoke(app, ["nueva", "boda-prueba", "--brief"])
    assert resultado.exit_code == 0, resultado.output
    config = Config.model_validate(yaml.safe_load((raiz / "config.yaml").read_text("utf-8")))
    obra = config.parametros_obra
    assert obra.num_capitulos == 10
    assert obra.palabras_por_capitulo.model_dump() == {"objetivo": 1250, "min": 1000, "max": 1500}
    assert obra.longitud_total_palabras == 12500
    assert obra.subgenero == "domestic_suspense"
    assert obra.restricciones_contenido == ["hospital"]
    brief = Brief.model_validate_json((raiz / "brief" / "brief.json").read_bytes())
    assert config.idea_semilla == idea_semilla(brief)
    for directorio in ARBOL:
        assert (raiz / directorio).is_dir(), directorio
    with sqlite3.connect(raiz / "estado" / "estado.db") as conn:
        assert conn.execute("SELECT valor FROM meta WHERE clave = 'schema_version'").fetchone()
    estado = CliRunner().invoke(app, ["estado", "boda-prueba", "--json"])
    assert json.loads(estado.stdout)["cursor"]["capitulo"] == 1
    slugs = [n["slug"] for n in TestClient(api).get("/novelas").json()]
    assert "boda-prueba" in slugs


def test_brief_excluyente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-26 y VER-34: 2, 2, 1, 1 y 1, y ninguno escribe config.yaml ni estado.db."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    raiz = _brief_valido(tmp_path)
    solo_brief = _brief_valido(tmp_path, "sin-brief-json")
    (solo_brief / "brief" / "brief.json").unlink()
    con_config = _brief_valido(tmp_path, "con-config")
    (con_config / "config.yaml").write_text("{}", encoding="utf-8")
    roto = _brief_valido(tmp_path, "brief-roto")
    (roto / "brief" / "brief.json").write_text('{"ocasion": "Aurora Ficticia"}', encoding="utf-8")
    for orden, codigo in (
        (["nueva", "boda-prueba", "--brief", "--idea", "x"], 2),
        (["nueva", "boda-prueba", "--brief", "--capitulos", "3"], 2),
        (["nueva", "boda-prueba", "--brief", "--palabras", "9000"], 2),
        (["nueva", "boda-prueba", "--brief", "--subgenero", "noir"], 2),
        (["nueva", "sin-brief-json", "--brief"], 1),
        (["nueva", "no-existe", "--brief"], 1),
        (["nueva", "con-config", "--brief"], 1),
        (["nueva", "brief-roto", "--brief"], 1),
        (["nueva", "boda-prueba", "--idea", "x"], 1),
        (["nueva", "nuevo-slug"], 2),
    ):
        resultado = CliRunner().invoke(app, orden)
        assert resultado.exit_code == codigo, (orden, resultado.output)
        assert "Aurora" not in resultado.output
    assert not (raiz / "config.yaml").exists()
    assert not (tmp_path / "nuevo-slug").exists() and not (tmp_path / "no-existe").exists()
    assert (con_config / "config.yaml").read_text(encoding="utf-8") == "{}"
    for slug in ("boda-prueba", "sin-brief-json", "con-config", "brief-roto"):
        assert not (tmp_path / slug / "estado" / "estado.db").exists(), slug
