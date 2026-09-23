"""API de solo lectura para el panel (architecture.md §11.1).

No hay verbo de escritura: mutar una novela es trabajo del orquestador por el CLI. Los modelos de
respuesta son los de `novela/dominio/`, y `estado.db` se abre con `mode=ro`.

    cd backend && uv run uvicorn api.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import capitulos, novelas
from novela.plataforma.estado_db import EstadoIlegible
from novela.plataforma.workspace import WorkspaceInvalido

app = FastAPI(title="novela", summary="Estado, capítulos y manifiestos, en solo lectura")
# El dev server de Vite.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET"])
app.include_router(novelas.router)
app.include_router(capitulos.router)


@app.exception_handler(WorkspaceInvalido)
@app.exception_handler(EstadoIlegible)
def _ilegible(_: Request, exc: Exception) -> JSONResponse:
    """Lo que en el CLI es la salida 4: falta un fichero o no valida contra su modelo."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})
