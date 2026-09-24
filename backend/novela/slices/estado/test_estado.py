import json
import sqlite3
import time
from collections.abc import Callable

from typer.testing import CliRunner

from novela.cli import app
from novela.plataforma.workspace import WorkspaceRepository

Novelas = Callable[[str], WorkspaceRepository]


def test_breve_acotado(novelas: Novelas) -> None:
    """CA-05: ≤ 12 líneas, con cursor, hilos abiertos y palabras."""
    novelas("demo-24")
    resultado = CliRunner().invoke(app, ["estado", "demo-24", "--breve"])
    assert resultado.exit_code == 0, resultado.output
    lineas = resultado.stdout.splitlines()
    assert len(lineas) <= 12
    texto = resultado.stdout
    assert "capítulo 7 de 24" in texto and "fase registro" in texto
    assert "hilos abiertos (3): hil-001, hil-002, hil-003" in texto
    assert "palabras: 2118" in texto
    assert "cerrados: 7/24" in texto


def test_breve_rendimiento(novelas: Novelas) -> None:
    """CA-31: < 500 ms sobre el workspace de 24 capítulos, sin contar el arranque del intérprete."""
    novelas("demo-terminado")
    runner = CliRunner()
    runner.invoke(app, ["estado", "demo-terminado", "--breve"])  # calienta imports
    inicio = time.perf_counter()
    resultado = runner.invoke(app, ["estado", "demo-terminado", "--breve"])
    assert resultado.exit_code == 0
    assert time.perf_counter() - inicio < 0.5


def test_workspace_inexistente_sale_4(novelas: Novelas) -> None:
    novelas("demo-24")
    assert CliRunner().invoke(app, ["estado", "no-existe", "--breve"]).exit_code == 4


def test_pendiente_codigos(novelas: Novelas) -> None:
    """CA-07: 0 con capítulos restantes, 1 con la novela terminada, y stdout vacío en los dos."""
    novelas("demo-24")
    novelas("demo-terminado")
    runner = CliRunner()
    quedan = runner.invoke(app, ["pendiente", "demo-24"])
    terminada = runner.invoke(app, ["pendiente", "demo-terminado"])
    assert (quedan.exit_code, quedan.stdout) == (0, "")
    assert (terminada.exit_code, terminada.stdout) == (1, "")


def test_estado_sin_tabla_usos(novelas: Novelas) -> None:
    """CA-07 (RF-07): una base anterior a la spec 0007 responde lo mismo que una con la tabla."""
    ws = novelas("demo-24")
    runner = CliRunner()
    con_tabla = runner.invoke(app, ["estado", "demo-24", "--json"])
    with sqlite3.connect(ws.raiz / "estado" / "estado.db") as conn:
        conn.execute("DROP TABLE usos_de_hecho")
    sin_tabla = runner.invoke(app, ["estado", "demo-24", "--json"])
    assert (con_tabla.exit_code, sin_tabla.exit_code) == (0, 0), sin_tabla.output
    assert json.loads(sin_tabla.stdout) == json.loads(con_tabla.stdout)
