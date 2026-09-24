"""`novela lint-prosa`: escribe qa/NN-prosa.json, no bloquea y emite un score por regla."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio import frontmatter
from novela.plataforma import langfuse
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]
BRIEF = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "brief" / "brief-completo.json"
# 25 palabras: pasa para un adulto (máx. 35) y no para un lector de 10 años (máx. 20).
FRASE = "Elena " + " ".join(["miraba"] * 23) + " fin."


class Espia:
    def __init__(self) -> None:
        self.recibidos: list[tuple[int, str, dict[str, float]]] = []

    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        self.recibidos.append((capitulo, run_id, dict(scores)))
        return []


@pytest.fixture
def espia(monkeypatch: pytest.MonkeyPatch) -> Espia:
    sink = Espia()
    monkeypatch.setattr(langfuse, "desde_entorno", lambda _entorno: sink)
    return sink


def _lint(ws: WorkspaceRepository, *args: str) -> Result:
    entorno = {"NOVELAS_DIR": str(ws.raiz.parent)}
    return CliRunner().invoke(app, ["lint-prosa", ws.slug, *args], env=entorno)


def _con_cuerpo(ws: WorkspaceRepository, cap: int, cuerpo: str) -> None:
    meta, _ = frontmatter.partir(fabrica.capitulo(fabrica.DEMO, cap))
    fabrica.escribir(ws.raiz, {f"capitulos/{cap:02d}.md": frontmatter.unir(meta, cuerpo)})


def test_escribe_el_informe_y_emite_un_score_por_regla(novelas: Novelas, espia: Espia) -> None:
    ws = novelas("demo-24")
    _con_cuerpo(ws, 3, "Un escalofrío le recorrió la espalda.\n\nLa lluvia seguía.\n")
    resultado = _lint(ws, "3")
    assert resultado.exit_code == 0, resultado.output
    informe = json.loads((ws.raiz / "qa" / "03-prosa.json").read_text("utf-8"))
    assert informe["capitulo"] == 3 and informe["bloqueante"] is False
    assert [h["codigo"] for h in informe["hallazgos"]] == ["cliche"]
    scores = {f"prosa_{r}" for r in ("repeticiones", "legibilidad", "lexico", "estilo")}
    assert set(informe["scores"]) == scores
    [(capitulo, run_id, emitidos)] = espia.recibidos
    assert capitulo == 3 and emitidos == informe["scores"]
    # El run del checkpoint del capítulo: el score cae en la misma sesión de Langfuse.
    assert run_id == json.loads((ws.raiz / "checkpoints" / "03.json").read_text())["run_id"]


def test_el_frontmatter_no_se_analiza(novelas: Novelas, espia: Espia) -> None:
    ws = novelas("demo-24")
    _con_cuerpo(ws, 2, "La lluvia seguía.\n")
    assert _lint(ws, "2").exit_code == 0
    informe = json.loads((ws.raiz / "qa" / "02-prosa.json").read_text("utf-8"))
    assert informe["hallazgos"] == []


def test_sin_capitulo_analiza_todos_los_escritos(novelas: Novelas, espia: Espia) -> None:
    ws = novelas("demo-24")
    assert _lint(ws).exit_code == 0
    assert sorted(p.name for p in (ws.raiz / "qa").glob("*-prosa.json")) == [
        f"{c:02d}-prosa.json" for c in range(1, 8)
    ]


def test_umbral_de_frase_segun_la_edad_del_brief(novelas: Novelas, espia: Espia) -> None:
    ws = novelas("demo-24")
    _con_cuerpo(ws, 3, FRASE + "\n")

    def codigos() -> list[str]:
        assert _lint(ws, "3").exit_code == 0
        informe = json.loads((ws.raiz / "qa" / "03-prosa.json").read_text("utf-8"))
        return [h["codigo"] for h in informe["hallazgos"]]

    assert "frase_larga" not in codigos()
    brief = json.loads(BRIEF.read_text("utf-8"))
    brief["destinatario"]["edad"]["valor"] = 10
    fabrica.escribir(ws.raiz, {"brief/brief.json": json.dumps(brief)})
    assert "frase_larga" in codigos()


def test_stdout_no_escribe_en_el_workspace(novelas: Novelas, espia: Espia) -> None:
    ws = novelas("demo-24")
    resultado = _lint(ws, "3", "--stdout")
    assert resultado.exit_code == 0
    assert json.loads(resultado.stdout)["capitulo"] == 3
    assert not (ws.raiz / "qa" / "03-prosa.json").exists()
