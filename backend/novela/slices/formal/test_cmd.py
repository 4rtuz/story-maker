import json
import shutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.plataforma import langfuse
from novela.slices.formal import cronologia, lean
from tests.fixtures import fabrica

Copiar = Callable[[str], Path]


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> Path:
    raiz = tmp_path_factory.mktemp("formal")
    fabrica.construir(raiz, "demo-partida", fabrica.PARTIDA, cerrados=3)
    fabrica.construir(raiz, "demo-coherente", fabrica.PARTIDA_COHERENTE, cerrados=3)
    fabrica.construir(raiz, "demo-antigua", fabrica.HUERFANA, cerrados=3)
    return raiz


@pytest.fixture
def copiar(base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Copiar:
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))

    def copia(slug: str) -> Path:
        shutil.copytree(base / slug, tmp_path / slug)
        return tmp_path / slug

    return copia


class Espia:
    def __init__(self) -> None:
        self.scores: dict[str, float] = {}

    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        self.scores |= scores
        return []


@pytest.fixture
def espia(monkeypatch: pytest.MonkeyPatch) -> Espia:
    sink = Espia()
    monkeypatch.setattr(langfuse, "desde_entorno", lambda _entorno: sink)
    return sink


def _lean_falso(monkeypatch: pytest.MonkeyPatch, codigo: int, salida: str) -> list[str]:
    """Sustituye la compilación: devuelve `codigo` y `salida`, y guarda el fichero que recibió."""
    vistos: list[str] = []

    def compilar(fichero: Path) -> tuple[int, str]:
        vistos.append(fichero.read_text(encoding="utf-8"))
        return codigo, salida

    monkeypatch.setattr(lean, "compilar", compilar)
    return vistos


def _verificar(raiz: Path) -> tuple[Result, dict[str, Any]]:
    resultado = CliRunner().invoke(app, ["verificar-lean", raiz.name])
    informe = json.loads((raiz / "qa" / "lean.json").read_text(encoding="utf-8"))
    return resultado, informe


def test_rechazo_dice_que_invariante_falla(
    copiar: Copiar, monkeypatch: pytest.MonkeyPatch, espia: Espia
) -> None:
    raiz = copiar("demo-partida")
    _lean_falso(monkeypatch, 1, "VIOLACION|exclusion|2|2|1\nerror: …\n")
    resultado, informe = _verificar(raiz)
    assert resultado.exit_code == 1, resultado.output
    assert informe["veredicto"] == "rechazado"
    assert informe["fuente"] == "cronologia"
    assert informe["invariantes"] == {
        "orden": True,
        "edad": True,
        "ubicuidad": True,
        "exclusion": False,
    }
    [v] = informe["violaciones"]
    assert (v["evento"], v["personaje"], v["otro"]) == ("evt-03-1", fabrica.TOMAS, "evt-02-1")
    assert (raiz / "formal" / "Cronologia.lean").is_file()
    assert espia.scores["lean_cronologia"] == 0.0
    assert espia.scores["lean_exclusion"] == 0.0
    assert espia.scores["lean_orden"] == 1.0


def test_aprobado(copiar: Copiar, monkeypatch: pytest.MonkeyPatch, espia: Espia) -> None:
    raiz = copiar("demo-coherente")
    _lean_falso(monkeypatch, 0, "")
    resultado, informe = _verificar(raiz)
    assert resultado.exit_code == 0, resultado.output
    assert informe["veredicto"] == "aprobado"
    assert informe["eventos"] == 3
    assert espia.scores["lean_cronologia"] == 1.0


def test_novela_antigua_deriva_de_la_linea_temporal(
    copiar: Copiar, monkeypatch: pytest.MonkeyPatch, espia: Espia
) -> None:
    """Sin cronología en la base: un evento por escena de linea_temporal, con el lugar y los
    personajes de la ficha del plan."""
    raiz = copiar("demo-antigua")
    vistos = _lean_falso(monkeypatch, 0, "")
    resultado, informe = _verificar(raiz)
    assert resultado.exit_code == 0, resultado.output
    assert (informe["fuente"], informe["eventos"]) == ("derivada", 6)
    # esc-03-2: «dia 3, 23:00», 30 minutos, en el puerto con Elena e Inés.
    assert (
        "-- 5: evt-03-2\n    { id := 5, momento := 4260, duracion := 30, lugar := 1," in vistos[0]
    )


def test_sin_datos(copiar: Copiar, monkeypatch: pytest.MonkeyPatch, espia: Espia) -> None:
    """Ni cronología ni línea temporal datable: lo dice y no compila nada."""
    raiz = copiar("demo-antigua")
    vistos = _lean_falso(monkeypatch, 0, "")
    monkeypatch.setattr(cronologia, "momento", lambda _texto: None)  # ninguna escena datable
    resultado, informe = _verificar(raiz)
    assert resultado.exit_code == 0, resultado.output
    assert "sin datos" in resultado.output
    assert informe["veredicto"] == "sin_datos"
    assert vistos == [] and espia.scores == {}


def test_sin_lean_el_gate_falla(
    copiar: Copiar, monkeypatch: pytest.MonkeyPatch, espia: Espia
) -> None:
    raiz = copiar("demo-coherente")
    monkeypatch.setattr(lean, "buscar_lean", lambda: None)
    resultado, informe = _verificar(raiz)
    assert resultado.exit_code == 1
    assert "lean no está instalado" in resultado.output
    assert informe["veredicto"] == "error"
