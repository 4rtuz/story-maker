"""`novela nueva`: crea el árbol de architecture.md §4, `config.yaml` y `estado.db`."""

from typing import Annotated, Any, NoReturn

import typer
import yaml
from pydantic import ValidationError

from novela.dominio.brief import NUM_CAPITULOS, OBJETIVO, PALABRAS_MAX, PALABRAS_MIN, Brief
from novela.dominio.brief import idea_semilla as semilla_del_brief
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


def _crear(ws: WorkspaceRepository, config: Config) -> None:
    (ws.raiz / "estado").mkdir(exist_ok=True)  # un workspace de brief ya lo tiene
    with ws.bloquear():
        for directorio in ARBOL:
            (ws.raiz / directorio).mkdir(parents=True, exist_ok=True)
        texto = yaml.safe_dump(config.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
        ws.escribir(ws.config_yaml, texto)
        estado_db.crear(ws.estado_db)
        with estado_db.abrir(ws.estado_db) as conn, estado_db.transaccion(conn):
            inicial = Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=1)
            estado_db.guardar(conn, Estado(cursor=inicial))


def _desde_brief(ws: WorkspaceRepository, idioma: str | None) -> Config:
    """La obra que pide el brief (RF-25). Ningún mensaje lleva valores del brief: son datos
    personales y stderr acaba en la conversación."""

    def parar(causa: str) -> NoReturn:
        typer.echo(f"{ws.slug}: {causa}", err=True)
        raise typer.Exit(1)

    ruta = ws.raiz / "brief" / "brief.json"
    if not ruta.is_file():
        parar("falta brief/brief.json; valídalo con novela brief validar")
    if ws.config_yaml.exists() or ws.estado_db.exists():
        parar("la novela ya existe; no se toca")
    try:
        brief = Brief.model_validate_json(ruta.read_bytes())
    except (OSError, ValidationError):
        parar("brief/brief.json no valida contra Brief")
    objetivo = OBJETIVO[brief.extension.valor]
    obra = {
        "num_capitulos": NUM_CAPITULOS,
        "palabras_por_capitulo": {"objetivo": objetivo, "min": PALABRAS_MIN, "max": PALABRAS_MAX},
        "longitud_total_palabras": NUM_CAPITULOS * objetivo,
        "subgenero": brief.genero.valor,
        "restricciones_contenido": list(brief.prohibidos.terminos),
        "idioma": idioma,
    }
    return _config(semilla_del_brief(brief), obra)


def nueva(
    slug: str,
    idea: Annotated[
        str | None, typer.Option(help="Idea semilla; obligatoria salvo con --brief")
    ] = None,
    brief: Annotated[
        bool, typer.Option("--brief", help="Deriva la obra de brief/brief.json (spec 0005)")
    ] = False,
    capitulos: Annotated[int | None, typer.Option(help="num_capitulos")] = None,
    palabras: Annotated[int | None, typer.Option(help="longitud_total_palabras")] = None,
    subgenero: Annotated[str | None, typer.Option()] = None,
    idioma: Annotated[str | None, typer.Option()] = None,
) -> None:
    ws = WorkspaceRepository.resolver(slug)  # valida el slug antes de tocar el disco
    if brief:
        if any(v is not None for v in (idea, capitulos, palabras, subgenero)):
            typer.echo("--brief no admite --idea, --capitulos, --palabras ni --subgenero", err=True)
            raise typer.Exit(USO_INCORRECTO)
        _crear(ws, _desde_brief(ws, idioma))
        typer.echo(f"{slug}: novela creada desde el brief en {ws.raiz}")
        return
    if idea is None:
        typer.echo("falta --idea (o --brief, para una novela de regalo)", err=True)
        raise typer.Exit(USO_INCORRECTO)
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
    _crear(ws, config)
    typer.echo(f"{slug}: workspace creado en {ws.raiz}")
