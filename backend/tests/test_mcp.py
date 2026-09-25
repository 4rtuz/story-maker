"""Servidor MCP (docs/mcp.md): tools de solo lectura contra un workspace de la fábrica, con el
cliente en memoria de FastMCP. Ninguna llamada a modelo."""

import asyncio
import base64
import io
import json
import shutil
import sqlite3
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.exceptions import ToolError
from pypdf import PdfReader

from api.main import app
from api.mcp import langfuse as langfuse_mcp
from api.mcp import servidor as servidor_mcp
from api.mcp.servidor import servidor
from novela.plataforma import langfuse
from novela.plataforma.workspace import huella
from tests.fixtures import fabrica

SLUG = "demo-mcp"
VERSIONADA = "demo-mcp-v2"
V1_CAP1 = "---\ntitulo: Antes\n---\nLa versión uno del capítulo.\n"


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    base = tmp_path_factory.mktemp("novelas")
    fabrica.construir(base, SLUG, fabrica.REGALO, cerrados=2)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("NOVELAS_DIR", str(base))
        yield base


@pytest.fixture(scope="module")
def versionada(base: Path) -> Path:
    """El formato en disco de la spec 0007: la v1 guardada en `versiones/v1/` con otro capítulo 1,
    `versiones.json` con las dos y `meta.version = 2` en la base vigente."""
    raiz = base / VERSIONADA
    shutil.copytree(base / SLUG, raiz)
    fabrica.escribir(raiz / "versiones" / "v1", {"capitulos/01.md": V1_CAP1})
    sello = {
        "1": fabrica.sha256(raiz / "versiones/v1/capitulos/01.md"),
        "2": fabrica.sha256(raiz / "capitulos/02.md"),
    }
    creada = "2026-09-01T10:00:00+00:00"
    registro = [
        {"numero": 1, "cambio": None, "creada": creada},
        {"numero": 2, "cambio": "cam-001", "creada": "2026-09-02T10:00:00+00:00"},
    ]
    version = {"numero": 1, "creada": creada, "cambio": None, "capitulos_sha256": sello}
    fabrica.escribir(
        raiz / "versiones",
        {
            "v1/version.json": json.dumps(version | {"ficheros": {}}),
            "versiones.json": json.dumps({"versiones": registro}),
        },
    )
    conn = sqlite3.connect(raiz / "estado" / "estado.db")
    with conn:
        conn.execute("INSERT INTO meta VALUES ('version', '2')")
    conn.close()
    return raiz


def llamar(tool: str, **args: Any) -> Any:
    async def _() -> Any:
        async with Client(servidor) as cliente:
            return await cliente.call_tool(tool, args)

    return asyncio.run(_())


def resultado(tool: str, **args: Any) -> Any:
    return llamar(tool, **args).structured_content["result"]


def test_list_novels(base: Path) -> None:
    [novela] = [n for n in resultado("list_novels") if n["slug"] == SLUG]
    assert novela["capitulos_hechos"] == 2
    assert novela["cursor"]["capitulo"] == 2
    assert novela["version"] == 1


def test_get_chapter_de_la_version_vigente(base: Path) -> None:
    texto = llamar("get_chapter", slug=SLUG, capitulo=1).data
    assert texto == (base / SLUG / "capitulos" / "01.md").read_text(encoding="utf-8")


def test_get_chapter_de_una_version_guardada(versionada: Path) -> None:
    assert llamar("get_chapter", slug=VERSIONADA, capitulo=1, version=1).data == V1_CAP1
    vigente = llamar("get_chapter", slug=VERSIONADA, capitulo=1, version=2).data
    assert vigente == (versionada / "capitulos" / "01.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "args",
    [
        {"slug": "../etc", "capitulo": 1},
        {"slug": SLUG, "capitulo": 0},
        {"slug": SLUG, "capitulo": 3},  # no escrito
        {"slug": SLUG, "capitulo": 1, "version": 2},  # inexistente
        {"slug": "no-existe", "capitulo": 1},
    ],
)
def test_get_chapter_rechaza(base: Path, args: dict[str, Any]) -> None:
    with pytest.raises(ToolError):
        llamar("get_chapter", **args)


def test_list_versions_sin_versiones_es_una_sola(base: Path) -> None:
    [v] = resultado("list_versions", slug=SLUG)
    assert (v["numero"], v["cambio"], v["capitulos_cambiados"]) == (1, None, [])


