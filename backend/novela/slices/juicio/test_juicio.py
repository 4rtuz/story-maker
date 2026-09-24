import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio.juicio import CRITERIOS
from novela.plataforma import langfuse
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.juicio import rubrica

Novelas = Callable[[str], WorkspaceRepository]


def juicio(evaluador: str = "juez", /, **puntuaciones: int) -> dict[str, Any]:
    return {
        "rubrica_version": rubrica.cargar().version,
        "evaluador": evaluador,
        "criterios": {
            c: {
                "puntuacion": puntuaciones.get(c, 4),
                "justificacion": f"justificación de {c}",
                "citas": [{"capitulo": 2, "texto": "Elena bajó al archivo."}],
            }
            for c in CRITERIOS
        },
    }


class SinkEspia:
    def __init__(self) -> None:
        self.scores: dict[str, float] = {}
        self.comentarios: dict[str, str] = {}
        self.donde: tuple[str, int, str] | None = None

    def emitir(
        self,
        slug: str,
        capitulo: int,
        run_id: str,
        scores: Mapping[str, float],
        comentarios: Mapping[str, str] | None = None,
    ) -> list[str]:
        self.donde = (slug, capitulo, run_id)
        self.scores |= scores
        self.comentarios |= comentarios or {}
        return []


@pytest.fixture
def espia(monkeypatch: pytest.MonkeyPatch) -> SinkEspia:
    sink = SinkEspia()
    monkeypatch.setattr(langfuse, "desde_entorno", lambda _entorno: sink)
    return sink


def _juzgar(ws: WorkspaceRepository, datos: dict[str, Any] | None) -> Result:
    if datos is not None:
        (ws.raiz / "qa" / "juicio.json").write_text(json.dumps(datos), encoding="utf-8")
    return CliRunner().invoke(app, ["juicio", ws.slug])


def test_aprobado_emite_un_score_por_criterio(novelas: Novelas, espia: SinkEspia) -> None:
    ws = novelas("demo-regalo")
    resultado = _juzgar(ws, juicio(tono=5))
    assert resultado.exit_code == 0, resultado.output
    assert "media 4.17" in resultado.output and "aprobado" in resultado.output
    assert espia.scores == {f"juez_{c}": (5.0 if c == "tono" else 4.0) for c in CRITERIOS}
    assert espia.comentarios["juez_tono"] == "justificación de tono"
    punto = ws.ultimo_checkpoint()
    assert punto is not None and espia.donde == (ws.slug, punto.capitulo, punto.run_id)


@pytest.mark.parametrize(
    ("puntuaciones", "motivo"),
    [
        ({"ritmo": 1}, "ritmo"),  # media 3.5, pero un criterio por debajo de 2
        ({c: 3 for c in CRITERIOS} | {"arco": 2}, "media 2.83"),
    ],
)
def test_por_debajo_del_umbral(
    novelas: Novelas, espia: SinkEspia, puntuaciones: dict[str, int], motivo: str
) -> None:
    resultado = _juzgar(novelas("demo-regalo"), juicio(**puntuaciones))
    assert resultado.exit_code == 1
    assert motivo in resultado.output
    assert len(espia.scores) == len(CRITERIOS)  # se emite igual: el score es la medida


@pytest.mark.parametrize(
    "datos",
    [
        None,  # no existe
        {k: v for k, v in juicio().items() if k != "criterios"},
        juicio() | {"rubrica_version": "rubrica-0"},
        juicio("humano"),
    ],
)
def test_juicio_invalido(novelas: Novelas, espia: SinkEspia, datos: dict[str, Any] | None) -> None:
    resultado = _juzgar(novelas("demo-regalo"), datos)
    assert resultado.exit_code == 4, resultado.output
    assert espia.scores == {}


def test_plantilla_humana_vacia_no_valida() -> None:
    """La plantilla lista para rellenar: sin puntuaciones no pasa el esquema, así que nadie
    confunde una revisión sin hacer con una hecha."""
    plantilla = Path(__file__).resolve().parents[4] / "docs" / "evaluacion" / "revision-humana.json"
    datos = json.loads(plantilla.read_text(encoding="utf-8"))
    assert datos["evaluador"] == "humano"
    assert list(datos["criterios"]) == list(CRITERIOS)
    assert all(v["puntuacion"] is None for v in datos["criterios"].values())


# Revisión humana FICTICIA, inventada para este test: no la ha hecho nadie.
HUMANO_FICTICIO = Path(__file__).resolve().parents[3] / "tests/fixtures/juicio/humano-FICTICIO.json"


def test_comparar_juicios(novelas: Novelas, espia: SinkEspia) -> None:
    ws = novelas("demo-regalo")
    (ws.raiz / "qa" / "juicio.json").write_text(json.dumps(juicio()), encoding="utf-8")
    resultado = CliRunner().invoke(
        app, ["comparar-juicios", ws.slug, "--humano", str(HUMANO_FICTICIO)]
    )
    assert resultado.exit_code == 0, resultado.output
    assert "tono: juez 4 · humano 2 · -2 · desacuerdo" in resultado.output
    assert "continuidad: juez 4 · humano 5 · +1 · acuerdo" in resultado.output
    assert espia.scores == {"juez_acuerdo_humano": 0.6667}  # 4 de 6 a ±1
    assert "ritmo -3" in espia.comentarios["juez_acuerdo_humano"]


def test_comparar_exige_evaluador_humano(novelas: Novelas, espia: SinkEspia) -> None:
    ws = novelas("demo-regalo")
    (ws.raiz / "qa" / "juicio.json").write_text(json.dumps(juicio()), encoding="utf-8")
    otro_juez = ws.raiz / "qa" / "otro.json"
    otro_juez.write_text(json.dumps(juicio()), encoding="utf-8")
    resultado = CliRunner().invoke(app, ["comparar-juicios", ws.slug, "--humano", str(otro_juez)])
    assert resultado.exit_code == 4
    assert espia.scores == {}
