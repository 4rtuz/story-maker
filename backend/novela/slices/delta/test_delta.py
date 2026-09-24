import json
import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import Result

from novela.dominio.artefactos import Memoria
from novela.dominio.estado import Delta, Estado
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository, huella
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


@pytest.mark.parametrize(
    ("uso", "causa"),
    [
        ({"hecho": "hec-002", "cita": "los escalones del faro por 8 vez"}, None),
        ({"hecho": "hec-002", "cita": "Elena nunca subió al faro."}, "no es literal"),
        ({"hecho": "hec-900", "cita": "los escalones del faro por 8 vez"}, "hecho inexistente"),
    ],
)
def test_hechos_usados_cita(novelas: Novelas, uso: dict[str, str], causa: str | None) -> None:
    """CA-02 (RF-02): un uso con cita literal de un hecho que existe aplica; una cita que no está
    en el cuerpo o un hecho que no existe salen con 1 y la base intacta."""
    ws, antes = _preparado(novelas)
    ruta = ws.raiz / "estado" / "deltas" / "08.json"
    delta = json.loads(ruta.read_text(encoding="utf-8"))
    ruta.write_text(json.dumps(delta | {"hechos_usados": [uso]}), encoding="utf-8")
    resultado = _aplicar(ws)
    if causa is None:
        assert resultado.exit_code == 0, resultado.output
        return
    assert resultado.exit_code == 1
    assert causa in resultado.output
    assert (ws.raiz / "estado" / "estado.db").read_bytes() == antes


def test_aplicar_registra_usos(novelas: Novelas) -> None:
    """CA-03 (RF-03) y la primera mitad de CA-06: demo-cambio construido con el CLI deja los usos
    de origen, conocimiento, lector y cita de cada hecho, y hec-002 lo usan 2, 4 y 6."""
    ws = novelas("demo-cambio")
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        usos = {
            h: [(u.capitulo, u.via) for u in estado_db.usos(conn, h)]
            for h in ("hec-002", "hec-102")
        }
        assert estado_db.capitulos_que_usan(conn, "hec-002") == [2, 4, 6]
    assert usos == {
        "hec-002": [(2, "origen"), (2, "conocimiento"), (2, "lector"), (4, "cita"), (6, "cita")],
        "hec-102": [(2, "origen"), (5, "cita")],
    }


def test_migracion_usos(novelas: Novelas) -> None:
    """CA-05 (RF-05): una base sin la tabla la gana al aplicar el siguiente delta, con sus
    triggers, y solo con los usos de ese capítulo: no hay backfill (spec 0007, D5)."""
    ws, _ = _preparado(novelas)
    with sqlite3.connect(ws.estado_db) as conn:
        conn.execute("DROP TABLE usos_de_hecho")
    assert _aplicar(ws).exit_code == 0
    with estado_db.abrir(ws.estado_db) as conn:
        capitulos = conn.execute("SELECT DISTINCT capitulo FROM usos_de_hecho").fetchall()
        with pytest.raises(sqlite3.IntegrityError, match="usos_de_hecho es append-only"):
            conn.execute("DELETE FROM usos_de_hecho")
    assert capitulos == [(8,)]


def test_renderiza_memoria(novelas: Novelas) -> None:
    """CA-19: memoria/resumenes/NN.md trae las tres granularidades del delta, con la escena por
    id; lo escribe aplicar-delta, no el cronista, y se reconstruye desde el delta sin cuota."""
    ws, _ = _preparado(novelas)
    ruta = ws.raiz / "memoria" / "resumenes" / "08.md"
    ruta.unlink(missing_ok=True)
    assert _aplicar(ws).exit_code == 0
    memoria = ws.leer_md(ruta, Memoria)
    resumen = Delta.model_validate_json(
        (ws.raiz / "estado" / "deltas" / "08.json").read_bytes()
    ).resumen
    assert (memoria.linea, memoria.parrafo, memoria.escena) == (
        resumen.linea,
        resumen.parrafo,
        resumen.escena,
    )
    assert set(memoria.escena) == {"esc-08-1", "esc-08-2"}


def _huellas(ws: WorkspaceRepository) -> tuple[bytes, str]:
    return ws.estado_db.read_bytes(), huella(ws.raiz / "memoria")


def _tabla(ws: WorkspaceRepository) -> list[tuple[str]]:
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        consulta = "SELECT name FROM sqlite_master WHERE name LIKE 'apariciones%' ORDER BY name"
        return conn.execute(consulta).fetchall()


