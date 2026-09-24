"""Conexión a `estado/estado.db`: PRAGMAs, transacciones y apertura en solo lectura.

La API abre con `mode=ro`, así que no tiene ruta de escritura ni por descuido. Toda escritura va
dentro de `BEGIN IMMEDIATE … COMMIT`: un corte a mitad deja la base en el punto anterior.
`estado.db-wal` es efímero y no se respalda.
"""

import sqlite3
from collections.abc import Collection, Iterable, Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Any

from novela.dominio.base import SCHEMA_VERSION, ColeccionAppendOnly
from novela.dominio.estado import Aparicion, Estado, UsoDeHecho


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


def _esquema() -> str:
    return resources.files(__package__).joinpath("esquema.sql").read_text("utf-8")


def inicializar(conn: sqlite3.Connection) -> None:
    """DDL y `meta.schema_version` sobre una conexión vacía. El estado inicial lo guarda quien
    crea la base."""
    conn.executescript(_esquema())
    conn.execute("INSERT INTO meta VALUES ('schema_version', ?)", (SCHEMA_VERSION,))


def asegurar_apariciones(conn: sqlite3.Connection) -> None:
    """Crea `apariciones` en una base anterior a la spec 0006, desde el mismo bloque de
    `esquema.sql`, y no hace nada si ya está. Sentencia a sentencia y no con `executescript`, que
    haría COMMIT de la transacción de quien llama."""
    bloque = _esquema().split("-- apariciones: inicio")[1].split("-- apariciones: fin")[0]
    sentencia = ""
    for linea in bloque.splitlines(keepends=True):  # los triggers llevan `;` dentro de BEGIN … END
        sentencia += linea
        if sqlite3.complete_statement(sentencia):
            conn.execute(sentencia)
            sentencia = ""


def registrar_apariciones(conn: sqlite3.Connection, filas: Iterable[Aparicion]) -> None:
    """Va dentro de la transacción de quien llama. Repetir un capítulo no duplica ni borra."""
    conn.executemany(
        "INSERT OR IGNORE INTO apariciones VALUES (?, ?, ?)",
        [(f.entidad, f.tipo, f.capitulo) for f in filas],
    )


