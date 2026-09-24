"""`novela validar-plan <slug>`: el gate del `trazador` en `/novela-nueva`. Sin él, una ficha mal
formada solo aparecía al pedir el briefing del escritor, ya fuera del reintento del trazador."""

import typer

from novela.dominio.plan import FichaCapitulo
from novela.plataforma import run
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository


def validar_plan(slug: str) -> None:
    """Escaleta y una ficha por capítulo contra sus modelos. 0 si valida; 1 y la causa si no."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with run.abrir(ws, 1, "arranque").registro("plan", "validar") as causas:
        errores: list[str] = []
        try:
            ws.escaleta()
        except WorkspaceInvalido as exc:
            errores.append(str(exc))
        for n in range(1, ws.config().parametros_obra.num_capitulos + 1):
            ruta = ws.raiz / "plan" / "capitulos" / f"{ws.nn(n)}.md"
            try:
                ws.leer_md(ruta, FichaCapitulo)
            except WorkspaceInvalido as exc:
                errores.append(str(exc))
        if errores:
            causas.append("; ".join(errores))
            typer.echo("\n".join(errores), err=True)
            raise typer.Exit(1)
    typer.echo("plan válido")
