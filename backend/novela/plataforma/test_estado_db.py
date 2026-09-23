import sqlite3
from pathlib import Path

import pytest

from novela.plataforma import estado_db


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
