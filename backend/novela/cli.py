"""CLI `novela`: solo registra el cmd.py de cada slice. Nada de lógica."""

import typer

from novela.plataforma.salida import con_codigos
from novela.slices.nueva.cmd import nueva

app = typer.Typer(no_args_is_help=True, add_completion=False, pretty_exceptions_enable=False)


@app.callback()
def novela() -> None:
    """Operaciones deterministas del harness: no llaman a ningún modelo."""


app.command()(con_codigos(nueva))
