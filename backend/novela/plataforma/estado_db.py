"""Conexión a `estado/estado.db`: PRAGMAs, transacciones y apertura en solo lectura.

La API abre con `mode=ro`, así que no tiene ruta de escritura ni por descuido. Toda escritura va
dentro de `BEGIN IMMEDIATE … COMMIT`: un corte a mitad deja la base en el punto anterior.
`estado.db-wal` es efímero y no se respalda.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

from novela.dominio.base import SCHEMA_VERSION


class EstadoIlegible(Exception):
    """La base no existe, no es de esta versión o no se puede abrir. Salida 4."""


def _conectar(ruta: Path, modo: str) -> sqlite3.Connection:
    uri = f"{ruta.resolve().as_uri()}?mode={modo}"
    try:
        conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    except sqlite3.OperationalError as exc:
        raise EstadoIlegible(f"{ruta}: {exc}") from exc
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def crear(ruta: Path) -> None:
    """DDL y `meta.schema_version`. El cursor y las métricas iniciales los escribe quien crea."""
    conn = _conectar(ruta, "rwc")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(resources.files(__package__).joinpath("esquema.sql").read_text())
        conn.execute("INSERT INTO meta VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
    finally:
        conn.close()


@contextmanager
def abrir(ruta: Path, *, solo_lectura: bool = False) -> Iterator[sqlite3.Connection]:
    conn = _conectar(ruta, "ro" if solo_lectura else "rw")
    try:
        # Solo la apertura es «estado ilegible»; un trigger que aborta dentro del with no lo es.
        try:
            fila = conn.execute("SELECT valor FROM meta WHERE clave = 'schema_version'").fetchone()
        except sqlite3.DatabaseError as exc:
            raise EstadoIlegible(f"{ruta}: {exc}") from exc
        if fila is None or fila[0] != SCHEMA_VERSION:
            version = None if fila is None else fila[0]
            raise EstadoIlegible(f"{ruta}: schema_version {version}, se esperaba {SCHEMA_VERSION}")
        yield conn
    finally:
        conn.close()


@contextmanager
def transaccion(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
