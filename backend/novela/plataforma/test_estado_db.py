import sqlite3
from pathlib import Path

import pytest
from hypothesis import given

from novela.dominio.estado import Estado, Hecho
from novela.plataforma import estado_db
from tests import estrategias


def test_conexion_ro_no_escribe(tmp_path: Path) -> None:
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with estado_db.abrir(ruta, solo_lectura=True) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO meta VALUES ('x', 'y')")


def test_abrir_no_crea_la_base(tmp_path: Path) -> None:
    for solo_lectura in (True, False):
        with pytest.raises(estado_db.EstadoIlegible):
            with estado_db.abrir(tmp_path / "no-existe.db", solo_lectura=solo_lectura):
                pass
    assert not (tmp_path / "no-existe.db").exists()


def test_transaccion_todo_o_nada(tmp_path: Path) -> None:
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with estado_db.abrir(ruta) as conn:
        with pytest.raises(RuntimeError):
            with estado_db.transaccion(conn):
                conn.execute("INSERT INTO meta VALUES ('x', 'y')")
                raise RuntimeError("corte")
        assert conn.execute("SELECT count(*) FROM meta WHERE clave = 'x'").fetchone() == (0,)
        assert conn.execute("PRAGMA journal_mode").fetchone() == ("wal",)


def test_version_distinta_es_estado_ilegible(tmp_path: Path) -> None:
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with sqlite3.connect(ruta) as conn:
        conn.execute("UPDATE meta SET valor = '0.9.0' WHERE clave = 'schema_version'")
    with pytest.raises(estado_db.EstadoIlegible, match="0.9.0"):
        with estado_db.abrir(ruta):
            pass


def test_trigger_dentro_del_with_no_es_estado_ilegible(tmp_path: Path) -> None:
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with estado_db.abrir(ruta) as conn:
            conn.execute("INSERT INTO tension_real VALUES (1, 5)")
            conn.execute("DELETE FROM tension_real")


def _en_memoria() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", isolation_level=None)
    estado_db.inicializar(conn)
    return conn


@given(estrategias.estados)
def test_guardar_y_leer_es_identidad(estado: Estado) -> None:
    conn = _en_memoria()
    with estado_db.transaccion(conn):
        estado_db.guardar(conn, estado)
    assert estado_db.leer(conn) == estado
    with estado_db.transaccion(conn):  # guardar lo mismo otra vez no añade nada
        estado_db.guardar(conn, estado)
    assert estado_db.leer(conn) == estado


@given(estrategias.estados, estrategias.hechos)
def test_guardar_no_reescribe_la_historia(estado: Estado, hecho: Hecho) -> None:
    if hecho.id in {h.id for h in estado.libro_de_hechos}:
        return
    ampliado = estado.model_copy(update={"libro_de_hechos": estado.libro_de_hechos.añadir(hecho)})
    conn = _en_memoria()
    with estado_db.transaccion(conn):
        estado_db.guardar(conn, ampliado)
    with pytest.raises(estado_db.HistoriaReescrita, match="libro_de_hechos"):
        with estado_db.transaccion(conn):
            estado_db.guardar(conn, estado)
    assert estado_db.leer(conn) == ampliado
