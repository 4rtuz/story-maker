"""Servidor MCP: consultar y descargar novelas y, si se habilita, pedir un cambio (docs/mcp.md).

Montado en la API en `/mcp` (streamable HTTP) y ejecutable por stdio con `python -m api.mcp`.
Las tools de lectura no escriben: la base se abre con `mode=ro` y el PDF se construye en memoria.
La única de escritura, `request_change`, está deshabilitada salvo con `STORY_MAKER_MCP_ESCRITURA=1`
y no toca el disco: lanza `novela cambio` como proceso, que es quien escribe.
"""

import asyncio
import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.utilities.types import File
from mcp.types import ClientCapabilities, ElicitationCapability
from pydantic import BaseModel, Field

from api.mcp.langfuse import TrazaLangfuse
from api.routers.lanzamientos import LOOPBACK
from api.routers.novelas import novelas as _novelas
from novela.dominio.canon import Mundo, Personaje
from novela.dominio.estado import Cursor
from novela.dominio.ids import SLUG_PATRON
from novela.plataforma import estado_db
from novela.plataforma.lanzador import BACKEND
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository, raiz_de_novelas

servidor = FastMCP(
    "story-maker",
    instructions="Consulta y descarga de novelas; request_change, si está habilitada, las cambia.",
    middleware=[TrazaLangfuse()],
)

Slug = Annotated[str, Field(pattern=SLUG_PATRON, description="slug de la novela")]
Capitulo = Annotated[int, Field(ge=1, le=999, description="número de capítulo")]
NumVersion = Annotated[int, Field(ge=1, description="número de versión; por defecto la vigente")]
SOLO_LECTURA = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
ESCRITURA = "STORY_MAKER_MCP_ESCRITURA"
MAX_TEXTO = 500  # el de `novela cambio`, que la API no importa (test_api_no_importa_slices)
Hecho = Annotated[str, Field(pattern=r"^hec-[0-9]{3}$", description="id del hecho que cambia")]
TextoDeCambio = Annotated[str, Field(min_length=1, max_length=MAX_TEXTO)]


class Novela(BaseModel):
    slug: str
    cursor: Cursor
    capitulos_hechos: int
    version: int


class VersionDeNovela(BaseModel):
    numero: int
    cambio: str | None  # None: la original
    creada: str | None
    estado: Literal["completa", "en_curso"]
    capitulos_cambiados: list[int]  # respecto a la anterior; vacío en la original


def _ws(slug: str) -> WorkspaceRepository:
    ws = WorkspaceRepository.resolver(slug)
    if not ws.existe():
        raise WorkspaceInvalido(f"no existe la novela {slug}")
    return ws


def _vigente(ws: WorkspaceRepository) -> int:
    """`meta.version` (spec 0007), o la 1 si la base no la tiene."""
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        fila = conn.execute("SELECT valor FROM meta WHERE clave = 'version'").fetchone()
    return int(fila[0]) if fila else 1


def _raiz(ws: WorkspaceRepository, version: int | None) -> Path:
    """Raíz de la versión: la del workspace si es la vigente, `versiones/vN/` si está guardada."""
    vigente = _vigente(ws)
    numero = vigente if version is None else version
    if not 1 <= numero <= vigente:
        raise ValueError(f"versión inexistente: v{numero} (vigente v{vigente})")
    return ws.raiz if numero == vigente else ws.raiz / "versiones" / f"v{numero}"


def _sello(ws: WorkspaceRepository, numero: int, vigente: int) -> dict[int, str]:
    """sha256 de los capítulos cerrados de una versión (spec 0007, `versiones.sello`)."""
    if numero == vigente:
        punto = ws.ultimo_checkpoint()
        return dict(punto.capitulos_sha256) if punto else {}
    ruta = ws.raiz / "versiones" / f"v{numero}" / "version.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))["capitulos_sha256"]
    return {int(c): sha for c, sha in datos.items()}


@servidor.tool(annotations=SOLO_LECTURA)
def list_novels() -> list[Novela]:
    """Las novelas del directorio de workspaces con su cursor, capítulos cerrados y versión."""
    lista = []
    for fila in _novelas():
        ws = _ws(fila.slug)
        punto = ws.ultimo_checkpoint()
        hechos = punto.capitulo if punto else 0
        lista.append(
            Novela(
                slug=fila.slug, cursor=fila.cursor, capitulos_hechos=hechos, version=_vigente(ws)
            )
        )
    return lista


