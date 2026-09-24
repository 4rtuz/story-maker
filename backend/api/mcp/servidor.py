"""Servidor MCP de solo lectura: consultar y descargar novelas (docs/mcp.md).

Montado en la API en `/mcp` (streamable HTTP) y ejecutable por stdio con `python -m api.mcp`.
Ninguna tool escribe: la base se abre con `mode=ro` y el PDF se construye en memoria.
"""

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.utilities.types import File
from pydantic import BaseModel, Field

from api.mcp.langfuse import TrazaLangfuse
from api.routers.novelas import novelas as _novelas
from novela.dominio.canon import Mundo, Personaje
from novela.dominio.estado import Cursor
from novela.dominio.ids import SLUG_PATRON
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository

servidor = FastMCP(
    "story-maker",
    instructions="Consulta y descarga de novelas, en solo lectura.",
    middleware=[TrazaLangfuse()],
)

Slug = Annotated[str, Field(pattern=SLUG_PATRON, description="slug de la novela")]
Capitulo = Annotated[int, Field(ge=1, le=999, description="número de capítulo")]
NumVersion = Annotated[int, Field(ge=1, description="número de versión; por defecto la vigente")]
SOLO_LECTURA = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


class Novela(BaseModel):
    slug: str
    cursor: Cursor
    capitulos_hechos: int
    version: int


class VersionDeNovela(BaseModel):
    numero: int
    cambio: str | None  # None: la original
    creada: str | None
    estado: Literal["completa", "en_curso"]
    capitulos_cambiados: list[int]  # respecto a la anterior; vacío en la original


def _ws(slug: str) -> WorkspaceRepository:
    ws = WorkspaceRepository.resolver(slug)
    if not ws.existe():
        raise WorkspaceInvalido(f"no existe la novela {slug}")
    return ws


def _vigente(ws: WorkspaceRepository) -> int:
    """`meta.version` (spec 0007), o la 1 si la base no la tiene."""
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        fila = conn.execute("SELECT valor FROM meta WHERE clave = 'version'").fetchone()
    return int(fila[0]) if fila else 1


def _raiz(ws: WorkspaceRepository, version: int | None) -> Path:
    """Raíz de la versión: la del workspace si es la vigente, `versiones/vN/` si está guardada."""
    vigente = _vigente(ws)
    numero = vigente if version is None else version
    if not 1 <= numero <= vigente:
        raise ValueError(f"versión inexistente: v{numero} (vigente v{vigente})")
    return ws.raiz if numero == vigente else ws.raiz / "versiones" / f"v{numero}"


def _sello(ws: WorkspaceRepository, numero: int, vigente: int) -> dict[int, str]:
    """sha256 de los capítulos cerrados de una versión (spec 0007, `versiones.sello`)."""
    if numero == vigente:
        punto = ws.ultimo_checkpoint()
        return dict(punto.capitulos_sha256) if punto else {}
    ruta = ws.raiz / "versiones" / f"v{numero}" / "version.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))["capitulos_sha256"]
    return {int(c): sha for c, sha in datos.items()}


@servidor.tool(annotations=SOLO_LECTURA)
def list_novels() -> list[Novela]:
    """Las novelas del directorio de workspaces con su cursor, capítulos cerrados y versión."""
    lista = []
    for fila in _novelas():
        ws = _ws(fila.slug)
        punto = ws.ultimo_checkpoint()
        hechos = punto.capitulo if punto else 0
        lista.append(
            Novela(
                slug=fila.slug, cursor=fila.cursor, capitulos_hechos=hechos, version=_vigente(ws)
            )
        )
    return lista


@servidor.tool(annotations=SOLO_LECTURA)
def get_chapter(slug: Slug, capitulo: Capitulo, version: NumVersion | None = None) -> str:
    """Un capítulo, tal cual está en disco (frontmatter incluido), de la versión indicada."""
    ws = _ws(slug)
    ruta = _raiz(ws, version) / "capitulos" / f"{ws.nn(capitulo)}.md"
    if capitulo > ws.config().parametros_obra.num_capitulos or not ruta.is_file():
        raise ValueError(f"no existe el capítulo {capitulo}")
    return ruta.read_text(encoding="utf-8")


