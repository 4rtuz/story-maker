"""`novela aplicar-delta <slug> <cap>`: la única vía de escritura de `estado.db` (invariante 1).

Valida el delta contra su esquema, comprueba la custodia y lo que el esquema no expresa, aplica
dentro de una única transacción y renderiza `memoria/resumenes/NN.md` desde el delta.
"""

from fnmatch import fnmatchcase
from pathlib import Path
from typing import Annotated

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
from novela.dominio.estado import Delta, Estado
from novela.dominio.plan import FichaCapitulo
from novela.dominio.qa import InformeQA
from novela.dominio.version import PeticionDeCambio, Version
from novela.plataforma import estado_db, run, versiones
from novela.plataforma.salida import USO_INCORRECTO, WORKSPACE_INVALIDO
from novela.plataforma.workspace import WorkspaceRepository, sha256
from novela.slices.delta import apply, custodia, violaciones
from novela.slices.formal import cronologia

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


def _fuera_de_modo(
    ws: WorkspaceRepository, cambio: PeticionDeCambio | None, capitulo: int, reaplicar: bool
) -> str | None:
    """RF-26, antes del lock y del run: un rechazo de modo no escribe nada (D11)."""
    if not reaplicar:
        if cambio and capitulo in cambio.plan.reaplicar:
            return f"el capítulo {ws.nn(capitulo)} es reaplicable: usa --reaplicar"
        return None
    if cambio is None:
        return "--reaplicar sin un cambio en curso"
    if capitulo in cambio.plan.regenerar:
        return f"el capítulo {ws.nn(capitulo)} es afectado por {cambio.id}: se regenera"
    punto = ws.ultimo_checkpoint()
    siguiente = (punto.capitulo if punto else 0) + 1
    if capitulo != siguiente:
        return f"--reaplicar fuera de orden: el siguiente es el {ws.nn(siguiente)}"
    return None


def _copiar_de_la_version(ws: WorkspaceRepository, version: int, nn: str) -> list[str]:
    """RF-25: capítulo, delta y qa/ del capítulo, desde `versiones/vN/`, si casan con su
    `version.json`. Se comprueba todo antes de escribir nada. Devuelve lo que no casa."""
    origen = ws.raiz / "versiones" / f"v{version}"
    ficheros = ws.leer_json(origen / "version.json", Version).ficheros
    propios = {f"capitulos/{nn}.md", f"estado/deltas/{nn}.json"}
    rutas = sorted(r for r in ficheros if r in propios or fnmatchcase(r, f"qa/{nn}-*.json"))
    distintos = [
        r for r in rutas if not (origen / r).is_file() or sha256(origen / r) != ficheros[r]
    ]
    distintos += [f"{r}: no está en version.json" for r in sorted(propios - set(rutas))]
    if not distintos:
        for relativa in rutas:
            ws.escribir(ws.raiz / relativa, (origen / relativa).read_bytes())
    return distintos


def _base_anterior(ws: WorkspaceRepository, version: int) -> Estado:
    """La base de `versiones/vN/`, en solo lectura: está en modo DELETE y no deja -wal ni -shm."""
    ruta = ws.raiz / "versiones" / f"v{version}" / ws.estado_db.relative_to(ws.raiz)
    with estado_db.abrir(ruta, solo_lectura=True) as conn:
        return estado_db.leer(conn)


def aplicar_delta(
    slug: str,
    capitulo: int,
    reaplicar: Annotated[
        bool, typer.Option("--reaplicar", help="Copia el capítulo de la versión anterior")
    ] = False,
) -> None:
    """Aplica estado/deltas/NN.json entero o no aplica nada. Sale con 1 si lo rechaza."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = ws.config().parametros_obra.num_capitulos
    if not 1 <= capitulo <= total:
        typer.echo(f"capítulo {capitulo} fuera de 1..{total}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    cambio = versiones.cambio_en_curso(ws)
    if motivo := _fuera_de_modo(ws, cambio, capitulo, reaplicar):
        typer.echo(f"aplicar-delta: {motivo}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    with ws.bloquear():
        abierto = run.abrir(ws, capitulo)
        nn = ws.nn(capitulo)
        orden = ("aplicar-delta", nn, "--reaplicar") if reaplicar else ("aplicar-delta", nn)
        with abierto.registro(*orden) as causas:

            def rechazar(motivos: list[str], codigo: int = 1) -> None:
                causas.extend(motivos)
                typer.echo(f"aplicar-delta {nn}: no se aplica nada", err=True)
                for motivo in motivos:
                    typer.echo(f"- {motivo}", err=True)
                raise typer.Exit(codigo)

            if reaplicar and cambio is not None:  # _fuera_de_modo exige el cambio
                if distintos := _copiar_de_la_version(ws, cambio.version_base, nn):
                    rechazar(
                        [f"instantánea distinta de version.json: {d}" for d in distintos],
                        WORKSPACE_INVALIDO,
                    )

            ruta_delta = ws.raiz / "estado" / "deltas" / f"{nn}.json"
            if not ruta_delta.is_file():
                rechazar([f"no existe estado/deltas/{nn}.json"])
            try:
                delta = Delta.model_validate_json(ruta_delta.read_bytes())
            except ValidationError as exc:
                rechazar([f"el delta no valida contra delta.schema.json: {exc}"])
                raise
            # Reaplicado, el capítulo ya pasó su custodia en la versión de la que se copia.
            if not reaplicar and (rotura := custodia.rotura(_cadena(ws, abierto, nn))):
                rechazar([f"custodia: {r}" for r in rotura])
            meta, cuerpo = frontmatter.partir(
                (ws.raiz / "capitulos" / f"{nn}.md").read_text(encoding="utf-8")
            )
            fm = FrontmatterCapitulo.model_validate(meta)  # pasó validar: la custodia lo asegura
            derivados = _derivados(ws, capitulo, fm)
            # Antes de abrir la base: sin ficha válida, salida 4 sin tocar nada (spec 0006, RF-21).
            ficha = ws.leer_md(ws.raiz / "plan" / "capitulos" / f"{nn}.md", FichaCapitulo)
            aparecen = apply.apariciones(capitulo, fm, ficha, delta)

            with estado_db.abrir(ws.estado_db) as conn:
                vigente = estado_db.leer(conn)
                motivos = violaciones.violaciones(vigente, delta, cuerpo, fm)
                if reaplicar:
                    motivos += violaciones.hilos_sin_abrir(vigente, delta)
                elif cambio and capitulo in cambio.plan.regenerar:
                    motivos += violaciones.de_regeneracion(
                        delta, cambio, _base_anterior(ws, cambio.version_base), vigente
                    )
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
                    estado_db.asegurar_apariciones(conn)  # bases anteriores a la spec 0006
                    estado_db.registrar_apariciones(conn, aparecen)
                    cronologia.asegurar(conn)  # bases anteriores a docs/formal/lean.md
                    cronologia.registrar(conn, delta)

            # Derivado de verdad: se reconstruye recorriendo estado/deltas/*.json, sin cuota.
            memoria = Memoria(capitulo=capitulo, **delta.resumen.model_dump())
            ruta_memoria = ws.raiz / "memoria" / "resumenes" / f"{nn}.md"
            ws.escribir(ruta_memoria, frontmatter.unir(memoria.model_dump(mode="json"), ""))
            typer.echo(
                f"aplicar-delta {nn}: {len(delta.libro_de_hechos)} hechos, "
                f"{len(delta.hilos)} hilos, {len(fm.pistas_plantadas)} pistas plantadas y "
                f"{len(fm.pistas_pagadas)} pagadas"
            )
