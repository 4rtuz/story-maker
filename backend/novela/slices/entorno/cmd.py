"""`novela comprobar-entorno [--limpio]`: la cáscara. Sin slug, sin lock y sin run: no toca ningún
workspace ni escribe en harness.log. Que `novela` esté en el PATH lo prueba que arranque."""

import shutil
from pathlib import Path
from typing import Annotated

import typer

from novela.plataforma import run
from novela.slices.entorno import comprobaciones


def _texto(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def comprobar_entorno(
    limpio: Annotated[
        bool, typer.Option("--limpio", help="además, sin cambios sin commitear (canario)")
    ] = False,
) -> None:
    """Hook, python y settings.local.json antes de lanzar. Un hallazgo por línea; sale con 1."""
    raiz = run.RAIZ_REPO
    hallazgos = comprobaciones.entorno(
        settings=_texto(raiz / ".claude" / "settings.json"),
        local=_texto(raiz / ".claude" / "settings.local.json"),
        hook_existe=(raiz / comprobaciones.HOOK).is_file(),
        python=shutil.which("python"),
        # git solo corre si hace falta.
        sucio=limpio and run.procedencia(raiz)[0],
        limpio=limpio,
    )
    for hallazgo in hallazgos:
        typer.echo(hallazgo)
    if hallazgos:
        raise typer.Exit(1)
