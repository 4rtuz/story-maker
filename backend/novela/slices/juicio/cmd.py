"""`novela juicio <slug>` y `novela comparar-juicios <slug> --humano <fichero>` (docs/evaluacion/
juez.md). Solo leen: el juicio lo escribe el `juez` en `qa/juicio.json` y la revisión humana la
aporta el operador. Emiten sus scores por el `ScoreSink` en el run del último checkpoint.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

import typer

from novela.dominio.juicio import CRITERIOS, Evaluador, Juicio
from novela.plataforma import langfuse, run
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository
from novela.slices.juicio import rubrica


def _leer(ws: WorkspaceRepository, ruta: Path, evaluador: Evaluador) -> Juicio:
    hecho = ws.leer_json(ruta, Juicio)
    version = rubrica.cargar().version
    if hecho.rubrica_version != version:
        raise WorkspaceInvalido(f"{ruta}: rúbrica {hecho.rubrica_version}, la vigente es {version}")
    if hecho.evaluador != evaluador:
        raise WorkspaceInvalido(f"{ruta}: evaluador {hecho.evaluador}, se esperaba {evaluador}")
    return hecho


def _emitir(
    ws: WorkspaceRepository, scores: Mapping[str, float], comentarios: Mapping[str, str]
) -> None:
    punto = ws.ultimo_checkpoint()
    if punto is None:
        raise WorkspaceInvalido(f"{ws.raiz}: sin checkpoint, no hay novela que juzgar")
    sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
    for fallo in sink.emitir(ws.slug, punto.capitulo, punto.run_id, scores, comentarios):
        typer.echo(f"aviso: {fallo}", err=True)


def fallos_del_umbral(hecho: Juicio, umbral: rubrica.Umbral) -> list[str]:
    notas = [hecho.criterios[c].puntuacion for c in CRITERIOS]
    media = sum(notas) / len(notas)
    fallos = [
        f"{c} {hecho.criterios[c].puntuacion} < {umbral.minimo_por_criterio}"
        for c in CRITERIOS
        if hecho.criterios[c].puntuacion < umbral.minimo_por_criterio
    ]
    if media < umbral.media_minima:
        fallos.insert(0, f"media {media:.2f} < {umbral.media_minima}")
    return fallos


def juicio(slug: str) -> None:
    """Valida qa/juicio.json, lo resume y emite juez_<criterio>. Sale con 1 bajo el umbral."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    reglas = rubrica.cargar()
    with ws.bloquear():
        hecho = _leer(ws, ws.raiz / "qa" / "juicio.json", "juez")
        _emitir(
            ws,
            {f"juez_{c}": float(v.puntuacion) for c, v in hecho.criterios.items()},
            {f"juez_{c}": v.justificacion for c, v in hecho.criterios.items()},
        )
    notas = [hecho.criterios[c].puntuacion for c in CRITERIOS]
    typer.echo(" · ".join(f"{c} {n}" for c, n in zip(CRITERIOS, notas, strict=True)))
    fallos = fallos_del_umbral(hecho, reglas.umbral)
    typer.echo(f"juicio: media {sum(notas) / len(notas):.2f} · {reglas.version} · ", nl=False)
    if not fallos:
        typer.echo("aprobado")
        return
    typer.echo("rechazado: " + "; ".join(fallos))
    raise typer.Exit(1)


def comparar(juez: Juicio, humano: Juicio) -> dict[str, tuple[int, int, int, bool]]:
    """criterio → (juez, humano, humano − juez, acuerdo). Acuerdo es diferencia de ±1 o menos."""
    tabla: dict[str, tuple[int, int, int, bool]] = {}
    for c in CRITERIOS:
        j, h = juez.criterios[c].puntuacion, humano.criterios[c].puntuacion
        tabla[c] = (j, h, h - j, abs(h - j) <= 1)
    return tabla


def comparar_juicios(
    slug: str,
    humano: Annotated[Path, typer.Option(help="Revisión humana: JSON contra juicio.schema.json")],
) -> None:
    """Humano contra juez, criterio a criterio; emite juez_acuerdo_humano (fracción de ±1)."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with ws.bloquear():
        tabla = comparar(
            _leer(ws, ws.raiz / "qa" / "juicio.json", "juez"), _leer(ws, humano, "humano")
        )
        acuerdo = round(sum(a for *_, a in tabla.values()) / len(tabla), 4)
        detalle = ", ".join(f"{c} {d:+d}" for c, (_, _, d, _) in tabla.items())
        _emitir(ws, {"juez_acuerdo_humano": acuerdo}, {"juez_acuerdo_humano": detalle})
    for c, (j, h, d, a) in tabla.items():
        typer.echo(f"{c}: juez {j} · humano {h} · {d:+d} · {'acuerdo' if a else 'desacuerdo'}")
    typer.echo(f"acuerdo ±1: {acuerdo:.2f}")
