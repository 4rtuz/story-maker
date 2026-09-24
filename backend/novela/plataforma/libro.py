"""Lectura del libro de regalo desde el workspace, común al PDF (`novela exportar --formato pdf`) y
a la lectura web (`GET /novelas/{slug}/libro`): así los dos no pueden divergir.

Solo lee. Del canon, las fichas de quien aparece y `canon/mundo.md`; el misterio no lo abre.
"""

from pydantic import ValidationError

from novela.dominio import ficha as fichas
from novela.dominio import frontmatter
from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.brief import Brief
from novela.dominio.canon import Mundo, Personaje
from novela.dominio.libro import EntradaDeFicha, EntradaDeIndice, Libro, dedicatoria
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository


def capitulo(ws: WorkspaceRepository, n: int) -> tuple[str, str]:
    """Título del frontmatter y cuerpo."""
    ruta = ws.raiz / "capitulos" / f"{ws.nn(n)}.md"
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkspaceInvalido(f"{ruta}: {exc}") from exc
    return ws.modelo_de_md(ruta, texto, FrontmatterCapitulo).titulo, frontmatter.partir(texto)[1]


def ficha(ws: WorkspaceRepository, n: int) -> fichas.Ficha:
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        filas = estado_db.apariciones(conn, n)
    sin = [c for c in range(1, n + 1) if c not in {f.capitulo for f in filas}]
    if sin:
        raise WorkspaceInvalido(
            f"capítulos cerrados sin apariciones en estado.db: {', '.join(map(str, sin))}"
        )
    personajes = {}
    for id_ in {f.entidad for f in filas if f.tipo == "personaje"}:
        ruta = ws.raiz / "canon" / "personajes" / f"{id_}.md"
        if ruta.is_file():  # los que falten los nombra SinCanon, todos a la vez
            identidad = ws.leer_md(ruta, Personaje).identidad
            personajes[id_] = (identidad.nombre, tuple(identidad.alias))
    mundo = ws.leer_md(ws.raiz / "canon" / "mundo.md", Mundo)
    escenarios = {e.id: (e.nombre, e.descripcion) for e in mundo.escenarios}
    try:
        return fichas.construir(filas, personajes, escenarios)
    except fichas.SinCanon as exc:
        raise WorkspaceInvalido(str(exc)) from exc


def dedicatoria_de(ws: WorkspaceRepository) -> str | None:
    ruta = ws.raiz / "brief" / "brief.json"
    if not ruta.is_file():
        return None
    try:
        return dedicatoria(Brief.model_validate_json(ruta.read_bytes()))
    except ValidationError:
        # Sin el texto del error: lleva los valores, que son datos personales (plan 0006, PD5).
        raise WorkspaceInvalido("brief/brief.json no valida contra Brief") from None


def _entradas(entradas: tuple[fichas.EntradaFicha, ...]) -> list[EntradaDeFicha]:
    return [
        EntradaDeFicha(id=e.id, nombre=e.nombre, detalle=e.detalle, capitulos=list(e.capitulos))
        for e in entradas
    ]


def libro(ws: WorkspaceRepository) -> Libro:
    """Portada, índice y ficha hasta el último checkpoint, sin el cuerpo de los capítulos."""
    punto = ws.ultimo_checkpoint()
    cerrados = punto.capitulo if punto else 0
    ficha_ = ficha(ws, cerrados) if cerrados else fichas.Ficha((), ())
    return Libro(
        titulo=ws.slug,
        dedicatoria=dedicatoria_de(ws),
        capitulos=[
            EntradaDeIndice(capitulo=n, titulo=capitulo(ws, n)[0]) for n in range(1, cerrados + 1)
        ],
        personajes=_entradas(ficha_.personajes),
        lugares=_entradas(ficha_.lugares),
    )
