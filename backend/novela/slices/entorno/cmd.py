"""`novela comprobar-entorno [--limpio]`: la cáscara. Sin slug, sin lock y sin run: no toca ningún
workspace ni escribe en harness.log. Que `novela` esté en el PATH lo prueba que arranque."""

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from novela.plataforma import langfuse, run
from novela.slices.entorno import comprobaciones


def _texto(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def _env_ignorado(raiz: Path) -> bool | None:
    """None sin `.env`. Sin git, o si falla, False: no se puede probar que no se versionaría."""
    if not (raiz / ".env").is_file():
        return None
    git = shutil.which("git")
    if git is None:
        return False
    try:
        r = subprocess.run(  # noqa: S603
            [git, "-C", str(raiz), "check-ignore", "-q", ".env"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def comprobar_entorno(
    limpio: Annotated[
        bool, typer.Option("--limpio", help="además, sin cambios sin commitear (canario)")
    ] = False,
) -> None:
    """Hook, python, settings.local.json y .env antes de lanzar. Un hallazgo por línea."""
    raiz = run.RAIZ_REPO
    hallazgos = comprobaciones.entorno(
        settings=_texto(raiz / ".claude" / "settings.json"),
        local=_texto(raiz / ".claude" / "settings.local.json"),
        hook_existe=(raiz / comprobaciones.HOOK).is_file(),
        python=shutil.which("python"),
        # git solo corre si hace falta.
        sucio=limpio and run.procedencia(raiz)[0],
        limpio=limpio,
        env_ignorado=_env_ignorado(raiz),
        # El mismo parser y la misma fusión que checkpoint: lo que se comprueba es lo que verá.
        scores=langfuse.entorno_efectivo(raiz),
    )
    for hallazgo in hallazgos:
        typer.echo(hallazgo)
    if hallazgos:
        raise typer.Exit(1)
