"""`novela validar <slug> <cap>`: el gate barato, antes de gastar tres llamadas a modelo.

Escribe `qa/NN-validacion.json` siempre, pase o no, con el sha256 del fichero que validó: es lo
que la custodia de `aplicar-delta` compara (RF-31, RF-32).
"""

import typer

from novela.dominio import frontmatter
from novela.dominio.canon import Misterio
from novela.dominio.plan import FichaCapitulo
from novela.dominio.qa import Hallazgo, InformeQA
from novela.plataforma import estado_db, run
from novela.plataforma.salida import USO_INCORRECTO
from novela.plataforma.workspace import WorkspaceRepository, sha256
from novela.slices.validacion import gates


def _contexto(ws: WorkspaceRepository, capitulo: int) -> gates.Contexto:
    raiz = ws.raiz
    ficha = ws.leer_md(raiz / "plan" / "capitulos" / f"{ws.nn(capitulo)}.md", FichaCapitulo)
    misterio = ws.leer_md(raiz / "canon" / "misterio.md", Misterio)
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
        personajes=frozenset(p.stem for p in raiz.glob("canon/personajes/*.md")),
        pistas=frozenset(p.id for p in misterio.pistas),
        hilos_abiertos=abiertos,
    )


def validar(slug: str, capitulo: int) -> None:
    """Esquema, longitud, pistas del plan, balance de hilos e ids. Sale con 1 si hay hallazgos."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = ws.config().parametros_obra.num_capitulos
    if not 1 <= capitulo <= total:
        typer.echo(f"capítulo {capitulo} fuera de 1..{total}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    with ws.bloquear():
        abierto = run.abrir(ws, capitulo)
        nn = ws.nn(capitulo)
        with abierto.registro("validar", nn) as causas:
            ctx = _contexto(ws, capitulo)
            ruta = ws.raiz / "capitulos" / f"{nn}.md"
            if ruta.is_file():
                texto = ruta.read_text(encoding="utf-8")
                try:
                    meta, cuerpo = frontmatter.partir(texto)
                    hallazgos = gates.validar(meta, cuerpo, ctx)
                except ValueError:
                    hallazgos = gates.validar(None, texto, ctx)
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
            if not hallazgos:
                typer.echo(f"validar {nn}: aprobado")
                return
            tipos = sorted({h.tipo for h in hallazgos})
            causas.append(f"{len(hallazgos)} hallazgos: {', '.join(tipos)}")
            typer.echo(
                f"validar {nn}: rechazado, {len(hallazgos)} hallazgos en qa/{nn}-validacion.json"
            )
            raise typer.Exit(1)
