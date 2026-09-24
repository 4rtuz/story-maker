"""`novela aplicar-delta <slug> <cap>`: la única vía de escritura de `estado.db` (invariante 1).

Valida el delta contra su esquema, comprueba la custodia y lo que el esquema no expresa, aplica
dentro de una única transacción y renderiza `memoria/resumenes/NN.md` desde el delta.
"""

from pathlib import Path

import typer
from pydantic import ValidationError

from novela.dominio import frontmatter
from novela.dominio.artefactos import (
    FrontmatterBriefing,
    FrontmatterCapitulo,
    Memoria,
    contar_palabras,
)
from novela.dominio.canon import Misterio
from novela.dominio.estado import Delta
from novela.dominio.qa import InformeQA
from novela.plataforma import estado_db, run
from novela.plataforma.salida import USO_INCORRECTO
from novela.plataforma.workspace import WorkspaceRepository, sha256
from novela.slices.delta import apply, custodia, violaciones

REVISORES = ("continuista", "lector-suspense", "editor-estilo")


def _hash_de_briefing(ws: WorkspaceRepository, ruta: Path) -> str | None:
    return ws.leer_md(ruta, FrontmatterBriefing).capitulo_sha256


def _cadena(ws: WorkspaceRepository, abierto: run.Run, nn: str) -> custodia.Cadena:
    capitulo = ws.raiz / "capitulos" / f"{nn}.md"
    briefings = abierto.dir / "briefings"
    cronista = briefings / f"{nn}-cronista.md"
    validacion = ws.raiz / "qa" / f"{nn}-validacion.json"
    return custodia.Cadena(
        sha_disco=sha256(capitulo) if capitulo.is_file() else None,
        sha_cronista=_hash_de_briefing(ws, cronista) if cronista.is_file() else None,
        validacion=ws.leer_json(validacion, InformeQA) if validacion.is_file() else None,
        shas_revision={
            agente: _hash_de_briefing(ws, ruta)
            for agente in REVISORES
            if (ruta := briefings / f"{nn}-{agente}.md").is_file()
        },
    )


def _derivados(ws: WorkspaceRepository, capitulo: int, fm: FrontmatterCapitulo) -> apply.Derivados:
    misterio = ws.leer_md(ws.raiz / "canon" / "misterio.md", Misterio)
    suspense = ws.raiz / "qa" / f"{ws.nn(capitulo)}-suspense.json"
    tension = None
    if suspense.is_file():
        valor = ws.leer_json(suspense, InformeQA).puntuaciones.get("tension")
        tension = None if valor is None else round(valor)
    palabras = 0
    for c in range(1, capitulo + 1):
        ruta = ws.raiz / "capitulos" / f"{ws.nn(c)}.md"
        if ruta.is_file():
            palabras += contar_palabras(frontmatter.partir(ruta.read_text(encoding="utf-8"))[1])
    objetivo = ws.config().parametros_obra.palabras_por_capitulo.objetivo
    return apply.Derivados(
        frontmatter=fm,
        pago_previsto={p.id: p.capitulo_pagado for p in misterio.pistas},
        tension=tension,
        palabras_totales=palabras,
        palabras_objetivo=objetivo * capitulo,
    )


def aplicar_delta(slug: str, capitulo: int) -> None:
    """Aplica estado/deltas/NN.json entero o no aplica nada. Sale con 1 si lo rechaza."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = ws.config().parametros_obra.num_capitulos
    if not 1 <= capitulo <= total:
        typer.echo(f"capítulo {capitulo} fuera de 1..{total}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    with ws.bloquear():
        abierto = run.abrir(ws, capitulo)
        nn = ws.nn(capitulo)
        with abierto.registro("aplicar-delta", nn) as causas:

            def rechazar(motivos: list[str]) -> None:
                causas.extend(motivos)
                typer.echo(f"aplicar-delta {nn}: no se aplica nada", err=True)
                for motivo in motivos:
                    typer.echo(f"- {motivo}", err=True)
                raise typer.Exit(1)

            ruta_delta = ws.raiz / "estado" / "deltas" / f"{nn}.json"
            if not ruta_delta.is_file():
                rechazar([f"no existe estado/deltas/{nn}.json"])
            try:
                delta = Delta.model_validate_json(ruta_delta.read_bytes())
            except ValidationError as exc:
                rechazar([f"el delta no valida contra delta.schema.json: {exc}"])
                raise
            if rotura := custodia.rotura(_cadena(ws, abierto, nn)):
                rechazar([f"custodia: {r}" for r in rotura])
            meta, cuerpo = frontmatter.partir(
                (ws.raiz / "capitulos" / f"{nn}.md").read_text(encoding="utf-8")
            )
            fm = FrontmatterCapitulo.model_validate(meta)  # pasó validar: la custodia lo asegura
            derivados = _derivados(ws, capitulo, fm)

            with estado_db.abrir(ws.estado_db) as conn:
                vigente = estado_db.leer(conn)
                motivos = violaciones.violaciones(vigente, delta, cuerpo, fm)
                tension = vigente.tension_real.entradas
                if len(tension) >= capitulo and tension[capitulo - 1] != derivados.tension:
                    motivos.append(f"tension_real del capítulo {nn} ya registrada con otro valor")
                if motivos:
                    rechazar(motivos)
                nuevo = apply.aplicar(vigente, delta, derivados)
                with estado_db.transaccion(conn):
                    estado_db.guardar(conn, nuevo)
                    estado_db.asegurar_usos(conn)  # base anterior a la spec 0007 (RF-05)
                    estado_db.registrar_usos(conn, apply.usos(delta))

            # Derivado de verdad: se reconstruye recorriendo estado/deltas/*.json, sin cuota.
            memoria = Memoria(capitulo=capitulo, **delta.resumen.model_dump())
            ruta_memoria = ws.raiz / "memoria" / "resumenes" / f"{nn}.md"
            ws.escribir(ruta_memoria, frontmatter.unir(memoria.model_dump(mode="json"), ""))
            typer.echo(
                f"aplicar-delta {nn}: {len(delta.libro_de_hechos)} hechos, "
                f"{len(delta.hilos)} hilos, {len(fm.pistas_plantadas)} pistas plantadas y "
                f"{len(fm.pistas_pagadas)} pagadas"
            )
