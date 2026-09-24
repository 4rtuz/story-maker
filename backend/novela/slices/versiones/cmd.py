"""`novela versiones`: lista las versiones, sus novedades, su verificación y el diff de un capítulo
(spec 0007, RF-22, RF-36, RF-37, RF-41). Solo lectura: no toma el lock ni abre run."""

import difflib
import re
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from novela.dominio import frontmatter
from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.version import RegistroDeVersiones, Version
from novela.plataforma import estado_db, versiones
from novela.plataforma.salida import USO_INCORRECTO, WORKSPACE_INVALIDO
from novela.plataforma.workspace import WorkspaceRepository, sha256
from novela.slices.versiones.novedades import calcular


def _rechazar(causa: str, codigo: int = USO_INCORRECTO) -> NoReturn:
    typer.echo(f"versiones: {causa}", err=True)
    raise typer.Exit(codigo)


def _numero(texto: str, vigente: int) -> int:
    """`vN` o `actual`, que es la vigente; fuera de 1..vigente, versión inexistente."""
    casa = re.fullmatch(r"v([0-9]+)", texto)
    numero = vigente if texto == "actual" else int(casa[1]) if casa else 0
    if not 1 <= numero <= vigente:
        _rechazar(f"versión inexistente: {texto} (vigente v{vigente})")
    return numero


def _raiz(ws: WorkspaceRepository, numero: int, vigente: int) -> Path:
    return ws.raiz if numero == vigente else ws.raiz / "versiones" / f"v{numero}"


def _registradas(ws: WorkspaceRepository) -> RegistroDeVersiones:
    ruta = ws.raiz / "versiones" / "versiones.json"
    return ws.leer_json(ruta, RegistroDeVersiones) if ruta.exists() else RegistroDeVersiones()


def _listado(ws: WorkspaceRepository, vigente: int) -> None:
    registradas = list(_registradas(ws).versiones)
    punto = ws.ultimo_checkpoint()
    terminada = punto is not None and punto.capitulo >= ws.config().parametros_obra.num_capitulos
    for n in range(1, vigente + 1):
        r = registradas[n - 1] if n <= len(registradas) else None
        fecha = r.creada.date().isoformat() if r else "—"
        origen = r.cambio if r and r.cambio else "original"
        estado = "completa" if n < vigente or terminada else "en_curso"
        cambiados = "—"
        if n > 1:
            k = len(calcular(versiones.sello(ws, n - 1, vigente), versiones.sello(ws, n, vigente)))
            cambiados = f"{k} capítulo{'s' * (k != 1)} cambiado{'s' * (k != 1)}"
        typer.echo(f"v{n} · {fecha} · {origen} · {estado} · {cambiados}")


def _novedades(ws: WorkspaceRepository, vigente: int, desde: str | None) -> None:
    """RF-37. Cada capítulo lo atribuye al último cambio que lo alteró desde `desde`."""
    inicio = _numero(desde, vigente) if desde else vigente - 1
    if not 1 <= inicio < vigente:
        _rechazar(f"no hay versión anterior a la vigente (v{vigente}) desde la que comparar")
    sellos = {n: versiones.sello(ws, n, vigente) for n in range(inicio, vigente + 1)}
    cambios = [r.cambio for r in _registradas(ws).versiones]
    for c in calcular(sellos[inicio], sellos[vigente]):
        ultima = max(
            n for n in range(inicio + 1, vigente + 1) if sellos[n - 1].get(c) != sellos[n].get(c)
        )
        ruta = ws.raiz / "capitulos" / f"{ws.nn(c)}.md"
        titulo = ws.modelo_de_md(ruta, ruta.read_text("utf-8"), FrontmatterCapitulo).titulo
        typer.echo(f"{ws.nn(c)} · {titulo} · {cambios[ultima - 1]}")


def _verificar(ws: WorkspaceRepository, vigente: int) -> None:
    """RF-22: cada `vN/` contra su `version.json`, fichero a fichero."""
    fallos = []
    for n in range(1, vigente):
        raiz = ws.raiz / "versiones" / f"v{n}"
        version = ws.leer_json(raiz / "version.json", Version)
        presentes = {
            p.relative_to(raiz).as_posix(): p
            for p in raiz.rglob("*")
            if p.is_file() and p != raiz / "version.json"
        }
        for relativa, esperado in version.ficheros.items():
            if relativa not in presentes:
                fallos.append(f"v{n}/{relativa}: ausente")
            elif sha256(presentes[relativa]) != esperado:
                fallos.append(f"v{n}/{relativa}: distinto")
        fallos += [f"v{n}/{r}: sobrante" for r in sorted(presentes.keys() - version.ficheros)]
    for fallo in fallos:
        typer.echo(fallo, err=True)
    if fallos:
        raise typer.Exit(WORKSPACE_INVALIDO)
    typer.echo(f"verificar: {vigente - 1} versiones intactas")


def _diff(ws: WorkspaceRepository, vigente: int, a: str, b: str, capitulo: int) -> None:
    """RF-41: diff unificado de los cuerpos, sin frontmatter."""
    cuerpos = []
    for texto in (a, b):
        ruta = _raiz(ws, _numero(texto, vigente), vigente) / "capitulos" / f"{ws.nn(capitulo)}.md"
        if not ruta.is_file():
            _rechazar(f"{texto} no tiene el capítulo {ws.nn(capitulo)}")
        cuerpos.append(frontmatter.partir(ruta.read_text("utf-8"))[1].splitlines())
    nombre = f"capitulos/{ws.nn(capitulo)}.md"
    antes, despues = cuerpos
    for linea in difflib.unified_diff(
        antes, despues, f"{a}/{nombre}", f"{b}/{nombre}", lineterm=""
    ):
        typer.echo(linea)


def listar_versiones(
    slug: str,
    novedades: Annotated[
        bool, typer.Option("--novedades", help="Capítulos que cambian respecto a --desde")
    ] = False,
    desde: Annotated[str | None, typer.Option(help="vN; por defecto, la anterior")] = None,
    verificar: Annotated[
        bool, typer.Option("--verificar", help="sha256 de cada versión guardada")
    ] = False,
    diff: Annotated[
        tuple[str, str] | None, typer.Option(help="vA vB|actual, con --capitulo")
    ] = None,
    capitulo: Annotated[int | None, typer.Option(help="Capítulo del --diff")] = None,
) -> None:
    """Las versiones de la novela; con opciones, sus novedades, su verificación o un diff."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    if novedades + verificar + (diff is not None) > 1:
        _rechazar("--novedades, --verificar y --diff se excluyen")
    if desde is not None and not novedades:
        _rechazar("--desde solo va con --novedades")
    if (diff is None) != (capitulo is None):
        _rechazar("--diff y --capitulo van juntos")
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        vigente = versiones.version_vigente(conn)
    if novedades:
        _novedades(ws, vigente, desde)
    elif verificar:
        _verificar(ws, vigente)
    elif diff is not None and capitulo is not None:
        _diff(ws, vigente, *diff, capitulo)
    else:
        _listado(ws, vigente)
