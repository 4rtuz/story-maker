"""CLI `novela`: solo registra el cmd.py de cada slice. Nada de lógica."""

import io
import sys

import typer

from novela.plataforma.salida import con_codigos
from novela.slices.auditoria.cmd import auditar
from novela.slices.briefing.cmd import briefing
from novela.slices.checkpoint.cmd import checkpoint
from novela.slices.delta.cmd import aplicar_delta
from novela.slices.entorno.cmd import comprobar_entorno
from novela.slices.estado.cmd import estado, pendiente
from novela.slices.export.cmd import exportar
from novela.slices.nueva.cmd import nueva
from novela.slices.producir.cmd import producir
from novela.slices.validacion.cmd import validar

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
app.command()(con_codigos(validar))
app.command("aplicar-delta")(con_codigos(aplicar_delta))
app.command()(con_codigos(checkpoint))
app.command()(con_codigos(auditar))
app.command()(con_codigos(exportar))
app.command("comprobar-entorno")(con_codigos(comprobar_entorno))
app.command()(con_codigos(producir))
