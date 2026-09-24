import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from typer.testing import Result

from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]
FECHA = r"\d{4}-\d{2}-\d{2}"


def _versiones(ws: WorkspaceRepository, *args: str) -> Result:
    return fabrica.cli(ws.raiz.parent, "versiones", ws.slug, *args, run="")


def test_listado(
    novelas: Novelas,
    regenerada: str,
    lock_ajeno: Callable[[Path], AbstractContextManager[None]],
) -> None:
    """CA-33 (RF-36) y la parte de CA-15: antes del cambio, solo la 1; tras la versión 2, dos
    líneas. Solo lectura: no toma el lock ni cambia la huella."""
    antes = novelas("demo-cambio")
    resultado = _versiones(antes)
    assert resultado.exit_code == 0, resultado.output
    assert resultado.output == "v1 · — · original · completa · —\n"

    ws = novelas(regenerada)
    huella = fabrica.huella(ws.raiz)
    with lock_ajeno(ws.lock):
        resultado = _versiones(ws)
    assert resultado.exit_code == 0, resultado.output
    lineas = resultado.output.splitlines()
    assert len(lineas) == 2, lineas
    assert re.fullmatch(rf"v1 · {FECHA} · original · completa · —", lineas[0])
    assert re.fullmatch(rf"v2 · {FECHA} · cam-001 · completa · 3 capítulos cambiados", lineas[1])
    assert fabrica.huella(ws.raiz) == huella


def test_novedades_cli(novelas: Novelas, regenerada: str) -> None:
    """CA-34 (RF-37): 02, 04 y 06 con su título y cam-001; --desde v1 es lo mismo; una versión
    que no es anterior a la vigente, o una novela sin versiones, salen con 2."""
    ws = novelas(regenerada)
    esperado = "".join(f"{n:02d} · La linterna, noche {n} · cam-001\n" for n in (2, 4, 6))
    for args in ((), ("--desde", "v1")):
        resultado = _versiones(ws, "--novedades", *args)
        assert resultado.exit_code == 0, resultado.output
        assert resultado.output == esperado
    assert _versiones(ws, "--novedades", "--desde", "v2").exit_code == 2
    assert _versiones(ws, "--desde", "v1").exit_code == 2
    assert _versiones(novelas("demo-cambio"), "--novedades").exit_code == 2


def test_verificar(novelas: Novelas, regenerada: str) -> None:
    """CA-20 (RF-22): la instantánea intacta sale con 0; con un byte cambiado en
    capitulos/03.md y un fichero de más en qa/, sale con 4 y los nombra."""
    ws = novelas(regenerada)
    resultado = _versiones(ws, "--verificar")
    assert resultado.exit_code == 0, resultado.output

    v1 = ws.raiz / "versiones" / "v1"
    capitulo = v1 / "capitulos" / "03.md"
    datos = bytearray(capitulo.read_bytes())
    datos[-2] ^= 1
    capitulo.write_bytes(bytes(datos))
    (v1 / "qa" / "sobra.json").write_text("{}", encoding="utf-8")
    resultado = _versiones(ws, "--verificar")
    assert resultado.exit_code == 4, resultado.output
    assert "v1/capitulos/03.md: distinto" in resultado.output
    assert "v1/qa/sobra.json: sobrante" in resultado.output


def test_diff(novelas: Novelas, regenerada: str) -> None:
    """CA-38 (RF-41): el 2 cambia en una línea `+` con la frase del hecho nuevo; el 1 no
    imprime diff. Una versión inexistente sale con 2."""
    ws = novelas(regenerada)
    resultado = _versiones(ws, "--diff", "v1", "actual", "--capitulo", "2")
    assert resultado.exit_code == 0, resultado.output
    assert f"+{fabrica.frase_regenerada(2)}" in resultado.output.splitlines()
    resultado = _versiones(ws, "--diff", "v1", "actual", "--capitulo", "1")
    assert (resultado.exit_code, resultado.output) == (0, "")
    assert _versiones(ws, "--diff", "v1", "actual").exit_code == 2
    assert _versiones(ws, "--diff", "v7", "actual", "--capitulo", "1").exit_code == 2
