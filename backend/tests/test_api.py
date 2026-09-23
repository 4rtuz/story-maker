"""API de solo lectura (spec 0001 §5.5): cinco GET, ningún verbo de escritura."""

import builtins
import io
import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from novela.plataforma.workspace import WorkspaceRepository, huella
from tests.fixtures import fabrica

BACKEND = Path(__file__).resolve().parents[1]  # código y .venv
cliente = TestClient(app)


def test_app_arranca() -> None:
    assert cliente.get("/docs").status_code == 200


def test_path_traversal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CA-26: el slug se valida antes de construir ninguna ruta. «No toca el disco» se comprueba,
    no se supone: toda apertura, stat o conexión fuera del código durante la petición queda
    registrada. FastAPI lee el fuente del endpoint para el mensaje de error; eso no es disco."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    tocado: list[Any] = []

    def espia(original: Callable[..., Any]) -> Callable[..., Any]:
        def registrar(*args: Any, **kwargs: Any) -> Any:
            tocado.append(args[0] if args else kwargs)
            return original(*args, **kwargs)

        return registrar

    for modulo, nombre in (
        (builtins, "open"),
        (io, "open"),
        (os, "stat"),
        (os, "scandir"),
        (sqlite3, "connect"),
    ):
        monkeypatch.setattr(modulo, nombre, espia(getattr(modulo, nombre)))
    respuesta = cliente.get("/novelas/..%2F..%2Fetc/estado")
    monkeypatch.undo()
    assert [p for p in tocado if not str(p).startswith(str(BACKEND))] == []
    assert respuesta.status_code == 422


@pytest.fixture
def solo_lectura(
    novelas: Callable[[str], WorkspaceRepository],
) -> Iterator[WorkspaceRepository]:
    """demo-24 en solo lectura mientras dura el test: si un endpoint intentara escribir, el sistema
    de ficheros lo impide. En Windows el atributo no protege directorios, así que además la huella
    del workspace tiene que salir igual que entró."""
    ws = novelas("demo-24")
    rutas = [ws.raiz, *ws.raiz.rglob("*")]
    antes = huella(ws.raiz)
    for ruta in rutas:
        ruta.chmod(stat.S_IREAD | (stat.S_IEXEC if ruta.is_dir() else 0))
    try:
        yield ws
    finally:
        for ruta in rutas:
            ruta.chmod(stat.S_IREAD | stat.S_IWRITE | (stat.S_IEXEC if ruta.is_dir() else 0))
    assert huella(ws.raiz) == antes


def test_cinco_get_en_solo_lectura(solo_lectura: WorkspaceRepository) -> None:
    """CA-25: los cinco GET sobre el fixture montado en solo lectura, y ningún verbo más."""
    ws = solo_lectura
    assert {m for ops in app.openapi()["paths"].values() for m in ops} == {"get"}

    novelas = cliente.get("/novelas")
    assert novelas.status_code == 200
    assert [(n["slug"], n["cursor"]["capitulo"]) for n in novelas.json()] == [("demo-24", 7)]

    estado = cliente.get("/novelas/demo-24/estado")
    assert estado.status_code == 200
    assert estado.json()["cursor"]["ultimo_paso"] == "aplicar-delta"

    indice = cliente.get("/novelas/demo-24/capitulos")
    assert indice.status_code == 200
    assert [c["capitulo"] for c in indice.json()] == list(range(1, 8))

    capitulo = cliente.get("/novelas/demo-24/capitulos/3")
    assert capitulo.status_code == 200
    assert capitulo.content == (ws.raiz / "capitulos" / "03.md").read_bytes()

    manifiesto = cliente.get(f"/novelas/demo-24/runs/{fabrica.run_id(7)}")
    assert manifiesto.status_code == 200
    assert manifiesto.json()["capitulo"] == 7

    for ruta in (
        "/novelas/no-existe/estado",
        "/novelas/no-existe/capitulos",
        "/novelas/demo-24/capitulos/8",  # dentro de rango, sin escribir
        "/novelas/demo-24/capitulos/25",  # fuera de rango
        "/novelas/demo-24/runs/r-20990101-0000",
    ):
        assert cliente.get(ruta).status_code == 404, ruta
