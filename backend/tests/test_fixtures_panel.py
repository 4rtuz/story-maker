"""CA-42 (RF-42, D56): el generador de los workspaces del panel no emite nada a Langfuse, ni con
claves en el entorno ni en el `.env` de la raíz del repo, y deja las dos cosas como estaban."""

import http.server
import os
import subprocess
import sys
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from novela.plataforma import langfuse, run
from tests.fixtures import panel

BACKEND = Path(__file__).resolve().parent.parent
_FICTICIAS = {
    "TRACE_TO_LANGFUSE": "true",
    "LANGFUSE_PUBLIC_KEY": "dummy-publica",
    "LANGFUSE_SECRET_KEY": "dummy-secreta",
    "LANGFUSE_BASE_URL": "http://ejemplo.invalid",
}


@pytest.fixture
def _sin_claves_reales() -> Iterator[None]:
    """Anula el autouse de sesión de conftest.py para los tests de este fichero: aquí las claves
    tienen que llegar, porque lo que se prueba es que panel.py las aparta (VER-25)."""
    yield


@pytest.fixture
def repo_con_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    lineas = "".join(f"{k}={v}\n" for k, v in _FICTICIAS.items())
    (raiz / ".env").write_text(lineas, encoding="utf-8")
    monkeypatch.setattr(run, "RAIZ_REPO", raiz)
    for clave, valor in _FICTICIAS.items():
        monkeypatch.setenv(clave, valor)
    return raiz


def test_generador_sin_claves(
    repo_con_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Control positivo: las claves están, en el entorno y en el .env de RAIZ_REPO.
    assert os.environ["TRACE_TO_LANGFUSE"] == "true"
    assert (run.RAIZ_REPO / ".env").is_file()

    vistos: list[dict[str, str]] = []
    raices: list[Path] = []
    real = langfuse.desde_entorno

    def registrar(entorno: Mapping[str, str]) -> langfuse.ScoreSink:
        vistos.append(dict(entorno))
        raices.append(run.RAIZ_REPO)
        return real(entorno)

    monkeypatch.setattr(langfuse, "desde_entorno", registrar)
    antes = dict(os.environ)
    panel.generar(tmp_path / "novelas")

    assert vistos, "el checkpoint de demo-24 tiene que haber pedido su emisor"
    for entorno in vistos:
        assert not set(entorno) & set(_FICTICIAS), entorno
    for raiz in raices:
        assert raiz != repo_con_env
        assert not (raiz / ".env").exists()
    assert run.RAIZ_REPO == repo_con_env
    assert dict(os.environ) == antes
    assert sorted(p.name for p in (tmp_path / "novelas").iterdir()) == [
        "demo-24",
        "grande-999",
        "recien-creada",
    ]


class _Contador(http.server.BaseHTTPRequestHandler):
    peticiones = 0

    def _contar(self) -> None:
        type(self).peticiones += 1
        self.send_response(200)
        self.end_headers()

    do_GET = do_POST = _contar

    def log_message(self, *_: object) -> None:
        return None


def test_generador_como_orden(tmp_path: Path) -> None:
    servidor = http.server.HTTPServer(("127.0.0.1", 0), _Contador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        entorno = {**os.environ, **_FICTICIAS}
        entorno["LANGFUSE_BASE_URL"] = f"http://127.0.0.1:{servidor.server_port}"
        destino = tmp_path / "novelas"
        r = subprocess.run(  # noqa: S603 (la orden es fija: este intérprete y el módulo)
            [sys.executable, "-m", "tests.fixtures.panel", str(destino)],
            cwd=BACKEND,
            env=entorno,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert r.returncode == 0, r.stderr
        for slug in ("demo-24", "recien-creada", "grande-999"):
            assert (destino / slug / "config.yaml").is_file()
        assert _Contador.peticiones == 0
    finally:
        servidor.shutdown()
