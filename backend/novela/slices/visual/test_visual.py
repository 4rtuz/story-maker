"""`novela registrar-visual`: valida el informe de la validación visual, lo guarda en
`qa/visual.json` y emite `visual_lectura` (docs/validacion-visual.md)."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.plataforma import langfuse
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]


class Espia:
    def __init__(self) -> None:
        self.recibidos: list[tuple[str, int, str, dict[str, float]]] = []

    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        self.recibidos.append((slug, capitulo, run_id, dict(scores)))
        return []


@pytest.fixture
def espia(monkeypatch: pytest.MonkeyPatch) -> Espia:
    sink = Espia()
    monkeypatch.setattr(langfuse, "desde_entorno", lambda _entorno: sink)
    return sink


def _ok(id_: str) -> dict[str, Any]:
    return {"id": id_, "ok": True, "detalle": ""}


def _informe(*comprobaciones: dict[str, Any], slug: str = "demo-regalo") -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "slug": slug,
        "herramienta": "playwright-test",
        "comprobaciones": list(comprobaciones),
        "capturas": ["docs/img/lectura-portada.png"],
    }


def _registrar(tmp_path: Path, informe: dict[str, Any] | str, slug: str = "demo-regalo") -> Result:
    fichero = tmp_path / "informe.json"
    fichero.write_text(informe if isinstance(informe, str) else json.dumps(informe), "utf-8")
    return CliRunner().invoke(app, ["registrar-visual", slug, "--fichero", str(fichero)])


TODO_OK = [_ok(i) for i in ("portada", "dedicatoria", "indice", "navegacion", "ficha")]


def test_todo_ok(novelas: Novelas, tmp_path: Path, espia: Espia) -> None:
    ws = novelas("demo-regalo")
    r = _registrar(tmp_path, _informe(*TODO_OK))
    assert r.exit_code == 0, r.output
    assert "5/5" in r.stdout
    guardado = json.loads((ws.raiz / "qa" / "visual.json").read_text("utf-8"))
    assert [c["id"] for c in guardado["comprobaciones"]] == [c["id"] for c in TODO_OK]
    assert espia.recibidos == [("demo-regalo", 3, fabrica.run_id(3), {"visual_lectura": 1.0})]


def test_fallo_nombra_el_rol(novelas: Novelas, tmp_path: Path, espia: Espia) -> None:
    novelas("demo-regalo")
    fallos = [
        {"id": "ficha", "ok": False, "detalle": "Tomás sin enlaces", "responsable": "escritor"},
        {"id": "navegacion", "ok": False, "detalle": "el 2 no abre", "responsable": "frontend"},
    ]
    r = _registrar(tmp_path, _informe(*TODO_OK[:3], *fallos))
    assert r.exit_code == 1
    assert "devolver a: escritor (ficha), frontend (navegacion)" in r.stdout
    assert espia.recibidos[0][3] == {"visual_lectura": 0.6}


@pytest.mark.parametrize(
    "comprobacion",
    [
        {"id": "ficha", "ok": False, "detalle": "x"},  # fallo sin responsable
        {"id": "ficha", "ok": True, "detalle": "", "responsable": "escritor"},  # ok con culpable
        {"id": "ficha", "ok": False, "detalle": "x", "responsable": "cronista"},  # rol ajeno
        {"id": "otra", "ok": True, "detalle": ""},
    ],
)
def test_informe_invalido(
    novelas: Novelas, tmp_path: Path, espia: Espia, comprobacion: dict[str, Any]
) -> None:
    ws = novelas("demo-regalo")
    r = _registrar(tmp_path, _informe(comprobacion))
    assert r.exit_code == 2 and "--fichero" in r.output
    assert not (ws.raiz / "qa" / "visual.json").exists() and espia.recibidos == []


def test_slug_distinto(novelas: Novelas, tmp_path: Path, espia: Espia) -> None:
    novelas("demo-regalo")
    assert _registrar(tmp_path, _informe(*TODO_OK, slug="otra")).exit_code == 2
    assert _registrar(tmp_path, "no es json").exit_code == 2
