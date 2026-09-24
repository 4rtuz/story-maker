import sqlite3
import statistics
import time
from pathlib import Path

import pytest
from hypothesis import given

from novela.dominio.estado import Aparicion, Estado, Hecho, UsoDeHecho
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


@given(estrategias.estados)
def test_leer_filtrado_por_personajes(estado: Estado) -> None:
    conn = _en_memoria()
    with estado_db.transaccion(conn):
        estado_db.guardar(conn, estado)
    elegidos = set(list(estado.personajes)[:1])
    filtrado = estado_db.leer(conn, personajes=elegidos)
    assert set(filtrado.personajes) == elegidos
    assert set(filtrado.conocimiento) <= elegidos
    assert all(r.de in elegidos or r.a in elegidos for r in filtrado.relaciones)
    assert all(o.poseedor is None or o.poseedor in elegidos for o in filtrado.objetos)
    assert filtrado.libro_de_hechos == estado.libro_de_hechos
    assert filtrado.hilos == estado.hilos


def _quitar_usos(ruta: Path) -> None:
    """Una base anterior a la spec 0007: sin la tabla, que se lleva su índice y sus triggers."""
    with sqlite3.connect(ruta) as conn:
        conn.execute("DROP TABLE usos_de_hecho")


def test_capitulos_que_usan(tmp_path: Path) -> None:
    """CA-06 (RF-06, RNF-01): capítulos distintos en orden, en solo lectura; < 50 ms sobre la base
    sintética de 99 capítulos, 300 hechos y 20 usos por hecho; sin tabla, EstadoIlegible."""
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    usos = [
        UsoDeHecho(hecho="hec-002", capitulo=c, via=v)
        for c, v in ((6, "cita"), (2, "origen"), (2, "lector"), (4, "cita"), (2, "conocimiento"))
    ]
    with estado_db.abrir(ruta) as conn, estado_db.transaccion(conn):
        estado_db.registrar_usos(conn, usos)
        estado_db.registrar_usos(conn, usos)  # repetir no duplica ni falla
    with estado_db.abrir(ruta, solo_lectura=True) as conn:
        assert estado_db.capitulos_que_usan(conn, "hec-002") == [2, 4, 6]
        assert estado_db.capitulos_que_usan(conn, "hec-900") == []
        assert sorted(estado_db.usos(conn, "hec-002"), key=str) == sorted(usos, key=str)

    sintetica = tmp_path / "sintetica.db"
    estado_db.crear(sintetica)
    vias = ("origen", "conocimiento", "lector", "cita")
    with estado_db.abrir(sintetica) as conn, estado_db.transaccion(conn):
        conn.executemany(
            "INSERT INTO usos_de_hecho VALUES (?, ?, ?)",
            (
                (f"hec-{h:03d}", (h + 5 * i) % 99 + 1, vias[i % 4])
                for h in range(1, 301)
                for i in range(20)
            ),
        )
    with estado_db.abrir(sintetica, solo_lectura=True) as conn:
        assert conn.execute("SELECT count(*) FROM usos_de_hecho").fetchone() == (6000,)
        inicio = time.perf_counter()
        capitulos = estado_db.capitulos_que_usan(conn, "hec-150")
        assert time.perf_counter() - inicio < 0.05
        assert capitulos == sorted({(150 + 5 * i) % 99 + 1 for i in range(20)})

    _quitar_usos(ruta)
    for solo_lectura in (True, False):
        with estado_db.abrir(ruta, solo_lectura=solo_lectura) as conn:
            with pytest.raises(estado_db.EstadoIlegible, match="usos_de_hecho"):
                estado_db.usos(conn, "hec-002")
            with pytest.raises(estado_db.EstadoIlegible, match="usos_de_hecho"):
                estado_db.capitulos_que_usan(conn, "hec-002")


