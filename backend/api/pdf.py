"""El libro de regalo en PDF (spec 0006) con los capítulos cerrados, construido en memoria: lo
sirven `GET /novelas/{slug}/pdf` (spec 0015) y la tool `download_novel` del MCP. No escribe en el
workspace."""

from novela.plataforma.workspace import WorkspaceRepository


class SinCapitulos(ValueError):
    """La novela todavía no tiene ningún capítulo cerrado que exportar."""


def pdf_de(ws: WorkspaceRepository, titulo: str) -> bytes:
    # Import diferido: la API no carga slices/ al arrancar (test_api_no_importa_slices). De export
    # solo usa lectores y `pdf.construir`, que devuelve bytes.
    from novela.plataforma import libro as libros
    from novela.slices.export import cmd as export
    from novela.slices.export import pdf

    punto = ws.ultimo_checkpoint()
    if punto is None:
        raise SinCapitulos("no hay capítulos cerrados que exportar")
    capitulos = [libros.capitulo(ws, c) for c in range(1, punto.capitulo + 1)]
    libro = pdf.Libro(
        titulo=titulo,
        idioma=ws.config().parametros_obra.idioma,
        dedicatoria=libros.libro(ws).dedicatoria,
        capitulos=tuple(pdf.Capitulo(n, t, c) for n, (t, c) in enumerate(capitulos, 1)),
        ficha=libros.ficha(ws, punto.capitulo),
        creado=export._creado(ws, punto),
    )
    return pdf.construir(libro)