def _copia(ws: WorkspaceRepository, slug: str) -> WorkspaceRepository:
    shutil.copytree(ws.raiz, ws.raiz.parent / slug)
    return WorkspaceRepository(ws.raiz.parent / slug)


@pytest.mark.parametrize(
    "romper",
    [
        lambda ruta: ruta.unlink(),
        lambda ruta: ruta.write_text(
            ruta.read_text(encoding="utf-8").replace("escenas:", "escenas_no:", 1), encoding="utf-8"
        ),
        lambda ruta: ruta.write_text("---\ncapitulo: [8\n---\n", encoding="utf-8"),
    ],
    ids=["sin-ficha", "sin-escenas", "yaml-roto"],
)
def test_aplicar_sin_ficha(novelas: Novelas, romper: Callable[[Path], object]) -> None:
    """CA-21 (RF-21), VAL-23: sin ficha de plan válida sale con 4 y no toca la base ni memoria/."""
    ws, _ = _preparado(novelas)
    romper(ws.raiz / "plan" / "capitulos" / "08.md")
    antes = _huellas(ws)
    resultado = _aplicar(ws)
    assert resultado.exit_code == 4, resultado.output
    assert "08.md" in resultado.output
    assert _huellas(ws) == antes


def test_migracion_apariciones(novelas: Novelas) -> None:
    """CA-22 (RF-22), VAL-24 (a): una base sin la tabla la gana al aplicar, con sus triggers e
    índice y filas solo del capítulo aplicado; el resto del estado queda igual que con la tabla."""
    con, _ = _preparado(novelas)
    sin = _copia(con, "demo-24-sin")
    fabrica.quitar_apariciones(sin.raiz)
    for ws in (con, sin):
        assert _aplicar(ws).exit_code == 0
    assert _tabla(sin) == _tabla(con) and len(_tabla(sin)) == 4
    with estado_db.abrir(sin.estado_db, solo_lectura=True) as a:
        with estado_db.abrir(con.estado_db, solo_lectura=True) as b:
            assert estado_db.leer(a) == estado_db.leer(b)
            migradas = estado_db.apariciones(a, 99)
            assert migradas and migradas == [
                f for f in estado_db.apariciones(b, 99) if f.capitulo == 8
            ]


def test_delta_rechazado_no_migra(novelas: Novelas) -> None:
    """VAL-24 (b), VER-9: un delta que rechaza `violaciones` deja la base sin la tabla."""
    ws, _ = _preparado(novelas)
    fabrica.quitar_apariciones(ws.raiz)
    ruta = ws.raiz / "estado" / "deltas" / "08.json"
    delta = json.loads(ruta.read_text(encoding="utf-8"))
    otra = {"id": "hec-003", "texto": "El faro nunca se apagó.", "capitulo": 8}
    delta["libro_de_hechos"].append(otra | {"cita": fabrica.frase_de_hecho(8)})
    ruta.write_text(json.dumps(delta), encoding="utf-8")
    assert _aplicar(ws).exit_code == 1
    assert _tabla(ws) == []


def test_fallo_al_registrar_no_deja_nada(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """VER-8: el registro va en la transacción del estado: si falla, ni estado ni memoria."""
    ws, _ = _preparado(novelas)
    antes = _huellas(ws)

    def falla(conn: sqlite3.Connection, filas: object) -> None:
        raise RuntimeError("corte al registrar")

    monkeypatch.setattr(estado_db, "registrar_apariciones", falla)
    assert _aplicar(ws).exit_code != 0
    assert _huellas(ws) == antes


def test_aplicar_registra_apariciones(novelas: Novelas) -> None:
    """CA-19 (RF-19), VAL-20: los 15 pares de demo-regalo, 5 por capítulo."""
    ws = novelas("demo-regalo")
    todos = {fabrica.ELENA, fabrica.TOMAS, fabrica.INES, fabrica.FARO, fabrica.PUERTO}
    segundo = todos - {fabrica.INES} | {fabrica.ARCHIVO}
    esperadas = {1: todos, 2: segundo, 3: todos}
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        filas = estado_db.apariciones(conn, 3)
    assert {(f.entidad, f.capitulo) for f in filas} == {
        (e, c) for c, entidades in esperadas.items() for e in entidades
    }
    assert len(filas) == 15
