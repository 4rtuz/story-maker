"""Servidor LSP por stdio: publica los diagnósticos de `diagnosticos.py` al abrir y al editar."""

from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer
from pygls.uris import to_fs_path

from novela.lsp import diagnosticos

SERVIDOR = LanguageServer("novela-lsp", "0.1.0")


def _publicar(ls: LanguageServer, uri: str) -> None:
    documento = ls.workspace.get_text_document(uri)
    ruta = to_fs_path(uri)
    try:
        diags = diagnosticos.diagnosticar(Path(ruta), documento.source) if ruta else []
    except Exception as exc:  # un workspace roto no tumba el editor
        diags = [
            types.Diagnostic(
                range=types.Range(types.Position(0, 0), types.Position(0, 0)),
                message=f"no se pudo comprobar el capítulo: {exc}",
                severity=types.DiagnosticSeverity.Error,
                source="novela",
            )
        ]
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=uri, version=documento.version, diagnostics=diags)
    )


@SERVIDOR.feature(types.TEXT_DOCUMENT_DID_OPEN)
def abierto(ls: LanguageServer, params: types.DidOpenTextDocumentParams) -> None:
    _publicar(ls, params.text_document.uri)


@SERVIDOR.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def cambiado(ls: LanguageServer, params: types.DidChangeTextDocumentParams) -> None:
    _publicar(ls, params.text_document.uri)
