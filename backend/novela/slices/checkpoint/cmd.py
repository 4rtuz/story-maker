"""`novela checkpoint <slug> <cap>`: confirma el capítulo, una sola vez y con el delta aplicado.

Antes de nada, vp_schema: cada salida del capítulo contra su modelo; si alguna no valida, sale con
1 sin escribir. Después escribe `checkpoints/NN.json` y `latest.json` —cursor, versiones, run y el
sello de los capítulos cerrados— y emite los seis scores agregados y uno por validador por el
`ScoreSink`. El checkpoint se escribe antes de emitir: si Langfuse no contesta, el capítulo cierra
igual y el fallo queda en `harness.log`.
"""

import json
from collections.abc import Iterable
from pathlib import Path

import typer
import yaml
from pydantic import BaseModel

from novela.dominio import frontmatter
from novela.dominio.artefactos import Checkpoint, FrontmatterCapitulo, contar_palabras
from novela.dominio.canon import Estilo, Misterio, Mundo, Personaje, Premisa
from novela.dominio.estado import Cursor, Delta
from novela.dominio.plan import Escaleta, FichaCapitulo
from novela.dominio.qa import InformeQA
from novela.dominio.validadores import VALIDADORES, validador_de
from novela.plataforma import estado_db, langfuse, run, versiones
from novela.plataforma.salida import USO_INCORRECTO, WORKSPACE_INVALIDO
from novela.plataforma.workspace import WorkspaceRepository, huella, sha256
from novela.slices.validacion import gates  # excepción de slices: architecture.md §3.0

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


def artefactos(nn: str, personajes: Iterable[str]) -> dict[str, tuple[type[BaseModel], bool]]:
    """Lo que valida vp_schema al cerrar el capítulo NN (spec 0009 §8.4): ruta POSIX → (modelo,
    obligatorio). Los informes de revisión pueden faltar por la política de cuota."""
    canon: dict[str, type[BaseModel]] = {
        "premisa": Premisa,
        "mundo": Mundo,
        "misterio": Misterio,
        "estilo": Estilo,
    }
    tabla: dict[str, tuple[type[BaseModel], bool]] = {
        f"canon/{nombre}.md": (modelo, True) for nombre, modelo in canon.items()
    }
    tabla |= {f"canon/personajes/{p}": (Personaje, True) for p in sorted(personajes)}
    tabla |= {
        "plan/escaleta.md": (Escaleta, True),
        f"plan/capitulos/{nn}.md": (FichaCapitulo, True),
        f"capitulos/{nn}.md": (FrontmatterCapitulo, True),
        f"qa/{nn}-validacion.json": (InformeQA, True),
    }
    tabla |= {
        f"qa/{nn}-{n}.json": (InformeQA, False) for n in ("continuidad", "estilo", "suspense")
    }
    tabla[f"estado/deltas/{nn}.json"] = (Delta, True)
    return tabla


def _crudo(ruta: Path) -> object | None:
    """Sin pasar por `leer_json`: su error lleva los valores y saldría con 4 (spec 0009 D5). Lo
    que no se puede parsear llega como texto, y el modelo lo rechaza entero."""
    if not ruta.is_file():
        return None
    texto = ruta.read_text(encoding="utf-8")
    try:
        return frontmatter.partir(texto)[0] if ruta.suffix == ".md" else json.loads(texto)
    except (ValueError, yaml.YAMLError):
        return texto


def calcular_scores_validadores(validacion: InformeQA) -> dict[str, float]:
    """RF-15 sin brief: un score binario por validador, en el orden del catálogo. vp_schema llega
    aquí aprobado —con hallazgos, checkpoint ya salió emitiendo su 0— y solo sale de RF-03; el
    resto vale 0 si qa/NN-validacion.json tiene algún hallazgo de sus tipos."""
    fallidos = {validador_de(h.tipo) for h in validacion.hallazgos} - {"vp_schema"}
    return {
        v.nombre: 0.0 if v.nombre in fallidos else 1.0 for v in VALIDADORES if v.valor == "binario"
    }


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

            fichas = [p.name for p in ws.raiz.glob("canon/personajes/*.md")]
            documentos = {
                ruta: (modelo, _crudo(ws.raiz / ruta), obligatorio)
                for ruta, (modelo, obligatorio) in artefactos(nn, fichas).items()
            }
            invalidos = gates.esquemas(documentos, {"num_capitulos": obra.num_capitulos})
            if invalidos:
                # Antes del sello: sobre una salida corrupta no se cierra nada (spec 0009 RF-05).
                sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
                fallos = sink.emitir(
                    slug, capitulo, abierto.id, {"vp_schema": 0.0}, version=version
                )
                for h in invalidos:
                    typer.echo(f"{h.referencia}: {h.ubicacion}", err=True)
                sitios = [f"esquema_invalido@{h.referencia}:{h.ubicacion}" for h in invalidos]
                causas.append("vp_schema: " + "; ".join(sitios))
                causas.extend(fallos)
                raise typer.Exit(1)

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
            # Obligatorio y ya validado por vp_schema.
            validacion = ws.leer_json(ws.raiz / "qa" / f"{nn}-validacion.json", InformeQA)
            # Una sola emisión, agregados primero: el sink para al primer fallo (RNF-03).
            scores |= calcular_scores_validadores(validacion)
            sink = langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))
            fallos = sink.emitir(slug, capitulo, abierto.id, scores, version=version)
            causas.extend(fallos)
            for fallo in fallos:
                typer.echo(f"aviso: {fallo}", err=True)
            typer.echo(f"checkpoint {nn}: cerrado · {len(scores)} scores")
