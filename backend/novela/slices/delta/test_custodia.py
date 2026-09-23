from collections.abc import Callable
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.qa import Hallazgo, InformeQA
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.delta import custodia
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]
sha = st.sampled_from(["a" * 64, "b" * 64, "c" * 64])


def _validacion(hash_: str | None, con_hallazgos: bool) -> InformeQA:
    hallazgos = [Hallazgo(tipo="pista_ausente", gravedad="alta", descripcion="x")]
    return InformeQA(
        capitulo=8,
        agente="validar",
        veredicto="rechazado" if con_hallazgos else "aprobado",
        hallazgos=hallazgos if con_hallazgos else [],
        capitulo_sha256=hash_,
    )


@given(
    disco=st.none() | sha,
    cronista=st.none() | sha,
    validado=st.none() | sha,
    hay_validacion=st.booleans(),
    con_hallazgos=st.booleans(),
    revision=st.dictionaries(
        st.sampled_from(["continuista", "lector-suspense", "editor-estilo"]), sha
    ),
)
def test_cadena_property(
    disco: str | None,
    cronista: str | None,
    validado: str | None,
    hay_validacion: bool,
    con_hallazgos: bool,
    revision: dict[str, str],
) -> None:
    """CA-36, la función: la cadena cierra si y solo si el fichero en disco es el que leyó el
    cronista y el que pasó la última validación sin hallazgos, y los briefings de revisión del
    run llevan todos el mismo hash."""
    cadena = custodia.Cadena(
        sha_disco=disco,
        sha_cronista=cronista,
        validacion=_validacion(validado, con_hallazgos) if hay_validacion else None,
        shas_revision=revision,
    )
    cierra = (
        disco is not None
        and cronista == disco
        and hay_validacion
        and validado == disco
        and not con_hallazgos
        and len(set(revision.values())) <= 1
    )
    assert (custodia.rotura(cadena) == []) is cierra


def _aplicar(ws: WorkspaceRepository) -> tuple[int, bytes]:
    resultado = fabrica.cli(ws.raiz.parent, "aplicar-delta", ws.slug, "8", run=fabrica.run_id(8))
    return resultado.exit_code, (ws.raiz / "estado" / "estado.db").read_bytes()


def _log(ws: WorkspaceRepository) -> str:
    return (ws.raiz / "runs" / fabrica.run_id(8) / "harness.log").read_text(encoding="utf-8")


def test_cadena_integra_aplica(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    codigo, _ = _aplicar(ws)
    assert codigo == 0


def test_capitulo_cambiado_tras_el_cronista(novelas: Novelas) -> None:
    """CA-36 en el comando: un byte cambiado en capitulos/NN.md después del briefing del
    cronista hace salir con 1, deja estado.db byte a byte idéntico y la causa en el log."""
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    antes = (ws.raiz / "estado" / "estado.db").read_bytes()
    capitulo = ws.raiz / "capitulos" / "08.md"
    capitulo.write_bytes(capitulo.read_bytes().replace(b"viento", b"vient0", 1))
    codigo, despues = _aplicar(ws)
    assert (codigo, despues) == (1, antes)
    assert "cronista" in _log(ws)


def test_briefing_de_revision_rancio(novelas: Novelas) -> None:
    """Un briefing de revisión del intento anterior lleva otro hash: la cadena no cierra."""
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    briefing = ws.raiz / "runs" / fabrica.run_id(8) / "briefings" / "08-continuista.md"
    texto = briefing.read_text(encoding="utf-8")
    meta_sha = texto.split("capitulo_sha256: ")[1][:64]
    briefing.write_bytes(texto.replace(meta_sha, "f" * 64).encode("utf-8"))
    antes = (ws.raiz / "estado" / "estado.db").read_bytes()
    codigo, despues = _aplicar(ws)
    assert (codigo, despues) == (1, antes)
    assert "revisión" in _log(ws)


def test_sin_validacion_no_aplica(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    Path(ws.raiz / "qa" / "08-validacion.json").unlink()
    assert _aplicar(ws)[0] == 1