def apariciones(conn: sqlite3.Connection, hasta: int) -> list[Aparicion]:
    """Las de los capítulos 1..`hasta`, por entidad y capítulo. Vale en solo lectura."""
    try:
        filas = conn.execute(
            "SELECT entidad, tipo, capitulo FROM apariciones WHERE capitulo <= ? "
            "ORDER BY entidad, capitulo",
            (hasta,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise EstadoIlegible(f"estado.db sin la tabla apariciones: {exc}") from exc
    return [Aparicion(entidad=e, tipo=t, capitulo=c) for e, t, c in filas]


def crear(ruta: Path, version: int | None = None, cambio: str | None = None) -> None:
    """`version` y `cambio` van a `meta` solo si se pasan: los escribe `novela cambio` al crear
    la base de una versión nueva (spec 0007, RF-16 y RF-19)."""
    conn = _conectar(ruta, "rwc")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        inicializar(conn)
        for clave, valor in (("version", version), ("cambio", cambio)):
            if valor is not None:
                conn.execute("INSERT INTO meta VALUES (?, ?)", (clave, str(valor)))
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


_MARCA_USOS = "-- usos_de_hecho:"


def asegurar_usos(conn: sqlite3.Connection) -> None:
    """RF-05: crea `usos_de_hecho`, su índice y sus triggers si faltan. Va dentro de la
    transacción de quien llama, así que ejecuta sentencia a sentencia: `executescript` haría un
    COMMIT implícito."""
    ddl = resources.files(__package__).joinpath("esquema.sql").read_text(encoding="utf-8")
    sentencia = ""
    for linea in ddl[ddl.index(_MARCA_USOS) :].splitlines(keepends=True):
        sentencia += linea
        if sqlite3.complete_statement(sentencia):
            conn.execute(sentencia)
            sentencia = ""


def registrar_usos(conn: sqlite3.Connection, usos: Iterable[UsoDeHecho]) -> None:
    """Append-only e idempotente: un uso ya registrado se ignora, nunca se reescribe (RF-04)."""
    conn.executemany(
        "INSERT OR IGNORE INTO usos_de_hecho VALUES (?, ?, ?)",
        ((u.hecho, u.capitulo, u.via) for u in usos),
    )


def _de_usos(conn: sqlite3.Connection, sql: str, hecho: str) -> list[Any]:
    try:
        return conn.execute(sql, (hecho,)).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        raise EstadoIlegible(f"estado.db sin tabla usos_de_hecho: {exc}") from exc


def usos(conn: sqlite3.Connection, hecho: str) -> list[UsoDeHecho]:
    """Por capítulo y, dentro de cada uno, en el orden en que se registraron."""
    filas = _de_usos(
        conn,
        "SELECT hecho, capitulo, via FROM usos_de_hecho WHERE hecho = ? ORDER BY capitulo, rowid",
        hecho,
    )
    return [UsoDeHecho(hecho=h, capitulo=c, via=v) for h, c, v in filas]


def capitulos_que_usan(conn: sqlite3.Connection, hecho: str) -> list[int]:
    sql = "SELECT DISTINCT capitulo FROM usos_de_hecho WHERE hecho = ? ORDER BY capitulo"
    return [c for (c,) in _de_usos(conn, sql, hecho)]


class HistoriaReescrita(ValueError):
    """Una colección append-only del estado nuevo no empieza por la del estado guardado."""


_APPEND_ONLY = ("linea_temporal", "libro_de_hechos", "conocimiento_lector")
_MUTABLES = ("relaciones", "objetos", "hilos")


def _filas(
    conn: sqlite3.Connection, tabla: str, donde: str = "", valores: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    # Todo en orden de inserción: las append-only lo exigen y las mutables se reescriben enteras
    # en el orden de la lista, así que leer devuelve lo que se guardó.
    filtro = f" WHERE {donde}" if donde else ""
    cursor = conn.execute(f"SELECT * FROM {tabla}{filtro} ORDER BY rowid", valores)  # noqa: S608
    columnas = [c[0] for c in cursor.description]
    return [dict(zip(columnas, fila, strict=True)) for fila in cursor]


def leer(conn: sqlite3.Connection, personajes: Collection[str] | None = None) -> Estado:
    """La vista serializada de architecture.md §7.1, desde las tablas.

    Con `personajes`, solo lo que toca a esos personajes en las colecciones que se indexan por
    entidad: el largo plazo se consulta, no se carga (architecture.md §6.4)."""
    cursores, metricas_ = _filas(conn, "cursor"), _filas(conn, "metricas")
    if len(cursores) != 1 or len(metricas_) != 1:
        raise EstadoIlegible("estado.db sin cursor o sin métricas")
    cursor, metricas = cursores[0], metricas_[0]
    ids = tuple(personajes) if personajes is not None else ()
    marcas = ", ".join("?" * len(ids))

    def de(tabla: str, donde: str = "", repetir: int = 1) -> list[dict[str, Any]]:
        if personajes is None or not donde:
            return _filas(conn, tabla)
        return _filas(conn, tabla, donde.format(marcas), ids * repetir)

    conocimiento: dict[str, list[dict[str, Any]]] = {}
    for fila in de("conocimiento", "personaje IN ({})"):
        conocimiento.setdefault(fila.pop("personaje"), []).append(fila)
    datos: dict[str, Any] = {
        "cursor": {k: v for k, v in cursor.items() if k != "id"},
        "personajes": {f.pop("id"): f for f in de("personajes", "id IN ({})")},
        "conocimiento": conocimiento,
        "relaciones": de("relaciones", "de IN ({0}) OR a IN ({0})", repetir=2),
        "objetos": de("objetos", "poseedor IS NULL OR poseedor IN ({})"),
        "pistas": {f.pop("id"): f for f in de("pistas")},
        "tension_real": [f["valor"] for f in de("tension_real")],
        "metricas": {k: v for k, v in metricas.items() if k != "id"},
    }
    datos |= {tabla: de(tabla) for tabla in (*_APPEND_ONLY, "hilos")}
    return Estado.model_validate(datos)


def _insertar(conn: sqlite3.Connection, tabla: str, filas: Iterable[dict[str, Any]]) -> None:
    for fila in filas:
        columnas = ", ".join(fila)
        marcas = ", ".join("?" * len(fila))
        conn.execute(f"INSERT INTO {tabla} ({columnas}) VALUES ({marcas})", tuple(fila.values()))  # noqa: S608


def _cola[T](tabla: str, antes: tuple[T, ...], despues: tuple[T, ...]) -> tuple[T, ...]:
    if despues[: len(antes)] != antes:
        raise HistoriaReescrita(f"{tabla} es append-only: el estado nuevo reescribe entradas")
    return despues[len(antes) :]


def guardar(conn: sqlite3.Connection, nuevo: Estado) -> None:
    """Escribe `nuevo` sobre lo que haya. Las mutables y derivadas se reescriben; de las
    append-only solo se insertan las entradas nuevas, y si el estado nuevo no empieza por el
    guardado se aborta: los triggers impedirían el UPDATE igualmente. Va dentro de la
    transacción de quien llama."""
    hay_cursor = conn.execute("SELECT 1 FROM cursor").fetchone() is not None
    antes = leer(conn) if hay_cursor else Estado(cursor=nuevo.cursor)
    for tabla in _APPEND_ONLY:
        viejas, nuevas = getattr(antes, tabla).entradas, getattr(nuevo, tabla).entradas
        _insertar(conn, tabla, (e.model_dump() for e in _cola(tabla, viejas, nuevas)))
    for personaje, entradas in nuevo.conocimiento.items():
        viejas = antes.conocimiento.get(personaje, ColeccionAppendOnly()).entradas
        cola = _cola("conocimiento", viejas, entradas.entradas)
        _insertar(conn, "conocimiento", ({"personaje": personaje} | e.model_dump() for e in cola))
    if set(antes.conocimiento) - set(nuevo.conocimiento):
        raise HistoriaReescrita("conocimiento es append-only: el estado nuevo pierde personajes")
    cola_tension = _cola("tension_real", antes.tension_real.entradas, nuevo.tension_real.entradas)
    primero = len(antes.tension_real) + 1
    _insertar(
        conn,
        "tension_real",
        ({"capitulo": primero + i, "valor": v} for i, v in enumerate(cola_tension)),
    )

    for tabla in ("cursor", "metricas", "personajes", "pistas", *_MUTABLES):
        conn.execute(f"DELETE FROM {tabla}")  # noqa: S608
    _insertar(conn, "cursor", [{"id": 1} | nuevo.cursor.model_dump()])
    _insertar(conn, "metricas", [{"id": 1} | nuevo.metricas.model_dump()])
    _insertar(conn, "personajes", ({"id": k} | v.model_dump() for k, v in nuevo.personajes.items()))
    _insertar(conn, "pistas", ({"id": k} | v.model_dump() for k, v in nuevo.pistas.items()))
    for tabla in _MUTABLES:
        _insertar(conn, tabla, (e.model_dump() for e in getattr(nuevo, tabla)))
