from collections.abc import Callable
from pathlib import Path

import pytest

from novela.plataforma.workspace import SlugInvalido, WorkspaceInvalido, WorkspaceRepository


def test_resolucion_de_ruta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NOVELAS_DIR", raising=False)
    local = WorkspaceRepository.resolver("demo").raiz
    assert local.resolve() == (tmp_path / "novelas" / "demo").resolve()

    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path / "fixtures"))
    assert WorkspaceRepository.resolver("demo").raiz == tmp_path / "fixtures" / "demo"


@pytest.mark.parametrize("slug", ["../etc", "..", "a/b", "a\b", "Demo", "demo\n", "", "_cola"])
def test_slug_invalido_antes_de_tocar_disco(slug: str) -> None:
    with pytest.raises(SlugInvalido):
        WorkspaceRepository.resolver(slug)


def test_escaleta_con_el_contexto_de_la_obra(
    novelas: Callable[[str], WorkspaceRepository],
) -> None:
    """La escaleta se valida con el num_capitulos de config.yaml, que `modelo_de_md` no pasa; si la
    curva no cuadra, WorkspaceInvalido, que la API sirve como 404."""
    ws = novelas("demo-24")
    assert len(ws.escaleta().curva_tension_objetivo) == 24
    config = ws.config_yaml.read_text(encoding="utf-8")
    ws.config_yaml.write_text(config.replace("num_capitulos: 24", "num_capitulos: 25"), "utf-8")
    with pytest.raises(WorkspaceInvalido, match="curva_tension_objetivo"):
        ws.escaleta()
