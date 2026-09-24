"""Regresión de la auditoría de seguridad (docs/security-report.md S-03): path traversal por el
slug y el run_id en cada ruta de la API y del CLI, y las guardas Host/Origin de /lanzamientos."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from api.main import app
from novela.cli import app as cli
from tests.test_lanzamientos import LOCAL, PANEL, Lanzados, cliente, lanzados  # noqa: F401

SLUGS_MALOS = ["..%2F..%2Fetc", "..", "demo%2F..%2F..", "Demo", "demo%00", "demo%5C..%5C.."]
SUFIJOS = [
    "/estado",
    "/config",
    "/escaleta",
    "/checkpoint",
    "/runs",
    "/capitulos",
    "/capitulos/1",
    "/runs/r-20260924-1200",
    "/runs/r-20260924-1200/log",
]


@pytest.mark.parametrize("sufijo", SUFIJOS)
@pytest.mark.parametrize("slug", SLUGS_MALOS)
def test_get_novelas_rechaza_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, slug: str, sufijo: str
) -> None:
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    r = TestClient(app).get(f"/novelas/{slug}{sufijo}")
    assert r.status_code in (404, 422), (slug, sufijo, r.status_code)


@pytest.mark.parametrize("run_id", ["..%2F..%2Fconfig.yaml", "..", "r-20260924-1200%2F..%2F.."])
def test_run_id_rechazado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_id: str) -> None:
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    for sufijo in ("", "/log"):
        r = TestClient(app).get(f"/novelas/demo/runs/{run_id}{sufijo}")
        assert r.status_code in (404, 422), (run_id, sufijo)


@pytest.mark.parametrize("accion", ["reanudar", "detener"])
@pytest.mark.parametrize("slug", ["..%2Fetc", "..%2F..%2Fnovelas%2Fotra", "Demo"])
def test_lanzamientos_rechaza_slug(lanzados: Lanzados, accion: str, slug: str) -> None:  # noqa: F811
    r = cliente().post(f"/lanzamientos/{slug}/{accion}", headers={"Origin": PANEL})
    assert r.status_code == 422
    assert lanzados == []


@pytest.mark.parametrize(
    "base", ["http://localhost.:8000", "http://127.0.0.1.nip.io:8000", "http://evil.test:8000"]
)
def test_host_no_local(lanzados: Lanzados, base: str) -> None:  # noqa: F811
    r = cliente(base=base).post(
        "/lanzamientos", json={"slug": "demo", "idea": "x"}, headers={"Origin": PANEL}
    )
    assert r.status_code == 403
    assert lanzados == []


@pytest.mark.parametrize("origen", ["null", "http://localhost:5174", "http://localhost:5173.evil"])
def test_origin_no_del_panel(lanzados: Lanzados, origen: str) -> None:  # noqa: F811
    r = cliente().post(
        "/lanzamientos", json={"slug": "demo", "idea": "x"}, headers={"Origin": origen}
    )
    assert r.status_code == 403
    assert lanzados == []


@pytest.mark.parametrize(
    "orden",
    [
        ["estado", "../otra", "--breve"],
        ["validar", "..", "1"],
        ["lint-prosa", "../otra"],
        ["briefing", "demo/../../otra", "1", "escritor"],
        ["brief", "validar", "..\\otra"],
    ],
)
def test_cli_rechaza_slug(tmp_path: Path, orden: list[str]) -> None:
    r = CliRunner().invoke(cli, orden, env={"NOVELAS_DIR": str(tmp_path)})
    assert r.exit_code == 2, r.output
