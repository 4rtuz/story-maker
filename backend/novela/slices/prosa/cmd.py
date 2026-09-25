"""`novela lint-prosa <slug> [<cap>]`: las cuatro reglas de prosa sobre capitulos/NN.md.

Informativo: sale con 0 aunque haya hallazgos y ningún gate lo lee. Escribe `qa/NN-prosa.json`
(o lo imprime con `--stdout`) y emite `prosa_<regla>` por el `ScoreSink`, con el run del
checkpoint del capítulo si lo tiene. Umbrales de legibilidad: los del brief si existe.
"""

from typing import Annotated, Literal

import typer

from novela.dominio import frontmatter
from novela.dominio.artefactos import Checkpoint
from novela.dominio.base import SCHEMA_VERSION, Modelo, SchemaVersion
from novela.dominio.brief import Brief
from novela.plataforma import langfuse, run
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository
from novela.slices.prosa.reglas import Contexto, Hallazgo, analizar


class InformeProsa(Modelo):
    schema_version: SchemaVersion = SCHEMA_VERSION
    capitulo: int
    bloqueante: Literal[False] = False
    hallazgos: list[Hallazgo]
    scores: dict[str, float]


def contexto(ws: WorkspaceRepository) -> Contexto:
    obra = ws.config().parametros_obra
    ruta = ws.raiz / "brief" / "brief.json"
    brief = ws.leer_json(ruta, Brief) if ruta.is_file() else None
    return Contexto(
        punto_de_vista=obra.punto_de_vista,
        tiempo_verbal=obra.tiempo_verbal,
        edad=brief.destinatario.edad.valor if brief else None,
        tono=brief.tono.valor if brief else None,
    )


def lint_prosa(
    slug: str,
    capitulo: Annotated[int | None, typer.Argument()] = None,
    stdout: Annotated[bool, typer.Option("--stdout", help="imprime el JSON, no escribe")] = False,
) -> None:
    """Repeticiones, legibilidad, léxico y estilo. Sin capítulo, todos los escritos."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = ws.config().parametros_obra.num_capitulos
    if capitulo is None:
        capitulos = [
            c for c in range(1, total + 1) if (ws.raiz / "capitulos" / f"{ws.nn(c)}.md").is_file()
        ]
    elif 1 <= capitulo <= total:
        capitulos = [capitulo]
    else:
        raise typer.BadParameter(f"capítulo {capitulo} fuera de 1..{total}")
    ctx = contexto(ws)
    sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
    with ws.bloquear():
        for c in capitulos:
            nn = ws.nn(c)
            ruta = ws.raiz / "capitulos" / f"{nn}.md"
            if not ruta.is_file():
                raise WorkspaceInvalido(f"falta capitulos/{nn}.md")
            texto = ruta.read_text(encoding="utf-8")
            try:
                cuerpo = frontmatter.partir(texto)[1]
            except ValueError:
                cuerpo = texto
            analisis = analizar(cuerpo, ctx)
            informe = InformeProsa(capitulo=c, **analisis.model_dump())
            if stdout:
                typer.echo(informe.model_dump_json(indent=2))
            else:
                ws.escribir(ws.raiz / "qa" / f"{nn}-prosa.json", informe.model_dump_json(indent=2))
                typer.echo(
                    f"lint-prosa {nn}: {len(informe.hallazgos)} hallazgos en qa/{nn}-prosa.json"
                )
            punto = ws.raiz / "checkpoints" / f"{nn}.json"
            run_id = ws.leer_json(punto, Checkpoint).run_id if punto.is_file() else "lint-prosa"
            for fallo in sink.emitir(slug, c, run_id, informe.scores):
                typer.echo(f"aviso: {fallo}", err=True)
