"""La fase de brief de principio a fin (spec 0005 §8.5), con el CLI real y un agente falso que
copia borradores prefabricados. Ningún test llama a un modelo."""

import re
from pathlib import Path

from novela.dominio.brief import BorradorBrief, Brief
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.brief import gates
from novela.slices.brief.assemble import Entrada
from novela.slices.brief.cmd import _entradas
from novela.slices.brief.test_cmd import valores_personales
from tests.fixtures.fabrica import cli

RAIZ_REPO = Path(__file__).resolve().parents[2]
FIXTURES = RAIZ_REPO / "backend" / "tests" / "fixtures" / "brief"
PROCEDIMIENTO = RAIZ_REPO / ".claude" / "commands" / "novela-brief.md"
RUN = "r-20260924-1200"
SLUG = "boda-prueba"


def test_procedimiento_novela_brief() -> None:
    """CA-02 (RF-02): el orden de las órdenes, el prompt, el criterio del log, los topes, la
    parada y la orden final; ninguna orden `novela` encadenada."""
    texto = PROCEDIMIENTO.read_text(encoding="utf-8")
    pasos = texto[texto.index("## Pasos") :]
    posiciones = [
        pasos.index("novela brief preparar"),
        pasos.index("Task `entrevistador`"),
        pasos.index("novela brief validar"),
    ]
    assert posiciones == sorted(posiciones)
    prompt = "slug: <slug>\nbriefing: novelas/<slug>/<ruta que imprimió novela brief preparar>\n"
    assert prompt + "salidas: brief/borrador.json\n" in texto
    for requisito in (
        "· agente:",
        "· usuario:",
        "2 reintentos seguidos",
        "5 rondas",
        "intervencion.md",
        "/novela-nueva <slug> --brief",
        "--setting-sources project ",
    ):
        assert requisito in texto, requisito
    # Sin las vallas: sus ``` desalinean los pares de comillas del código en línea.
    en_linea = re.sub(r"```.*?```", "", texto, flags=re.DOTALL)
    ordenes = [o for o in re.findall(r"`([^`]+)`", en_linea) if o.startswith("novela ")]
    assert ordenes
    assert [o for o in ordenes if any(s in o for s in (";", "&&", "|"))] == []


def _cli(base: Path, *orden: str) -> int:
    return cli(base, *orden, run=RUN).exit_code


def _log(base: Path, slug: str = SLUG) -> list[str]:
    return (base / slug / "runs" / RUN / "harness.log").read_text(encoding="utf-8").splitlines()


def _agente(base: Path, borrador: str, slug: str = SLUG) -> None:
    (base / slug / "brief" / "borrador.json").write_bytes((FIXTURES / borrador).read_bytes())


def _procedencia_del_brief(raiz: Path) -> list[str]:
    """Los gates de procedencia sobre el brief escrito: 0 citas en fragmentos marcados y 0 campos
    cerrados desde texto libre (RNF-01, RNF-02)."""
    brief = Brief.model_validate_json((raiz / "brief" / "brief.json").read_bytes())
    datos = brief.model_dump(exclude={"schema_version", "ocasion", "entradas", "ficticio"})
    lista: list[Entrada] = _entradas(WorkspaceRepository(raiz))
    return [h.codigo for h in gates.procedencia(BorradorBrief.model_validate(datos), lista)]


def test_flujo_completo(tmp_path: Path) -> None:
    """CA-23 (RF-23, RNF-04, RNF-12): una línea por subcomando, con el prefijo que decide el
    procedimiento y sin ningún valor personal; y el brief escrito, limpio de la carta."""
    respuestas, carta = (
        str(FIXTURES / "respuestas-completas.md"),
        str(FIXTURES / "carta-inyectada.md"),
    )
    aclaracion = tmp_path / "aclaracion.md"
    aclaracion.write_text("Respuesta: sí, la edad es la que dije.\n", encoding="utf-8")

    assert _cli(tmp_path, "brief", "iniciar", SLUG, "--ocasion", "boda") == 0
    assert (
        _cli(tmp_path, "brief", "entrada", SLUG, "--tipo", "respuesta", "--fichero", respuestas)
        == 0
    )
    assert (
        _cli(tmp_path, "brief", "entrada", SLUG, "--tipo", "texto-libre", "--fichero", carta) == 0
    )
    assert _cli(tmp_path, "brief", "preparar", SLUG) == 0
    _agente(tmp_path, "borrador-sin-edad.json")
    assert _cli(tmp_path, "brief", "validar", SLUG) == 1
    fichero = str(aclaracion)
    assert (
        _cli(tmp_path, "brief", "entrada", SLUG, "--tipo", "respuesta", "--fichero", fichero) == 0
    )
    assert _cli(tmp_path, "brief", "preparar", SLUG) == 0
    _agente(tmp_path, "borrador-limpio.json")
    assert _cli(tmp_path, "brief", "validar", SLUG) == 0
    assert _cli(tmp_path, "nueva", SLUG, "--brief") == 0
    # El arquitecto reutiliza el run de la entrevista, aunque se abriera sin canon/ (VER-14).
    assert _cli(tmp_path, "briefing", SLUG, "1", "arquitecto") == 0

    log = _log(tmp_path)
    ordenes = [re.sub(r" -> .*", "", linea).split(" ", 1)[1] for linea in log]
    assert ordenes == [
        "brief iniciar boda",
        "brief entrada respuesta",
        "brief entrada texto_libre",
        "brief preparar",
        "brief validar",
        "brief entrada respuesta",
        "brief preparar",
        "brief validar",
        "briefing 01 arquitecto",
    ]
    assert " -> 1 · usuario: falta_campo@destinatario.edad" in log[4]
    assert log[7].endswith("brief validar -> 0")
    assert _procedencia_del_brief(tmp_path / SLUG) == []

    # La otra ejecución: el borrador que obedece a la carta.
    base = tmp_path / "obediente"
    assert _cli(base, "brief", "iniciar", SLUG, "--ocasion", "boda") == 0
    assert _cli(base, "brief", "entrada", SLUG, "--tipo", "respuesta", "--fichero", respuestas) == 0
    assert _cli(base, "brief", "entrada", SLUG, "--tipo", "texto-libre", "--fichero", carta) == 0
    assert _cli(base, "brief", "preparar", SLUG) == 0
    _agente(base, "borrador-obediente.json")
    assert _cli(base, "brief", "validar", SLUG) == 1
    assert " -> 1 · agente: " in _log(base)[-1]
    assert not (base / SLUG / "brief" / "brief.json").exists()

    fugas = valores_personales(
        "borrador-sin-edad.json", "borrador-limpio.json", "borrador-obediente.json"
    )
    todo = "\n".join(_log(tmp_path) + _log(base))
    assert [v for v in fugas if v in todo] == []
