from collections.abc import Callable

from typer.testing import CliRunner

from novela.cli import app
from novela.dominio import frontmatter
from novela.plataforma.workspace import WorkspaceRepository

Novelas = Callable[[str], WorkspaceRepository]


def test_plan_valido_sale_0(novelas: Novelas) -> None:
    novelas("demo-24")
    r = CliRunner().invoke(app, ["validar-plan", "demo-24"])
    assert r.exit_code == 0, r.output


def test_ficha_sin_cerrar_sale_1_y_la_nombra(novelas: Novelas) -> None:
    """El caso de regalo-carmen: el trazador olvidó el `---` de cierre en todas las fichas."""
    ws = novelas("demo-24")
    ruta = ws.raiz / "plan" / "capitulos" / "03.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace("\n---\n", "\n", 1).rstrip("-\n") + "\n",
        encoding="utf-8",
    )
    r = CliRunner().invoke(app, ["validar-plan", "demo-24"])
    assert r.exit_code == 1
    assert "03.md" in r.output and "sin cerrar" in r.output


def test_ficha_ausente_sale_1(novelas: Novelas) -> None:
    ws = novelas("demo-24")
    (ws.raiz / "plan" / "capitulos" / "24.md").unlink()
    r = CliRunner().invoke(app, ["validar-plan", "demo-24"])
    assert r.exit_code == 1
    assert "24.md" in r.output


def test_personaje_sin_ficha_en_el_canon_sale_1(novelas: Novelas) -> None:
    """El caso de ejemplo-carmen: el trazador puso al perro del brief como per-tango sin ficha."""
    ws = novelas("demo-24")
    ruta = ws.raiz / "plan" / "capitulos" / "05.md"
    meta, cuerpo = frontmatter.partir(ruta.read_text(encoding="utf-8"))
    meta["escenas"][0]["personajes"].append("per-tango")
    ruta.write_text(frontmatter.unir(meta, cuerpo), encoding="utf-8")
    r = CliRunner().invoke(app, ["validar-plan", "demo-24"])
    assert r.exit_code == 1
    assert "per-tango" in r.output and "05.md" in r.output
