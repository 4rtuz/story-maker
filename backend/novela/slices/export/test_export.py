from collections.abc import Callable

from typer.testing import CliRunner

from novela.cli import app
from novela.plataforma.workspace import WorkspaceRepository

Novelas = Callable[[str], WorkspaceRepository]


def test_md_concatena_en_orden(novelas: Novelas) -> None:
    """Los 24 capítulos en orden, ninguno repetido y sin frontmatter: es metadato del harness."""
    ws = novelas("demo-terminado")
    resultado = CliRunner().invoke(app, ["exportar", ws.slug, "--formato", "md"])
    assert resultado.exit_code == 0, resultado.output
    texto = (ws.raiz / "export" / "novela.md").read_text(encoding="utf-8")
    titulos = [linea for linea in texto.splitlines() if linea.startswith("# Capítulo")]
    assert titulos == [f"# Capítulo {n}" for n in range(1, 25)]
    assert "run_id:" not in texto and not texto.startswith("---")