@servidor.tool(annotations=SOLO_LECTURA)
def list_versions(slug: Slug) -> list[VersionDeNovela]:
    """El historial de versiones y qué capítulos cambió cada una. Sin `versiones/`, una sola."""
    ws = _ws(slug)
    vigente = _vigente(ws)
    ruta = ws.raiz / "versiones" / "versiones.json"
    registro = json.loads(ruta.read_text(encoding="utf-8"))["versiones"] if ruta.is_file() else []
    punto = ws.ultimo_checkpoint()
    terminada = punto is not None and punto.capitulo >= ws.config().parametros_obra.num_capitulos
    sellos = {n: _sello(ws, n, vigente) for n in range(1, vigente + 1)}
    lista = []
    for n in range(1, vigente + 1):
        r = registro[n - 1] if n <= len(registro) else {}
        antes = sellos.get(n - 1)
        cambiados = (
            [] if antes is None else sorted(c for c, s in sellos[n].items() if antes.get(c) != s)
        )
        lista.append(
            VersionDeNovela(
                numero=n,
                cambio=r.get("cambio"),
                creada=r.get("creada"),
                estado="completa" if n < vigente or terminada else "en_curso",
                capitulos_cambiados=cambiados,
            )
        )
    return lista


@servidor.tool(annotations=SOLO_LECTURA)
def query_story_bible(
    slug: Slug,
    tipo: Literal["personajes", "lugares", "hechos", "cronologia"],
    filtro: Annotated[
        str | None, Field(max_length=200, description="subcadena, sin distinguir mayúsculas")
    ] = None,
) -> list[dict[str, Any]]:
    """La biblia de la historia desde la base de estado, en solo lectura: personajes con su
    estado y capítulos, lugares con sus capítulos, el libro de hechos o la línea temporal. Del
    canon solo sale lo que ya imprime el libro de regalo: nombres, alias y descripción."""
    ws = _ws(slug)
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        estado = estado_db.leer(conn)
        apariciones = estado_db.apariciones(conn, 999)
    capitulos: dict[str, list[int]] = {}
    for a in apariciones:
        capitulos.setdefault(a.entidad, []).append(a.capitulo)
    filas: list[dict[str, Any]]
    if tipo == "personajes":
        filas = []
        for id_, p in estado.personajes.items():
            ruta = ws.raiz / "canon" / "personajes" / f"{id_}.md"
            identidad = ws.leer_md(ruta, Personaje).identidad if ruta.is_file() else None
            filas.append(
                {
                    "id": id_,
                    "nombre": identidad.nombre if identidad else None,
                    "alias": identidad.alias if identidad else [],
                    **p.model_dump(mode="json"),
                    "capitulos": capitulos.get(id_, []),
                }
            )
    elif tipo == "lugares":
        mundo = ws.leer_md(ws.raiz / "canon" / "mundo.md", Mundo)
        filas = [
            {
                "id": e.id,
                "nombre": e.nombre,
                "descripcion": e.descripcion,
                "capitulos": capitulos.get(e.id, []),
            }
            for e in mundo.escenarios
        ]
    elif tipo == "hechos":
        filas = [h.model_dump(mode="json") for h in estado.libro_de_hechos]
    else:
        filas = [e.model_dump(mode="json") for e in estado.linea_temporal]
    if filtro:
        filas = [f for f in filas if filtro.lower() in json.dumps(f, ensure_ascii=False).lower()]
    return filas


@servidor.tool(annotations=SOLO_LECTURA)
def download_novel(slug: Slug) -> File:
    """La novela en PDF (el libro de regalo de la spec 0006) con los capítulos cerrados, como
    recurso embebido en base64. Se construye en memoria: no escribe en el workspace."""
    # Import diferido: la API no carga slices/ (test_api_no_importa_slices). De export solo se
    # usan lectores y `pdf.construir`, que devuelve bytes; test_ninguna_tool_escribe lo cubre.
    from novela.slices.export import cmd as export
    from novela.slices.export import pdf

    ws = _ws(slug)
    punto = ws.ultimo_checkpoint()
    if punto is None:
        raise ValueError("no hay capítulos cerrados que exportar")
    capitulos = [export._capitulo(ws, c) for c in range(1, punto.capitulo + 1)]
    libro = pdf.Libro(
        titulo=slug,
        idioma=ws.config().parametros_obra.idioma,
        dedicatoria=None,
        capitulos=tuple(pdf.Capitulo(n, t, c) for n, (t, c) in enumerate(capitulos, 1)),
        ficha=export._ficha(ws, punto.capitulo),
        creado=export._creado(ws, punto),
    )
    return File(data=pdf.construir(libro), format="pdf", name=f"{slug}.pdf")
