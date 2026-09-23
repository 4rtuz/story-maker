import json
import socket
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.artefactos import Checkpoint
from novela.plataforma import atomic
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
