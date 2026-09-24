import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio import frontmatter
from novela.dominio.artefactos import Manifest
from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.canon import Misterio
from novela.dominio.ids import Agente
from novela.plataforma.workspace import WorkspaceRepository, huella
from novela.slices.briefing import assemble, recipes
from tests import estrategias
from tests.fixtures import fabrica
from tests.fuentes import FICHA, PERSONAJE, fuentes

RECETAS = recipes.cargar()
# Qué capas recibe cada agente que excluye el misterio: ahí es donde se puede colar.
CAPAS = {
    Agente.ESCRITOR: ["premisa", "estilo", "ficha", "personaje"],
    Agente.EDITOR_ESTILO: ["estilo", "personaje", "capitulo"],
    Agente.CRONISTA: ["capitulo"],
    Agente.JUEZ: ["brief", "premisa", "estilo", "personaje", "obra"],
}


def _fuentes_con(misterio: Misterio, agente: Agente, **textos: str) -> assemble.Fuentes:
    ficheros = {
        "canon/premisa.md": textos.get("premisa", "Premisa sin secretos."),
        "canon/mundo.md": "Un pueblo.",
        "canon/estilo.md": textos.get("estilo", "Seco."),
        "brief/brief.json": textos.get("brief", "{}"),
        "canon/misterio.md": frontmatter.unir(misterio.model_dump(mode="json"), ""),
    }
    return replace(
        fuentes(),
        agente=agente,
        ficheros=ficheros,
        misterio=misterio,
        misterio_texto=ficheros["canon/misterio.md"],
        ficha=FICHA,
        ficha_texto=textos.get("ficha", "La ficha de este capítulo."),
        personajes={"per-a": (PERSONAJE, textos.get("personaje", "Ficha de A."))},
        capitulo_actual=textos.get("capitulo", "El capítulo recién escrito."),
        capitulos={1: textos.get("obra", "La novela entera.")},
    )


@given(
    misterio=estrategias.misterios(),
    agente=st.sampled_from(sorted(CAPAS)),
    inyectar=st.booleans(),
    datos=st.data(),
)
def test_misterio_nunca_en_briefing(
    misterio: Misterio, agente: Agente, inyectar: bool, datos: st.DataObject
) -> None:
    """CA-09: para cualquier canon, lo que viene de canon/misterio.md no entra en el briefing de
    quien lo excluye. Si otra capa lo trae, el ensamblado aborta en vez de devolver nada."""
    fuga = datos.draw(st.sampled_from(misterio.verdad_oculta.entradas))
    assume(len(fuga) >= assemble.MIN_FRAGMENTO)
    donde = datos.draw(st.sampled_from(CAPAS[agente]))
    textos = {donde: f"Relleno. {fuga} Más relleno."} if inyectar else {}
    f = _fuentes_con(misterio, agente, **textos)
    if inyectar:
        with pytest.raises(assemble.FugaDelSecreto):
            assemble.ensamblar(RECETAS[agente], f)
        return
    cuerpo = assemble.ensamblar(RECETAS[agente], f).cuerpo
    assert f.ficheros["canon/misterio.md"].strip() not in cuerpo
    assert all(p not in cuerpo for p in misterio.verdad_oculta if len(p) >= assemble.MIN_FRAGMENTO)


@given(misterio=estrategias.misterios())
def test_misterio_incrustado(misterio: Misterio) -> None:
    """CA-10: el continuista y el lector-suspense reciben el misterio literal, incrustado."""
    for agente in (Agente.CONTINUISTA, Agente.LECTOR_SUSPENSE):
        f = _fuentes_con(misterio, agente)
        ficheros = dict(f.ficheros) | {"plan/escaleta.md": "La escaleta."}
        cuerpo = assemble.ensamblar(RECETAS[agente], replace(f, ficheros=ficheros)).cuerpo
        assert f.ficheros["canon/misterio.md"].strip() in cuerpo


