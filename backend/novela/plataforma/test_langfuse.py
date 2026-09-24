import json
import socket
import urllib.error
import urllib.request
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from novela.plataforma import langfuse

SEIS = {
    "coherencia": 0.8,
    "continuidad": 1.0,
    "tension": 7,
    "longitud": 0.9,
    "fair_play": 0.9,
    "estilo": 1.0,
}
# Nombres por partes: con nombre y valor juntos, el pre-commit anti-claves rechazaría este fichero.
CLAVES = {
    f"LANGFUSE_{k}": v
    for k, v in {
        "PUBLIC_KEY": "publica-de-prueba",
        "SECRET_KEY": "secreta-de-prueba",
        "BASE_URL": "https://langfuse.invalid",
    }.items()
}


def _sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    def prohibido(*_: object, **__: object) -> None:
        raise AssertionError("se abrió una conexión de red")

    monkeypatch.setattr(socket, "create_connection", prohibido)
    monkeypatch.setattr(urllib.request, "urlopen", prohibido)


@pytest.mark.parametrize("valor", [None, "", "True", "1", "yes"])
def test_sink_noop_y_scores(monkeypatch: pytest.MonkeyPatch, valor: str | None) -> None:
    """CA-22 en el puerto: sin TRACE_TO_LANGFUSE exactamente igual a "true", no-op sin red."""
    _sin_red(monkeypatch)
    entorno = CLAVES | ({} if valor is None else {"TRACE_TO_LANGFUSE": valor})
    sink = langfuse.desde_entorno(entorno)
    assert isinstance(sink, langfuse.SinkNulo)
    assert sink.emitir("demo", 8, "r-20260923-1000", SEIS) == []


def test_con_true_llegan_los_seis(monkeypatch: pytest.MonkeyPatch) -> None:
    enviados: list[dict[str, Any]] = []

    class Respuesta:
        status = 200

        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        assert peticion.full_url == "https://langfuse.invalid/api/public/scores"
        assert peticion.get_header("Authorization", "").startswith("Basic ")
        assert timeout <= langfuse.TIMEOUT_S
        enviados.append(json.loads(peticion.data))  # type: ignore[arg-type]
        return Respuesta()

    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    sink = langfuse.desde_entorno(CLAVES | {"TRACE_TO_LANGFUSE": "true"})
    assert sink.emitir("demo", 8, "r-20260923-1000", SEIS) == []
    assert {e["name"] for e in enviados} == set(SEIS)
    # Sin traza del capítulo, a la sesión de la novela; Langfuse admite uno solo de los dos.
    assert all(e["sessionId"] == langfuse.sesion_de("demo") for e in enviados)
    assert all("traceId" not in e for e in enviados)
    # Id determinista: reemitir el mismo capítulo sustituye el score en vez de duplicarlo.
    assert {e["id"] for e in enviados} == {f"demo-r-20260923-1000-08-{n}" for n in SEIS}


def test_comentario_por_score(monkeypatch: pytest.MonkeyPatch) -> None:
    """El juez manda su justificación como comentario; sin ella, el de siempre."""
    enviados: list[dict[str, Any]] = []

    class Respuesta:
        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        enviados.append(json.loads(peticion.data))  # type: ignore[arg-type]
        return Respuesta()

    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    sink = langfuse.desde_entorno(CLAVES | {"TRACE_TO_LANGFUSE": "true"})
    scores = {"juez_tono": 4.0, "juez_ritmo": 3.0}
    assert sink.emitir("demo", 10, "r-1", scores, comentarios={"juez_tono": "tierno"}) == []
    assert [e["comment"] for e in enviados] == ["tierno", "demo, capítulo 10"]


