"""`novela costes`, `novela traza` y `novela prompts publicar` (docs/observabilidad.md)."""

import json
import shutil
import subprocess
from typing import Annotated

import typer

from novela.plataforma import atomic, langfuse, run
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.observabilidad import costes as _costes
from novela.slices.observabilidad import prompts as _prompts
from novela.slices.observabilidad import traza as _traza
from novela.slices.observabilidad.api import Api


def _api() -> Api:
    return Api.de(langfuse.entorno_efectivo(run.RAIZ_REPO))


def costes(
    slug: str,
    json_: Annotated[bool, typer.Option("--json", help="El informe entero en JSON")] = False,
    markdown: Annotated[
        bool, typer.Option(help="Escribe docs/evaluacion/costes-<slug>.md")
    ] = False,
) -> None:
    """Tokens, coste USD y latencia por paso, por rol y por novela, desde Langfuse."""
    ws = WorkspaceRepository.resolver(slug)
    try:
        observaciones = _costes.descargar(_api(), slug)
    except (OSError, ValueError) as exc:  # URLError y HTTPError son OSError
        typer.echo(f"Langfuse no contestó: {exc}", err=True)
        raise typer.Exit(1) from exc
    informe = _costes.agregar(slug, observaciones, _costes.sesiones_del_workspace(ws.raiz))
    if markdown:
        destino = _costes.DESTINO / f"costes-{slug}.md"
        atomic.escribir(destino, _costes.markdown(informe))
        typer.echo(f"escrito {destino}", err=json_)
    if json_:
        typer.echo(json.dumps(informe, ensure_ascii=False, indent=2))
    elif not markdown:
        for p in [*informe["pasos"], {"paso": "novela", **informe["total"]}]:
            typer.echo(
                f"{p['paso']}: {p['llamadas']} llamadas · {p['tokens_entrada']} entrada · "
                f"{p['tokens_salida']} salida · {p['coste_usd']:.4f} USD · {p['latencia_s']} s"
            )


def traza(slug: str, paso: str) -> None:
    """Abre la traza de un paso en la sesión de la novela e imprime su traceparent, para
    `export CC_LANGFUSE_TRACEPARENT=$(novela traza <slug> /novela-brief)` antes de `claude`.
    `/novela-continuar` es el capítulo siguiente; cualquier otro texto, el nombre del paso."""
    ws = WorkspaceRepository.resolver(slug)
    efectivo = langfuse.entorno_efectivo(run.RAIZ_REPO)
    padre = _traza.abrir(efectivo, slug, _traza.paso_de(ws, paso), _prompts.metadatos_de_version())
    if padre is None:
        typer.echo("sin traza: TRACE_TO_LANGFUSE no es true o Langfuse no contestó", err=True)
        return
    typer.echo(padre)


prompts_app = typer.Typer(no_args_is_help=True, help="Prompts de los roles en Langfuse.")


def _sha_corto() -> str:
    git = shutil.which("git")
    if git is None:
        return "sin-git"
    r = subprocess.run(  # noqa: S603
        [git, "-C", str(run.RAIZ_REPO), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout.strip() or "sin-git"


@prompts_app.command()
def publicar() -> None:
    """Sube cada .claude/agents/*.md como prompt de texto; sin versión nueva si no cambió."""
    try:
        resultado = _prompts.publicar(_api(), _prompts.AGENTES, _sha_corto())
    except (OSError, ValueError) as exc:
        typer.echo(f"Langfuse no aceptó la publicación: {exc}", err=True)
        raise typer.Exit(1) from exc
    for rol, version in resultado.items():
        typer.echo(f"{rol}: {version}")
