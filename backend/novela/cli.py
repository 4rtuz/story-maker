"""CLI `novela`: solo registra el cmd.py de cada slice. Nada de lógica."""

import io
import sys

import typer

from novela.plataforma.salida import con_codigos
from novela.slices.auditoria.cmd import auditar
from novela.slices.brief import cmd as brief
from novela.slices.briefing.cmd import briefing
from novela.slices.checkpoint.cmd import checkpoint
from novela.slices.delta.cmd import aplicar_delta
from novela.slices.entorno.cmd import comprobar_entorno
from novela.slices.estado.cmd import estado, pendiente
from novela.slices.export.cmd import exportar
from novela.slices.formal.cmd import verificar_lean
from novela.slices.juicio.cmd import comparar_juicios, juicio
from novela.slices.nueva.cmd import nueva
from novela.slices.observabilidad import cmd as observabilidad
from novela.slices.plan.cmd import validar_plan
from novela.slices.producir.cmd import producir
from novela.slices.prohibidas import cmd as prohibidas
from novela.slices.prosa.cmd import lint_prosa
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
app.command("validar-plan")(con_codigos(validar_plan))
app.command()(con_codigos(checkpoint))
app.command()(con_codigos(auditar))
app.command()(con_codigos(exportar))
app.command("comprobar-entorno")(con_codigos(comprobar_entorno))
app.command()(con_codigos(producir))
app.command("verificar-lean")(con_codigos(verificar_lean))
app.command("lint-prosa")(con_codigos(lint_prosa))
app.command()(con_codigos(juicio))
app.command("comparar-juicios")(con_codigos(comparar_juicios))
app.command()(con_codigos(observabilidad.costes))
app.command()(con_codigos(observabilidad.traza))
app.add_typer(observabilidad.prompts_app, name="prompts")

brief_app = typer.Typer(no_args_is_help=True, help="Fase de brief de una novela de regalo.")
brief_app.command()(con_codigos(brief.iniciar))
brief_app.command()(con_codigos(brief.entrada))
brief_app.command()(con_codigos(brief.preparar))
brief_app.command()(con_codigos(brief.validar))
app.add_typer(brief_app, name="brief")

prohibidas_app = typer.Typer(no_args_is_help=True, help="Guardrail de palabras prohibidas.")
prohibidas_app.command("añadir")(con_codigos(prohibidas.anadir))
prohibidas_app.command()(con_codigos(prohibidas.listar))
prohibidas_app.command()(con_codigos(prohibidas.comprobar))
app.add_typer(prohibidas_app, name="prohibidas")