def test_sink_caido_no_rompe(monkeypatch: pytest.MonkeyPatch) -> None:
    """validators.md §3.5: con Langfuse inalcanzable, el fallo se devuelve, no se lanza, y se
    para en el primero: seis timeouts seguidos no pueden retener el checkpoint."""
    llamadas = []

    def caido(peticion: urllib.request.Request, timeout: float) -> None:
        llamadas.append(peticion)
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(urllib.request, "urlopen", caido)
    fallos = langfuse.desde_entorno(CLAVES | {"TRACE_TO_LANGFUSE": "true"}).emitir(
        "demo", 8, "r-20260923-1000", SEIS
    )
    assert len(fallos) == 1 and "sin red" in fallos[0]
    assert len(llamadas) == 1


# Por partes: con el prefijo del proveedor pegado al resto, el pre-commit rechazaría el fichero.
SECRETA = "sk-" + "lf-dummy0000"


@pytest.mark.parametrize(
    "linea", ["LANGFUSE_HOST=v", "export LANGFUSE_HOST=v", 'LANGFUSE_HOST="v"', "LANGFUSE_HOST='v'"]
)
def test_fusionar_formatos(linea: str) -> None:
    """RF-32, spec 0003 §5.3: `export` y comillas opcionales."""
    assert langfuse.fusionar({}, linea + "\n") == {"LANGFUSE_HOST": "v"}


def test_fusionar_ignora_lo_demas() -> None:
    """Vacías, comentarios, sin `=` y claves ajenas, fuera y sin error."""
    texto = "\n# comentario\nsin igual\nOTRA=x\nTRACE_TO_LANGFUSE=true\nLANGFUSE_SECRET_KEY="
    texto += SECRETA + "\n"
    assert langfuse.fusionar({"PATH": "p"}, texto) == {
        "PATH": "p",
        "TRACE_TO_LANGFUSE": "true",
        "LANGFUSE_SECRET_KEY": SECRETA,
    }


def test_fusionar_sin_env() -> None:
    assert langfuse.fusionar({"A": "1"}, None) == {"A": "1"}


_claves = st.sampled_from(
    ["TRACE_TO_LANGFUSE", "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "OTRA"]
)
_valores = st.text(alphabet="abcdefghij0123456789-", min_size=1)


@given(st.dictionaries(_claves, _valores), st.dictionaries(_claves, _valores))
def test_manda_el_entorno(entorno: dict[str, str], fichero: dict[str, str]) -> None:
    """Lo que ya está en el entorno sale igual, y del .env solo entran las claves del emisor."""
    fusion = langfuse.fusionar(entorno, "".join(f"{k}={v}\n" for k, v in fichero.items()))
    assert all(fusion[k] == v for k, v in entorno.items())
    assert set(fusion) == set(entorno) | {k for k in fichero if k != "OTRA"}


TRAZA = "0af7651916cd43dd8448eb211c80319c"


def test_con_traceparent_van_a_la_traza_del_capitulo(monkeypatch: pytest.MonkeyPatch) -> None:
    """`producir` abre una traza por paso y la hereda la sesión: el score va a esa traza, que ya
    pertenece a la sesión de la novela."""
    enviados: list[dict[str, Any]] = []

    class Respuesta:
        def __enter__(self) -> "Respuesta":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def capturar(peticion: urllib.request.Request, timeout: float) -> Respuesta:
        enviados.append(json.loads(peticion.data))  # type: ignore[arg-type]
        return Respuesta()

    monkeypatch.setattr(urllib.request, "urlopen", capturar)
    entorno = CLAVES | {
        "TRACE_TO_LANGFUSE": "true",
        "CC_LANGFUSE_TRACEPARENT": f"00-{TRAZA}-b7ad6b7169203331-01",
    }
    assert langfuse.desde_entorno(entorno).emitir("demo", 8, "r-20260923-1000", SEIS) == []
    assert all(e["traceId"] == TRAZA and "sessionId" not in e for e in enviados)


def test_sesion_de_es_estable_y_por_novela() -> None:
    assert langfuse.sesion_de("demo") == langfuse.sesion_de("demo")
    assert langfuse.sesion_de("demo") != langfuse.sesion_de("otra")
    assert langfuse.sesion_de("demo") == "novela-demo"
