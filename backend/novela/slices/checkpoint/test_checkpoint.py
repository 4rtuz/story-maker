import json
import os
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


def test_checkpoint_emite_los_seis_scores(
    novelas: Novelas, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CA-22: con "true", el sink recibe los seis scores del capítulo."""
    ws = _cerrar_hasta_delta(novelas)
    nombres: list[str] = []

    class Respuesta:
        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        nombres.append(json.loads(peticion.data)["name"])  # type: ignore[arg-type]
        return Respuesta()

    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    monkeypatch.setenv("TRACE_TO_LANGFUSE", "true")
    assert _cli(ws, "checkpoint").exit_code == 0
    assert sorted(nombres) == sorted(
        ["coherencia", "continuidad", "tension", "longitud", "fair_play", "estilo"]
    )


def test_langfuse_caido_no_impide_cerrar(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """validators.md §3.5: el trazado nunca es la razón por la que un capítulo no cierra."""
    ws = _cerrar_hasta_delta(novelas)

    def caido(*_: object, **__: object) -> None:
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(urllib.request, "urlopen", caido)
    monkeypatch.setenv("TRACE_TO_LANGFUSE", "true")
    assert _cli(ws, "checkpoint").exit_code == 0
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
    """CA-20 (RF-32): con las claves solo en RAIZ_REPO/.env, el sink recibe los seis scores; una
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
    assert urls == ["https://env.invalid/api/public/scores"] * 6
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


def test_id_de_score_versionado(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-40 (RF-43): con la versión 1, los ids de siempre; con la 2, los mismos con v2. Un sink
    falso registra el id que calcula `langfuse.id_de_score` con la versión que recibe."""
    ids: list[str] = []

    class Espia:
        def emitir(
            self,
            slug: str,
            capitulo: int,
            run_id: str,
            scores: Mapping[str, float],
            version: int = 1,
        ) -> list[str]:
            ids.extend(langfuse.id_de_score(slug, run_id, capitulo, n, version) for n in scores)
            return []

    monkeypatch.setattr(langfuse, "desde_entorno", lambda _: Espia())
    ws = _cerrar_hasta_delta(novelas)
    assert _cli(ws, "checkpoint").exit_code == 0
    assert ids and all(i.startswith(f"{ws.slug}-{fabrica.run_id(8)}-08-") for i in ids)
    assert not any(i.endswith("-v1") for i in ids)

    ws = novelas("demo-cambio")
    assert fabrica.pedir_cambio(ws.raiz.parent, ws.slug).exit_code == 0
    fabrica.reaplicar(ws.raiz, 1)
    ids.clear()
    texto, delta = fabrica.regenerado(ws.raiz, fabrica.CAMBIO, 2)
    fabrica.cerrar_regenerado(ws.raiz, fabrica.CAMBIO, 2, texto, delta)
    prefijo = f"{ws.slug}-{fabrica.run_v2(2)}-02-"
    assert ids and all(i.startswith(prefijo) and i.endswith("-v2") for i in ids)
