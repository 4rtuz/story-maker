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


def test_md_novedades(novelas: Novelas, regenerada: str) -> None:
    """CA-35 (RF-38): con la versión 2, la sección de novedades con un enlace por capítulo
    cambiado, un ancla delante de cada capítulo y la marca solo bajo los cambiados."""
    ws = novelas(regenerada)
    resultado = CliRunner().invoke(app, ["exportar", ws.slug, "--formato", "md"])
    assert resultado.exit_code == 0, resultado.output
    texto = (ws.raiz / "export" / "novela.md").read_text(encoding="utf-8")
    cabecera = texto.split('<a id="capitulo-01"></a>')[0]
    assert cabecera.startswith("# Novedades de la versión 2\n")
    enlaces = [f"[Capítulo {n} — La linterna, noche {n}](#capitulo-{n:02d})" for n in (2, 4, 6)]
    assert [e for e in enlaces if e in cabecera] == enlaces
    assert cabecera.count("](#capitulo-") == 3
    marca = "*Modificado en la versión 2.*"
    for n in range(1, 7):
        despues = texto.split(f'<a id="capitulo-{n:02d}"></a>\n\n# Capítulo {n}\n\n')
        assert len(despues) == 2, n
        assert despues[1].startswith(marca) == (n in (2, 4, 6)), n
    assert texto.count(marca) == 3
