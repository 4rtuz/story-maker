"""`novela nueva`: crea el árbol de architecture.md §4, `config.yaml` y `estado.db`."""

from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError

from novela.dominio.config import Config
from novela.dominio.estado import Cursor, Estado
from novela.plataforma import estado_db
from novela.plataforma.salida import USO_INCORRECTO
from novela.plataforma.workspace import CONFIG_DIR, WorkspaceRepository

ARBOL = (
    "canon/personajes",
    "plan/capitulos",
    "estado/deltas",
    "memoria/resumenes",
    "capitulos",
    "qa",
    "checkpoints",
    "runs",
    "export",
)


def _config(idea: str, obra: dict[str, Any]) -> Config:
    datos = yaml.safe_load((CONFIG_DIR / "default.yaml").read_text(encoding="utf-8"))
    datos["parametros_obra"] |= {k: v for k, v in obra.items() if v is not None}
    return Config.model_validate({**datos, "idea_semilla": idea})


def nueva(
    slug: str,
    idea: Annotated[str, typer.Option(help="Idea semilla: la única entrada humana obligatoria")],
    capitulos: Annotated[int | None, typer.Option(help="num_capitulos")] = None,
    palabras: Annotated[int | None, typer.Option(help="longitud_total_palabras")] = None,
    subgenero: Annotated[str | None, typer.Option()] = None,
    idioma: Annotated[str | None, typer.Option()] = None,
) -> None:
    ws = WorkspaceRepository.resolver(slug)  # valida el slug antes de tocar el disco
    try:
        config = _config(
            idea,
            {
                "num_capitulos": capitulos,
                "longitud_total_palabras": palabras,
                "subgenero": subgenero,
                "idioma": idioma,
            },
        )
    except ValidationError as exc:
        typer.echo(f"config inválida:\n{exc}", err=True)
        raise typer.Exit(USO_INCORRECTO) from exc
    try:
        ws.raiz.mkdir(parents=True)  # sin exist_ok: reclamar el slug es la comprobación
    except FileExistsError as exc:
        typer.echo(f"{slug}: el workspace ya existe; no se toca", err=True)
        raise typer.Exit(1) from exc
    (ws.raiz / "estado").mkdir()
    with ws.bloquear():
        for directorio in ARBOL:
            (ws.raiz / directorio).mkdir(parents=True, exist_ok=True)
        texto = yaml.safe_dump(config.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
        ws.escribir(ws.config_yaml, texto)
        estado_db.crear(ws.estado_db)
        with estado_db.abrir(ws.estado_db) as conn, estado_db.transaccion(conn):
            inicial = Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=1)
            estado_db.guardar(conn, Estado(cursor=inicial))
    typer.echo(f"{slug}: workspace creado en {ws.raiz}")
