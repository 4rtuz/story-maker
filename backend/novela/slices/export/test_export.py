from collections.abc import Callable

import ebooklib
from ebooklib import epub
from typer.testing import CliRunner

from novela.cli import app
from novela.plataforma.workspace import WorkspaceRepository

Novelas = Callable[[str], WorkspaceRepository]


def test_md_concatena_en_orden(novelas: Novelas) -> None:
    """Los 24 capítulos en orden, ninguno repetido y sin frontmatter: es metadato del harness."""
    ws = novelas("demo-terminado")
    resultado = CliRunner().invoke(app, ["exportar", ws.slug, "--formato", "md"])
    assert resultado.exit_code == 0, resultado.output
    texto = (ws.raiz / "export" / "novela.md").read_text(encoding="utf-8")
    titulos = [linea for linea in texto.splitlines() if linea.startswith("# Capítulo")]
    assert titulos == [f"# Capítulo {n}" for n in range(1, 25)]
    assert "run_id:" not in texto and not texto.startswith("---")


def test_epub_reabrible(novelas: Novelas) -> None:
    """CA-24: ebooklib lo reabre con los 24 capítulos. Que exista y pese no basta: un epub
    corrupto pesa igual. El índice sale de los títulos del frontmatter."""
    ws = novelas("demo-terminado")
    resultado = CliRunner().invoke(app, ["exportar", ws.slug, "--formato", "epub"])
    assert resultado.exit_code == 0, resultado.output
    libro = epub.read_epub(str(ws.raiz / "export" / "novela.epub"))
    documentos = libro.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    assert sum(d.is_chapter() for d in documentos) == 24  # el nav también es documento
    assert [e.title for e in libro.toc] == [f"La linterna, noche {n}" for n in range(1, 25)]