@given(misterio=estrategias.misterios())
def test_el_error_no_repite_el_secreto(misterio: Misterio) -> None:
    """El mensaje del aborto llega al orquestador: nombra la capa, no el texto filtrado."""
    secreto = "Tomás apagó el faro con la llave que nunca devolvió."
    misterio = misterio.model_copy(update={"verdad_oculta": ColeccionAppendOnly([secreto])})
    f = _fuentes_con(misterio, Agente.EDITOR_ESTILO, estilo=secreto)
    with pytest.raises(assemble.FugaDelSecreto) as error:
        assemble.ensamblar(RECETAS[Agente.EDITOR_ESTILO], f)
    assert "canon/estilo.md" in str(error.value)
    assert secreto not in str(error.value)


# --- La cáscara: novela briefing ----------------------------------------------------------------

GOLDEN = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "golden" / "08-escritor.md"
RUN = "r-20260923-1000"
Novelas = Callable[[str], WorkspaceRepository]


def _briefing(ws: WorkspaceRepository, cap: int, agente: str, run_id: str = RUN) -> Result:
    entorno = {"NOVELAS_DIR": str(ws.raiz.parent), "NOVELA_RUN_ID": run_id}
    return CliRunner().invoke(app, ["briefing", ws.slug, str(cap), agente], env=entorno)


def _fichero(ws: WorkspaceRepository, cap: int, agente: str, run_id: str = RUN) -> Path:
    return ws.raiz / "runs" / run_id / "briefings" / f"{cap:02d}-{agente}.md"


def test_golden_escritor(novelas: Novelas) -> None:
    """CA-08: el briefing del escritor sobre el fixture coincide byte a byte con el esperado. Si
    cambia a propósito, REGENERAR=1 lo reescribe y el diff del golden es la revisión."""
    ws = novelas("demo-24")
    resultado = _briefing(ws, 8, "escritor")
    assert resultado.exit_code == 0, resultado.output
    obtenido = _fichero(ws, 8, "escritor").read_bytes()
    if os.environ.get("REGENERAR") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_bytes(obtenido)
    assert obtenido == GOLDEN.read_bytes()


def test_fuga_por_cli_no_deja_fichero(novelas: Novelas) -> None:
    """CA-09, la mitad del comando: sale != 0 y no deja fichero."""
    ws = novelas("demo-24")
    ficha = ws.raiz / "plan" / "capitulos" / "08.md"
    secreto = "Lo hizo para cobrar el seguro que había firmado tres semanas antes del naufragio."
    ficha.write_bytes(ficha.read_bytes() + f"\nNota del trazador: {secreto}\n".encode())
    resultado = _briefing(ws, 8, "escritor")
    assert resultado.exit_code == 1
    assert "canon/misterio.md" in resultado.output and secreto not in resultado.output
    assert not _fichero(ws, 8, "escritor").exists()


def test_misterio_incrustado_por_cli(novelas: Novelas) -> None:
    """CA-10 sobre el workspace: el continuista recibe canon/misterio.md literal."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    assert _briefing(ws, 8, "continuista").exit_code == 0
    misterio = (ws.raiz / "canon" / "misterio.md").read_text(encoding="utf-8").strip()
    assert misterio in _fichero(ws, 8, "continuista").read_text(encoding="utf-8")


def test_presupuesto_excedido_falla(novelas: Novelas) -> None:
    """CA-11: canon/ no se degrada nunca; si ella sola no cabe, sale != 0 y no hay fichero."""
    ws = novelas("demo-24")
    premisa = ws.raiz / "canon" / "premisa.md"
    premisa.write_bytes(premisa.read_bytes() + ("La niebla. " * 30_000).encode())
    resultado = _briefing(ws, 8, "escritor")
    assert resultado.exit_code == 1
    assert "presupuesto" in resultado.output
    assert not _fichero(ws, 8, "escritor").exists()


def test_hash_del_capitulo_incrustado(novelas: Novelas) -> None:
    """CA-34: quien incrusta capitulos/NN.md lleva su sha256; el escritor, que no, no lo lleva."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    assert _briefing(ws, 8, "continuista").exit_code == 0
    assert _briefing(ws, 8, "escritor").exit_code == 0
    meta = frontmatter.partir(_fichero(ws, 8, "continuista").read_text(encoding="utf-8"))[0]
    assert meta["capitulo_sha256"] == fabrica.sha256(ws.raiz / "capitulos" / "08.md")
    meta = frontmatter.partir(_fichero(ws, 8, "escritor").read_text(encoding="utf-8"))[0]
    assert "capitulo_sha256" not in meta


