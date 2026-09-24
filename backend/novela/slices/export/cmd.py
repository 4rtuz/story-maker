"""`novela exportar <slug> --formato md|epub|pdf`: saca los capítulos cerrados a `export/`.

No reescribe prosa: un exportador que edita convierte el fichero exportado en otra versión del
capítulo. El frontmatter no sale; es metadato del harness.

`pdf` es el libro de regalo de la spec 0006: portada, índice, capítulos y una ficha de personajes y
lugares desde la tabla `apariciones`. Del canon solo lee las fichas de quien aparece y
`canon/mundo.md`; el misterio no lo abre.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

import typer

from novela.dominio.artefactos import Checkpoint, Manifest
from novela.plataforma.libro import capitulo as _capitulo
from novela.plataforma.libro import ficha as _ficha
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.export import epub, markdown, pdf

TITULO_MAX = 120


class Formato(StrEnum):
    MD = "md"
    EPUB = "epub"
    PDF = "pdf"


def _titulo(titulo: str | None, slug: str) -> str:
    if titulo is None:
        return slug
    titulo = titulo.strip()
    if not titulo or len(titulo) > TITULO_MAX:
        raise typer.BadParameter(f"--titulo: entre 1 y {TITULO_MAX} caracteres sin contar espacios")
    return titulo


def _creado(ws: WorkspaceRepository, punto: Checkpoint) -> datetime:
    """CreationDate del PDF: la del run del último checkpoint, para que sea determinista."""
    ruta = ws.raiz / "runs" / punto.run_id / "manifest.json"
    return datetime.fromisoformat(ws.leer_json(ruta, Manifest).creado)


def _pdf(
    ws: WorkspaceRepository, titulo: str, punto: Checkpoint, capitulos: list[tuple[str, str]]
) -> bytes:
    if not (ws.raiz / "brief" / "brief.json").is_file():
        typer.echo("sin dedicatoria: el workspace no tiene brief/brief.json")
    libro = pdf.Libro(
        titulo=titulo,
        idioma=ws.config().parametros_obra.idioma,
        dedicatoria=None,
        capitulos=tuple(pdf.Capitulo(n, t, c) for n, (t, c) in enumerate(capitulos, 1)),
        ficha=_ficha(ws, punto.capitulo),
        creado=_creado(ws, punto),
    )
    try:
        return pdf.construir(libro)
    except pdf.GlifoAusente as exc:
        typer.echo(f"exportar: {exc}", err=True)
        raise typer.Exit(1) from exc


def exportar(
    slug: str,
    formato: Annotated[Formato, typer.Option("--formato")],
    titulo: Annotated[
        str | None, typer.Option("--titulo", help="título de la portada; solo con pdf")
    ] = None,
) -> None:
    """Exporta los capítulos cerrados, en orden, a export/novela.<formato>."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with ws.bloquear():
        punto = ws.ultimo_checkpoint()
        if punto is None:
            typer.echo("no hay capítulos cerrados que exportar", err=True)
            raise typer.Exit(1)
        capitulos = [_capitulo(ws, c) for c in range(1, punto.capitulo + 1)]
        ruta = ws.raiz / "export" / f"novela.{formato}"
        if formato is Formato.MD:
            ws.escribir(ruta, markdown.concatenar([cuerpo for _, cuerpo in capitulos]))
        elif formato is Formato.EPUB:
            idioma = ws.config().parametros_obra.idioma
            ws.escribir(ruta, epub.construir(slug, idioma, capitulos))
        else:
            ws.escribir(ruta, _pdf(ws, _titulo(titulo, slug), punto, capitulos))
    typer.echo(f"exportar: {len(capitulos)} capítulos en export/{ruta.name}")
