"""`novela verificar-lean <slug>`: la cronología de la novela, demostrada en Lean.

Lee la base de estado (la tabla `cronologia` o, en una novela anterior, lo que se deriva de
`linea_temporal` y del plan), genera `formal/Cronologia.lean`, lo compila contra `formal/lean/` y
escribe `qa/lean.json`. Sale con 1 si un invariante falla o si Lean no está: el gate no se salta.
Emite `lean_cronologia` y un `lean_<invariante>` por el `ScoreSink`. Docs: docs/formal/lean.md.
"""

import os
from pathlib import Path
from typing import Literal

import typer

from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.canon import Personaje
from novela.dominio.estado import EventoCronologia
from novela.dominio.plan import EscenaPlan, FichaCapitulo
from novela.plataforma import estado_db, langfuse, run
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.formal import cronologia, lean

Invariante = lean.Invariante

_DESCRIPCION = {
    "orden": "{evento} se declara posterior a {otro} y empieza antes de que {otro} termine",
    "edad": "{personaje} tiene {otro} años en {evento}, incoherente con su edad del canon",
    "ubicuidad": "{personaje} está en {evento} y en {otro} a la vez, en lugares distintos",
    "exclusion": "{personaje} aparece en {evento}, después de salir de la historia en {otro}",
}


class ViolacionLean(Modelo):
    invariante: Invariante
    evento: str
    personaje: str | None
    otro: str
    descripcion: str


class InformeLean(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    veredicto: Literal["aprobado", "rechazado", "sin_datos", "error"]
    fuente: Literal["cronologia", "derivada"] | None = None
    eventos: int = 0
    invariantes: dict[Invariante, bool] = {}
    violaciones: list[ViolacionLean] = []
    escenas_omitidas: list[str] = []
    salida_lean: str | None = None  # solo si Lean falló sin decir qué invariante


def _edades(ws: WorkspaceRepository) -> dict[str, int]:
    """El nacimiento sale del canon: `identidad.edad` es la edad en el momento 0."""
    edades = {}
    for ruta in sorted((ws.raiz / "canon" / "personajes").glob("*.md")):
        identidad = ws.leer_md(ruta, Personaje).identidad
        if identidad.edad is not None:
            edades[identidad.id] = identidad.edad
    return edades


def verificar_lean(slug: str) -> None:
    """Sale con 1 si la cronología viola un invariante o Lean no puede comprobarla."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with ws.bloquear():
        with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
            estado = estado_db.leer(conn)
            eventos = cronologia.leer(conn)
        fuente: Literal["cronologia", "derivada"] = "cronologia"
        omitidas: list[str] = []
        if not eventos:
            fuente = "derivada"
            escenas: dict[str, EscenaPlan] = {}
            for capitulo in sorted({e.capitulo for e in estado.linea_temporal}):
                ruta = ws.raiz / "plan" / "capitulos" / f"{ws.nn(capitulo)}.md"
                if ruta.is_file():
                    escenas |= {e.id: e for e in ws.leer_md(ruta, FichaCapitulo).escenas}
            eventos, omitidas = cronologia.derivar(estado.linea_temporal, escenas)
        informe = _comprobar(ws, eventos, fuente, omitidas)
        ws.escribir(ws.raiz / "qa" / "lean.json", informe.model_dump_json(indent=2))
    if informe.veredicto in ("aprobado", "rechazado"):
        scores = {"lean_cronologia": float(informe.veredicto == "aprobado")}
        scores |= {f"lean_{i}": float(ok) for i, ok in informe.invariantes.items()}
        sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
        run_id = os.environ.get("NOVELA_RUN_ID", "verificar-lean")
        for fallo in sink.emitir(slug, max(1, estado.cursor.capitulo), run_id, scores):
            typer.echo(f"aviso: {fallo}", err=True)
    _anunciar(informe)


def _comprobar(
    ws: WorkspaceRepository,
    eventos: list[EventoCronologia],
    fuente: Literal["cronologia", "derivada"],
    omitidas: list[str],
) -> InformeLean:
    base = {"fuente": fuente, "eventos": len(eventos), "escenas_omitidas": omitidas}
    if not eventos:
        return InformeLean(veredicto="sin_datos", **base)
    edades = _edades(ws)
    fichero = ws.raiz / "formal" / "Cronologia.lean"
    ws.escribir(fichero, lean.generar(ws.slug, eventos, edades))
    try:
        codigo, salida = lean.compilar(Path(fichero))
    except lean.LeanAusente as exc:
        return InformeLean(veredicto="error", salida_lean=str(exc), **base)
    halladas = lean.violaciones(salida, lean.Tabla.de(eventos, edades))
    violaciones = [
        ViolacionLean(
            invariante=v.invariante,
            evento=v.evento,
            personaje=v.personaje,
            otro=v.otro,
            descripcion=_DESCRIPCION[v.invariante].format(**vars(v)),
        )
        for v in halladas
    ]
    if codigo and not violaciones:
        return InformeLean(veredicto="error", salida_lean=salida[-4000:], **base)
    fallan = {v.invariante for v in violaciones}
    return InformeLean(
        veredicto="rechazado" if codigo else "aprobado",
        invariantes={i: i not in fallan for i in lean.INVARIANTES},
        violaciones=violaciones,
        **base,
    )


def _anunciar(informe: InformeLean) -> None:
    if informe.veredicto == "sin_datos":
        typer.echo("verificar-lean: sin datos de cronología; no hay nada que demostrar")
        return
    if informe.veredicto == "aprobado":
        typer.echo(f"verificar-lean: {informe.eventos} eventos, los cuatro invariantes demostrados")
        return
    if informe.veredicto == "error":
        typer.echo(f"verificar-lean: Lean no pudo comprobarlo: {informe.salida_lean}", err=True)
    else:
        typer.echo(f"verificar-lean: {len(informe.violaciones)} violaciones en qa/lean.json")
        for v in informe.violaciones:
            typer.echo(f"- {v.invariante}: {v.descripcion}")
    raise typer.Exit(1)