def test_list_versions_con_el_capitulo_que_cambio(versionada: Path) -> None:
    v1, v2 = resultado("list_versions", slug=VERSIONADA)
    assert (v1["numero"], v1["cambio"], v1["estado"]) == (1, None, "completa")
    assert (v2["numero"], v2["cambio"], v2["estado"]) == (2, "cam-001", "en_curso")
    assert v2["capitulos_cambiados"] == [1]


def test_story_bible_hechos_y_cronologia(base: Path) -> None:
    hechos = resultado("query_story_bible", slug=SLUG, tipo="hechos")
    assert [h["id"] for h in hechos] == ["hec-001", "hec-002"]
    [uno] = resultado("query_story_bible", slug=SLUG, tipo="hechos", filtro=hechos[0]["texto"])
    assert uno["id"] == "hec-001"
    cronologia = resultado("query_story_bible", slug=SLUG, tipo="cronologia")
    assert {e["capitulo"] for e in cronologia} == {1, 2}


def test_story_bible_personajes_y_lugares_sin_secretos(base: Path) -> None:
    personajes = resultado("query_story_bible", slug=SLUG, tipo="personajes")
    elena = next(p for p in personajes if p["id"] == fabrica.ELENA)
    assert elena["nombre"] and elena["capitulos"] == [1, 2]
    assert "secreto" not in json.dumps(personajes)
    lugares = resultado("query_story_bible", slug=SLUG, tipo="lugares", filtro="archivo")
    assert [lugar["id"] for lugar in lugares] == [fabrica.ARCHIVO]
    assert lugares[0]["capitulos"] == [2]


def test_story_bible_rechaza_un_tipo_desconocido(base: Path) -> None:
    with pytest.raises(ToolError):
        llamar("query_story_bible", slug=SLUG, tipo="misterio")


def test_download_novel_es_el_pdf_de_los_capitulos_cerrados(base: Path) -> None:
    [bloque] = llamar("download_novel", slug=SLUG).content
    assert bloque.resource.mime_type == "application/pdf"
    lector = PdfReader(io.BytesIO(base64.b64decode(bloque.resource.blob)))
    texto = "".join(p.extract_text() for p in lector.pages)
    assert "La linterna, noche 2" in texto


def test_ninguna_tool_de_lectura_escribe(base: Path, versionada: Path) -> None:
    """Todas menos `request_change`, la única de escritura, que tiene sus propios tests."""
    antes = {d.name: huella(d) for d in base.iterdir()}
    for slug in (SLUG, VERSIONADA):
        resultado("list_novels")
        llamar("get_chapter", slug=slug, capitulo=2)
        resultado("list_versions", slug=slug)
        for tipo in ("personajes", "lugares", "hechos", "cronologia"):
            resultado("query_story_bible", slug=slug, tipo=tipo)
        llamar("download_novel", slug=slug)
    assert {d.name: huella(d) for d in base.iterdir()} == antes
    lectura = [t for t in asyncio.run(servidor.list_tools()) if t.name != "request_change"]
    assert len(lectura) == 5
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in lectura)


