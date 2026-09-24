"""`novela checkpoint <slug> <cap>`: confirma el capítulo, una sola vez y con el delta aplicado.

Escribe `checkpoints/NN.json` y `latest.json` —cursor, versiones, run y el sello de los
capítulos cerrados— y emite los seis scores por el `ScoreSink`. El checkpoint se escribe antes de
emitir: si Langfuse no contesta, el capítulo cierra igual y el fallo queda en `harness.log`.
"""

import typer

from novela.dominio import frontmatter
from novela.dominio.artefactos import Checkpoint, contar_palabras
from novela.dominio.estado import Cursor
from novela.dominio.qa import InformeQA
from novela.plataforma import estado_db, langfuse, run, versiones
from novela.plataforma.salida import USO_INCORRECTO, WORKSPACE_INVALIDO
from novela.plataforma.workspace import WorkspaceRepository, huella, sha256

_VEREDICTO = {"aprobado": 1.0, "aprobado_con_reservas": 0.5, "rechazado": 0.0}


def serializar(punto: Checkpoint) -> str:
    return punto.model_dump_json(indent=2)


def restaurar(texto: str | bytes) -> Checkpoint:
    return Checkpoint.model_validate_json(texto)


def calcular_scores(
    suspense: InformeQA | None,
    continuidad: InformeQA | None,
    estilo: InformeQA | None,
    palabras: int,
    objetivo: int,
) -> dict[str, float]:
    """Los seis de RF-21. tension, fair_play y coherencia los puntúa el lector-suspense;
    continuidad y estilo salen del veredicto de su gate; longitud, de la distancia al objetivo.
    Lo que no tiene de dónde salir no se emite."""
    scores: dict[str, float] = {}
    if suspense:
        scores |= {
            k: v
            for k, v in suspense.puntuaciones.items()
            if k in ("tension", "fair_play", "coherencia")
        }
    if continuidad:
        scores["continuidad"] = _VEREDICTO[continuidad.veredicto]
    if estilo:
        scores["estilo"] = _VEREDICTO[estilo.veredicto]
    if objetivo:
        scores["longitud"] = round(max(0.0, 1 - abs(palabras / objetivo - 1)), 4)
    return scores


def _informe(ws: WorkspaceRepository, nn: str, nombre: str) -> InformeQA | None:
    ruta = ws.raiz / "qa" / f"{nn}-{nombre}.json"
    return ws.leer_json(ruta, InformeQA) if ruta.is_file() else None


def checkpoint(slug: str, capitulo: int) -> None:
    """Cierra el capítulo: después de esto, el siguiente puede empezar y este no se toca."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    obra = ws.config().parametros_obra
    if not 1 <= capitulo <= obra.num_capitulos:
        typer.echo(f"capítulo {capitulo} fuera de 1..{obra.num_capitulos}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    with ws.bloquear():
        abierto = run.abrir(ws, capitulo)
        nn = ws.nn(capitulo)
        with abierto.registro("checkpoint", nn) as causas:

            def parar(codigo: int, causa: str) -> None:
                causas.append(causa)
                typer.echo(causa, err=True)
                raise typer.Exit(codigo)

            with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
                cursor = estado_db.leer(conn).cursor
                version = versiones.version_vigente(conn)
            if (cursor.capitulo, cursor.ultimo_paso) != (capitulo, "aplicar-delta"):
                parar(1, f"el delta del capítulo {nn} no está aplicado: nunca checkpoint antes")

            sello = {}
            for c in range(1, capitulo + 1):
                ruta = ws.raiz / "capitulos" / f"{ws.nn(c)}.md"
                if not ruta.is_file():
                    parar(WORKSPACE_INVALIDO, f"falta capitulos/{ws.nn(c)}.md")
                sello[c] = sha256(ruta)
            punto = Checkpoint(
                capitulo=capitulo,
                cursor=Cursor(
                    capitulo=capitulo,
                    fase="cerrado",
                    ultimo_paso="checkpoint",
                    intento=cursor.intento,
                ),
                run_id=abierto.id,
                version_canon=huella(ws.raiz / "canon"),
                version_plan=huella(ws.raiz / "plan"),
                capitulos_sha256=sello,
            )
            texto = serializar(punto)
            ws.escribir(ws.raiz / "checkpoints" / f"{nn}.json", texto)
            ws.escribir(ws.raiz / "checkpoints" / "latest.json", texto)

            cuerpo = frontmatter.partir((ws.raiz / "capitulos" / f"{nn}.md").read_text("utf-8"))[1]
            scores = calcular_scores(
                _informe(ws, nn, "suspense"),
                _informe(ws, nn, "continuidad"),
                _informe(ws, nn, "estilo"),
                contar_palabras(cuerpo),
                obra.palabras_por_capitulo.objetivo,
            )
            sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
            fallos = sink.emitir(slug, capitulo, abierto.id, scores, version)
            causas.extend(fallos)
            for fallo in fallos:
                typer.echo(f"aviso: {fallo}", err=True)
            typer.echo(f"checkpoint {nn}: cerrado · {len(scores)} scores")
