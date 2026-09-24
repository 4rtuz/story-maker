"""La regeneración completa de una versión con el CLI real y el agente falso (spec 0007 §7).

Recorre la versión nueva como el procedimiento: `novela cambio --siguiente` dice qué toca, un
reaplicable se reaplica sin agentes y un afectado pasa por el bucle entero con el agente falso de
`fabrica`. Ningún paso llama a un modelo.
"""

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from typer.testing import Result

from novela.dominio.version import PeticionDeCambio, Version
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica
from tests.fixtures.fabrica import Novela

Novelas = Callable[[str], WorkspaceRepository]
COPIADOS = ("capitulos", "estado/deltas", "memoria", "qa", "checkpoints")


def _shas(raiz: Path) -> dict[str, str]:
    return {
        p.relative_to(raiz).as_posix(): fabrica.sha256(p)
        for d in COPIADOS
        for p in sorted((raiz / d).rglob("*"))
        if p.is_file()
    }


def _cli(raiz: Path, *orden: str) -> Result:
    return fabrica.cli(raiz.parent, *orden, run="", entorno={"NOVELAS_DIR": str(raiz.parent)})


def _pendiente(raiz: Path) -> int:
    return _cli(raiz, "pendiente", raiz.name).exit_code


def _version_intacta(raiz: Path, antes: dict[str, str]) -> None:
    """RNF-04: versiones/v1/ tiene los ficheros de antes del cambio, con sus sha256, y ninguno
    más que los que lista version.json."""
    v1 = raiz / "versiones" / "v1"
    version = Version.model_validate_json((v1 / "version.json").read_bytes())
    presentes = {
        p.relative_to(v1).as_posix(): fabrica.sha256(p)
        for p in v1.rglob("*")
        if p.is_file() and p.name != "version.json"
    }
    assert presentes == version.ficheros
    assert {r: s for r, s in presentes.items() if not r.startswith("estado/estado")} == antes


def test_recorrido_demo_cambio(novelas: Novelas) -> None:
    """CA-29, CA-41, CA-19 tras la regeneración y el último punto de CA-22."""
    ws = novelas("demo-cambio")
    antes, terminada = _shas(ws.raiz), _pendiente(ws.raiz)
    assert fabrica.pedir_cambio(ws.raiz.parent, ws.slug).exit_code == 0
    pasos = fabrica.completar(ws.raiz, fabrica.CAMBIO)
    assert pasos == [f"{n:02d} {'regenerar' if n % 2 == 0 else 'reaplicar'}" for n in range(1, 7)]
    assert fabrica.siguiente(ws.raiz) == "completo"
    assert _pendiente(ws.raiz) == terminada != 0

    v1 = ws.raiz / "versiones" / "v1"
    for n in range(1, 7):
        iguales = fabrica.sha256(ws.raiz / f"capitulos/{n:02d}.md") == fabrica.sha256(
            v1 / f"capitulos/{n:02d}.md"
        )
        assert iguales == (n % 2 == 1), n
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        hechos = {h.id for h in estado_db.leer(conn).libro_de_hechos}
    assert {"hec-103", "hec-102"} <= hechos and "hec-002" not in hechos
    _version_intacta(ws.raiz, antes)

    logs = {p.parent.name: p.read_text("utf-8") for p in (ws.raiz / "runs").glob("*/harness.log")}
    assert sum("cambio cam-001 -> 0" in log for log in logs.values()) == 1
    for n in (1, 3, 5):
        assert f"aplicar-delta {n:02d} --reaplicar -> 0" in logs[fabrica.run_v2(n)]


@st.composite
def _novelas_con_usos(draw: st.DrawFn) -> tuple[Novela, str]:
    """De 3 a 6 capítulos, con hechos extra y usos en hechos_usados posteriores a su origen, y el
    hecho que cambia."""
    k = draw(st.integers(3, 6))
    extras = draw(st.lists(st.integers(1, k), max_size=2))
    hechos_extra = tuple((f"hec-{101 + i}", c) for i, c in enumerate(extras))
    origenes = {f"hec-{n:03d}": n for n in range(1, k + 1)} | dict(hechos_extra)
    candidatos = sorted((c, h) for h, o in origenes.items() for c in range(o + 1, k + 1))
    usados = tuple(sorted(draw(st.sets(st.sampled_from(candidatos), max_size=6))))
    novela = Novela(k, pistas=((1, k),), hilos=((1, k),), hechos_extra=hechos_extra, usados=usados)
    return novela, draw(st.sampled_from(sorted(origenes)))


@settings(max_examples=25, deadline=None)
@given(_novelas_con_usos())
def test_regeneracion_no_toca_reaplicables_property(caso: tuple[Novela, str]) -> None:
    """CA-30 (RF-13, RF-25, RNF-05, RNF-11): todo reaplicable queda idéntico a versiones/v1/,
    todo afectado se regenera y versiones/v1/ no cambia."""
    novela, hecho = caso
    base = Path(tempfile.mkdtemp(prefix="regeneracion-"))
    try:
        raiz = fabrica.construir(base, "demo-prop", novela, cerrados=novela.num_capitulos)
        antes = _shas(raiz)
        resultado = fabrica.pedir_cambio(base, "demo-prop", hecho=hecho)
        assert resultado.exit_code == 0, resultado.output
        fabrica.completar(raiz, novela)
        v1 = raiz / "versiones" / "v1"
        ruta = raiz / "cambios" / "cam-001.json"
        cambio = WorkspaceRepository(raiz).leer_json(ruta, PeticionDeCambio)
        for n in range(1, novela.num_capitulos + 1):
            relativa = f"capitulos/{n:02d}.md"
            iguales = fabrica.sha256(raiz / relativa) == fabrica.sha256(v1 / relativa)
            assert iguales == (n in cambio.plan.reaplicar), (n, cambio.plan)
        _version_intacta(raiz, antes)
    finally:
        shutil.rmtree(base, ignore_errors=True)