def test_sello_capitulos_cerrados(novelas: Novelas) -> None:
    """CA-39: tras el checkpoint del 7, un byte cambiado en un capítulo cerrado hace salir al
    briefing del 8 con 4 sin escribir; sin cambios, se escribe."""
    ws = novelas("demo-24")
    assert _briefing(ws, 8, "escritor").exit_code == 0
    _fichero(ws, 8, "escritor").unlink()
    tercero = ws.raiz / "capitulos" / "03.md"
    tercero.write_bytes(tercero.read_bytes().replace(b"Elena", b"Elen4", 1))
    resultado = _briefing(ws, 8, "escritor")
    assert resultado.exit_code == 4
    assert "03" in resultado.output
    assert not _fichero(ws, 8, "escritor").exists()


def test_capitulo_sin_checkpoint_del_anterior(novelas: Novelas) -> None:
    """validators.md §4.10: nunca un capítulo N+1 con el N sin checkpoint."""
    ws = novelas("demo-24")
    assert _briefing(ws, 9, "escritor").exit_code == 1
    assert not _fichero(ws, 9, "escritor").exists()


def test_manifiesto_y_log_por_cli(novelas: Novelas) -> None:
    """CA-13 y CA-33 desde el comando: el run del entorno, su manifiesto y su línea de log; un
    NOVELA_RUN_ID con basura aborta sin crear directorio."""
    ws = novelas("demo-24")
    assert _briefing(ws, 8, "escritor").exit_code == 0
    assert (ws.raiz / "runs" / RUN / "manifest.json").exists()
    log = (ws.raiz / "runs" / RUN / "harness.log").read_text(encoding="utf-8")
    assert "briefing 08 escritor -> 0" in log
    antes = sorted(p.name for p in (ws.raiz / "runs").iterdir())
    assert _briefing(ws, 8, "escritor", run_id="../../fuera").exit_code == 2
    assert sorted(p.name for p in (ws.raiz / "runs").iterdir()) == antes


ARRANQUE = "r-20260101-0000"


def _nueva(base: Path, slug: str = "nuevo") -> WorkspaceRepository:
    orden = ["nueva", slug, "--idea", "Un faro.", "--capitulos", "3", "--palabras", "900"]
    assert CliRunner().invoke(app, orden, env={"NOVELAS_DIR": str(base)}).exit_code == 0
    return WorkspaceRepository(base / slug)


def _manifiesto(ws: WorkspaceRepository, run_id: str) -> Manifest:
    return Manifest.model_validate_json((ws.raiz / "runs" / run_id / "manifest.json").read_bytes())


def test_arranque_no_contamina_el_capitulo_1(tmp_path: Path) -> None:
    """CA-07 (RF-11): arquitecto y trazador comparten un run de arranque, y el primer briefing del
    escritor abre otro que registra el canon y el plan que de verdad hay."""
    ws = _nueva(tmp_path)
    arquitecto = fabrica.cli(tmp_path, "briefing", ws.slug, "1", "arquitecto", run=ARRANQUE)
    assert arquitecto.exit_code == 0, arquitecto.output
    fabrica.escribir(ws.raiz, fabrica.canon(fabrica.HUERFANA) | fabrica.plan(fabrica.HUERFANA))
    resultado = fabrica.cli(tmp_path, "briefing", ws.slug, "1", "trazador", run=ARRANQUE)
    assert resultado.exit_code == 0, resultado.output
    briefings = ws.raiz / "runs" / ARRANQUE / "briefings"
    assert {p.name for p in briefings.iterdir()} == {"01-arquitecto.md", "01-trazador.md"}
    assert _manifiesto(ws, ARRANQUE).fase == "arranque"

    entorno = {"NOVELAS_DIR": str(tmp_path)}  # sin NOVELA_RUN_ID: el run sale del reloj
    resultado = fabrica.cli(tmp_path, "briefing", ws.slug, "1", "escritor", run="", entorno=entorno)
    assert resultado.exit_code == 0, resultado.output
    [capitulo] = [p.name for p in (ws.raiz / "runs").iterdir() if p.name != ARRANQUE]
    manifiesto = _manifiesto(ws, capitulo)
    assert manifiesto.fase == "capitulo"
    assert manifiesto.version_canon == huella(ws.raiz / "canon")
    assert manifiesto.version_plan == huella(ws.raiz / "plan")