def test_asegurar_usos_dentro_de_la_transaccion(tmp_path: Path) -> None:
    """RF-05, la mitad de plataforma: sobre una base sin la tabla, la crea con sus triggers sin
    cerrar la transacción de quien llama; sobre una que ya la tiene, no hace nada."""
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    _quitar_usos(ruta)
    with estado_db.abrir(ruta) as conn:
        with pytest.raises(RuntimeError):
            with estado_db.transaccion(conn):
                estado_db.asegurar_usos(conn)
                assert conn.in_transaction
                raise RuntimeError("corte")
        with pytest.raises(estado_db.EstadoIlegible):  # el corte se llevó también el DDL
            estado_db.usos(conn, "hec-001")
        for _ in range(2):
            with estado_db.transaccion(conn):
                estado_db.asegurar_usos(conn)
                assert conn.in_transaction
        estado_db.registrar_usos(conn, [UsoDeHecho(hecho="hec-001", capitulo=1, via="origen")])
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM usos_de_hecho")


def _apariciones_en_master(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    consulta = "SELECT type, name, sql FROM sqlite_master WHERE name LIKE 'apariciones%' ORDER BY 2"
    return conn.execute(consulta).fetchall()


def test_consulta_apariciones(tmp_path: Path) -> None:
    """CA-24, VAL-26, VAL-45: filtro por capítulo, orden por entidad y capítulo, en solo lectura,
    y 99 × 50 filas en menos de 50 ms."""
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    filas = [
        Aparicion(
            entidad=f"per-{e:02d}" if e % 2 else f"esc-e{e:02d}",
            tipo="personaje" if e % 2 else "escenario",
            capitulo=c,
        )
        for c in range(99, 0, -1)
        for e in range(50)
    ]
    with estado_db.abrir(ruta) as conn, estado_db.transaccion(conn):
        estado_db.registrar_apariciones(conn, filas)
        estado_db.registrar_apariciones(conn, filas[:10])  # INSERT OR IGNORE: no duplica
    with estado_db.abrir(ruta, solo_lectura=True) as conn:
        dos = estado_db.apariciones(conn, 2)
        esperadas = sorted(
            (f for f in filas if f.capitulo <= 2), key=lambda f: (f.entidad, f.capitulo)
        )
        assert dos == esperadas and len(dos) == 100
        assert estado_db.apariciones(conn, 0) == []
        tiempos = []
        for _ in range(5):
            inicio = time.perf_counter()
            todas = estado_db.apariciones(conn, 99)
            tiempos.append(time.perf_counter() - inicio)
        assert len(todas) == 4950
        assert statistics.median(tiempos) < 0.05


def test_apariciones_sin_tabla_es_estado_ilegible(tmp_path: Path) -> None:
    """VER-6: sin la tabla, EstadoIlegible (salida 4) y no OperationalError."""
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with sqlite3.connect(ruta) as conn:
        conn.execute("DROP TABLE apariciones")
    with estado_db.abrir(ruta, solo_lectura=True) as conn:
        with pytest.raises(estado_db.EstadoIlegible, match="apariciones"):
            estado_db.apariciones(conn, 3)


def test_asegurar_apariciones_dentro_de_la_transaccion(tmp_path: Path) -> None:
    """VER-3 y VER-4: sin COMMIT implícito (un ROLLBACK la deshace), idempotente, y la base migrada
    queda igual que la creada."""
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with estado_db.abrir(ruta) as conn:
        creada = _apariciones_en_master(conn)
        assert len(creada) == 4
        conn.execute("DROP TABLE apariciones")
        with pytest.raises(RuntimeError):
            with estado_db.transaccion(conn):
                estado_db.asegurar_apariciones(conn)
                raise RuntimeError("corte")
        assert _apariciones_en_master(conn) == []
        with estado_db.transaccion(conn):
            estado_db.asegurar_apariciones(conn)
            estado_db.asegurar_apariciones(conn)
        assert _apariciones_en_master(conn) == creada
