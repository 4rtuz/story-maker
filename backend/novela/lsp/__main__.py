"""`uv run python -m novela.lsp`: el servidor LSP por stdio (docs/lsp.md)."""

from novela.lsp.servidor import SERVIDOR

SERVIDOR.start_io()
