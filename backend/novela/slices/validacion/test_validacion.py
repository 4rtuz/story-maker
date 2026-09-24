import json
import statistics
import time
from collections.abc import Callable
from pathlib import Path

import jsonschema
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio import frontmatter
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.validacion import gates
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


def test_validar_nombres(novelas: Novelas) -> None:
    """CA-07 (integración): el pov escrito con una tilde de más hace salir con 1, con
    nombre_mal_escrito en el informe."""
    ws = novelas("demo-24")
    meta, cuerpo = frontmatter.partir(fabrica.capitulo(fabrica.DEMO, 8))
    fabrica.escribir(ws.raiz, {"capitulos/08.md": frontmatter.unir(meta, "Éléna. " + cuerpo)})
    assert _validar(ws, 8).exit_code == 1
    hallazgos = _informe(ws, 8)["hallazgos"]
    assert [(h["tipo"], h["referencia"]) for h in hallazgos] == [  # type: ignore[attr-defined]
        ("nombre_mal_escrito", fabrica.ELENA)
    ]


def test_rendimiento_nombres() -> None:
    """RNF-01: mediana de 20 ejecuciones de gates.nombres, 5.000 palabras y 50 formas, ≤ 100 ms."""
    formas = [
        gates.FormaCanonica(f"per-p{i}", f"Nombre{chr(97 + i % 26)}{i // 26} Apellido", "x")
        for i in range(50)
    ]
    cuerpo = "\n".join("Elena miró el faro y Nombrea0 calló sin razón alguna." for _ in range(500))
    assert len(cuerpo.split()) >= 5000
    tiempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        gates.nombres(cuerpo, formas)
        tiempos.append(time.perf_counter() - inicio)
    assert statistics.median(tiempos) <= 0.1


def test_personaje_invalido_sale_con_4(novelas: Novelas) -> None:
    """Spec 0009 §9: validar lee las fichas enteras, así que una inválida es un workspace roto."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    fabrica.escribir(ws.raiz, {"canon/personajes/per-rota.md": "---\nidentidad: {}\n---\n"})
    assert _validar(ws, 8).exit_code == 4


def test_origen_hook_en_el_log(novelas: Novelas) -> None:
    """CA-07 (RF-06, VAL-13): con --origen hook solo cambia la orden de la línea; el código, la
    salida y el informe son los mismos, con el capítulo válido y con el inválido."""
    ws = novelas("demo-24")
    log = ws.raiz / "runs" / RUN["NOVELA_RUN_ID"] / "harness.log"
    informe = ws.raiz / "qa" / "08-validacion.json"
    meta, cuerpo = frontmatter.partir(fabrica.capitulo(fabrica.DEMO, 8))
    invalido = frontmatter.unir(meta | {"pistas_plantadas": []}, cuerpo)
    for texto, codigo in ((fabrica.capitulo(fabrica.DEMO, 8), 0), (invalido, 1)):
        fabrica.escribir(ws.raiz, {"capitulos/08.md": texto})
        vistos = []
        for origen in ([], ["--origen", "hook"]):
            r = fabrica.cli(
                ws.raiz.parent, "validar", ws.slug, "8", *origen, run=RUN["NOVELA_RUN_ID"]
            )
            vistos.append((r.exit_code, r.stdout, informe.read_bytes()))
        assert vistos[0] == vistos[1] and vistos[0][0] == codigo
        orquestador, hook = log.read_text(encoding="utf-8").splitlines()[-2:]
        assert f"validar 08 -> {codigo}" in orquestador
        assert f"validar-hook 08 -> {codigo}" in hook and "validar 08 -> " not in hook


def test_origen_invalido(novelas: Novelas) -> None:
    """CA-08 (RF-07, VAL-14, VER-1): un origen fuera de la lista sale con 2 sin tocar qa/ ni runs/
    y sin dejar el lock tomado."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})

    def foto() -> dict[str, bytes]:
        return {
            str(p.relative_to(ws.raiz)): p.read_bytes()
            for d in ("qa", "runs")
            for p in (ws.raiz / d).rglob("*")
            if p.is_file()
        }

    antes = foto()
    for valor in ("otro", "HOOK", ""):
        r = fabrica.cli(
            ws.raiz.parent, "validar", ws.slug, "8", "--origen", valor, run=RUN["NOVELA_RUN_ID"]
        )
        assert r.exit_code == 2, (valor, r.output)
    assert foto() == antes
    with ws.bloquear():
        pass
