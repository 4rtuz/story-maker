"""CLI `novela`: solo registra el cmd.py de cada slice. Nada de lógica."""

import io
import sys

import typer

from novela.plataforma.salida import con_codigos
from novela.slices.briefing.cmd import briefing
from novela.slices.estado.cmd import estado, pendiente
from novela.slices.nueva.cmd import nueva

app = typer.Typer(no_args_is_help=True, add_completion=False, pretty_exceptions_enable=False)


@app.callback()
def novela() -> None:
    """Operaciones deterministas del harness: no llaman a ningún modelo."""
    # En Windows, con la salida entubada, Python escribe en la página de códigos ANSI y el
    # orquestador lee UTF-8: las tildes llegarían rotas.
    for flujo in (sys.stdout, sys.stderr):
        if isinstance(flujo, io.TextIOWrapper):
            flujo.reconfigure(encoding="utf-8")


app.command()(con_codigos(nueva))
app.command()(con_codigos(estado))
app.command()(con_codigos(pendiente))
app.command()(con_codigos(briefing))
