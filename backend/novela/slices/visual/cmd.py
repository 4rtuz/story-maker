"""`novela registrar-visual <slug> --fichero <json>`: registra la validación visual de la lectura.

Valida el informe contra `InformeVisual`, lo guarda en `qa/visual.json` y emite `visual_lectura`
(fracción de comprobaciones correctas) con el run del último checkpoint. Sale con 1 si alguna
falla, y nombra a qué rol se devuelve cada una.
"""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from novela.dominio.visual import InformeVisual
from novela.plataforma import langfuse, run
from novela.plataforma.workspace import WorkspaceRepository


def registrar_visual(
    slug: str,
    fichero: Annotated[Path, typer.Option("--fichero", help="informe JSON de la validación")],
) -> None:
    """Valida el informe visual, lo guarda en qa/visual.json y emite visual_lectura."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    try:
        informe = InformeVisual.model_validate_json(fichero.read_bytes())
    except (OSError, ValidationError) as exc:
        raise typer.BadParameter(f"--fichero: {exc}") from exc
    if informe.slug != ws.slug:
        raise typer.BadParameter(f"--fichero: el informe es de {informe.slug}, no de {ws.slug}")
    with ws.bloquear():
        punto = ws.ultimo_checkpoint()
        if punto is None:
            typer.echo("registrar-visual: no hay capítulos cerrados", err=True)
            raise typer.Exit(1)
        ws.escribir(ws.raiz / "qa" / "visual.json", informe.model_dump_json(indent=2) + "\n")
    sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
    for fallo in sink.emitir(slug, punto.capitulo, punto.run_id, {"visual_lectura": informe.score}):
        typer.echo(f"aviso: {fallo}", err=True)
    correctas = sum(c.ok for c in informe.comprobaciones)
    typer.echo(f"visual: {correctas}/{len(informe.comprobaciones)} comprobaciones ok")
    if informe.devolver_a:
        typer.echo("devolver a: " + ", ".join(f"{r} ({i})" for r, i in informe.devolver_a))
        raise typer.Exit(1)
