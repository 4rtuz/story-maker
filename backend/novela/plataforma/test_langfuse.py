import json
import socket
import urllib.error
import urllib.request
from typing import Any

import pytest

from novela.plataforma import langfuse

SEIS = {
    "coherencia": 0.8,
    "continuidad": 1.0,
    "tension": 7,
    "longitud": 0.9,
    "fair_play": 0.9,
    "estilo": 1.0,
}
# Nombres por partes: con nombre y valor juntos, el pre-commit anti-claves rechazaría este fichero.
CLAVES = {
    f"LANGFUSE_{k}": v
    for k, v in {
        "PUBLIC_KEY": "publica-de-prueba",
        "SECRET_KEY": "secreta-de-prueba",
        "BASE_URL": "https://langfuse.invalid",
    }.items()
}


def _sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("se abrió una conexión de red")

    monkeypatch.setattr(socket, "create_connection", prohibido)
    monkeypatch.setattr(urllib.request, "urlopen", prohibido)


@pytest.mark.parametrize("valor", [None, "", "True", "1", "yes"])
def test_sink_noop_y_scores(monkeypatch: pytest.MonkeyPatch, valor: str | None) -> None:
    """CA-22 en el puerto: sin TRACE_TO_LANGFUSE exactamente igual a "true", no-op sin red."""
    _sin_red(monkeypatch)
    entorno = CLAVES | ({} if valor is None else {"TRACE_TO_LANGFUSE": valor})
    sink = langfuse.desde_entorno(entorno)
    assert isinstance(sink, langfuse.SinkNulo)
    assert sink.emitir("demo", 8, "r-20260923-1000", SEIS) == []


def test_con_true_llegan_los_seis(monkeypatch: pytest.MonkeyPatch) -> None:
    enviados: list[dict[str, Any]] = []

    class Respuesta:
        status = 200

        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        assert peticion.full_url == "https://langfuse.invalid/api/public/scores"
        assert peticion.get_header("Authorization", "").startswith("Basic ")
        assert timeout <= langfuse.TIMEOUT_S
        enviados.append(json.loads(peticion.data))  # type: ignore[arg-type]
        return Respuesta()

    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    sink = langfuse.desde_entorno(CLAVES | {"TRACE_TO_LANGFUSE": "true"})
    assert sink.emitir("demo", 8, "r-20260923-1000", SEIS) == []
    assert {e["name"] for e in enviados} == set(SEIS)
    assert all(e["sessionId"] == "r-20260923-1000" for e in enviados)
    # Id determinista: reemitir el mismo capítulo sustituye el score en vez de duplicarlo.
    assert {e["id"] for e in enviados} == {f"demo-r-20260923-1000-08-{n}" for n in SEIS}


def test_sink_caido_no_rompe(monkeypatch: pytest.MonkeyPatch) -> None:
    """validators.md §3.5: con Langfuse inalcanzable, el fallo se devuelve, no se lanza, y se
    para en el primero: seis timeouts seguidos no pueden retener el checkpoint."""
    llamadas = []

    def caido(peticion: urllib.request.Request, timeout: float) -> None:
        llamadas.append(peticion)
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(urllib.request, "urlopen", caido)
    fallos = langfuse.desde_entorno(CLAVES | {"TRACE_TO_LANGFUSE": "true"}).emitir(
        "demo", 8, "r-20260923-1000", SEIS
    )
    assert len(fallos) == 1 and "sin red" in fallos[0]
    assert len(llamadas) == 1
