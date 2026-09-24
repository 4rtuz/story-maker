"""`novela validar-plan <slug>`: el gate del `trazador` en `/novela-nueva`. Sin él, una ficha mal
formada solo aparecía al pedir el briefing del escritor, ya fuera del reintento del trazador."""

import typer

from novela.dominio.plan import FichaCapitulo
from novela.plataforma import run
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository


def validar_plan(slug: str) -> None:
    """Escaleta y fichas contra sus modelos, y cada personaje de una ficha con la suya en el
    canon. 0 si valida; 1 y la causa si no."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with run.abrir(ws, 1, "arranque").registro("plan", "validar") as causas:
        errores: list[str] = []
        try:
            ws.escaleta()
        except WorkspaceInvalido as exc:
            errores.append(str(exc))
        canon = {p.stem for p in (ws.raiz / "canon" / "personajes").glob("per-*.md")}
        for n in range(1, ws.config().parametros_obra.num_capitulos + 1):
            ruta = ws.raiz / "plan" / "capitulos" / f"{ws.nn(n)}.md"
            try:
                ficha = ws.leer_md(ruta, FichaCapitulo)
            except WorkspaceInvalido as exc:
                errores.append(str(exc))
                continue
            usados = {ficha.pov, *(p for e in ficha.escenas for p in e.personajes)}
            if sin_ficha := sorted(usados - canon):
                errores.append(f"{ruta}: sin ficha en canon/personajes/: {', '.join(sin_ficha)}")
        if errores:
            causas.append("; ".join(errores))
            typer.echo("\n".join(errores), err=True)
            raise typer.Exit(1)
    typer.echo("plan válido")
