"""Epub con ebooklib: un documento por capítulo, el índice desde los títulos del frontmatter."""

import io

from ebooklib import epub
from markdown_it import MarkdownIt


def construir(slug: str, idioma: str, capitulos: list[tuple[str, str]]) -> bytes:
    """`capitulos` son pares (título, cuerpo markdown), en orden."""
    libro = epub.EpubBook()
    libro.set_identifier(slug)
    libro.set_title(slug)
    libro.set_language(idioma)
    md = MarkdownIt("commonmark")
    documentos = []
    for n, (titulo, cuerpo) in enumerate(capitulos, 1):
        doc = epub.EpubHtml(title=titulo, file_name=f"cap-{n:03d}.xhtml", lang=idioma)
        doc.content = md.render(cuerpo)
        libro.add_item(doc)
        documentos.append(doc)
    libro.toc = documentos
    libro.add_item(epub.EpubNcx())
    libro.add_item(epub.EpubNav())
    libro.spine = ["nav", *documentos]
    salida = io.BytesIO()
    epub.write_epub(salida, libro)
    return salida.getvalue()
