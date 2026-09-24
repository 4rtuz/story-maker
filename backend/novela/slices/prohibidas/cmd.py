"""`novela prohibidas`: las listas del guardrail y su comprobación a mano (docs/guardrails.md).

`comprobar` recorre los capítulos escritos de un workspace existente sin tocarlos: solo añade sus
coincidencias al log de auditoría. Es lo que se aplica a una novela anterior al guardrail.
"""

from typing import Annotated

import typer

from novela.dominio import frontmatter
from novela.dominio.prohibidas import buscar
from novela.plataforma import policy_db
from novela.plataforma.workspace import WorkspaceRepository


def anadir(
    slug: str, terminos: Annotated[list[str], typer.Argument(help="Palabras o frases")]
) -> None:
    """Añade términos al nivel novela: los que surgen después del brief."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with ws.bloquear(), policy_db.escribir(ws) as conn:
        policy_db.anadir(conn, terminos, "novela")
    typer.echo(f"{slug}: {len(terminos)} términos en el nivel novela")


def listar(slug: str) -> None:
    """Un término por línea: `nivel<TAB>término`."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with ws.bloquear():
        for t in policy_db.prohibidos(ws):
            typer.echo(f"{t.nivel}\t{t.texto}")


def comprobar(slug: str) -> None:
    """Todos los capítulos escritos contra las listas. Sale con 1 si hay alguna coincidencia."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = 0
    with ws.bloquear():
        terminos = policy_db.prohibidos(ws)
        for ruta in sorted((ws.raiz / "capitulos").glob("*.md")):
            texto = ruta.read_text(encoding="utf-8")
            try:
                cuerpo = frontmatter.partir(texto)[1]
            except ValueError:
                cuerpo = texto
            coincidencias = buscar(cuerpo, terminos)
            for c in coincidencias:
                typer.echo(
                    f"{ruta.stem} línea {c.linea}: «{c.forma}» es el término prohibido "
                    f"«{c.termino.texto}» ({c.termino.nivel})"
                )
            if coincidencias and ruta.stem.isdigit():
                policy_db.auditar(ws, "comprobar", int(ruta.stem), coincidencias)
            total += len(coincidencias)
    typer.echo(f"{slug}: {total} coincidencias")
    if total:
        raise typer.Exit(1)
