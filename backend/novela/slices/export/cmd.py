"""`novela exportar <slug> --formato md|epub`: saca los capítulos cerrados a `export/`.

No reescribe prosa: un exportador que edita convierte el fichero exportado en otra versión del
capítulo. El frontmatter no sale; es metadato del harness.
"""

from enum import StrEnum
from typing import Annotated

import typer

from novela.dominio import frontmatter
from novela.dominio.artefactos import FrontmatterCapitulo
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository
from novela.slices.export import epub, markdown


class Formato(StrEnum):
    MD = "md"
    EPUB = "epub"


def _capitulo(ws: WorkspaceRepository, capitulo: int) -> tuple[str, str]:
    """Título del frontmatter y cuerpo."""
    ruta = ws.raiz / "capitulos" / f"{ws.nn(capitulo)}.md"
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkspaceInvalido(f"{ruta}: {exc}") from exc
    return ws.modelo_de_md(ruta, texto, FrontmatterCapitulo).titulo, frontmatter.partir(texto)[1]


def exportar(slug: str, formato: Annotated[Formato, typer.Option("--formato")]) -> None:
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
        else:
            idioma = ws.config().parametros_obra.idioma
            ws.escribir(ruta, epub.construir(slug, idioma, capitulos))
    typer.echo(f"exportar: {len(capitulos)} capítulos en export/{ruta.name}")
