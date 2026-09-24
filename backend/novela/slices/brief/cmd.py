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
import yaml
from pydantic import BaseModel, ValidationError

from novela.dominio import frontmatter
from novela.dominio.brief import (
    Brief,
    EntradaMeta,
    Hallazgo,
    InformeBrief,
    InicioBrief,
    Ocasion,
    TipoEntrada,
)
from novela.plataforma import run
from novela.plataforma.salida import USO_INCORRECTO
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository
from novela.slices.brief import assemble, entradas, gates

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
    ficticio: Annotated[
        bool, typer.Option(help="Destinatario inventado: novela de ejemplo o de evaluación")
    ] = False,
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
            inicio = InicioBrief(ocasion=cast(Ocasion, ocasion), creado=creado, ficticio=ficticio)
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


def _entradas(ws: WorkspaceRepository) -> list[assemble.Entrada]:
    lista = []
    for ruta in sorted((ws.raiz / "brief" / "entradas").glob("ent-[0-9][0-9].md")):
        relativa = ruta.relative_to(ws.raiz).as_posix()
        try:
            meta, cuerpo = frontmatter.partir(ruta.read_text(encoding="utf-8"))
            leida = EntradaMeta.model_validate(meta)
        except (OSError, ValueError, yaml.YAMLError):  # ValidationError incluido, sin su valor
            raise WorkspaceInvalido(f"{relativa}: frontmatter inválido") from None
        if leida.id != ruta.stem:
            raise WorkspaceInvalido(f"{relativa}: dice ser {leida.id}")
        lista.append(assemble.Entrada(leida, cuerpo))
    return lista


def _texto(ruta: Path) -> str | None:
    """Lo que escribió el agente, tal cual: si no es UTF-8, el briefing lo muestra igual."""
    return ruta.read_bytes().decode("utf-8", errors="replace") if ruta.is_file() else None


def preparar(slug: str) -> None:
    """Escribe el briefing del entrevistador e imprime `<ruta> · <n> tokens`."""
    ws = WorkspaceRepository.resolver(slug)
    _brief_abierto(ws)
    inicio = _inicio(ws)
    brief = ws.raiz / "brief"
    with ws.bloquear():
        abierto = run.abrir(ws, 1, "arranque")
        with abierto.registro("brief", "preparar") as causas:
            parar = _parada(causas)
            lista = _entradas(ws)
            if not lista:
                parar(1, "el brief no tiene entradas: añádelas con novela brief entrada")
            borrador, informe = _texto(brief / "borrador.json"), _texto(brief / "informe.json")
            try:
                texto, tokens = assemble.ensamblar(
                    inicio.ocasion, lista, borrador, informe, abierto.id
                )
            except (entradas.MarcaEnTexto, assemble.PresupuestoExcedido) as exc:
                parar(1, str(exc))
            # RR sube uno por briefing distinto del run; si nada cambió, vale el último (RF-13).
            previos = sorted((abierto.dir / "briefings").glob("brief-[0-9][0-9]-entrevistador.md"))
            if previos and previos[-1].read_bytes() == texto.encode("utf-8"):
                ruta = previos[-1]
            else:
                rr = int(previos[-1].name[6:8]) + 1 if previos else 1
                ruta = abierto.dir / "briefings" / f"brief-{rr:02d}-entrevistador.md"
                ws.escribir(ruta, texto)
    typer.echo(f"{ruta.relative_to(ws.raiz).as_posix()} · {tokens} tokens")


def resumen(hallazgos: list[Hallazgo]) -> str:
    """La causa de la línea de log (PD7): `agente:` si el fallo es del borrador, `usuario:` si
    falta un dato o se contradice. Solo códigos y rutas de campo."""
    de_agente = any(h.tipo in ("esquema", "procedencia") for h in hallazgos)
    pares = [f"{h.codigo}@{c}" for h in hallazgos for c in h.campos or ["-"]]
    return f"{'agente' if de_agente else 'usuario'}: {'; '.join(pares)}"


def validar(slug: str) -> None:
    """Valida brief/borrador.json, escribe brief/informe.json y, sin hallazgos, brief/brief.json."""
    ws = WorkspaceRepository.resolver(slug)
    _brief_abierto(ws)
    inicio = _inicio(ws)
    brief = ws.raiz / "brief"
    with ws.bloquear(), run.abrir(ws, 1, "arranque").registro("brief", "validar") as causas:
        lista = _entradas(ws)
        # Custodia (RF-22): lo que el agente citó es lo que se ingirió.
        for e in lista:
            if hashlib.sha256(e.texto.encode()).hexdigest() != e.meta.sha256:
                raise WorkspaceInvalido(
                    f"brief/entradas/{e.meta.id}.md: el cuerpo no casa con su sha256; "
                    "las entradas no se editan a mano"
                )
        ruta = brief / "borrador.json"
        borrador, hallazgos = gates.esquema(ruta.read_bytes() if ruta.is_file() else None)
        if borrador is not None:
            hallazgos = (
                gates.faltantes(borrador)
                + gates.contradicciones(borrador)
                + gates.procedencia(borrador, lista)
            )
        definitivo = None
        if not hallazgos and borrador is not None:  # sin hallazgos, siempre hay borrador
            datos = borrador.model_dump(exclude={"schema_version", "preguntas"})
            entradas_ = [e.meta.model_dump() for e in lista]
            try:
                definitivo = Brief.model_validate(
                    datos
                    | {
                        "ocasion": inicio.ocasion,
                        "entradas": entradas_,
                        "ficticio": inicio.ficticio,
                    }
                )
            except ValidationError as exc:  # sin su valor: un gate dejó pasar algo que Brief no
                campos = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
                raise WorkspaceInvalido(f"brief/brief.json no valida ({campos})") from None
        preguntas = borrador.preguntas if borrador is not None else []
        informe = InformeBrief(valido=not hallazgos, hallazgos=hallazgos, preguntas=preguntas)
        ws.escribir(brief / "informe.json", informe.model_dump_json(indent=2))
        if definitivo is None:
            causa = resumen(hallazgos)
            causas.append(causa)
            typer.echo(f"{causa}\ndetalle en brief/informe.json", err=True)
            raise typer.Exit(1)
        ws.escribir(brief / "brief.json", definitivo.model_dump_json(indent=2))
    typer.echo("brief/brief.json")
