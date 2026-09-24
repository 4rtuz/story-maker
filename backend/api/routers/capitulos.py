"""El índice de capítulos y cada capítulo, tal cual están en disco."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import PlainTextResponse

from api.routers.novelas import SLUG, Workspace
from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.libro import Libro
from novela.plataforma.libro import libro as construir_libro

router = APIRouter(prefix="/novelas", tags=["capitulos"])


class Markdown(PlainTextResponse):
    media_type = "text/markdown"


@router.get(SLUG + "/capitulos")
def indice(ws: Workspace) -> list[FrontmatterCapitulo]:
    capitulos = sorted((ws.raiz / "capitulos").glob("*.md"))
    return [ws.leer_md(ruta, FrontmatterCapitulo) for ruta in capitulos]


@router.get(SLUG + "/capitulos/{n}", response_class=Markdown)
def capitulo(ws: Workspace, n: Annotated[int, Path(ge=1, le=999)]) -> str:
    total = ws.config().parametros_obra.num_capitulos
    ruta = ws.raiz / "capitulos" / f"{ws.nn(n)}.md" if n <= total else None
    if ruta is None or not ruta.is_file():
        raise HTTPException(404, f"no existe el capítulo {n}")
    return ruta.read_text(encoding="utf-8")


@router.get(SLUG + "/libro")
def libro(ws: Workspace) -> Libro:
    """Portada, índice y ficha de la lectura web; lo mismo que el PDF (docs/lectura-web.md)."""
    return construir_libro(ws)
