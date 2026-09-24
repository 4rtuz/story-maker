import json
import os
import re
import socket
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.artefactos import Checkpoint
from novela.plataforma import atomic, langfuse, run
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.checkpoint import cmd
from tests import estrategias
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]
sha = st.text(alphabet="0123456789abcdef", min_size=64, max_size=64)
checkpoints = st.builds(
    Checkpoint,
    capitulo=estrategias.capitulo,
    cursor=estrategias.cursores,
    run_id=st.from_regex(r"r-[0-9]{8}-[0-9]{4}", fullmatch=True),
    version_canon=sha,
    version_plan=sha,
    capitulos_sha256=st.dictionaries(estrategias.capitulo, sha, max_size=5),
)


@given(checkpoints)
def test_roundtrip_property(punto: Checkpoint) -> None:
    """CA-21, validators.md §3.6: restore(checkpoint(e)) == e, también pasando por disco."""
    assert cmd.restaurar(cmd.serializar(punto)) == punto
    with tempfile.TemporaryDirectory() as directorio:
        ruta = Path(directorio) / "latest.json"
        atomic.escribir(ruta, cmd.serializar(punto))
        assert WorkspaceRepository(Path(directorio)).leer_json(ruta, Checkpoint) == punto


def _cerrar_hasta_delta(novelas: Novelas) -> WorkspaceRepository:
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    assert _cli(ws, "aplicar-delta").exit_code == 0
    return ws


def _cli(ws: WorkspaceRepository, orden: str) -> Any:
    return fabrica.cli(ws.raiz.parent, orden, ws.slug, "8", run=fabrica.run_id(8))


