import sqlite3
from importlib import resources
from pathlib import Path

import pytest

from novela.plataforma import estado_db

FILAS = {
    "libro_de_hechos": "INSERT INTO libro_de_hechos VALUES ('hec-001', 't', 1, 'c')",
    "conocimiento": "INSERT INTO conocimiento VALUES ('per-a', 'hec-001', 1, NULL)",
    "linea_temporal": "INSERT INTO linea_temporal VALUES ('esc-01-1', 1, 'dia 1', 30, NULL)",
    "conocimiento_lector": "INSERT INTO conocimiento_lector VALUES ('hec-001', 1, NULL)",
    "tension_real": "INSERT INTO tension_real VALUES (1, 5)",
    "apariciones": "INSERT INTO apariciones VALUES ('per-a', 'personaje', 1)",
}


@pytest.fixture
def base() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        resources.files("novela.plataforma").joinpath("esquema.sql").read_text("utf-8")
    )
    for insert in FILAS.values():
        conn.execute(insert)
    return conn


@pytest.mark.parametrize("operacion", ["UPDATE {t} SET rowid = rowid", "DELETE FROM {t}"])
@pytest.mark.parametrize("tabla", sorted(FILAS))
def test_append_only_por_trigger(base: sqlite3.Connection, tabla: str, operacion: str) -> None:
    """CA-02, y CA-18 de la 0006: doce casos, seis tablas por dos operaciones, con el mensaje."""
    with pytest.raises(sqlite3.IntegrityError, match=f"{tabla} es append-only"):
        base.execute(operacion.format(t=tabla))
    assert base.execute(f"SELECT count(*) FROM {tabla}").fetchone() == (1,)  # noqa: S608


def test_usos_append_only(tmp_path: Path) -> None:
    """CA-01 (RF-01): se inserta, no se actualiza ni se borra, y el motor rechaza una `via`
    desconocida y un capítulo que no es entero."""
    ruta = tmp_path / "estado.db"
    estado_db.crear(ruta)
    with estado_db.abrir(ruta) as conn:
        conn.execute("INSERT INTO usos_de_hecho VALUES ('hec-001', 1, 'origen')")
        for orden in ("UPDATE usos_de_hecho SET capitulo = 2", "DELETE FROM usos_de_hecho"):
            with pytest.raises(sqlite3.IntegrityError, match="usos_de_hecho es append-only"):
                conn.execute(orden)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute("INSERT INTO usos_de_hecho VALUES ('hec-001', 2, 'menciona')")
        with pytest.raises(sqlite3.IntegrityError, match="cannot store TEXT"):
            conn.execute("INSERT INTO usos_de_hecho VALUES ('hec-001', 'dos', 'cita')")
        assert conn.execute("SELECT * FROM usos_de_hecho").fetchall() == [("hec-001", 1, "origen")]


@pytest.mark.parametrize(
    "insert",
    [
        "INSERT INTO apariciones VALUES ('obj-001', 'objeto', 2)",  # CHECK
        "INSERT INTO apariciones VALUES ('per-b', 'personaje', 'uno')",  # STRICT
        "INSERT INTO apariciones VALUES (NULL, 'personaje', 2)",  # NOT NULL
    ],
)
def test_apariciones_append_only(base: sqlite3.Connection, insert: str) -> None:
    """CA-18, VAL-19: la tabla rechaza filas basura, además de UPDATE y DELETE."""
    with pytest.raises(sqlite3.IntegrityError):
        base.execute(insert)
    indice = "SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?"
    assert base.execute(indice, ("apariciones_por_capitulo",)).fetchall() == [
        ("apariciones_por_capitulo",)
    ]
