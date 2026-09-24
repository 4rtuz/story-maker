"""API de solo lectura (spec 0001 §5.5): cinco GET, ningún verbo de escritura."""

import builtins
import io
import json
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


@pytest.mark.parametrize(
    "ruta",
    [
        "/novelas/..%2F..%2Fetc/estado",
        # spec 0004, CA-32 a CA-37: los GET nuevos pasan por la misma dependencia.
        "/novelas/..%2F..%2Fetc/config",
        "/novelas/..%2F..%2Fetc/escaleta",
        "/novelas/..%2F..%2Fetc/checkpoint",
    ],
)
def test_path_traversal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ruta: str) -> None:
    """CA-26: el slug se valida antes de construir ninguna ruta. «No toca el disco» se comprueba,
    no se supone: toda apertura, stat o conexión fuera del código durante la petición queda
    registrada. FastAPI lee el fuente del endpoint para el mensaje de error; eso no es disco."""
    respuesta, fuera = _pedir_espiando(monkeypatch, tmp_path, ruta)
    assert fuera == []
    assert respuesta.status_code == 422


def _pedir_espiando(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ruta: str
) -> tuple[Any, list[Any]]:
    """La respuesta y lo que la petición abrió, miró o conectó fuera de `backend/`."""
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
    respuesta = cliente.get(ruta)
    monkeypatch.undo()
    return respuesta, [p for p in tocado if not str(p).startswith(str(BACKEND))]


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


# --- spec 0004: los GET del panel -------------------------------------------------------------


@pytest.fixture
def recien_creada(novelas: Callable[[str], WorkspaceRepository], tmp_path: Path) -> Path:
    """Solo `novela nueva`: sin plan, sin checkpoints y sin runs. `nueva` no abre run. Pide
    `novelas` por su NOVELAS_DIR en tmp_path."""
    resultado = fabrica.cli(
        tmp_path, "nueva", "recien-creada", "--idea", "Un faro apagado.", run=fabrica.run_id(1)
    )
    assert resultado.exit_code == 0, resultado.output
    return tmp_path / "recien-creada"


def test_config(novelas: Callable[[str], WorkspaceRepository]) -> None:
    """CA-32: el modelo validado, con sus valores por defecto, no el YAML literal (D53)."""
    ws = novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/config")
    assert respuesta.status_code == 200
    assert respuesta.json() == ws.config().model_dump(mode="json")
    assert cliente.get("/novelas/no-existe/config").status_code == 404


def test_escaleta(novelas: Callable[[str], WorkspaceRepository], recien_creada: Path) -> None:
    """CA-33 y VER-1: 200 con la curva de la obra, aunque la respuesta pase por la validación de
    FastAPI, que no lleva el contexto de `num_capitulos`; sin plan, 404."""
    novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/escaleta")
    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()["curva_tension_objetivo"]) == 24
    assert cliente.get("/novelas/recien-creada/escaleta").status_code == 404


def test_checkpoint(novelas: Callable[[str], WorkspaceRepository], recien_creada: Path) -> None:
    """CA-34: el `latest.json` tal cual, o `null` sin checkpoints."""
    ws = novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/checkpoint")
    assert respuesta.status_code == 200
    assert respuesta.json()["capitulo"] == 7
    assert respuesta.json() == json.loads((ws.raiz / "checkpoints" / "latest.json").read_bytes())
    vacia = cliente.get("/novelas/recien-creada/checkpoint")
    assert vacia.status_code == 200
    assert vacia.json() is None


@pytest.mark.parametrize(
    ("fichero", "romper"),
    [
        # La curva de 23 valores no cuadra con num_capitulos 24.
        (
            "plan/escaleta.md",
            lambda t: t.replace("curva_tension_objetivo:\n- 2\n", "curva_tension_objetivo:\n", 1),
        ),
        ("plan/escaleta.md", lambda t: t.replace("\n---\n", "\n", 1)),  # frontmatter sin cerrar
        ("plan/escaleta.md", lambda t: t.replace("actos:", "actos: [", 1)),  # YAML roto
        ("config.yaml", lambda t: t.replace("parametros_obra:", "parametros_obra: [", 1)),
    ],
)
def test_ilegible_da_404(
    novelas: Callable[[str], WorkspaceRepository], fichero: str, romper: Callable[[str], str]
) -> None:
    """VER-2: un fichero que falta o no valida sale como 404 con su `detail`, nunca como 500."""
    ws = novelas("demo-24")
    ruta = ws.raiz / fichero
    texto = ruta.read_text(encoding="utf-8")
    assert romper(texto) != texto
    ruta.write_text(romper(texto), encoding="utf-8")
    recurso = "config" if fichero == "config.yaml" else "escaleta"
    respuesta = cliente.get(f"/novelas/demo-24/{recurso}")
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]
