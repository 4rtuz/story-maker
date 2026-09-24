"""`GET /novelas/{slug}/libro`: portada, índice y ficha de la lectura web (docs/lectura-web.md).

La misma lógica que el PDF de la spec 0006, servida en solo lectura. El brief no se sirve: solo la
dedicatoria que sale de él.
"""

import shutil
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from novela.plataforma.workspace import WorkspaceRepository, huella
from tests.fixtures import fabrica

cliente = TestClient(app)
BRIEF = Path(__file__).parent / "fixtures" / "brief" / "brief-completo.json"
Novelas = Callable[[str], WorkspaceRepository]


def test_libro_sin_brief(novelas: Novelas) -> None:
    ws = novelas("demo-regalo")
    antes = huella(ws.raiz)
    respuesta = cliente.get("/novelas/demo-regalo/libro")
    assert respuesta.status_code == 200, respuesta.text
    libro = respuesta.json()
    assert libro["titulo"] == "demo-regalo"
    assert libro["dedicatoria"] is None
    indice = cliente.get("/novelas/demo-regalo/capitulos").json()
    esperado = [{"capitulo": c["capitulo"], "titulo": c["titulo"]} for c in indice]
    assert libro["capitulos"] == esperado
    personajes = {p["id"]: p for p in libro["personajes"]}
    assert personajes[fabrica.ELENA]["capitulos"] == [1, 2, 3]
    assert personajes[fabrica.ELENA]["nombre"]
    lugares = {lu["id"]: lu for lu in libro["lugares"]}
    assert lugares[fabrica.ARCHIVO]["capitulos"] == [2]
    assert huella(ws.raiz) == antes  # la API no escribe


def test_libro_con_brief(novelas: Novelas) -> None:
    ws = novelas("demo-regalo")
    (ws.raiz / "brief").mkdir(exist_ok=True)
    shutil.copy(BRIEF, ws.raiz / "brief" / "brief.json")
    libro = cliente.get("/novelas/demo-regalo/libro").json()
    assert libro["dedicatoria"] == "Para Aurora Ficticia, en el día de su boda."


def test_libro_brief_invalido_no_filtra_datos(novelas: Novelas) -> None:
    ws = novelas("demo-regalo")
    (ws.raiz / "brief").mkdir(exist_ok=True)
    (ws.raiz / "brief" / "brief.json").write_text('{"ocasion": "Aurora Ficticia"}', "utf-8")
    respuesta = cliente.get("/novelas/demo-regalo/libro")
    assert respuesta.status_code == 404
    assert "Aurora" not in respuesta.text


def test_libro_sin_capitulos_cerrados(novelas: Novelas, tmp_path: Path) -> None:
    novelas("demo-regalo")  # fija NOVELAS_DIR en tmp_path
    r = fabrica.cli(tmp_path, "nueva", "vacia", "--idea", "Un faro.", run=fabrica.run_id(1))
    assert r.exit_code == 0, r.output
    libro = cliente.get("/novelas/vacia/libro").json()
    assert (libro["capitulos"], libro["personajes"], libro["lugares"]) == ([], [], [])


def test_libro_404() -> None:
    assert cliente.get("/novelas/no-existe/libro").status_code == 404
