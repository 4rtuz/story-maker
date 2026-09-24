import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from novela.dominio.estado import EventoCronologia
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.formal import cronologia
from tests.fixtures import fabrica
from tests.fixtures.fabrica import ELENA, TOMAS


def test_aplicar_delta_registra_la_cronologia(tmp_path: Path) -> None:
    raiz = fabrica.construir(tmp_path, "demo-partida", fabrica.PARTIDA, cerrados=3)
    with estado_db.abrir(WorkspaceRepository(raiz).estado_db, solo_lectura=True) as conn:
        eventos = cronologia.leer(conn)
    assert [e.id for e in eventos] == ["evt-01-1", "evt-02-1", "evt-03-1", "evt-03-2"]
    assert eventos[0].edades == {ELENA: 40}
    assert eventos[0].duracion_min == 40
    assert eventos[1].excluye == [TOMAS]
    assert eventos[1].tras == ["evt-01-1"]
    assert eventos[2].personajes == [ELENA, TOMAS]


def test_base_sin_tablas_de_cronologia(tmp_path: Path) -> None:
    """Una base anterior: leer no falla, devuelve vacío."""
    conn = sqlite3.connect(tmp_path / "vieja.db")
    assert cronologia.leer(conn) == []


def test_edad_de_quien_no_esta_se_rechaza() -> None:
    """Una edad de alguien ausente no tendría fila donde guardarse: se rechaza en el borde."""
    with pytest.raises(ValidationError, match="edades"):
        EventoCronologia(id="evt-01-1", momento=0, lugar="esc-faro", edades={ELENA: 40})
