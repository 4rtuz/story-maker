"""Códigos de salida, iguales para todos los subcomandos (spec 0001 §5.1).

0 correcto · 1 gate fallido o hallazgos · 2 uso incorrecto · 3 lock ocupado · 4 workspace
inválido o estado ilegible. Cada `cmd.py` sale con 0 o 1; las otras tres las decide esto, a partir
de la excepción, para que ningún slice las elija por su cuenta.
"""

import functools
from collections.abc import Callable

import typer

from novela.plataforma.estado_db import EstadoIlegible
from novela.plataforma.lock import WorkspaceOcupado
from novela.plataforma.run import RunInvalido
from novela.plataforma.workspace import SlugInvalido, WorkspaceInvalido

USO_INCORRECTO, LOCK_OCUPADO, WORKSPACE_INVALIDO = 2, 3, 4


def con_codigos[**P](comando: Callable[P, None]) -> Callable[P, None]:
    @functools.wraps(comando)
    def envoltura(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            comando(*args, **kwargs)
        except (SlugInvalido, RunInvalido) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(USO_INCORRECTO) from exc
        except WorkspaceOcupado as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(LOCK_OCUPADO) from exc
        except (WorkspaceInvalido, EstadoIlegible) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(WORKSPACE_INVALIDO) from exc

    return envoltura
