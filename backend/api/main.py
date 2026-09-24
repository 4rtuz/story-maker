"""API del panel (architecture.md §11.1).

`/novelas` es de solo lectura: la base de cada novela se abre con `mode=ro`. `/lanzamientos` lanza
el CLI (`novela producir`), que es quien escribe; la API no toca ningún workspace. Los modelos de
respuesta son los de `novela/dominio/`.

    cd backend && NOVELAS_DIR=../novelas uv run uvicorn api.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import capitulos, lanzamientos, novelas
from novela.plataforma.estado_db import EstadoIlegible
from novela.plataforma.workspace import WorkspaceInvalido

app = FastAPI(title="novela", summary="Estado, capítulos y manifiestos; lanzamiento de novelas")
# El dev server de Vite. POST solo lo usa /lanzamientos, que además tiene sus propias guardas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(lanzamientos.ORIGENES),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(novelas.router)
app.include_router(capitulos.router)
app.include_router(lanzamientos.router)


@app.exception_handler(WorkspaceInvalido)
@app.exception_handler(EstadoIlegible)
def _ilegible(_: Request, exc: Exception) -> JSONResponse:
    """Lo que en el CLI es la salida 4: falta un fichero o no valida contra su modelo."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})
