"""`GET /novelas`, el estado de una novela y sus manifiestos."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.responses import FileResponse

from novela.dominio.artefactos import Checkpoint, Manifest, TramoDeLog
from novela.dominio.config import Config
from novela.dominio.estado import CursorDeNovela, Estado
from novela.dominio.ids import RUN_ID_PATRON, SLUG_PATRON
from novela.dominio.metricas import InformeDeCostes
from novela.dominio.plan import Escaleta
from novela.plataforma import estado_db
from novela.plataforma.workspace import (
    FueraDelLog,
    SlugInvalido,
    WorkspaceRepository,
    raiz_de_novelas,
)


def _workspace(slug: Annotated[str, Path(pattern=SLUG_PATRON)]) -> WorkspaceRepository:
    """El slug llega validado por el patrón antes de que esto construya ninguna ruta: es la única
    superficie de inyección real del sistema (validators.md §3.2). Misma regex que el CLI."""
    ws = WorkspaceRepository.resolver(slug)
    if not ws.existe():
        raise HTTPException(404, f"no existe la novela {slug}")
    return ws


Workspace = Annotated[WorkspaceRepository, Depends(_workspace)]
RunIdPath = Annotated[str, Path(pattern=RUN_ID_PATRON)]
# `:path` porque Starlette decodifica `%2F` antes de enrutar: con `{slug}` a secas, `..%2F..%2Fetc`
# no casaría ninguna ruta y el 404 dependería del enrutado, no de la validación.
SLUG = "/{slug:path}"

router = APIRouter(prefix="/novelas", tags=["novelas"])


def _leer(ws: WorkspaceRepository) -> Estado:
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        return estado_db.leer(conn)


@router.get("")
def novelas() -> list[CursorDeNovela]:
    raiz = raiz_de_novelas()
    lista = []
    for directorio in sorted(raiz.iterdir()) if raiz.is_dir() else []:
        try:
            ws = WorkspaceRepository.resolver(directorio.name)
        except SlugInvalido:
            continue  # no lo creó `novela nueva`
        if ws.existe():
            lista.append(CursorDeNovela(slug=ws.slug, cursor=_leer(ws).cursor))
    return lista


@router.get(SLUG + "/estado")
def estado(ws: Workspace) -> Estado:
    return _leer(ws)


# spec 0004: lo que el panel necesita y no está en el estado, servido con su modelo tal cual (D4).
@router.get(SLUG + "/config")
def config(ws: Workspace) -> Config:
    return ws.config()


@router.get(SLUG + "/escaleta", response_model=Escaleta)
def escaleta(ws: Workspace) -> Response:
    # Ya serializada: FastAPI revalidaría el modelo sin el contexto de num_capitulos y el
    # validador de la obra lo rechazaría con un 500 (VER-1).
    return Response(ws.escaleta().model_dump_json(), media_type="application/json")


@router.get(SLUG + "/checkpoint")
def checkpoint(ws: Workspace) -> Checkpoint | None:
    return ws.ultimo_checkpoint()


@router.get(SLUG + "/runs")
def runs(ws: Workspace) -> list[Manifest]:
    return ws.manifiestos()


@router.get(SLUG + "/runs/{run_id}/log")
def log(ws: Workspace, run_id: RunIdPath, desde: Annotated[int, Query(ge=0)] = 0) -> TramoDeLog:
    """El tramo de `harness.log` desde el byte `desde`, que el panel encadena con `hasta` (D48).
    Un run sin log todavía responde un tramo vacío: solo existe entre el manifiesto y la primera
    línea."""
    if not (ws.raiz / "runs" / run_id).is_dir():
        raise HTTPException(404, f"no existe el run {run_id}")
    try:
        return ws.tramo_de_log(run_id, desde)
    except FueraDelLog as exc:
        raise HTTPException(416, str(exc)) from exc


@router.get(SLUG + "/runs/{run_id}")
def manifiesto(ws: Workspace, run_id: RunIdPath) -> Manifest:
    ruta = ws.raiz / "runs" / run_id / "manifest.json"
    if not ruta.is_file():
        raise HTTPException(404, f"no existe el run {run_id}")
    return ws.leer_json(ruta, Manifest)


# spec 0015 §5.4: lo que `novela portada` y `novela costes --guardar` dejaron en el workspace.
@router.get(
    SLUG + "/portada",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}, "description": "La portada, sin texto"}},
)
def portada(ws: Workspace) -> FileResponse:
    ruta = ws.raiz / "portada.jpg"
    if not ruta.is_file():
        raise HTTPException(404, f"{ws.slug} no tiene portada")
    return FileResponse(ruta, media_type="image/jpeg")


@router.get(SLUG + "/metricas")
def metricas(ws: Workspace) -> InformeDeCostes:
    ruta = ws.raiz / "metricas.json"
    if not ruta.is_file():
        raise HTTPException(404, f"{ws.slug} no tiene métricas guardadas")
    return ws.leer_json(ruta, InformeDeCostes)
