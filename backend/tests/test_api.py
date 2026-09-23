"""API de solo lectura (spec 0001 §5.5): cinco GET, ningún verbo de escritura."""

from fastapi.testclient import TestClient

from api.main import app

cliente = TestClient(app)


def test_app_arranca() -> None:
    assert cliente.get("/docs").status_code == 200