def test_cada_llamada_se_registra_en_langfuse(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trazas: list[dict[str, Any]] = []
    monkeypatch.setattr(langfuse_mcp, "emitir", trazas.append)
    llamar("get_chapter", slug=SLUG, capitulo=1)
    with pytest.raises(ToolError):
        llamar("get_chapter", slug=SLUG, capitulo=9)
    assert [(t["name"], t["input"], bool(t["error"])) for t in trazas] == [
        ("mcp.get_chapter", {"slug": SLUG, "capitulo": 1}, False),
        ("mcp.get_chapter", {"slug": SLUG, "capitulo": 9}, True),
    ]


def test_montado_en_la_api_por_streamable_http(base: Path) -> None:
    inicio = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    cabeceras = {"Accept": "application/json, text/event-stream"}
    with TestClient(app, base_url="http://127.0.0.1:8000") as cliente:
        respuesta = cliente.post("/mcp/", json=inicio, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert '"name":"story-maker"' in respuesta.text.replace(" ", "")


@pytest.mark.parametrize("ajena", [{"Host": "novelas.example"}, {"Origin": "http://evil.example"}])
def test_http_rechaza_host_y_origen_ajenos(base: Path, ajena: dict[str, str]) -> None:
    """Como /lanzamientos: un dominio que resuelve a 127.0.0.1 (DNS rebinding) no pasa."""
    cabeceras = {"Accept": "application/json, text/event-stream"} | ajena
    with TestClient(app, base_url="http://127.0.0.1:8000") as cliente:
        respuesta = cliente.post("/mcp/", json={}, headers=cabeceras)
    assert respuesta.status_code in (403, 421)


def test_sin_claves_langfuse_no_hace_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(langfuse_mcp, "_sink", lambda: langfuse.SinkNulo())
    llamadas: list[Any] = []
    monkeypatch.setattr(urllib.request, "urlopen", llamadas.append)
    langfuse_mcp.emitir({"name": "mcp.list_novels", "input": {}, "error": None})
    assert llamadas == []


def test_langfuse_caido_no_rompe_la_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        langfuse_mcp, "_sink", lambda: langfuse.SinkLangfuse("http://127.0.0.1:9", "pk", "sk")
    )
    langfuse_mcp.emitir({"name": "mcp.list_novels", "input": {}, "error": None})


# --- request_change: la única tool de escritura -----------------------------------------------

CAMBIABLE = "demo-mcp-cambio"
PEDIDO = {"slug": CAMBIABLE, "hecho": "hec-002", "texto": fabrica.TEXTO_CAMBIO}


@pytest.fixture(scope="module")
def plantilla(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("plantilla")
    fabrica.construir(base, CAMBIABLE, fabrica.CAMBIO, cerrados=fabrica.CAMBIO.num_capitulos)
    return base / CAMBIABLE


@pytest.fixture
def cambiable(plantilla: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Una novela terminada, copia fresca por test, con la escritura habilitada. El CLI corre de
    verdad como subproceso del venv, contra este NOVELAS_DIR."""
    raiz = tmp_path / CAMBIABLE
    shutil.copytree(plantilla, raiz)
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    monkeypatch.setenv(servidor_mcp.ESCRITURA, "1")
    servidor.enable(names={"request_change"})
    yield raiz
    servidor.disable(names={"request_change"})


def _listadas() -> set[str]:
    return {t.name for t in asyncio.run(servidor.list_tools())}


def llamar_con(handler: Any, tool: str, modo: str = "legacy", **args: Any) -> Any:
    """Con elicitation; `legacy`, la era del handshake, que aún tiene canal de vuelta."""

    async def _() -> Any:
        async with Client(servidor, elicitation_handler=handler, mode=modo) as cliente:
            return await cliente.call_tool(tool, args)

    return asyncio.run(_())


def test_request_change_deshabilitada_por_defecto(base: Path) -> None:
    assert "request_change" not in _listadas()
    with pytest.raises(ToolError):
        llamar("request_change", slug=SLUG, hecho="hec-002", texto="otro")


def test_request_change_sin_la_variable_no_escribe_aunque_este_listada(
    cambiable: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(servidor_mcp.ESCRITURA)
    with pytest.raises(ToolError, match="deshabilitada"):
        llamar("request_change", **PEDIDO)


def test_request_change_anotada_como_destructiva(cambiable: Path) -> None:
    [tool] = [t for t in asyncio.run(servidor.list_tools()) if t.name == "request_change"]
    assert tool.annotations
    assert tool.annotations.read_only_hint is False and tool.annotations.destructive_hint


@pytest.mark.parametrize(
    "malo",
    [
        {"slug": "../etc"},
        {"hecho": "hec-2"},
        {"texto": ""},
        {"texto": "x" * 501},
        {"motivo": "m" * 501},
    ],
)
def test_request_change_valida_parametros(cambiable: Path, malo: dict[str, str]) -> None:
    antes = fabrica.huella(cambiable)
    with pytest.raises(ToolError):
        llamar("request_change", **(PEDIDO | malo))
    assert fabrica.huella(cambiable) == antes


def test_request_change_sin_confirmacion_simula_y_no_escribe(cambiable: Path) -> None:
    antes = fabrica.huella(cambiable)
    plan = resultado_de(llamar("request_change", **PEDIDO))
    assert plan["aplicado"] is False and plan["confirmacion"]
    assert "regenerar 02, 04, 06" in plan["plan"]
    assert fabrica.huella(cambiable) == antes


def test_request_change_con_token_incorrecto_no_aplica(cambiable: Path) -> None:
    antes = fabrica.huella(cambiable)
    with pytest.raises(ToolError, match="confirmación"):
        llamar("request_change", **PEDIDO, confirmacion="0" * 16)
    assert fabrica.huella(cambiable) == antes


def test_request_change_el_token_ata_la_peticion(cambiable: Path) -> None:
    """El token de una petición no confirma otra: cambia el texto, cambia el token."""
    token = resultado_de(llamar("request_change", **PEDIDO))["confirmacion"]
    otro = PEDIDO | {"texto": "La puerta de la linterna estaba forzada."}
    with pytest.raises(ToolError, match="confirmación"):
        llamar("request_change", **otro, confirmacion=token)
    assert not (cambiable / "versiones").exists()


def test_request_change_con_token_correcto_aplica(cambiable: Path) -> None:
    token = resultado_de(llamar("request_change", **PEDIDO))["confirmacion"]
    hecho = resultado_de(llamar("request_change", **PEDIDO, confirmacion=token))
    assert hecho["aplicado"] is True
    assert hecho["siguiente"] == f"novela producir {CAMBIABLE}"
    assert (cambiable / "versiones" / "v1").is_dir()
    assert (cambiable / "cambios" / "cam-001.json").is_file()


def test_request_change_con_elicitation_aceptada_aplica(cambiable: Path) -> None:
    vistos: list[str] = []

    async def acepta(mensaje: str, *_: Any) -> dict[str, bool]:
        vistos.append(mensaje)
        return {"value": True}

    assert resultado_de(llamar_con(acepta, "request_change", **PEDIDO))["aplicado"] is True
    assert "regenerar 02, 04, 06" in vistos[0]
    assert (cambiable / "cambios" / "cam-001.json").is_file()


def test_request_change_con_elicitation_rechazada_no_aplica(cambiable: Path) -> None:
    async def rechaza(*_: Any) -> ElicitResult[Any]:
        return ElicitResult(action="decline")

    antes = fabrica.huella(cambiable)
    assert resultado_de(llamar_con(rechaza, "request_change", **PEDIDO))["aplicado"] is False
    assert fabrica.huella(cambiable) == antes


def test_request_change_en_la_era_sin_canal_de_vuelta_pide_el_token(cambiable: Path) -> None:
    async def acepta(*_: Any) -> dict[str, bool]:
        return {"value": True}

    antes = fabrica.huella(cambiable)
    plan = resultado_de(llamar_con(acepta, "request_change", modo="auto", **PEDIDO))
    assert plan["aplicado"] is False and plan["confirmacion"]
    assert fabrica.huella(cambiable) == antes


def test_request_change_traza_sin_el_texto_largo(
    cambiable: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trazas: list[dict[str, Any]] = []
    monkeypatch.setattr(langfuse_mcp, "emitir", trazas.append)
    largo = "La puerta de la linterna estaba intacta. " * 10
    llamar("request_change", **(PEDIDO | {"texto": largo}))
    [traza] = trazas
    assert traza["name"] == "mcp.request_change"
    assert traza["input"]["hecho"] == "hec-002"
    assert len(traza["input"]["texto"]) < 150 and str(len(largo)) in traza["input"]["texto"]


def resultado_de(respuesta: Any) -> Any:
    return respuesta.structured_content


def test_request_change_por_http_solo_desde_loopback(cambiable: Path) -> None:
    """La guarda de Host/Origin del montaje deja pasar un Host local desde otra máquina; la tool
    comprueba además la IP del cliente (la de TestClient es `testclient`)."""
    cabeceras = {"Accept": "application/json, text/event-stream"}
    inicio = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    llamada = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "request_change", "arguments": PEDIDO},
    }
    antes = fabrica.huella(cambiable)
    with TestClient(app, base_url="http://127.0.0.1:8000") as cliente:
        r = cliente.post("/mcp/", json=inicio, headers=cabeceras)
        sesion = cabeceras | {"mcp-session-id": r.headers["mcp-session-id"]}
        aviso = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        cliente.post("/mcp/", json=aviso, headers=sesion)
        respuesta = cliente.post("/mcp/", json=llamada, headers=sesion)
    assert "solo se admite desde este equipo" in respuesta.text, respuesta.text
    assert fabrica.huella(cambiable) == antes
