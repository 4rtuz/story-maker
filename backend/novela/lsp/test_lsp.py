"""El linter de edición manual: diagnósticos sobre un capítulo editado, sin tocar el workspace."""

import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lsprotocol import types

from novela.dominio.brief import Brief
from novela.lsp import diagnosticos
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.nueva.test_nueva import _brief_valido
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]


def _cap07(ws: WorkspaceRepository) -> tuple[Path, str]:
    ruta = ws.raiz / "capitulos" / "07.md"
    return ruta, ruta.read_text(encoding="utf-8")


def _de(diags: list[types.Diagnostic], codigo: str) -> list[types.Diagnostic]:
    return [d for d in diags if d.code == codigo]


def _linea(texto: str, frase: str) -> int:
    return next(n for n, linea in enumerate(texto.splitlines()) if frase in linea)


def test_capitulo_intacto_sin_errores_ni_avisos(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    antes = fabrica.sha256(ws.estado_db)
    diags = diagnosticos.diagnosticar(*_cap07(ws))
    assert [d for d in diags if d.severity != types.DiagnosticSeverity.Information] == []
    assert fabrica.sha256(ws.estado_db) == antes


def test_termino_prohibido_con_rango_exacto(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    ruta, texto = _cap07(ws)
    texto += "Dijo: ¡CABRONES!\n"
    [d] = _de(diagnosticos.diagnosticar(ruta, texto), "termino_prohibido")
    n = len(texto.splitlines()) - 1
    assert d.severity == types.DiagnosticSeverity.Error
    assert d.range == types.Range(types.Position(n, 7), types.Position(n, 15))
    assert "«cabrón» (global)" in d.message


def test_nombre_mal_escrito_con_rango_exacto(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    ruta, texto = _cap07(ws)
    texto += "Y Eléna calló.\n"
    [d] = _de(diagnosticos.diagnosticar(ruta, texto), "nombre_mal_escrito")
    n = len(texto.splitlines()) - 1
    assert d.severity == types.DiagnosticSeverity.Error
    assert d.range == types.Range(types.Position(n, 2), types.Position(n, 7))
    assert "«Elena»" in d.message


def test_la_edicion_que_quita_la_cita_cambia_el_hecho(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    ruta, texto = _cap07(ws)
    editado = texto.replace(fabrica.frase_de_hecho(7), fabrica.frase_regenerada(7))
    [d] = _de(diagnosticos.diagnosticar(ruta, editado), "hecho_cambiado")
    assert d.severity == types.DiagnosticSeverity.Warning
    assert d.message.startswith("la edición cambia el hecho hec-007")
    assert d.range.start.line == _linea(texto, fabrica.frase_de_hecho(7)[:20])


def test_prosa_como_informacion(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    ruta, texto = _cap07(ws)
    texto += "\nYo miré. Yo vi. Yo supe.\n"
    [d, *_] = _de(diagnosticos.diagnosticar(ruta, texto), "narrador_primera_persona")
    assert d.severity == types.DiagnosticSeverity.Information
    assert d.range.start.line == len(texto.splitlines()) - 1


def test_fuera_de_un_workspace_no_hay_diagnosticos(tmp_path: Path) -> None:
    assert diagnosticos.diagnosticar(tmp_path / "notas.md", "cabrón") == []
    assert diagnosticos.diagnosticar(tmp_path / "x" / "capitulos" / "01.md", "cabrón") == []


def _mensaje(proc: subprocess.Popen[bytes], cuerpo: dict[str, Any]) -> None:
    datos = json.dumps(cuerpo).encode()
    assert proc.stdin is not None
    proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(datos) + datos)
    proc.stdin.flush()


def _leer(proc: subprocess.Popen[bytes]) -> dict[str, Any]:
    assert proc.stdout is not None
    largo = 0
    while (linea := proc.stdout.readline().strip()) != b"":
        if linea.lower().startswith(b"content-length:"):
            largo = int(linea.split(b":")[1])
    resultado: dict[str, Any] = json.loads(proc.stdout.read(largo))
    return resultado


def test_el_servidor_publica_en_did_open_y_did_change(novelas: Novelas) -> None:
    """De punta a punta por stdio, como lo lanza el editor."""
    ws = novelas("demo-24")
    ruta, texto = _cap07(ws)
    uri = ruta.as_uri()
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "novela.lsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    try:
        _mensaje(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"processId": None, "rootUri": None, "capabilities": {}},
            },
        )
        assert _leer(proc)["id"] == 1
        _mensaje(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        documento = {"uri": uri, "languageId": "markdown", "version": 1, "text": texto}
        _mensaje(
            proc,
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": documento},
            },
        )
        _mensaje(
            proc,
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": uri, "version": 2},
                    "contentChanges": [{"text": texto + "¡cabrón!\n"}],
                },
            },
        )
        publicados: list[dict[str, Any]] = []
        while len(publicados) < 2:
            m = _leer(proc)
            if m.get("method") == "textDocument/publishDiagnostics":
                publicados.append(m["params"])
    finally:
        proc.kill()
        proc.wait(timeout=10)
    assert [p["uri"] for p in publicados] == [uri, uri]
    codigos = [[d.get("code") for d in p["diagnostics"]] for p in publicados]
    assert "termino_prohibido" not in codigos[0]
    assert codigos[1].count("termino_prohibido") == 1


def test_grafia_del_destinatario_del_brief(novelas: Novelas, tmp_path: Path) -> None:
    """El destinatario de brief/brief.json entra en las formas de vp_nombres."""
    ws = novelas("demo-24")
    otro = _brief_valido(tmp_path, "brief-prueba") / "brief" / "brief.json"
    (ws.raiz / "brief").mkdir(exist_ok=True)
    shutil.copy(otro, ws.raiz / "brief" / "brief.json")
    nombre = Brief.model_validate_json(otro.read_text("utf-8")).destinatario.nombre.valor
    token = next(t for t in nombre.split() if len(t) >= 3)
    variante = token[0] + token[1].swapcase() + token[2:]
    ruta, texto = _cap07(ws)
    [d] = _de(
        diagnosticos.diagnosticar(ruta, texto + f"Y {variante} llegó.\n"), "nombre_mal_escrito"
    )
    assert f"grafía de destinatario: «{token}»" in d.message
