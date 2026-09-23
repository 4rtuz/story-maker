"""API de solo lectura (spec 0001 §5.5): cinco GET, ningún verbo de escritura."""

import builtins
import io
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app

BACKEND = Path(__file__).resolve().parents[1]  # código y .venv
cliente = TestClient(app)


def test_app_arranca() -> None:
    assert cliente.get("/docs").status_code == 200


def test_path_traversal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CA-26: el slug se valida antes de construir ninguna ruta. «No toca el disco» se comprueba,
    no se supone: toda apertura, stat o conexión fuera del código durante la petición queda
    registrada. FastAPI lee el fuente del endpoint para el mensaje de error; eso no es disco."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    tocado: list[Any] = []

    def espia(original: Callable[..., Any]) -> Callable[..., Any]:
        def registrar(*args: Any, **kwargs: Any) -> Any:
            tocado.append(args[0] if args else kwargs)
            return original(*args, **kwargs)

        return registrar

    for modulo, nombre in (
        (builtins, "open"),
        (io, "open"),
        (os, "stat"),
        (os, "scandir"),
        (sqlite3, "connect"),
    ):
        monkeypatch.setattr(modulo, nombre, espia(getattr(modulo, nombre)))
    respuesta = cliente.get("/novelas/..%2F..%2Fetc/estado")
    monkeypatch.undo()
    assert [p for p in tocado if not str(p).startswith(str(BACKEND))] == []
    assert respuesta.status_code == 422
