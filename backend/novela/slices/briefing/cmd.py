"""`novela briefing <slug> <cap> <agente>`: la cáscara. Lee, llama a assemble y escribe."""

from pathlib import Path

import typer
from pydantic import BaseModel

from novela.dominio.artefactos import Memoria
from novela.dominio.brief import Brief
from novela.dominio.canon import Estilo, Misterio, Mundo, Personaje, Premisa
from novela.dominio.ids import Agente
from novela.dominio.plan import FichaCapitulo
from novela.plataforma import estado_db, run
from novela.plataforma.salida import USO_INCORRECTO, WORKSPACE_INVALIDO
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository, sha256
from novela.slices.briefing import assemble, recipes

_CANON: dict[str, type[BaseModel]] = {
    "premisa": Premisa,
    "mundo": Mundo,
    "estilo": Estilo,
    "misterio": Misterio,
}


# El deny de Read de canon/misterio.md también deniega escribirlo, así que el arquitecto escribe
# el misterio aquí, y el gate, que es el briefing del trazador, lo promueve (spec 0003 v0.5).
BORRADOR = "misterio.borrador.md"


def _texto(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def cargar_fuentes(
    ws: WorkspaceRepository, capitulo: int, agente: Agente, run_id: str
) -> assemble.Fuentes:
    """Lee lo que cualquier receta puede pedir y lo valida en el borde. Son ficheros pequeños:
    leerlos todos cuesta menos que decidir cuáles. Salvo para el arquitecto, que lo escribe, el
    canon tiene que estar completo (RF-38)."""
    raiz = ws.raiz
    borrador = raiz / "canon" / BORRADOR
    # Solo el trazador ve el borrador, y como el misterio: bajo su nombre, `canon/*` de una receta
    # lo recogería sin pasar por el guardarraíl del misterio.
    con_borrador = agente is Agente.TRAZADOR and borrador.is_file()
    ficheros = {"config.yaml": ws.config_yaml.read_text(encoding="utf-8")}
    for ruta in sorted([*raiz.glob("canon/*.md"), raiz / "plan" / "escaleta.md"]):
        if ruta.name == BORRADOR or (con_borrador and ruta.name == "misterio.md"):
            continue
        if ruta.is_file():
            texto = ruta.read_text(encoding="utf-8")
            if ruta.parent.name == "canon" and ruta.stem in _CANON:
                ws.modelo_de_md(ruta, texto, _CANON[ruta.stem])
            ficheros[ruta.relative_to(raiz).as_posix()] = texto
    if (brief := raiz / "brief" / "brief.json").is_file():
        ficheros["brief/brief.json"] = ws.leer_json(brief, Brief).model_dump_json(indent=2)
    if con_borrador:
        texto = borrador.read_text(encoding="utf-8")
        ws.modelo_de_md(borrador, texto, Misterio)
        ficheros["canon/misterio.md"] = texto
    personajes = {}
    for ruta in sorted(raiz.glob("canon/personajes/*.md")):
        texto = ruta.read_text(encoding="utf-8")
        personajes[ruta.stem] = (ws.modelo_de_md(ruta, texto, Personaje), texto)
    if agente is not Agente.ARQUITECTO:
        for nombre in _CANON:
            if f"canon/{nombre}.md" not in ficheros:
                # Al trazador le falta el borrador, que es lo que el arquitecto puede escribir.
                ausente = borrador if (agente, nombre) == (Agente.TRAZADOR, "misterio") else None
                raise WorkspaceInvalido(f"{ausente or raiz / 'canon' / f'{nombre}.md'}: falta")
        if not personajes:
            raise WorkspaceInvalido(f"{raiz / 'canon' / 'personajes'}: no hay fichas")
    misterio_texto = ficheros.get("canon/misterio.md")
    misterio = None
    if misterio_texto is not None:
        misterio = ws.modelo_de_md(raiz / "canon" / "misterio.md", misterio_texto, Misterio)

    nn = ws.nn(capitulo)
    ruta_ficha = raiz / "plan" / "capitulos" / f"{nn}.md"
    ficha_texto = _texto(ruta_ficha)
    ficha = ws.modelo_de_md(ruta_ficha, ficha_texto, FichaCapitulo) if ficha_texto else None
    if ficha and ficha.capitulo != capitulo:
        raise WorkspaceInvalido(f"{ruta_ficha}: dice ser del capítulo {ficha.capitulo}")
    presentes = {p for e in ficha.escenas for p in e.personajes} if ficha else None
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        estado = estado_db.leer(conn, personajes=presentes)

    # El juez juzga la obra hasta el capítulo pedido, ese incluido; el resto, lo anterior a él.
    hasta = capitulo + 1 if agente is Agente.JUEZ else capitulo
    resumenes = {}
    for c in range(1, hasta):
        ruta = raiz / "memoria" / "resumenes" / f"{ws.nn(c)}.md"
        if (resumen := _texto(ruta)) is not None:
            resumenes[c] = ws.modelo_de_md(ruta, resumen, Memoria)
    anterior = raiz / "capitulos" / f"{ws.nn(capitulo - 1)}.md" if capitulo > 1 else None
    actual = raiz / "capitulos" / f"{nn}.md"
    obra = {}
    if agente is Agente.JUEZ:
        for c in range(1, hasta):
            if (escrito := _texto(raiz / "capitulos" / f"{ws.nn(c)}.md")) is not None:
                obra[c] = escrito
    return assemble.Fuentes(
        agente=agente,
        capitulo=capitulo,
        run_id=run_id,
        ficheros=ficheros,
        ficha=ficha,
        ficha_texto=ficha_texto,
        misterio=misterio,
        misterio_texto=misterio_texto,
        personajes=personajes,
        estado=estado,
        capitulo_anterior=_texto(anterior) if anterior else None,
        capitulo_actual=_texto(actual),
        sha_actual=sha256(actual) if actual.is_file() else None,
        resumenes=resumenes,
        digitos=len(nn),
        capitulos=obra,
    )


def _promover(ws: WorkspaceRepository) -> None:
    """El gate pasó: el borrador pasa a canon/misterio.md, atómico, y después se borra. Cortado
    entre las dos cosas, el siguiente gate lo repite, porque con los dos manda el borrador."""
    borrador = ws.raiz / "canon" / BORRADOR
    if borrador.is_file():
        ws.escribir(ws.raiz / "canon" / "misterio.md", borrador.read_bytes())
        borrador.unlink()


def _sello_roto(ws: WorkspaceRepository) -> list[int]:
    punto = ws.ultimo_checkpoint()
    if punto is None:
        return []
    actuales: dict[int, str | None] = {}
    for c in punto.capitulos_sha256:
        ruta = ws.raiz / "capitulos" / f"{ws.nn(c)}.md"
        actuales[c] = sha256(ruta) if ruta.is_file() else None
    return assemble.capitulos_alterados(punto.capitulos_sha256, actuales)


def briefing(slug: str, capitulo: int, agente: Agente) -> None:
    """Ensambla el contexto exacto de una invocación en runs/<run_id>/briefings/NN-<agente>.md."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    total = ws.config().parametros_obra.num_capitulos
    if not 1 <= capitulo <= total:
        typer.echo(f"capítulo {capitulo} fuera de 1..{total}", err=True)
        raise typer.Exit(USO_INCORRECTO)
    with ws.bloquear():
        # El arranque va a su propio run: si no, el capítulo 1 hereda el canon vacío (RF-11).
        arranque = agente in (Agente.ARQUITECTO, Agente.TRAZADOR)
        abierto = run.abrir(ws, capitulo, "arranque" if arranque else "capitulo")
        nn = ws.nn(capitulo)
        with abierto.registro("briefing", nn, agente.value) as causas:

            def parar(codigo: int, causa: str) -> None:
                causas.append(causa)
                typer.echo(causa, err=True)
                raise typer.Exit(codigo)

            punto = ws.ultimo_checkpoint()
            if capitulo > 1 and (punto is None or punto.capitulo < capitulo - 1):
                parar(1, f"el capítulo {ws.nn(capitulo - 1)} no tiene checkpoint")
            # Sello (RF-35): un capítulo cerrado que cambia viola el invariante 7.
            if alterados := _sello_roto(ws):
                lista = ", ".join(ws.nn(c) for c in alterados)
                parar(WORKSPACE_INVALIDO, f"capítulos cerrados alterados o ausentes: {lista}")

            receta = recipes.cargar()[agente]
            try:
                hecho = assemble.ensamblar(receta, cargar_fuentes(ws, capitulo, agente, abierto.id))
            except (assemble.FugaDelSecreto, assemble.PresupuestoExcedido) as exc:
                parar(1, str(exc))
                raise
            except assemble.FuenteAusente as exc:
                parar(WORKSPACE_INVALIDO, str(exc))
                raise
            destino = abierto.dir / "briefings" / f"{nn}-{agente.value}.md"
            ws.escribir(destino, hecho.texto)
            if agente is Agente.TRAZADOR:
                _promover(ws)
            pasos = hecho.meta.degradacion
            degradado = f" · degradado: {'; '.join(pasos)}" if pasos else ""
            typer.echo(
                f"{destino.relative_to(ws.raiz).as_posix()} · {hecho.meta.tokens_estimados} de "
                f"{receta.presupuesto_tokens} tokens{degradado}"
            )
