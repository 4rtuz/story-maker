"""`novela brief`: la cáscara de la fase de brief (spec 0005). Lee, llama a las funciones puras y
escribe.

El brief lleva datos personales, así que nada de lo que lee llega al log ni a stderr: ni valores,
ni texto de las entradas, ni la ruta del fichero ingerido (RF-23, PD3). Solo ids, códigos y rutas
de campo.
"""

import hashlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn, cast, get_args

import typer
from pydantic import BaseModel, ValidationError

from novela.dominio import frontmatter
from novela.dominio.brief import EntradaMeta, InicioBrief, Ocasion, TipoEntrada
from novela.plataforma import run
from novela.plataforma.salida import USO_INCORRECTO
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository
from novela.slices.brief import entradas

MAX_ENTRADAS, MAX_CARACTERES = 20, 20000
TIPOS: dict[str, TipoEntrada] = {"respuesta": "respuesta", "texto-libre": "texto_libre"}


def _brief_abierto(ws: WorkspaceRepository) -> None:
    """Antes del lock y del run: una novela ya creada no se toca, ni su manifiesto (RF-07)."""
    if ws.config_yaml.exists():
        typer.echo("brief cerrado: la novela ya existe", err=True)
        raise typer.Exit(1)


def leer[M: BaseModel](ws: WorkspaceRepository, ruta: Path, modelo: type[M]) -> M:
    """Como `ws.leer_json`, pero el error solo nombra la ruta relativa y los campos: el mensaje
    de Pydantic incluye el valor, y aquí el valor puede ser un nombre."""
    relativa = ruta.relative_to(ws.raiz).as_posix()
    try:
        return modelo.model_validate_json(ruta.read_bytes())
    except OSError:
        raise WorkspaceInvalido(f"{relativa}: no se puede leer") from None
    except ValidationError as exc:
        campos = ", ".join(".".join(map(str, e["loc"])) or "-" for e in exc.errors())
        raise WorkspaceInvalido(f"{relativa}: no valida ({campos})") from None


def _inicio(ws: WorkspaceRepository) -> InicioBrief:
    ruta = ws.raiz / "brief" / "inicio.json"
    if not ruta.is_file():
        raise WorkspaceInvalido(f"{ws.slug}: no hay brief (falta brief/inicio.json)")
    return leer(ws, ruta, InicioBrief)


def _parada(causas: list[str]) -> Callable[[int, str], NoReturn]:
    def parar(codigo: int, causa: str) -> NoReturn:
        causas.append(causa)
        typer.echo(causa, err=True)
        raise typer.Exit(codigo)

    return parar


def iniciar(
    slug: str,
    ocasion: Annotated[str, typer.Option(help="hijo, pareja, boda, aniversario o jubilacion")],
) -> None:
    """Crea el workspace del brief: brief/entradas/, estado/, runs/ y brief/inicio.json."""
    ws = WorkspaceRepository.resolver(slug)  # valida el slug antes de tocar el disco
    if ocasion not in get_args(Ocasion):
        typer.echo(f"ocasión inválida; se espera una de {', '.join(get_args(Ocasion))}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    try:
        ws.raiz.mkdir(parents=True)  # sin exist_ok: reclamar el slug es la comprobación
    except FileExistsError as exc:
        typer.echo(f"{slug}: el workspace ya existe; no se toca", err=True)
        raise typer.Exit(1) from exc
    for directorio in ("brief/entradas", "estado", "runs"):
        (ws.raiz / directorio).mkdir(parents=True)
    # ponytail: si inicio.json no llega a escribirse, el slug queda reclamado; se borra a mano.
    with ws.bloquear():
        with run.abrir(ws, 1, "arranque").registro("brief", "iniciar", ocasion):
            creado = datetime.now().astimezone().isoformat(timespec="seconds")
            inicio = InicioBrief(ocasion=cast(Ocasion, ocasion), creado=creado)
            ws.escribir(ws.raiz / "brief" / "inicio.json", inicio.model_dump_json(indent=2))
    typer.echo(f"{slug}: brief iniciado en {ws.raiz}")


def entrada(
    slug: str,
    tipo: Annotated[str, typer.Option(help="respuesta o texto-libre")],
    fichero: Annotated[Path, typer.Option(help="Lo que aporta el cliente, en UTF-8")],
) -> None:
    """Ingiere un fichero del cliente como brief/entradas/ent-NN.md e imprime su id."""
    ws = WorkspaceRepository.resolver(slug)
    _brief_abierto(ws)
    if tipo not in TIPOS:
        typer.echo("tipo inválido; se espera respuesta o texto-libre", err=True)
        raise typer.Exit(USO_INCORRECTO)
    _inicio(ws)
    directorio = ws.raiz / "brief" / "entradas"
    with ws.bloquear(), run.abrir(ws, 1, "arranque").registro("brief", "entrada", TIPOS[tipo]) as c:
        parar = _parada(c)
        try:
            crudo = fichero.read_bytes()
        except OSError:
            parar(USO_INCORRECTO, "el fichero no existe o no se puede leer")
        try:
            texto = entradas.normalizar_entrada(crudo.decode("utf-8-sig"))  # BOM fuera
        except UnicodeDecodeError:
            parar(USO_INCORRECTO, "el fichero no es UTF-8 válido")
        if not texto.strip():
            parar(USO_INCORRECTO, "el fichero queda vacío tras normalizar")
        if len(texto) > MAX_CARACTERES:
            parar(USO_INCORRECTO, f"{len(texto)} caracteres; el máximo es {MAX_CARACTERES}")
        existentes = sorted(directorio.glob("ent-[0-9][0-9].md"))
        if len(existentes) >= MAX_ENTRADAS:
            parar(1, f"el brief ya tiene {MAX_ENTRADAS} entradas")
        id_ = f"ent-{max((int(p.stem[4:]) for p in existentes), default=0) + 1:02d}"
        meta = EntradaMeta(
            id=id_,
            tipo=TIPOS[tipo],
            sha256=hashlib.sha256(texto.encode()).hexdigest(),
            caracteres=len(texto),
        )
        ws.escribir(directorio / f"{id_}.md", frontmatter.unir(meta.model_dump(mode="json"), texto))
    typer.echo(id_)
