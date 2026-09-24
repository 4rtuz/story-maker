"""Listas de palabras prohibidas y log de auditoría del guardrail, en la base de la novela
(docs/guardrails.md).

Leer no escribe: `novela validar` sobre un capítulo limpio deja la base intacta, como antes del
guardrail. Solo escriben `nueva` (la siembra), `prohibidas añadir` y una coincidencia (su fila de
auditoría). Una base anterior al guardrail recibe las tablas en su primera escritura.
"""

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib import resources

from novela.dominio.prohibidas import NIVELES, Coincidencia, Nivel, Termino, clave
from novela.plataforma import estado_db
from novela.plataforma.workspace import CONFIG_DIR, WorkspaceRepository

GLOBALES = CONFIG_DIR / "prohibidas-globales.txt"


def _globales() -> list[str]:
    lineas = GLOBALES.read_text(encoding="utf-8").splitlines()
    return [t.strip() for t in lineas if t.strip() and not t.startswith("#")]


def preparar(conn: sqlite3.Connection, cliente: Iterable[str] = ()) -> None:
    """Crea las tablas si faltan y siembra el nivel global y el del cliente. Idempotente. Va en
    la transacción de quien llama, sentencia a sentencia: `executescript` haría COMMIT."""
    ddl = resources.files(__package__).joinpath("esquema.sql").read_text("utf-8")
    bloque = ddl.split("-- policy: inicio")[1].split("-- policy: fin")[0]
    sentencia = ""
    for linea in bloque.splitlines(keepends=True):
        sentencia += linea
        if sqlite3.complete_statement(sentencia):
            conn.execute(sentencia)
            sentencia = ""
    anadir(conn, _globales(), "global")
    anadir(conn, cliente, "cliente")


def anadir(conn: sqlite3.Connection, terminos: Iterable[str], nivel: Nivel) -> None:
    filas = [(t.strip(), nivel) for t in terminos if clave(t)]
    conn.executemany("INSERT OR IGNORE INTO prohibidas VALUES (?, ?)", filas)


def _unicos(terminos: Iterable[Termino]) -> tuple[Termino, ...]:
    """Por nivel y término; uno que ya está en un nivel anterior no se repite en el siguiente."""
    vistos: dict[tuple[str, ...], Termino] = {}
    for t in sorted(terminos, key=lambda t: (NIVELES.index(t.nivel), t.texto)):
        vistos.setdefault(clave(t.texto), t)
    return tuple(vistos.values())


def terminos(conn: sqlite3.Connection) -> tuple[Termino, ...]:
    filas = conn.execute("SELECT termino, nivel FROM prohibidas").fetchall()
    return _unicos(Termino(texto, nivel) for texto, nivel in filas)


def detalle(c: Coincidencia) -> str:
    return f"línea {c.linea}: «{c.forma}»"


def registrar(
    conn: sqlite3.Connection, origen: str, capitulo: int, coincidencias: Iterable[Coincidencia]
) -> None:
    momento = datetime.now(UTC).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT INTO auditoria_policy (momento, origen, decision, nivel, termino, capitulo, "
        "detalle) VALUES (?, ?, 'rechazar', ?, ?, ?, ?)",
        [
            (momento, origen, c.termino.nivel, c.termino.texto, capitulo, detalle(c))
            for c in coincidencias
        ],
    )


def _cliente(ws: WorkspaceRepository) -> list[str]:
    return ws.config().parametros_obra.restricciones_contenido  # los vetos del brief


def prohibidos(ws: WorkspaceRepository) -> tuple[Termino, ...]:
    """Los tres niveles, en solo lectura. Sin tablas, el global del fichero y el del cliente."""
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        try:
            return terminos(conn)
        except sqlite3.OperationalError:  # no such table: base anterior al guardrail
            pass
    return _unicos(
        [Termino(t, "global") for t in _globales()] + [Termino(t, "cliente") for t in _cliente(ws)]
    )


@contextmanager
def escribir(ws: WorkspaceRepository) -> Iterator[sqlite3.Connection]:
    with estado_db.abrir(ws.estado_db) as conn, estado_db.transaccion(conn):
        preparar(conn, _cliente(ws))
        yield conn


def auditar(
    ws: WorkspaceRepository, origen: str, capitulo: int, coincidencias: Iterable[Coincidencia]
) -> None:
    with escribir(ws) as conn:
        registrar(conn, origen, capitulo, coincidencias)
