from pathlib import Path

from novela.dominio.estado import EventoCronologia
from novela.slices.formal import lean
from tests.fixtures import fabrica
from tests.fixtures.fabrica import ELENA, INES, TOMAS

GOLDEN = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "golden" / "Cronologia.lean"
EDADES = {ELENA: 40, TOMAS: 40, INES: 40}


def _eventos(novela: fabrica.Novela) -> list[EventoCronologia]:
    return [EventoCronologia.model_validate(e) for _, e in novela.cronologia]


def test_generador_determinista() -> None:
    """El fichero de la novela de la partida, byte a byte: ids numéricos por orden, nombres en
    comentarios y un teorema por invariante."""
    texto = lean.generar("demo-partida", _eventos(fabrica.PARTIDA), EDADES)
    assert texto == GOLDEN.read_text(encoding="utf-8")
    assert texto == lean.generar("demo-partida", _eventos(fabrica.PARTIDA), dict(EDADES))


def test_lee_las_violaciones_de_la_salida() -> None:
    """Las líneas VIOLACION de Lean vuelven con los ids del workspace."""
    tabla = lean.Tabla.de(_eventos(fabrica.PARTIDA), EDADES)
    salida = "otra cosa\nVIOLACION|exclusion|2|2|1\nVIOLACION|ubicuidad|3|2|0\n"
    assert lean.violaciones(salida, tabla) == [
        lean.Violacion("exclusion", "evt-03-1", TOMAS, "evt-02-1"),
        lean.Violacion("ubicuidad", "evt-03-2", TOMAS, "evt-01-1"),
    ]
