"""`novela cambio`: pide que un hecho sea otro y prepara la versión nueva (spec 0007).

Cáscara: argumentos, precondiciones, lock, run y códigos. El plan lo calcula `plan.py` y la
instantánea y el restablecimiento de la raíz, `plataforma/versiones.py`. Todo rechazo sale antes
de tocar el disco, así que solo abre run y deja línea la petición que se prepara (D11).
"""

import re
from datetime import datetime
from typing import Annotated, NoReturn

import typer

from novela.dominio.texto import normalizar
from novela.dominio.version import PeticionDeCambio
from novela.plataforma import estado_db, run, versiones
from novela.plataforma.salida import USO_INCORRECTO, WORKSPACE_INVALIDO
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.cambio import plan

MAX_TEXTO = 500


def _rechazar(causa: str, codigo: int) -> NoReturn:
    typer.echo(f"cambio: {causa}", err=True)
    raise typer.Exit(codigo)


def _lista(ws: WorkspaceRepository, capitulos: list[int]) -> str:
    return ", ".join(ws.nn(c) for c in capitulos) or "—"


def _intervencion_viva(ws: WorkspaceRepository) -> bool:
    """La regla de `/novela-continuar`: un `intervencion.md` sin línea `resuelto:` está vivo."""
    return any(
        not any(linea.startswith("resuelto:") for linea in ruta.read_text("utf-8").splitlines())
        for ruta in (ws.raiz / "runs").glob("*/intervencion.md")
    )


def _siguiente(ws: WorkspaceRepository) -> None:
    """RF-24: una sola línea. «Completo» se deriva del checkpoint y no se escribe (D12)."""
    cambio = versiones.ultimo_cambio(ws)
    if cambio is None or cambio.estado != "en_curso":
        typer.echo("sin cambio")
        return
    punto = ws.ultimo_checkpoint()
    total = ws.config().parametros_obra.num_capitulos
    typer.echo(plan.siguiente_paso(cambio.plan, punto.capitulo if punto else 0, total))


def _nueva_peticion(
    ws: WorkspaceRepository, hecho: str, texto: str, motivo: str | None
) -> PeticionDeCambio:
    """RF-10 a RF-15 sobre la edición vigente, en solo lectura."""
    if en_curso := versiones.cambio_en_curso(ws):
        _rechazar(f"cambio en curso: {en_curso.id}", 1)
    if _intervencion_viva(ws):
        _rechazar("intervención sin resolver en runs/*/intervencion.md", 1)
    punto = ws.ultimo_checkpoint()
    total = ws.config().parametros_obra.num_capitulos
    if punto is None or punto.capitulo < total:
        _rechazar(f"novela sin terminar: {punto.capitulo if punto else 0} de {total}", 1)
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        hechos = {h.id: h for h in estado_db.leer(conn).libro_de_hechos}
        if hecho not in hechos:
            _rechazar(f"{hecho} no está en libro_de_hechos", USO_INCORRECTO)
        if normalizar(texto.strip()) == normalizar(hechos[hecho].texto.strip()):
            _rechazar(f"el texto nuevo es el vigente de {hecho}", USO_INCORRECTO)
        usos = [u for h in hechos for u in estado_db.usos(conn, h)]  # sin tabla: EstadoIlegible
        base = versiones.version_vigente(conn)
    if not any(u.hecho == hecho for u in usos):
        _rechazar(f"{hecho} no tiene usos registrados en usos_de_hecho", WORKSPACE_INVALIDO)
    try:
        reservado = plan.id_reservado(hechos)
    except plan.SinIdsLibres as exc:
        _rechazar(str(exc), WORKSPACE_INVALIDO)
    anterior = versiones.ultimo_cambio(ws)
    return PeticionDeCambio(
        id=f"cam-{int(anterior.id[-3:]) + 1 if anterior else 1:03d}",
        hecho=hecho,
        texto_anterior=hechos[hecho].texto,
        texto=texto,
        motivo=motivo,
        hecho_nuevo=reservado,
        version_base=base,
        version_nueva=base + 1,
        plan=plan.plan_de_regeneracion(usos, hecho, total),
        estado="preparando",
        # Sin microsegundos: run._run_id lo compara con el `creado` de los manifiestos, que va
        # en segundos, y el run de esta petición no puede quedar «anterior» a ella.
        creado=datetime.now().astimezone().replace(microsecond=0),
    )


def _simulacion(ws: WorkspaceRepository, p: PeticionDeCambio) -> None:
    plan_ = p.plan
    typer.echo(f"simulación: {p.hecho} → {p.hecho_nuevo} · versión {p.version_nueva}")
    typer.echo(f"regenerar {_lista(ws, plan_.regenerar)}")
    for capitulo, requeridos in plan_.requeridos.items():
        typer.echo(f"requeridos {ws.nn(capitulo)}: {', '.join(requeridos)}")
    typer.echo(f"reaplicar {_lista(ws, plan_.reaplicar)}")


def cambio(
    slug: str,
    hecho: Annotated[str | None, typer.Option(help="Id del hecho que cambia (hec-NNN)")] = None,
    texto: Annotated[str | None, typer.Option(help="Texto nuevo del hecho, ≤ 500")] = None,
    motivo: Annotated[str | None, typer.Option(help="Por qué se pide, ≤ 500")] = None,
    simular: Annotated[bool, typer.Option("--simular", help="Solo imprime el plan")] = False,
    siguiente: Annotated[
        bool, typer.Option("--siguiente", help="Qué hacer con el siguiente capítulo")
    ] = False,
) -> None:
    """Registra la petición, guarda la edición vigente en versiones/vN/ y restablece la raíz."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    if siguiente:
        if hecho is not None or texto is not None or motivo is not None or simular:
            _rechazar("--siguiente excluye --hecho, --texto, --motivo y --simular", USO_INCORRECTO)
        _siguiente(ws)
        return
    if hecho is None or texto is None:
        _rechazar("faltan --hecho y --texto", USO_INCORRECTO)
    if not re.fullmatch(r"hec-[0-9]{3}", hecho):
        _rechazar(f"--hecho {hecho!r} no casa ^hec-[0-9]{{3}}$", USO_INCORRECTO)
    if not texto.strip() or len(texto) > MAX_TEXTO:
        _rechazar(f"--texto vacío o de más de {MAX_TEXTO} caracteres", USO_INCORRECTO)
    if motivo is not None and len(motivo) > MAX_TEXTO:
        _rechazar(f"--motivo de más de {MAX_TEXTO} caracteres", USO_INCORRECTO)

    previo = versiones.ultimo_cambio(ws)
    if previo is not None and previo.estado == "preparando":
        # RF-20: la misma petición completa la preparación cortada; otra espera a que termine.
        if (previo.hecho, previo.texto, previo.motivo) != (hecho, texto, motivo):
            _rechazar(f"cambio en curso: {previo.id} (en preparación)", 1)
        peticion = previo
    else:
        peticion = _nueva_peticion(ws, hecho, texto, motivo)
        if simular:
            _simulacion(ws, peticion)
            return

    with ws.bloquear():
        versiones.registrar_peticion(ws, peticion)
        abierto = run.abrir(ws, 1)  # tras registrar: ya es un run de la versión nueva (D4)
        with abierto.registro("cambio", peticion.id):
            versiones.preparar(ws, peticion)
    p = peticion.plan
    typer.echo(
        f"cambio {peticion.id}: {peticion.hecho} → {peticion.hecho_nuevo} · "
        f"versión {peticion.version_nueva} · regenerar {_lista(ws, p.regenerar)} · "
        f"reaplicar {len(p.reaplicar)} capítulos"
    )