def test_escribe_checkpoint_y_sello(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-20 y RF-35: NN.json y latest.json con cursor cerrado, run y el hash de cada capítulo
    cerrado. CA-22: sin TRACE_TO_LANGFUSE no se abre ninguna conexión y se escribe igual."""
    ws = _cerrar_hasta_delta(novelas)
    monkeypatch.delenv("TRACE_TO_LANGFUSE", raising=False)

    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("checkpoint abrió una conexión de red")

    monkeypatch.setattr(socket, "create_connection", prohibido)
    monkeypatch.setattr(urllib.request, "urlopen", prohibido)
    assert _cli(ws, "checkpoint").exit_code == 0
    punto = ws.ultimo_checkpoint()
    assert punto is not None and punto == ws.leer_json(
        ws.raiz / "checkpoints" / "08.json", Checkpoint
    )
    assert (punto.capitulo, punto.cursor.fase, punto.run_id) == (8, "cerrado", fabrica.run_id(8))
    assert punto.capitulos_sha256 == {
        n: fabrica.sha256(ws.raiz / "capitulos" / f"{n:02d}.md") for n in range(1, 9)
    }


def test_checkpoint_emite_un_score_por_validador(
    novelas: Novelas, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CA-22 y CA-17 de la 0009, sin brief: con "true", el sink manda los seis agregados y un
    vp_* por validador, con el id determinista y un comentario sin nada del capítulo."""
    ws = _cerrar_hasta_delta(novelas)
    cuerpos: list[dict[str, Any]] = []

    class Respuesta:
        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        cuerpos.append(json.loads(peticion.data))  # type: ignore[arg-type]
        return Respuesta()

    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("checkpoint abrió una conexión de red")

    monkeypatch.setattr(socket, "create_connection", prohibido)
    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    monkeypatch.setenv("TRACE_TO_LANGFUSE", "true")
    assert _cli(ws, "checkpoint").exit_code == 0
    assert sorted(c["name"] for c in cuerpos) == sorted(
        ["coherencia", "continuidad", "tension", "longitud", "fair_play", "estilo", *VP_SIN_BRIEF]
    )
    for cuerpo in cuerpos:
        if cuerpo["name"].startswith("vp_"):
            assert re.fullmatch(rf"demo-24-{fabrica.run_id(8)}-08-vp_[a-z]+", cuerpo["id"])
            assert cuerpo["comment"] == "demo-24, capítulo 8"


def test_langfuse_caido_no_impide_cerrar(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """validators.md §3.5: el trazado nunca es la razón por la que un capítulo no cierra."""
    ws = _cerrar_hasta_delta(novelas)

    def caido(*_: object, **__: object) -> None:
        raise urllib.error.URLError("sin red")

    llamadas: list[object] = []

    def caido_contado(*args: object, **kwargs: object) -> None:
        llamadas.append(args)
        caido()

    monkeypatch.setattr(urllib.request, "urlopen", caido_contado)
    monkeypatch.setenv("TRACE_TO_LANGFUSE", "true")
    assert _cli(ws, "checkpoint").exit_code == 0
    assert len(llamadas) == 1  # CA-18 (0009): con trece scores, un solo intento
    assert ws.ultimo_checkpoint() is not None
    log = (ws.raiz / "runs" / fabrica.run_id(8) / "harness.log").read_text(encoding="utf-8")
    assert "checkpoint 08 -> 0 · Langfuse no recibió" in log


def test_nunca_antes_de_aplicar_delta(novelas: Novelas) -> None:
    """validators.md §4.10: nunca checkpoint antes de aplicar-delta."""
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    assert _cli(ws, "checkpoint").exit_code == 1
    assert ws.ultimo_checkpoint() is not None and ws.ultimo_checkpoint().capitulo == 7  # type: ignore[union-attr]


# Nombres y valores por partes: juntos, el pre-commit anti-claves rechazaría este fichero.
_EMISOR = {
    "TRACE_TO_LANGFUSE": "true",
    **{
        f"LANGFUSE_{k}": v
        for k, v in {
            "PUBLIC_KEY": "publica-de-prueba",
            "SECRET_KEY": "secreta-de-prueba",
            "BASE_URL": "https://env.invalid",
        }.items()
    },
}


def _repo_con_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, texto: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text(texto, encoding="utf-8")
    monkeypatch.setattr(run, "RAIZ_REPO", repo)
    for clave in [*_EMISOR, "LANGFUSE_HOST"]:
        monkeypatch.delenv(clave, raising=False)


def _lineas(entorno: dict[str, str]) -> str:
    return "".join(f"{k}={v}\n" for k, v in entorno.items())


def test_claves_desde_env(
    novelas: Novelas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CA-20 (RF-32): con las claves solo en RAIZ_REPO/.env, el sink recibe los trece scores; una
    clave ajena no llega al sink, y os.environ no cambia."""
    ws = _cerrar_hasta_delta(novelas)
    _repo_con_env(tmp_path, monkeypatch, _lineas(_EMISOR) + "OTRA=x\n")
    vistos: list[dict[str, str]] = []
    real = langfuse.desde_entorno

    def espia(entorno: dict[str, str]) -> langfuse.ScoreSink:
        vistos.append(dict(entorno))
        return real(entorno)

    urls: list[str] = []

    class Respuesta:
        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        urls.append(peticion.full_url)
        return Respuesta()

    monkeypatch.setattr(langfuse, "desde_entorno", espia)
    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    antes = dict(os.environ)
    assert _cli(ws, "checkpoint").exit_code == 0
    assert dict(os.environ) == antes
    assert urls == ["https://env.invalid/api/public/scores"] * 13
    assert len(vistos) == 1 and "OTRA" not in vistos[0]


def test_manda_el_entorno_del_proceso(
    novelas: Novelas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CA-20: con TRACE_TO_LANGFUSE también en el entorno y otro valor, manda el entorno."""
    ws = _cerrar_hasta_delta(novelas)
    _repo_con_env(tmp_path, monkeypatch, _lineas(_EMISOR))
    monkeypatch.setenv("TRACE_TO_LANGFUSE", "false")

    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("checkpoint abrió una conexión de red")

    monkeypatch.setattr(urllib.request, "urlopen", prohibido)
    assert _cli(ws, "checkpoint").exit_code == 0


def test_env_ilegible_no_rompe_ni_se_imprime(
    novelas: Novelas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CA-20: un .env con líneas que no entiende no hace fallar a checkpoint, y ninguna línea
    suya llega a la salida."""
    ws = _cerrar_hasta_delta(novelas)
    basura = ["=sin-clave", "LANGFUSE_HOST", "\x00\x01 binario", 'LANGFUSE_X="sin cerrar']
    _repo_con_env(tmp_path, monkeypatch, "\n".join(basura) + "\n")
    resultado = _cli(ws, "checkpoint")
    assert resultado.exit_code == 0
    assert not any(linea in resultado.output for linea in basura)


# --- spec 0009: vp_schema y un score por validador ---------------------------------------------


class SinkEspia:
    """ScoreSink de la spec 0009 §7: guarda cada (nombre, valor), en orden, y no sale a la red."""

    def __init__(self) -> None:
        self.recibidos: list[tuple[str, float]] = []

    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        self.recibidos += list(scores.items())
        return []


@pytest.fixture
def espia(monkeypatch: pytest.MonkeyPatch) -> SinkEspia:
    sink = SinkEspia()
    monkeypatch.setattr(langfuse, "desde_entorno", lambda _entorno: sink)

    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("un test de scores abrió una conexión de red")

    monkeypatch.setattr(socket, "create_connection", prohibido)
    return sink


def _sin_veredicto(ws: WorkspaceRepository, relativa: str) -> None:
    ruta = ws.raiz / relativa
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    del datos["veredicto"]
    ruta.write_text(json.dumps(datos), encoding="utf-8")


def _ultima_linea(ws: WorkspaceRepository) -> str:
    log = ws.raiz / "runs" / fabrica.run_id(8) / "harness.log"
    return log.read_text(encoding="utf-8").splitlines()[-1]


def test_vp_schema_rechaza_y_emite_cero(novelas: Novelas, espia: SinkEspia) -> None:
    """CA-05 (RF-05, VER-29): un informe sin veredicto para el cierre antes de escribir nada, emite
    vp_schema a 0 y deja la causa sin valores, con rutas POSIX también en Windows."""
    ws = _cerrar_hasta_delta(novelas)
    antes = (ws.raiz / "checkpoints" / "latest.json").read_bytes()
    _sin_veredicto(ws, "qa/08-estilo.json")
    resultado = _cli(ws, "checkpoint")
    assert resultado.exit_code == 1
    assert not (ws.raiz / "checkpoints" / "08.json").exists()
    assert (ws.raiz / "checkpoints" / "latest.json").read_bytes() == antes
    assert espia.recibidos == [("vp_schema", 0.0)]
    assert "qa/08-estilo.json: veredicto" in resultado.output
    linea = _ultima_linea(ws)
    assert "checkpoint 08 -> 1 · vp_schema: esquema_invalido@qa/08-estilo.json:veredicto" in linea
    assert "\\" not in linea


def test_vp_schema_validacion_invalida(novelas: Novelas, espia: SinkEspia) -> None:
    """VAL-7 (b): sin qa/NN-validacion.json válido no salen los scores que se derivan de él."""
    ws = _cerrar_hasta_delta(novelas)
    _sin_veredicto(ws, "qa/08-validacion.json")
    assert _cli(ws, "checkpoint").exit_code == 1
    assert espia.recibidos == [("vp_schema", 0.0)]


def test_vp_schema_obligatorios_y_opcionales(novelas: Novelas, espia: SinkEspia) -> None:
    """VAL-4: faltar un informe de revisión no es hallazgo; faltar el delta o una ficha de
    personaje inválida, sí."""
    ws = _cerrar_hasta_delta(novelas)
    (ws.raiz / "estado" / "deltas" / "08.json").unlink()
    ines = ws.raiz / "canon" / "personajes" / f"{fabrica.INES}.md"
    ines.write_text("---\nvoz: 1\n---\n", encoding="utf-8")
    resultado = _cli(ws, "checkpoint")
    assert resultado.exit_code == 1
    assert "estado/deltas/08.json: (ausente)" in resultado.output
    assert f"canon/personajes/{fabrica.INES}.md: identidad" in resultado.output

    # Se reparan los dos y se quitan los tres informes de revisión: cierra.
    fabrica.escribir(ws.raiz, fabrica.canon(fabrica.DEMO))
    fabrica.escribir(ws.raiz, {"estado/deltas/08.json": json.dumps(fabrica.delta(fabrica.DEMO, 8))})
    for revisor in ("continuidad", "estilo", "suspense"):
        (ws.raiz / "qa" / f"08-{revisor}.json").unlink()
    assert _cli(ws, "checkpoint").exit_code == 0
    assert (ws.raiz / "checkpoints" / "08.json").exists()


VP_SIN_BRIEF = [
    "vp_schema",
    "vp_longitud",
    "vp_pistas",
    "vp_hilos",
    "vp_ids",
    "vp_nombres",
    "vp_prohibidas",
]


def test_sin_brief_sin_cobertura(novelas: Novelas, espia: SinkEspia) -> None:
    """CA-16 (checkpoint) y VAL-39: siete vp_* a 1, sin vp_cobertura, detrás de los agregados y en
    el orden del catálogo, en una sola emisión."""
    ws = _cerrar_hasta_delta(novelas)
    assert _cli(ws, "checkpoint").exit_code == 0
    nombres = [n for n, _ in espia.recibidos]
    assert nombres[-7:] == VP_SIN_BRIEF and len(nombres) == 13
    assert all(v == 1.0 for n, v in espia.recibidos if n.startswith("vp_"))


@pytest.mark.parametrize(
    ("tipo", "validador"),
    [
        ("longitud_fuera_de_rango", "vp_longitud"),
        ("pista_ausente", "vp_pistas"),
        ("hilo_cerrado_sin_abrir", "vp_hilos"),
        ("id_inexistente", "vp_ids"),
        ("nombre_mal_escrito", "vp_nombres"),
        ("termino_prohibido", "vp_prohibidas"),
        ("frontmatter_invalido", None),  # VER-14: vp_schema solo sale de RF-03
    ],
)
def test_cada_tipo_apaga_su_score(
    novelas: Novelas, espia: SinkEspia, tipo: str, validador: str | None
) -> None:
    """CA-15 (segunda mitad) y VAL-23: un hallazgo en qa/08-validacion.json apaga solo su vp_*."""
    ws = _cerrar_hasta_delta(novelas)
    hallazgo = {"tipo": tipo, "gravedad": "alta", "descripcion": "d"}
    fabrica.escribir(
        ws.raiz, {"qa/08-validacion.json": fabrica.informe(8, "validar", hallazgos=[hallazgo])}
    )
    assert _cli(ws, "checkpoint").exit_code == 0
    vp = {n: v for n, v in espia.recibidos if n.startswith("vp_")}
    assert vp == {n: 0.0 if n == validador else 1.0 for n in VP_SIN_BRIEF}


def test_langfuse_caido_en_el_rechazo(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAL-26: con vp_schema rechazando y Langfuse caído, sigue el 1, un solo intento y la causa."""
    ws = _cerrar_hasta_delta(novelas)
    _sin_veredicto(ws, "qa/08-estilo.json")
    llamadas: list[object] = []

    def caido(*args: object, **_: object) -> None:
        llamadas.append(args)
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(urllib.request, "urlopen", caido)
    monkeypatch.setenv("TRACE_TO_LANGFUSE", "true")
    assert _cli(ws, "checkpoint").exit_code == 1
    assert len(llamadas) == 1
    assert "checkpoint 08 -> 1 · vp_schema: esquema_invalido@qa/08-estilo.json:veredicto" in (
        _ultima_linea(ws)
    )
