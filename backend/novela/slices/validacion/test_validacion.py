import json
import time
from collections.abc import Callable
from pathlib import Path

import jsonschema
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio import frontmatter
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]
ESQUEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "schemas" / "qa-informe.schema.json").read_text("utf-8")
)
RUN = {"NOVELA_RUN_ID": "r-20260923-1000"}


def _validar(ws: WorkspaceRepository, cap: int) -> Result:
    entorno = {"NOVELAS_DIR": str(ws.raiz.parent)} | RUN
    return CliRunner().invoke(app, ["validar", ws.slug, str(cap)], env=entorno)


def _informe(ws: WorkspaceRepository, cap: int) -> dict[str, object]:
    informe: dict[str, object] = json.loads(
        (ws.raiz / "qa" / f"{cap:02d}-validacion.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(informe, ESQUEMA)
    return informe


def test_informe_valida(novelas: Novelas) -> None:
    """CA-16: tras un fallo, qa/NN-validacion.json valida contra qa-informe.schema.json."""
    ws = novelas("demo-24")
    meta, cuerpo = frontmatter.partir(fabrica.capitulo(fabrica.DEMO, 8))
    meta["pistas_plantadas"] = []  # el plan manda plantar pis-004
    fabrica.escribir(ws.raiz, {"capitulos/08.md": frontmatter.unir(meta, cuerpo)})
    resultado = _validar(ws, 8)
    assert resultado.exit_code == 1
    informe = _informe(ws, 8)
    assert informe["veredicto"] == "rechazado"
    assert [h["referencia"] for h in informe["hallazgos"]] == ["pis-004"]  # type: ignore[attr-defined]


def test_informe_al_pasar(novelas: Novelas) -> None:
    """CA-35: con el capítulo válido sale con 0 y deja el informe igual, aprobado, sin hallazgos
    y con el sha256 del fichero que validó."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    resultado = _validar(ws, 8)
    assert resultado.exit_code == 0, resultado.output
    informe = _informe(ws, 8)
    assert (informe["veredicto"], informe["hallazgos"]) == ("aprobado", [])
    assert informe["capitulo_sha256"] == fabrica.sha256(ws.raiz / "capitulos" / "08.md")
    log = (ws.raiz / "runs" / RUN["NOVELA_RUN_ID"] / "harness.log").read_text(encoding="utf-8")
    assert "validar 08 -> 0" in log


def test_sesion_en_el_log(novelas: Novelas) -> None:
    """CA-12 (RF-21, F-44): con NOVELA_SESSION_ID válido la línea lleva sesion=<uuid> y conserva la
    subcadena `validar NN -> <código>` que cuenta el procedimiento. Un valor que no es UUID no se
    escribe y no cambia el código de salida: no acaba en una ruta."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    log = ws.raiz / "runs" / RUN["NOVELA_RUN_ID"] / "harness.log"
    uuid = "0f8fad5b-d9cb-469f-a165-70867728950e"

    def ultima(**sesion: str) -> tuple[int, str]:
        entorno = {"NOVELAS_DIR": str(ws.raiz.parent)} | RUN | sesion
        codigo = fabrica.cli(ws.raiz.parent, "validar", ws.slug, "8", run="", entorno=entorno)
        return codigo.exit_code, log.read_text(encoding="utf-8").splitlines()[-1]

    codigo, linea = ultima(NOVELA_SESSION_ID=uuid)
    assert codigo == 0
    assert f"sesion={uuid}" in linea and "validar 08 -> 0" in linea
    codigo, linea = ultima(NOVELA_SESSION_ID="no-es-un-uuid")
    assert codigo == ultima()[0]
    assert "sesion=" not in linea and "validar 08 -> 0" in linea


def test_capitulo_ausente_es_hallazgo_no_crash(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    assert _validar(ws, 8).exit_code == 1
    informe = _informe(ws, 8)
    assert informe["capitulo_sha256"] is None
    assert [h["tipo"] for h in informe["hallazgos"]] == ["frontmatter_invalido"]  # type: ignore[attr-defined]


def test_rendimiento(novelas: Novelas) -> None:
    """CA-27 (RNF-01): validar un capítulo de 4.000 palabras en menos de 2 s."""
    ws = novelas("demo-24")
    meta, cuerpo = frontmatter.partir(fabrica.capitulo(fabrica.DEMO, 8))
    largo = cuerpo + ("El mar siguió en su sitio. " * 700)
    assert len(largo.split()) >= 4000
    fabrica.escribir(ws.raiz, {"capitulos/08.md": frontmatter.unir(meta, largo)})
    inicio = time.perf_counter()
    resultado = _validar(ws, 8)
    assert time.perf_counter() - inicio < 2
    assert resultado.exit_code == 1  # fuera de rango para esta novela, que es de 300 palabras


def test_regeneracion(novelas: Novelas) -> None:
    """CA-27 (RF-31): con un cambio en curso, el 2 regenerado con el contrato de la versión 1
    pasa; sin una pista plantada, con un hilo abierto de más o un cerrado de menos, 1 con
    regeneracion_altera_contrato en qa/02-validacion.json."""
    ws = novelas("demo-cambio")
    assert fabrica.pedir_cambio(ws.raiz.parent, ws.slug).exit_code == 0
    fabrica.reaplicar(ws.raiz, 1)
    meta, cuerpo = frontmatter.partir(fabrica.capitulo_regenerado(fabrica.CAMBIO, 2))
    assert (meta["pistas_plantadas"], meta["hilos_abiertos"], meta["hilos_cerrados"]) == (
        ["pis-001"],
        ["hil-002"],
        ["hil-003"],
    )
    for retoque, codigo in (
        ({}, 0),
        ({"pistas_plantadas": []}, 1),
        ({"hilos_abiertos": ["hil-002", "hil-009"]}, 1),
        ({"hilos_cerrados": []}, 1),
    ):
        fabrica.escribir(ws.raiz, {"capitulos/02.md": frontmatter.unir(meta | retoque, cuerpo)})
        resultado = fabrica.v2(ws.raiz, "validar", 2)
        assert resultado.exit_code == codigo, (retoque, resultado.output)
        hallazgos = _informe(ws, 2)["hallazgos"]
        assert isinstance(hallazgos, list)
        tipos = {h["tipo"] for h in hallazgos}
        assert ("regeneracion_altera_contrato" in tipos) == bool(codigo), retoque