@servidor.tool(annotations=SOLO_LECTURA)
def get_chapter(slug: Slug, capitulo: Capitulo, version: NumVersion | None = None) -> str:
    """Un capítulo, tal cual está en disco (frontmatter incluido), de la versión indicada."""
    ws = _ws(slug)
    ruta = _raiz(ws, version) / "capitulos" / f"{ws.nn(capitulo)}.md"
    if capitulo > ws.config().parametros_obra.num_capitulos or not ruta.is_file():
        raise ValueError(f"no existe el capítulo {capitulo}")
    return ruta.read_text(encoding="utf-8")


@servidor.tool(annotations=SOLO_LECTURA)
def list_versions(slug: Slug) -> list[VersionDeNovela]:
    """El historial de versiones y qué capítulos cambió cada una. Sin `versiones/`, una sola."""
    ws = _ws(slug)
    vigente = _vigente(ws)
    ruta = ws.raiz / "versiones" / "versiones.json"
    registro = json.loads(ruta.read_text(encoding="utf-8"))["versiones"] if ruta.is_file() else []
    punto = ws.ultimo_checkpoint()
    terminada = punto is not None and punto.capitulo >= ws.config().parametros_obra.num_capitulos
    sellos = {n: _sello(ws, n, vigente) for n in range(1, vigente + 1)}
    lista = []
    for n in range(1, vigente + 1):
        r = registro[n - 1] if n <= len(registro) else {}
        antes = sellos.get(n - 1)
        cambiados = (
            [] if antes is None else sorted(c for c, s in sellos[n].items() if antes.get(c) != s)
        )
        lista.append(
            VersionDeNovela(
                numero=n,
                cambio=r.get("cambio"),
                creada=r.get("creada"),
                estado="completa" if n < vigente or terminada else "en_curso",
                capitulos_cambiados=cambiados,
            )
        )
    return lista


@servidor.tool(annotations=SOLO_LECTURA)
def query_story_bible(
    slug: Slug,
    tipo: Literal["personajes", "lugares", "hechos", "cronologia"],
    filtro: Annotated[
        str | None, Field(max_length=200, description="subcadena, sin distinguir mayúsculas")
    ] = None,
) -> list[dict[str, Any]]:
    """La biblia de la historia desde la base de estado, en solo lectura: personajes con su
    estado y capítulos, lugares con sus capítulos, el libro de hechos o la línea temporal. Del
    canon solo sale lo que ya imprime el libro de regalo: nombres, alias y descripción."""
    ws = _ws(slug)
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        estado = estado_db.leer(conn)
        apariciones = estado_db.apariciones(conn, 999)
    capitulos: dict[str, list[int]] = {}
    for a in apariciones:
        capitulos.setdefault(a.entidad, []).append(a.capitulo)
    filas: list[dict[str, Any]]
    if tipo == "personajes":
        filas = []
        for id_, p in estado.personajes.items():
            ruta = ws.raiz / "canon" / "personajes" / f"{id_}.md"
            identidad = ws.leer_md(ruta, Personaje).identidad if ruta.is_file() else None
            filas.append(
                {
                    "id": id_,
                    "nombre": identidad.nombre if identidad else None,
                    "alias": identidad.alias if identidad else [],
                    **p.model_dump(mode="json"),
                    "capitulos": capitulos.get(id_, []),
                }
            )
    elif tipo == "lugares":
        mundo = ws.leer_md(ws.raiz / "canon" / "mundo.md", Mundo)
        filas = [
            {
                "id": e.id,
                "nombre": e.nombre,
                "descripcion": e.descripcion,
                "capitulos": capitulos.get(e.id, []),
            }
            for e in mundo.escenarios
        ]
    elif tipo == "hechos":
        filas = [h.model_dump(mode="json") for h in estado.libro_de_hechos]
    else:
        filas = [e.model_dump(mode="json") for e in estado.linea_temporal]
    if filtro:
        filas = [f for f in filas if filtro.lower() in json.dumps(f, ensure_ascii=False).lower()]
    return filas