def test_run_fijado_de_otra_fase(tmp_path: Path, novelas: Novelas) -> None:
    """CA-16 (RF-27, F-41): NOVELA_RUN_ID no mezcla el arranque con el capítulo 1, ni un capítulo
    con otro. Sale con 2 sin escribir el briefing."""
    ws = _nueva(tmp_path)
    arquitecto = fabrica.cli(tmp_path, "briefing", ws.slug, "1", "arquitecto", run=ARRANQUE)
    assert arquitecto.exit_code == 0, arquitecto.output
    fabrica.escribir(ws.raiz, fabrica.canon(fabrica.HUERFANA) | fabrica.plan(fabrica.HUERFANA))
    assert fabrica.cli(tmp_path, "briefing", ws.slug, "1", "escritor", run=ARRANQUE).exit_code == 2
    assert not (ws.raiz / "runs" / ARRANQUE / "briefings" / "01-escritor.md").exists()

    demo = novelas("demo-24")  # el run del capítulo 2 ya tiene manifiesto
    assert _briefing(demo, 8, "escritor", run_id=fabrica.run_id(2)).exit_code == 2
    assert not _fichero(demo, 8, "escritor", run_id=fabrica.run_id(2)).exists()


def test_canon_invalido_en_el_log(tmp_path: Path) -> None:
    """CA-18: la línea de log del canon inválido es contrato de /novela-nueva. El briefing del
    trazador es el gate del arquitecto, y el procedimiento solo reintenta si la ve."""
    ws = _nueva(tmp_path)
    fabrica.escribir(ws.raiz, fabrica.canon(fabrica.HUERFANA) | fabrica.plan(fabrica.HUERFANA))
    fabrica.escribir(ws.raiz, {"canon/premisa.md": "---\nlogline: 3\n---\nSin premisa.\n"})
    resultado = fabrica.cli(tmp_path, "briefing", ws.slug, "1", "trazador", run=ARRANQUE)
    assert resultado.exit_code == 4
    log = (ws.raiz / "runs" / ARRANQUE / "harness.log").read_text(encoding="utf-8")
    assert "briefing 01 trazador -> error · WorkspaceInvalido" in log.splitlines()[-1]


def test_misterio_invalido_en_el_log(tmp_path: Path) -> None:
    """CA-22 (RF-34, F-09): /novela-nueva no reintenta al arquitecto si la causa nombra
    misterio.md, que no puede leer ni, por tanto, reescribir. La causa tiene que nombrarlo."""
    ws = _nueva(tmp_path)
    fabrica.escribir(ws.raiz, fabrica.canon(fabrica.HUERFANA) | fabrica.plan(fabrica.HUERFANA))
    fabrica.escribir(ws.raiz, {"canon/misterio.md": "---\npistas: 3\n---\nRoto.\n"})
    resultado = fabrica.cli(tmp_path, "briefing", ws.slug, "1", "trazador", run=ARRANQUE)
    assert resultado.exit_code == 4
    ultima = (ws.raiz / "runs" / ARRANQUE / "harness.log").read_text("utf-8").splitlines()[-1]
    assert "WorkspaceInvalido" in ultima and "misterio.md" in ultima


def _con_canon(tmp_path: Path) -> WorkspaceRepository:
    ws = _nueva(tmp_path)
    fabrica.escribir(ws.raiz, fabrica.canon(fabrica.HUERFANA) | fabrica.plan(fabrica.HUERFANA))
    return ws


def _ultima(ws: WorkspaceRepository, run_id: str) -> str:
    return (ws.raiz / "runs" / run_id / "harness.log").read_text("utf-8").splitlines()[-1]


