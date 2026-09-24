"""`novela validar <slug> <cap>`: el gate barato, antes de gastar tres llamadas a modelo.

Escribe `qa/NN-validacion.json` siempre, pase o no, con el sha256 del fichero que validó: es lo
que la custodia de `aplicar-delta` compara (RF-31, RF-32).
"""

from dataclasses import replace
from enum import StrEnum
from typing import Annotated

import typer

from novela.dominio import frontmatter
from novela.dominio.canon import Misterio, Personaje
from novela.dominio.plan import FichaCapitulo
from novela.dominio.prohibidas import Coincidencia, buscar
from novela.dominio.qa import Hallazgo, InformeQA
from novela.plataforma import estado_db, langfuse, policy_db, run
from novela.plataforma.salida import USO_INCORRECTO
from novela.plataforma.workspace import WorkspaceRepository, sha256
from novela.slices.validacion import gates


def _contexto(ws: WorkspaceRepository, capitulo: int) -> gates.Contexto:
    raiz = ws.raiz
    ficha = ws.leer_md(raiz / "plan" / "capitulos" / f"{ws.nn(capitulo)}.md", FichaCapitulo)
    misterio = ws.leer_md(raiz / "canon" / "misterio.md", Misterio)
    # Enteros, no solo el nombre del fichero: vp_nombres necesita nombre y alias. Uno inválido
    # sale con 4, como cualquier artefacto del canon.
    fichas = {p.stem: p for p in raiz.glob("canon/personajes/*.md")}
    personajes = [ws.leer_md(fichas[id_], Personaje) for id_ in sorted(fichas)]
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        hilos = estado_db.leer(conn).hilos
    # Abiertos al empezar el capítulo, aunque su delta ya se haya aplicado.
    abiertos = frozenset(
        h.id
        for h in hilos
        if h.abierto_en < capitulo and (h.cerrado_en is None or h.cerrado_en >= capitulo)
    )
    return gates.Contexto(
        capitulo=capitulo,
        palabras=ws.config().parametros_obra.palabras_por_capitulo,
        ficha=ficha,
        personajes=frozenset(fichas),
        pistas=frozenset(p.id for p in misterio.pistas),
        hilos_abiertos=abiertos,
        formas=tuple(
            gates.FormaCanonica(p.identidad.id, texto, f"canon/personajes/{id_}.md")
            for id_, p in zip(sorted(fichas), personajes, strict=True)
            for texto in (p.identidad.nombre, *p.identidad.alias)
        ),
    )


class Origen(StrEnum):
    orquestador = "orquestador"
    hook = "hook"


def validar(
    slug: str,
    capitulo: int,
    origen: Annotated[
        Origen, typer.Option("--origen", help="hook: la línea no cuenta como intento (spec 0008)")
    ] = Origen.orquestador,
) -> None:
    """Esquema, longitud, pistas del plan, balance de hilos, ids y grafía de nombres. Sale con 1
    si hay hallazgos."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = ws.config().parametros_obra.num_capitulos
    if not 1 <= capitulo <= total:
        typer.echo(f"capítulo {capitulo} fuera de 1..{total}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    with ws.bloquear():
        abierto = run.abrir(ws, capitulo)
        nn = ws.nn(capitulo)
        # `validar-hook NN` no contiene `validar NN -> `, que es lo que cuenta el procedimiento.
        orden = "validar-hook" if origen is Origen.hook else "validar"
        with abierto.registro(orden, nn) as causas:
            ctx = replace(_contexto(ws, capitulo), prohibidos=policy_db.prohibidos(ws))
            ruta = ws.raiz / "capitulos" / f"{nn}.md"
            coincidencias: list[Coincidencia] = []
            if ruta.is_file():
                texto = ruta.read_text(encoding="utf-8")
                try:
                    meta, cuerpo = frontmatter.partir(texto)
                except ValueError:
                    meta, cuerpo = None, texto
                hallazgos = gates.validar(meta, cuerpo, ctx)
                if any(h.tipo == "termino_prohibido" for h in hallazgos):
                    coincidencias = buscar(cuerpo, ctx.prohibidos)
                sha: str | None = sha256(ruta)
            else:
                descripcion = f"no existe capitulos/{nn}.md"
                hallazgos = [
                    Hallazgo(tipo="frontmatter_invalido", gravedad="alta", descripcion=descripcion)
                ]
                sha = None
            informe = InformeQA(
                capitulo=capitulo,
                agente="validar",
                veredicto="rechazado" if hallazgos else "aprobado",
                hallazgos=hallazgos,
                capitulo_sha256=sha,
            )
            ws.escribir(ws.raiz / "qa" / f"{nn}-validacion.json", informe.model_dump_json(indent=2))
            if coincidencias:
                # Guardrail (docs/guardrails.md): al log de auditoría y a Langfuse. El score solo
                # con coincidencias; el del capítulo aprobado es vp_prohibidas, en checkpoint.
                policy_db.auditar(ws, orden, capitulo, coincidencias)
                sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
                score = {"guardrail_prohibidas": float(len(coincidencias))}
                for fallo in sink.emitir(slug, capitulo, abierto.id, score):
                    causas.append(fallo)
                    typer.echo(f"aviso: {fallo}", err=True)
            if not hallazgos:
                typer.echo(f"validar {nn}: aprobado")
                return
            tipos = sorted({h.tipo for h in hallazgos})
            causas.append(f"{len(hallazgos)} hallazgos: {', '.join(tipos)}")
            typer.echo(
                f"validar {nn}: rechazado, {len(hallazgos)} hallazgos en qa/{nn}-validacion.json"
            )
            raise typer.Exit(1)
