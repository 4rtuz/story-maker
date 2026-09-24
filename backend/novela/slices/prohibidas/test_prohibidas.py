"""Guardrail de palabras prohibidas de punta a punta, con el CLI real (docs/guardrails.md)."""

import json
import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio import frontmatter
from novela.plataforma import langfuse
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.nueva.test_nueva import _brief_valido
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]


def _cli(ws: WorkspaceRepository, *orden: str) -> Result:
    return fabrica.cli(ws.raiz.parent, *orden, run=fabrica.run_id(8))


def _capitulo_con(ws: WorkspaceRepository, linea: str) -> int:
    """El capítulo 8 de la demo con `linea` al final; devuelve su número de línea."""
    texto = fabrica.capitulo(fabrica.DEMO, 8).rstrip("\n") + "\n" + linea + "\n"
    fabrica.escribir(ws.raiz, {"capitulos/08.md": texto})
    return len(frontmatter.partir(texto)[1].splitlines())


def _hallazgos(ws: WorkspaceRepository) -> list[dict[str, str]]:
    informe = json.loads((ws.raiz / "qa" / "08-validacion.json").read_text(encoding="utf-8"))
    return [h for h in informe["hallazgos"] if h["tipo"] == "termino_prohibido"]


def _auditoria(ws: WorkspaceRepository) -> list[tuple[object, ...]]:
    with sqlite3.connect(ws.estado_db) as conn:
        return conn.execute(
            "SELECT origen, decision, nivel, termino, capitulo, detalle FROM auditoria_policy"
        ).fetchall()


class SinkEspia:
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
    return sink


def test_global_devuelve_el_capitulo_con_termino_y_linea(
    novelas: Novelas, espia: SinkEspia
) -> None:
    """Un insulto de la lista global, en mayúsculas y sin tilde: validar sale con 1, el informe
    que recibe el escritor dice qué término y dónde, queda en la auditoría y sale como score."""
    ws = novelas("demo-24")
    linea = _capitulo_con(ws, "—¡CABRONES! —gritó.")
    resultado = _cli(ws, "validar", ws.slug, "8")
    assert resultado.exit_code == 1, resultado.output
    [h] = _hallazgos(ws)
    assert (h["referencia"], h["ubicacion"]) == ("global", f"línea {linea}")
    assert "«CABRONES»" in h["descripcion"] and "«cabrón»" in h["descripcion"]
    assert _auditoria(ws) == [
        ("validar", "rechazar", "global", "cabrón", 8, f"línea {linea}: «CABRONES»")
    ]
    assert ("guardrail_prohibidas", 1.0) in espia.recibidos


def test_capitulo_limpio_pasa_sin_tocar_la_base(novelas: Novelas, espia: SinkEspia) -> None:
    """Sin coincidencias, validar no escribe en la base ni emite nada: la custodia y el
    invariante 1 siguen como antes del guardrail."""
    ws = novelas("demo-24")
    fabrica.escribir(ws.raiz, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})
    antes = fabrica.sha256(ws.estado_db)
    assert _cli(ws, "validar", ws.slug, "8").exit_code == 0
    assert fabrica.sha256(ws.estado_db) == antes
    assert _auditoria(ws) == []
    assert espia.recibidos == []


def test_cliente_desde_el_brief(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`nueva --brief` carga `prohibidos.terminos` del brief como nivel cliente, junto a la
    lista global."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    _brief_valido(tmp_path)
    assert CliRunner().invoke(app, ["nueva", "boda-prueba", "--brief"]).exit_code == 0
    resultado = CliRunner().invoke(app, ["prohibidas", "listar", "boda-prueba"])
    assert resultado.exit_code == 0, resultado.output
    lineas = resultado.output.splitlines()
    assert "cliente\thospital" in lineas
    assert "global\tcabrón" in lineas


def test_novela_se_anade_despues_y_casa_en_plural(novelas: Novelas, espia: SinkEspia) -> None:
    ws = novelas("demo-24")
    anadir = _cli(ws, "prohibidas", "añadir", ws.slug, "Villa Rosa", "farolero")
    assert anadir.exit_code == 0, anadir.output
    assert "novela\tVilla Rosa" in _cli(ws, "prohibidas", "listar", ws.slug).output.splitlines()
    _capitulo_con(ws, "Los faroleros de la villa rosa.")
    assert _cli(ws, "validar", ws.slug, "8").exit_code == 1
    assert sorted(h["descripcion"] for h in _hallazgos(ws)) == [
        "«faroleros» es el término prohibido «farolero» (novela)",
        "«villa rosa» es el término prohibido «Villa Rosa» (novela)",
    ]


def test_comprobar_recorre_sin_reescribir(novelas: Novelas) -> None:
    """La comprobación a mano sobre un workspace existente: 0 si está limpio; 1 con el capítulo,
    la línea y el término si no, y los capítulos intactos."""
    ws = novelas("demo-24")
    assert _cli(ws, "prohibidas", "comprobar", ws.slug).exit_code == 0
    linea = _capitulo_con(ws, "Qué imbéciles.")
    antes = fabrica.sha256(ws.raiz / "capitulos" / "08.md")
    resultado = _cli(ws, "prohibidas", "comprobar", ws.slug)
    assert resultado.exit_code == 1
    assert f"08 línea {linea}: «imbéciles» es el término prohibido «imbécil» (global)" in (
        resultado.output
    )
    assert fabrica.sha256(ws.raiz / "capitulos" / "08.md") == antes
    assert [fila[0] for fila in _auditoria(ws)] == ["comprobar"]


def test_auditoria_append_only(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    _capitulo_con(ws, "Qué imbéciles.")
    _cli(ws, "prohibidas", "comprobar", ws.slug)
    with sqlite3.connect(ws.estado_db) as conn:
        for orden in ("UPDATE auditoria_policy SET nivel = 'x'", "DELETE FROM auditoria_policy"):
            with pytest.raises(sqlite3.IntegrityError, match="auditoria_policy es append-only"):
                conn.execute(orden)
