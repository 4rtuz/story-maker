"""Versiones de la novela (spec 0007): edición vigente, cambio en curso e instantáneas."""

import sqlite3


def version_vigente(conn: sqlite3.Connection) -> int:
    """`meta.version`, o la 1 si la base no la tiene (RF-16)."""
    fila = conn.execute("SELECT valor FROM meta WHERE clave = 'version'").fetchone()
    return 1 if fila is None else int(fila[0])
