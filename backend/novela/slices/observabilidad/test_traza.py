"""La traza de un paso: un span OTLP raíz con la sesión de la novela, al que se cuelga la sesión de
Claude Code por `CC_LANGFUSE_TRACEPARENT`. Sin red: `urlopen` está sustituido."""

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from novela.plataforma import langfuse
from novela.slices.observabilidad import traza

ENTORNO = {
    "TRACE_TO_LANGFUSE": "true",
    "LANGFUSE_PUBLIC_KEY": "publica-de-prueba",
    "LANGFUSE_SECRET_KEY": "secreta-de-prueba",
    "LANGFUSE_BASE_URL": "https://langfuse.invalid",
}


def _atributos(span: dict[str, Any]) -> dict[str, Any]:
    def valor(v: dict[str, Any]) -> Any:
        if "arrayValue" in v:
            return [x["stringValue"] for x in v["arrayValue"]["values"]]
        return v["stringValue"]

    return {a["key"]: valor(a["value"]) for a in span["attributes"]}


def test_abre_la_traza_del_paso_en_la_sesion_de_la_novela(monkeypatch: pytest.MonkeyPatch) -> None:
    enviados: list[urllib.request.Request] = []

    class Respuesta:
        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return b"{}"

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        enviados.append(peticion)
        return Respuesta()

    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    padre = traza.abrir(ENTORNO, "demo", "capitulo 03", {"sha_commit": "abc"})

    assert padre is not None
    assert langfuse.traza_de({"CC_LANGFUSE_TRACEPARENT": padre}) is not None
    (peticion,) = enviados
    assert peticion.full_url == "https://langfuse.invalid/api/public/otel/v1/traces"
    assert peticion.get_header("X-langfuse-ingestion-version") == "4"
    span = json.loads(peticion.data)["resourceSpans"][0]["scopeSpans"][0]["spans"][0]  # type: ignore[arg-type]
    assert padre == f"00-{span['traceId']}-{span['spanId']}-01"
    atributos = _atributos(span)
    assert atributos["langfuse.session.id"] == "novela-demo"
    assert atributos["langfuse.trace.name"] == "demo · capitulo 03"
    assert "demo" in atributos["langfuse.trace.tags"]
    assert atributos["langfuse.trace.metadata.paso"] == "capitulo 03"
    assert atributos["langfuse.trace.metadata.sha_commit"] == "abc"


def test_sin_trace_to_langfuse_no_hay_red(monkeypatch: pytest.MonkeyPatch) -> None:
    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("se abrió una conexión de red")

    monkeypatch.setattr(urllib.request, "urlopen", prohibido)
    assert traza.abrir(ENTORNO | {"TRACE_TO_LANGFUSE": ""}, "demo", "nueva", {}) is None


def test_langfuse_caido_no_para_el_paso(monkeypatch: pytest.MonkeyPatch) -> None:
    def caido(*_: object, **__: object) -> None:
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(urllib.request, "urlopen", caido)
    assert traza.abrir(ENTORNO, "demo", "nueva", {}) is None


def test_novela_traza_imprime_el_traceparent_para_una_sesion_interactiva(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typer.testing import CliRunner

    from novela.cli import app

    padre = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
    monkeypatch.setattr(
        traza, "abrir", lambda _e, slug, paso, _m: padre if paso == "brief" else None
    )
    r = CliRunner().invoke(app, ["traza", "demo", "brief"])
    assert r.exit_code == 0 and r.stdout.strip() == padre
    r = CliRunner().invoke(app, ["traza", "demo", "otro"])
    assert r.exit_code == 0 and r.stdout.strip() == ""


def test_paso_de_una_orden(tmp_path: object) -> None:
    """El paso que nombra la traza: el mismo para `producir` y para `novela traza` a mano."""
    from pathlib import Path

    from novela.plataforma.workspace import WorkspaceRepository

    assert isinstance(tmp_path, Path)
    ws = WorkspaceRepository(tmp_path / "demo")
    assert traza.paso_de(ws, "/novela-continuar") == "capitulo 01"
    (ws.raiz / "checkpoints").mkdir(parents=True)
    (ws.raiz / "checkpoints" / "latest.json").write_text('{"capitulo": 4}', encoding="utf-8")
    assert traza.paso_de(ws, "/novela-continuar") == "capitulo 05"
    assert traza.paso_de(ws, "/novela-brief") == "brief"
    assert traza.paso_de(ws, "/novela-nueva") == "nueva"
    assert traza.paso_de(ws, "/novela-auditar") == "auditoria"
    assert traza.paso_de(ws, "cambio") == "cambio"