@pytest.mark.parametrize(
    ("agente", "run_id"), [("trazador", ARRANQUE), ("escritor", "r-20260101-0100")]
)
@pytest.mark.parametrize(
    "falta", ["premisa.md", "mundo.md", "estilo.md", "misterio.md", "personajes"]
)
def test_canon_incompleto(tmp_path: Path, agente: str, run_id: str, falta: str) -> None:
    """CA-26 (RF-38, F-48): el gate del arquitecto validaba solo los ficheros del canon que
    existían. Sin uno, o sin fichas de personaje, cualquier agente salvo el arquitecto sale con 4
    y la causa nombra lo que falta."""
    ws = _con_canon(tmp_path)
    objetivo = ws.raiz / "canon" / falta
    if objetivo.is_dir():
        for ficha in objetivo.iterdir():
            ficha.unlink()
    else:
        objetivo.unlink()
    resultado = fabrica.cli(tmp_path, "briefing", ws.slug, "1", agente, run=run_id)
    assert resultado.exit_code == 4
    ultima = _ultima(ws, run_id)
    # Al trazador le falta el borrador: es lo que el arquitecto escribe (RF-37).
    nombre = "misterio.borrador.md" if (agente, falta) == ("trazador", "misterio.md") else falta
    assert "WorkspaceInvalido" in ultima and nombre in ultima


def test_arquitecto_sin_canon(tmp_path: Path) -> None:
    """CA-26: el arquitecto es quien escribe el canon; su briefing no lo exige."""
    ws = _nueva(tmp_path)
    assert (
        fabrica.cli(tmp_path, "briefing", ws.slug, "1", "arquitecto", run=ARRANQUE).exit_code == 0
    )


BORRADOR = "canon/misterio.borrador.md"
ROTO = "---\npistas: 3\n---\nRoto.\n"


def _con_borrador(tmp_path: Path, texto: str | None = None) -> tuple[WorkspaceRepository, bytes]:
    """El canon tal como lo deja el arquitecto: el misterio solo en el borrador (F-28)."""
    ws = _con_canon(tmp_path)
    misterio = ws.raiz / "canon" / "misterio.md"
    datos = misterio.read_bytes() if texto is None else texto.encode()
    misterio.unlink()
    (ws.raiz / BORRADOR).write_bytes(datos)
    return ws, datos


def _gate(tmp_path: Path, ws: WorkspaceRepository) -> Result:
    return fabrica.cli(tmp_path, "briefing", ws.slug, "1", "trazador", run=ARRANQUE)


def test_borrador_promovido(tmp_path: Path) -> None:
    """CA-25 (RF-37): con el canon válido, el gate escribe el borrador en canon/misterio.md, tal
    cual, y lo borra. El trazador lo recibe como el misterio."""
    ws, datos = _con_borrador(tmp_path)
    assert _gate(tmp_path, ws).exit_code == 0
    assert (ws.raiz / "canon" / "misterio.md").read_bytes() == datos
    assert not (ws.raiz / BORRADOR).exists()
    briefing = (ws.raiz / "runs" / ARRANQUE / "briefings" / "01-trazador.md").read_text("utf-8")
    assert "canon/misterio.md" in briefing and "borrador" not in briefing


def test_borrador_invalido_se_queda(tmp_path: Path) -> None:
    """CA-25: un borrador inválido sale con 4 y nombra el borrador, sin la subcadena misterio.md
    que en /novela-nueva prohíbe el reintento: el arquitecto sí puede leerlo y reescribirlo."""
    ws, _ = _con_borrador(tmp_path, ROTO)
    assert _gate(tmp_path, ws).exit_code == 4
    ultima = _ultima(ws, ARRANQUE)
    assert "misterio.borrador.md" in ultima and "misterio.md" not in ultima
    assert (ws.raiz / BORRADOR).is_file() and not (ws.raiz / "canon" / "misterio.md").exists()


