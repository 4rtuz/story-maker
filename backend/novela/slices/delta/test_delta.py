import json
import sqlite3
from collections.abc import Callable

import pytest
from pydantic import ValidationError
from typer.testing import Result

from novela.dominio.estado import Delta, Estado
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica


def test_delta_valida() -> None:
    """El delta del cronista trae las tres granularidades del resumen; sin ellas no es un delta."""
    ejemplo = fabrica.delta(fabrica.DEMO, 7)
    delta = Delta.model_validate(ejemplo)
    assert set(delta.resumen.escena) == {"esc-07-1", "esc-07-2"}
    assert Delta.model_validate_json(delta.model_dump_json()) == delta
    with pytest.raises(ValidationError, match="resumen"):
        Delta.model_validate({k: v for k, v in ejemplo.items() if k != "resumen"})
    for derivada in ("pistas", "metricas", "tension_real", "cursor"):
        with pytest.raises(ValidationError, match=derivada):
            Delta.model_validate({**ejemplo, derivada: {}})


Novelas = Callable[[str], WorkspaceRepository]


def _preparado(novelas: Novelas) -> tuple[WorkspaceRepository, bytes]:
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    return ws, (ws.raiz / "estado" / "estado.db").read_bytes()


def _aplicar(ws: WorkspaceRepository) -> Result:
    return fabrica.cli(ws.raiz.parent, "aplicar-delta", ws.slug, "8", run=fabrica.run_id(8))


def test_transaccion_todo_o_nada(novelas: Novelas) -> None:
    """CA-17: un delta que intenta reescribir una entrada de libro_de_hechos deja estado.db byte
    a byte idéntico: nada de la transacción queda, no solo el INSERT que falla."""
    ws, antes = _preparado(novelas)
    ruta = ws.raiz / "estado" / "deltas" / "08.json"
    delta = json.loads(ruta.read_text(encoding="utf-8"))
    otra = {"id": "hec-003", "texto": "El faro nunca se apagó.", "capitulo": 8}
    delta["libro_de_hechos"].append(otra | {"cita": fabrica.frase_de_hecho(8)})
    ruta.write_text(json.dumps(delta), encoding="utf-8")
    resultado = _aplicar(ws)
    assert resultado.exit_code == 1
    assert "hec-003" in resultado.output
    assert (ws.raiz / "estado" / "estado.db").read_bytes() == antes


def test_corte_dentro_de_la_transaccion(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-04, la mitad de la base: una excepción dentro de la transacción del delta deja
    estado.db en el punto anterior aunque ya se hubieran escrito filas."""
    ws, antes = _preparado(novelas)
    real = estado_db.guardar

    def a_medias(conn: sqlite3.Connection, nuevo: Estado) -> None:
        real(conn, nuevo)
        raise RuntimeError("corte de luz")

    monkeypatch.setattr(estado_db, "guardar", a_medias)
    assert _aplicar(ws).exit_code != 0
    assert (ws.raiz / "estado" / "estado.db").read_bytes() == antes


def test_aplica_y_es_idempotente_en_disco(novelas: Novelas) -> None:
    ws, _ = _preparado(novelas)
    assert _aplicar(ws).exit_code == 0
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        una = estado_db.leer(conn)
    assert una.cursor.capitulo == 8 and "hec-008" in {h.id for h in una.libro_de_hechos}
    assert _aplicar(ws).exit_code == 0  # reanudar repite el paso
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        assert estado_db.leer(conn) == una
