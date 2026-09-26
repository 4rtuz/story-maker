"""`GET /novelas/{slug}/pdf` (spec 0015 §5.4): el libro de regalo de la spec 0006 con los capítulos
cerrados, para el botón «Descargar PDF» de Lectura. Se construye en memoria, como `download_novel`
del MCP: la API no escribe."""

import io
import shutil
from collections.abc import Callable

from fastapi.testclient import TestClient
from pypdf import PdfReader

from api.main import app
from novela.plataforma.workspace import WorkspaceRepository, huella

cliente = TestClient(app)
Novelas = Callable[[str], WorkspaceRepository]


def test_pdf_de_los_capitulos_cerrados(novelas: Novelas) -> None:
    ws = novelas("demo-regalo")
    antes = huella(ws.raiz)
    r = cliente.get("/novelas/demo-regalo/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'attachment; filename="demo-regalo.pdf"'
    texto = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Demo regalo" in texto  # el título legible del panel, no el slug
    assert huella(ws.raiz) == antes


def test_sin_capitulos_cerrados_ni_novela_es_404(novelas: Novelas) -> None:
    ws = novelas("demo-regalo")
    shutil.rmtree(ws.raiz / "checkpoints")
    assert cliente.get("/novelas/demo-regalo/pdf").status_code == 404
    assert cliente.get("/novelas/no-existe/pdf").status_code == 404
