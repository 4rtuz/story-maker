"""`novela portada <slug> [--forzar]`: la ilustración de la cubierta en `portada.jpg`.

La pide a Pollinations.ai (D2): una GET sin clave que devuelve la imagen. Es la única red del CLI
además de Langfuse. Lo que no empiece como un JPEG no se escribe.
"""

import urllib.request
from collections.abc import Callable
from typing import Annotated

import typer

from novela.dominio.canon import Mundo, Personaje
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.portada import nucleo

# La generación tarda: la primera petición de un prompt nuevo espera a que se pinte la imagen.
TIMEOUT_S = 180.0
AGENTE = "story-maker-novela/0.1 (portada)"


class SinPortada(Exception):
    """El servicio contestó algo que no es un JPEG."""


def descargar(url: str) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})  # noqa: S310
    with urllib.request.urlopen(peticion, timeout=TIMEOUT_S) as respuesta:  # noqa: S310
        datos: bytes = respuesta.read()
        return datos


def prompt_de(ws: WorkspaceRepository) -> str:
    """Subgénero del config y escenarios del canon; los personajes solo para quitar sus nombres."""
    mundo = ws.leer_md(ws.raiz / "canon" / "mundo.md", Mundo)
    nombres = []
    for ficha in sorted((ws.raiz / "canon" / "personajes").glob("*.md")):
        identidad = ws.leer_md(ficha, Personaje).identidad
        nombres += [identidad.nombre, *identidad.alias]
    return nucleo.prompt(
        ws.config().parametros_obra.subgenero, [e.descripcion for e in mundo.escenarios], nombres
    )


def generar(
    ws: WorkspaceRepository, forzar: bool = False, pedir: Callable[[str], bytes] | None = None
) -> bool:
    """True si escribió la portada; False si ya había y no se forzó. Los fallos se lanzan
    (OSError de red, SinPortada): decide quien llama."""
    destino = ws.exigir().raiz / "portada.jpg"
    if destino.exists() and not forzar:
        return False
    datos = (pedir or descargar)(nucleo.url(ws.slug, prompt_de(ws)))
    if not nucleo.es_jpeg(datos):
        raise SinPortada(f"la respuesta no es un JPEG ({len(datos)} bytes)")
    with ws.bloquear():
        ws.escribir(destino, datos)
    return True


def portada(
    slug: str,
    forzar: Annotated[bool, typer.Option(help="Sustituye la portada existente")] = False,
) -> None:
    """Ilustración de cubierta de Pollinations.ai en novelas/<slug>/portada.jpg, sin texto."""
    ws = WorkspaceRepository.resolver(slug)
    try:
        escrita = generar(ws, forzar)
    except (OSError, SinPortada) as exc:  # URLError, HTTPError y el plazo son OSError
        typer.echo(f"sin portada: {exc}", err=True)
        raise typer.Exit(1) from exc
    destino = ws.raiz / "portada.jpg"
    typer.echo(f"escrita {destino}" if escrita else f"ya existe {destino}; --forzar la sustituye")
