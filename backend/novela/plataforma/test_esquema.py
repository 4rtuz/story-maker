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
}


@pytest.fixture
def base() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(resources.files("novela.plataforma").joinpath("esquema.sql").read_text())
    for insert in FILAS.values():
        conn.execute(insert)
    return conn


@pytest.mark.parametrize("operacion", ["UPDATE {t} SET rowid = rowid", "DELETE FROM {t}"])
@pytest.mark.parametrize("tabla", sorted(FILAS))
def test_append_only_por_trigger(base: sqlite3.Connection, tabla: str, operacion: str) -> None:
    """CA-02: diez casos, cinco tablas por dos operaciones, cada uno con el mensaje del trigger."""
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
