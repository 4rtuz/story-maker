"""`GET /novelas`, el estado de una novela y sus manifiestos."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from novela.dominio.estado import Estado
from novela.dominio.ids import SLUG_PATRON
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository


def _workspace(slug: Annotated[str, Path(pattern=SLUG_PATRON)]) -> WorkspaceRepository:
    """El slug llega validado por el patrón antes de que esto construya ninguna ruta: es la única
    superficie de inyección real del sistema (validators.md §3.2). Misma regex que el CLI."""
    ws = WorkspaceRepository.resolver(slug)
    if not ws.existe():
        raise HTTPException(404, f"no existe la novela {slug}")
    return ws


Workspace = Annotated[WorkspaceRepository, Depends(_workspace)]
# `:path` porque Starlette decodifica `%2F` antes de enrutar: con `{slug}` a secas, `..%2F..%2Fetc`
# no casaría ninguna ruta y el 404 dependería del enrutado, no de la validación.
SLUG = "/{slug:path}"

router = APIRouter(prefix="/novelas", tags=["novelas"])


@router.get(SLUG + "/estado")
def estado(ws: Workspace) -> Estado:
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        return estado_db.leer(conn)
