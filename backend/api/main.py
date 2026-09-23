"""API de solo lectura para el panel (architecture.md §11.1).

No hay verbo de escritura: mutar una novela es trabajo del orquestador por el CLI. Los modelos de
respuesta son los de `novela/dominio/`, y `estado.db` se abre con `mode=ro`.

    cd backend && uv run uvicorn api.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import novelas

app = FastAPI(title="novela", summary="Estado, capítulos y manifiestos, en solo lectura")
# El dev server de Vite.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET"])
app.include_router(novelas.router)