@servidor.tool(annotations=SOLO_LECTURA)
def download_novel(slug: Slug) -> File:
    """La novela en PDF (el libro de regalo de la spec 0006) con los capítulos cerrados, como
    recurso embebido en base64. Se construye en memoria: no escribe en el workspace."""
    from api.pdf import pdf_de

    return File(data=pdf_de(_ws(slug), titulo=slug), format="pdf", name=f"{slug}.pdf")


class PlanDeCambio(BaseModel):
    plan: str  # la salida de `novela cambio --simular`: qué se regenera y qué se reaplica
    confirmacion: str  # el token que aplica exactamente esta petición con este plan
    aplicado: bool
    salida: str | None = None  # la línea de `novela cambio`, si se aplicó
    siguiente: str | None = None  # la orden que regenera, si se aplicó


def _solo_loopback() -> None:
    """Por HTTP, además de la guarda de Host/Origin del montaje, el cliente ha de ser local."""
    try:
        peticion = get_http_request()
    except RuntimeError:
        return  # stdio o en memoria: el cliente es quien arrancó el proceso
    if peticion.client is None or peticion.client.host not in LOOPBACK:
        raise ToolError("request_change solo se admite desde este equipo")


async def _novela(*argumentos: str) -> subprocess.CompletedProcess[str]:
    """El CLI del propio venv, sin shell y con los argumentos en lista, como `lanzador`."""
    entorno = {**os.environ, "NOVELAS_DIR": str(raiz_de_novelas().resolve()), "PYTHONUTF8": "1"}
    return await asyncio.to_thread(
        subprocess.run,  # noqa: S603 — orden fija, argumentos validados por el esquema
        [sys.executable, "-m", "novela", *argumentos],
        cwd=BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )


def _exigir(r: subprocess.CompletedProcess[str]) -> str:
    if r.returncode:
        raise ToolError((r.stderr or r.stdout).strip() or f"novela salió con {r.returncode}")
    return r.stdout.strip()


@servidor.tool(
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}
)
async def request_change(
    slug: Slug,
    hecho: Hecho,
    texto: TextoDeCambio,
    ctx: Context,
    motivo: Annotated[str | None, Field(max_length=MAX_TEXTO)] = None,
    confirmacion: Annotated[
        str | None, Field(max_length=64, description="el token de una llamada anterior")
    ] = None,
) -> PlanDeCambio:
    """Pide que un hecho de una novela terminada sea otro (`novela cambio`, spec 0007). Primero
    simula y devuelve el plan; solo aplica si el usuario lo confirma por elicitation o, si el
    cliente no la soporta, repitiendo la llamada con `confirmacion` igual al token devuelto.
    No regenera: devuelve la orden que lo hace."""
    if os.environ.get(ESCRITURA) != "1":
        raise ToolError(f"escritura deshabilitada: arranca el servidor con {ESCRITURA}=1")
    _solo_loopback()
    peticion = ["cambio", slug, "--hecho", hecho, "--texto", texto]
    if motivo is not None:
        peticion += ["--motivo", motivo]
    plan = _exigir(await _novela(*peticion, "--simular"))
    firmado = json.dumps([slug, hecho, texto, motivo, plan], ensure_ascii=False).encode()
    token = hashlib.sha256(firmado).hexdigest()[:16]
    simulado = PlanDeCambio(plan=plan, confirmacion=token, aplicado=False)
    if confirmacion is not None:
        if not hmac.compare_digest(confirmacion, token):
            raise ToolError("confirmación incorrecta: no es el token de esta petición y este plan")
    elif ctx.session.check_client_capability(
        ClientCapabilities(elicitation=ElicitationCapability())
    ):
        try:
            respuesta = await ctx.elicit(
                f"¿Aplicar este cambio a {slug}? {hecho}: {texto}\n\n{plan}", response_type=bool
            )
        except ToolError:
            # ponytail: la era 2026-07-28 no tiene canal de vuelta; ahí vale el token. Soportar
            # su `InputRequiredResult` si algún cliente moderno no puede repetir la llamada.
            return simulado
        if respuesta.action != "accept" or not respuesta.data:
            return simulado
    else:
        return simulado
    salida = _exigir(await _novela(*peticion))
    return simulado.model_copy(
        update={"aplicado": True, "salida": salida, "siguiente": f"novela producir {slug}"}
    )


if os.environ.get(ESCRITURA) != "1":
    servidor.disable(names={"request_change"})
