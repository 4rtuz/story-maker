"""`novela estado` y `novela pendiente`: lectura del estado, sin tomar el lock ni escribir."""

from typing import Annotated

import typer

from novela.dominio.estado import Estado
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository


def _leer(ws: WorkspaceRepository) -> Estado:
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        return estado_db.leer(conn)


def _lista(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "—"


def estado(
    slug: str,
    breve: Annotated[bool, typer.Option("--breve", help="≤ 12 líneas para el orquestador")] = False,
    json: Annotated[bool, typer.Option("--json", help="documento de architecture.md §7.1")] = False,
) -> None:
    """Cursor, hilos, pistas y palabras. Por defecto, --breve."""
    if breve and json:
        raise typer.BadParameter("--breve y --json son excluyentes")
    ws = WorkspaceRepository.resolver(slug).exigir()
    actual = _leer(ws)
    if json:
        typer.echo(actual.model_dump_json(indent=2))
        return
    # --breve lo paga el orquestador en contexto muchas veces por novela: doce líneas como techo.
    total = ws.config().parametros_obra.num_capitulos
    punto = ws.ultimo_checkpoint()
    c = actual.cursor
    abiertos = sorted(h.id for h in actual.hilos if h.estado == "abierto")
    por_pagar = sorted(p for p, e in actual.pistas.items() if e.estado in ("plantada", "huerfana"))
    m = actual.metricas
    typer.echo(
        f"{slug} · capítulo {c.capitulo} de {total} · fase {c.fase} · "
        f"último paso {c.ultimo_paso or '—'} · intento {c.intento}"
    )
    cerrado = f"último checkpoint: capítulo {punto.capitulo}, run {punto.run_id}" if punto else ""
    typer.echo(
        f"cerrados: {punto.capitulo if punto else 0}/{total}" + (f" ({cerrado})" if punto else "")
    )
    typer.echo(f"hilos abiertos ({len(abiertos)}): {_lista(abiertos)}")
    typer.echo(f"pistas por pagar ({len(por_pagar)}): {_lista(por_pagar)}")
    typer.echo(f"palabras: {m.palabras_totales} (desviación {m.desviacion_vs_plan:+.3f})")


def pendiente(slug: str) -> None:
    """Sale con 0 si quedan capítulos y con 1 si no. No imprime nada: lo consume un `while`."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    punto = ws.ultimo_checkpoint()
    cerrados = punto.capitulo if punto else 0
    if cerrados >= ws.config().parametros_obra.num_capitulos:
        raise typer.Exit(1)