def test_borrador_valido_con_otro_invalido(tmp_path: Path) -> None:
    """CA-25: solo se promueve si valida el canon entero; si no, el borrador se queda."""
    ws, _ = _con_borrador(tmp_path)
    fabrica.escribir(ws.raiz, {"canon/premisa.md": "---\nlogline: 3\n---\nSin premisa.\n"})
    assert _gate(tmp_path, ws).exit_code == 4
    assert (ws.raiz / BORRADOR).is_file() and not (ws.raiz / "canon" / "misterio.md").exists()


def test_gana_el_borrador(tmp_path: Path) -> None:
    """CA-25: con los dos, manda el borrador. Es el estado que deja una promoción cortada entre
    escribir misterio.md y borrar el borrador, y el de un reintento del arquitecto."""
    ws, datos = _con_borrador(tmp_path)
    (ws.raiz / "canon" / "misterio.md").write_text(ROTO, encoding="utf-8")
    assert _gate(tmp_path, ws).exit_code == 0
    assert (ws.raiz / "canon" / "misterio.md").read_bytes() == datos
    assert not (ws.raiz / BORRADOR).exists()


def test_el_borrador_no_llega_a_otros_agentes(novelas: Novelas) -> None:
    """Un borrador olvidado no entra en ningún briefing salvo el del trazador: `canon/*` de una
    receta lo recogería sin pasar por el guardarraíl del misterio."""
    ws = novelas("demo-24")
    # El continuista es la receta con `canon/*`, además del trazador, y juzga el capítulo 8.
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    (ws.raiz / BORRADOR).write_text("secreto-del-borrador", encoding="utf-8")
    assert _briefing(ws, 8, "continuista").exit_code == 0
    assert "secreto-del-borrador" not in _fichero(ws, 8, "continuista").read_text("utf-8")


@given(misterio=estrategias.misterios())
def test_pista_permitida_dentro_del_secreto_no_lo_tapa(misterio: Misterio) -> None:
    """Contraejemplo que encontró Hypothesis: una pista permitida que es subcadena del secreto no
    puede ocultar la fuga del secreto entero."""
    pista = misterio.pistas.entradas[0].model_copy(
        update={"contenido": "la llave", "capitulo_plantado": 1}
    )
    secreto = "Tomás abrió la puerta con la llave que nunca devolvió."
    misterio = misterio.model_copy(
        update={
            "pistas": ColeccionAppendOnly([pista, *misterio.pistas.entradas[1:]]),
            "verdad_oculta": ColeccionAppendOnly([secreto]),
        }
    )
    f = _fuentes_con(misterio, Agente.CRONISTA, capitulo=f"Relleno. {secreto}")
    with pytest.raises(assemble.FugaDelSecreto):
        assemble.ensamblar(RECETAS[Agente.CRONISTA], f)


BRIEF = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "brief" / "brief-completo.json"


def test_juez_ve_la_novela_entera_y_el_brief(novelas: Novelas) -> None:
    """El juez juzga la obra: brief, canon sin misterio, todos los personajes y los capítulos
    del 1 al pedido, completos si caben."""
    ws = novelas("demo-regalo")
    (ws.raiz / "brief").mkdir(exist_ok=True)
    (ws.raiz / "brief" / "brief.json").write_bytes(BRIEF.read_bytes())
    resultado = _briefing(ws, 3, "juez", run_id=fabrica.run_id(3))
    assert resultado.exit_code == 0, resultado.output
    texto = _fichero(ws, 3, "juez", run_id=fabrica.run_id(3)).read_text(encoding="utf-8")
    assert "## permanente · brief/brief.json" in texto
    for c in (1, 2, 3):
        capitulo = (ws.raiz / "capitulos" / f"{c:02d}.md").read_text(encoding="utf-8")
        assert capitulo.strip() in texto
    misterio = (ws.raiz / "canon" / "misterio.md").read_text(encoding="utf-8")
    assert misterio.strip() not in texto and "misterio.md" not in texto


def test_juez_sin_brief_falla(novelas: Novelas) -> None:
    ws = novelas("demo-regalo")
    resultado = _briefing(ws, 3, "juez", run_id=fabrica.run_id(3))
    assert resultado.exit_code == 4
    assert "brief/brief.json" in resultado.output
