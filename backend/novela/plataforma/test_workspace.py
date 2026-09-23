from pathlib import Path

import pytest

from novela.plataforma.workspace import SlugInvalido, WorkspaceRepository


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
