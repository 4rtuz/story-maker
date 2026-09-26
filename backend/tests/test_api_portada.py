"""`GET /novelas/{slug}/portada` y `GET /novelas/{slug}/metricas` (spec 0015 §5.4): lo que el CLI
dejó en el workspace, tal cual y en solo lectura."""

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from api.main import app
from novela.dominio.metricas import Consumo, InformeDeCostes, TotalDeCostes
from novela.plataforma.workspace import WorkspaceRepository, huella

cliente = TestClient(app)
Novelas = Callable[[str], WorkspaceRepository]
JPEG = b"\xff\xd8\xff\xe0 portada"
CERO = Consumo(
    llamadas=0,
    tokens_entrada=0,
    tokens_salida=0,
    tokens_cache_lectura=0,
    coste_usd=0.0,
    latencia_media_llamada_s=0.0,
)


def test_portada(novelas: Novelas) -> None:
    """RF-06: el JPEG con `image/jpeg`; 404 sin portada o sin novela."""
    ws = novelas("demo-24")
    assert cliente.get("/novelas/demo-24/portada").status_code == 404
    assert cliente.get("/novelas/no-existe/portada").status_code == 404
    (ws.raiz / "portada.jpg").write_bytes(JPEG)
    antes = huella(ws.raiz)
    r = cliente.get("/novelas/demo-24/portada")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg" and r.content == JPEG
    assert huella(ws.raiz) == antes


def test_metricas(novelas: Novelas) -> None:
    """RF-07: el informe guardado por `novela costes --guardar`; 404 sin él o si no valida."""
    ws = novelas("demo-24")
    assert cliente.get("/novelas/demo-24/metricas").status_code == 404
    informe = InformeDeCostes(
        slug="demo-24",
        sesion="novela-demo-24",
        generado=datetime(2026, 9, 25, tzinfo=UTC),
        pasos=[],
        total=TotalDeCostes(**CERO.model_dump(), latencia_s=0.0),
    )
    (ws.raiz / "metricas.json").write_text(informe.model_dump_json(), encoding="utf-8")
    r = cliente.get("/novelas/demo-24/metricas")
    assert r.status_code == 200
    assert InformeDeCostes.model_validate(r.json()) == informe
    (ws.raiz / "metricas.json").write_text('{"slug": "demo-24"}', encoding="utf-8")
    assert cliente.get("/novelas/demo-24/metricas").status_code == 404
