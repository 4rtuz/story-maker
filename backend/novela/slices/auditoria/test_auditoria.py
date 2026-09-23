import json
from collections.abc import Callable
from pathlib import Path

import jsonschema
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.plataforma.workspace import WorkspaceRepository

Novelas = Callable[[str], WorkspaceRepository]
ESQUEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "schemas" / "qa-informe.schema.json").read_text("utf-8")
)


def _auditar(ws: WorkspaceRepository) -> tuple[Result, set[tuple[str, str]]]:
    resultado = CliRunner().invoke(app, ["auditar", ws.slug])
    informe = json.loads((ws.raiz / "qa" / "auditoria.json").read_text(encoding="utf-8"))
    jsonschema.validate(informe, ESQUEMA)
    return resultado, {(h["tipo"], h["referencia"]) for h in informe["hallazgos"]}


def test_pista_huerfana(novelas: Novelas) -> None:
    """CA-23: una pista plantada en el 1 que nadie paga se reporta y auditar sale con 1."""
    resultado, hallazgos = _auditar(novelas("demo-huerfana"))
    assert resultado.exit_code == 1, resultado.output
    assert hallazgos == {("pista_huerfana", "pis-002")}


def test_novela_terminada_limpia(novelas: Novelas) -> None:
    """Control: sin él, el rojo de arriba no distingue un auditor que lo marca todo."""
    resultado, hallazgos = _auditar(novelas("demo-terminado"))
    assert (resultado.exit_code, hallazgos) == (0, set()), resultado.output


def test_a_mitad_reporta_lo_no_resuelto(novelas: Novelas) -> None:
    """Las otras tres comprobaciones. Con 7 de 24 cerrados: tres hilos abiertos, la pista falsa
    del 23 sin desmontar y rev-004, cuya pista se planta en el 8."""
    resultado, hallazgos = _auditar(novelas("demo-24"))
    assert resultado.exit_code == 1
    assert hallazgos == {
        ("hilo_sin_cerrar", "hil-001"),
        ("hilo_sin_cerrar", "hil-002"),
        ("hilo_sin_cerrar", "hil-003"),
        ("pista_falsa_sin_desmontar", "pfa-001"),
        ("revelacion_sin_pista", "rev-004"),
    }
