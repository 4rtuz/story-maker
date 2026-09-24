"""Con Lean de verdad. Se salta si no hay `lean` ni en el PATH ni en ~/.elan/bin."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from novela.cli import app
from novela.dominio.estado import EventoCronologia
from novela.slices.formal import lean
from tests.fixtures import fabrica
from tests.fixtures.fabrica import ELENA, INES, TOMAS

pytestmark = pytest.mark.skipif(lean.buscar_lean() is None, reason="lean no está instalado")
EDADES = {ELENA: 40, TOMAS: 40, INES: 40}


def _compilar(tmp_path: Path, novela: fabrica.Novela) -> tuple[int, str]:
    eventos = [EventoCronologia.model_validate(e) for _, e in novela.cronologia]
    fichero = tmp_path / "Cronologia.lean"
    fichero.write_text(lean.generar("prueba", eventos, EDADES), encoding="utf-8")
    return lean.compilar(fichero)


def test_compila_la_cronologia_coherente(tmp_path: Path) -> None:
    codigo, salida = _compilar(tmp_path, fabrica.PARTIDA_COHERENTE)
    assert (codigo, salida.strip()) == (0, "")


def test_no_compila_la_incoherente(tmp_path: Path) -> None:
    codigo, salida = _compilar(tmp_path, fabrica.PARTIDA)
    assert codigo == 1
    assert "sinUbicuidad cronologia = true\nis false" in salida
    assert "respetaExclusiones cronologia = true\nis false" in salida
    assert "respetaOrden cronologia = true\nis false" not in salida


def test_edad_incoherente(tmp_path: Path) -> None:
    """Elena declara 42 años el día 1 y el canon le da 40: el invariante (b)."""
    malo = fabrica.Novela(
        1, (), (), cronologia=((1, {**fabrica.PARTIDA.cronologia[0][1], "edades": {ELENA: 42}}),)
    )
    codigo, salida = _compilar(tmp_path, malo)
    assert codigo == 1
    assert "VIOLACION|edad|0|0|42" in salida


def test_caso_real_solo_lo_ve_lean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """docs/formal/lean.md §5: validar y aplicar-delta pasan los tres capítulos (construir lo
    exige), auditar sale limpio, y verificar-lean encuentra a Tomás en dos sitios y de vuelta."""
    raiz = fabrica.construir(tmp_path, "demo-partida", fabrica.PARTIDA, cerrados=3)
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    auditar = CliRunner().invoke(app, ["auditar", "demo-partida"])
    assert auditar.exit_code == 0, auditar.output
    verificar = CliRunner().invoke(app, ["verificar-lean", "demo-partida"])
    assert verificar.exit_code == 1, verificar.output
    informe = json.loads((raiz / "qa" / "lean.json").read_text(encoding="utf-8"))
    assert {
        (v["invariante"], v["evento"], v["personaje"], v["otro"]) for v in informe["violaciones"]
    } == {
        ("ubicuidad", "evt-03-2", TOMAS, "evt-01-1"),
        ("exclusion", "evt-03-1", TOMAS, "evt-02-1"),
    }
