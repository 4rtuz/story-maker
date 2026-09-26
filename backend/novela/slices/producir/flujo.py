"""La novela de principio a fin: `/novela-nueva`, `/novela-continuar` capítulo a capítulo y
`/novela-auditar`, cada uno en su sesión. Es el bucle desatendido de AGENTS.md § Proceso:
ejecución, con las mismas paradas: un código distinto de 0, una sesión que no avanza el
checkpoint, o un `intervencion.md` vivo, que es una decisión humana y nunca se salta."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from novela.plataforma.workspace import WorkspaceRepository

Final = Literal["terminado", "fallido", "detenido"]


@dataclass(frozen=True)
class Puertos:
    sesion: Callable[[str], int]  # prompt → código de salida de `claude -p`
    entorno: Callable[[], str | None]  # None, o los hallazgos
    pendiente: Callable[[], bool]  # `novela pendiente`
    detener: Callable[[], bool]  # el panel pidió parar
    informar: Callable[[str, str], None]  # paso, detalle
    # Extras (spec 0015, RF-05): pueden lanzar lo que sea; `_sin_parar` lo anota y sigue.
    portada: Callable[[], None]  # `novela portada`
    metricas: Callable[[], None]  # `novela costes --guardar`
    anotar: Callable[[str], None]  # una línea en el registro del lanzamiento


def entrecomillar(texto: str) -> str:
    """Como `entrecomillar` de frontend/src/features/lanzar/orden.ts (D44)."""
    return "'" + texto.replace("'", "'\\''") + "'"


def orden_nueva(slug: str, idea: str, capitulos: int | None, palabras: int | None) -> str:
    partes = [f"/novela-nueva {slug} --idea {entrecomillar(idea)}"]
    if capitulos:
        partes.append(f"--capitulos {capitulos}")
    if palabras:
        partes.append(f"--palabras {palabras}")
    return " ".join(partes)


def intervencion_viva(ws: WorkspaceRepository) -> str | None:
    """Regla de lectura 3 de los procedimientos: sin `resuelto:`, está viva."""
    for ruta in sorted(ws.raiz.glob("runs/*/intervencion.md")):
        lineas = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
        if not any(linea.startswith("resuelto:") for linea in lineas):
            return str(ruta.relative_to(ws.raiz))
    return None


def _sesion(ws: WorkspaceRepository, p: Puertos, prompt: str) -> tuple[Final, str] | None:
    codigo = p.sesion(prompt)
    if viva := intervencion_viva(ws):
        return "fallido", f"necesita una decisión humana: lee {viva} y resuélvelo antes de reanudar"
    if codigo != 0:
        return "fallido", f"la sesión «{prompt.split()[0]}» salió con {codigo}"
    return None


def _sin_parar(p: Puertos, que: str, extra: Callable[[], None]) -> None:
    """Sin red, la novela se produce igual, sin portada y sin métricas (RNF-02)."""
    try:
        extra()
    except Exception as exc:
        p.anotar(f"sin {que}: {type(exc).__name__}: {exc}")


def _latest(ws: WorkspaceRepository) -> bytes | None:
    ruta = ws.raiz / "checkpoints" / "latest.json"
    return ruta.read_bytes() if ruta.is_file() else None


def _export(ws: WorkspaceRepository) -> dict[str, int]:
    """Qué hay en `export/` y cuándo se escribió: `export/` no se vacía nunca, ni con `novela
    cambio`, así que solo cuenta lo que escribe la sesión de auditoría (docs/formal/tla.md, H-3)."""
    export = ws.raiz / "export"
    return {p.name: p.stat().st_mtime_ns for p in export.iterdir()} if export.is_dir() else {}


def _cerrados(ws: WorkspaceRepository) -> int:
    """Solo para la etiqueta del paso: lo que cuenta lo decide `novela pendiente`."""
    try:
        return int(json.loads(_latest(ws) or b"{}").get("capitulo", 0))
    except (ValueError, AttributeError):
        return 0


def producir(ws: WorkspaceRepository, nueva: str | None, p: Puertos) -> tuple[Final, str]:
    """`nueva` es la orden `/novela-nueva`, o None para reanudar una novela que ya existe."""
    escaleta = ws.raiz / "plan" / "escaleta.md"
    p.informar("entorno", "comprobando el entorno")
    if hallazgos := p.entorno():
        return "fallido", hallazgos
    if not ws.raiz.exists():  # `novela nueva` reclama el directorio, no config.yaml
        if nueva is None:
            return "fallido", f"no existe la novela {ws.slug} y no hay idea con la que crearla"
        p.informar("nueva", "el arquitecto escribe el canon y el trazador el plan")
        if parada := _sesion(ws, p, nueva):
            return parada
        if not escaleta.is_file():
            return "fallido", "/novela-nueva terminó sin plan/escaleta.md"
        _sin_parar(p, "portada", p.portada)
    elif not escaleta.is_file():
        return "fallido", "el workspace existe sin plan/escaleta.md: /novela-nueva no se reanuda"
    elif viva := intervencion_viva(ws):
        return "fallido", f"necesita una decisión humana: lee {viva} y resuélvelo antes de reanudar"

    while p.pendiente():
        capitulo = _cerrados(ws) + 1
        if p.detener():
            return "detenido", f"detenido antes del capítulo {capitulo:02d}; reanuda para seguir"
        p.informar(f"capitulo {capitulo:02d}", "escritura, revisión y registro")
        antes = _latest(ws)
        if parada := _sesion(ws, p, f"/novela-continuar {ws.slug} --capitulos 1"):
            return parada
        if _latest(ws) == antes:
            return "fallido", f"la sesión del capítulo {capitulo:02d} no avanzó el checkpoint"
        _sin_parar(p, "métricas", p.metricas)

    p.informar("auditoria", "pistas huérfanas, hilos sin cerrar y exportación")
    previo = _export(ws)
    parada = _sesion(ws, p, f"/novela-auditar {ws.slug}")
    _sin_parar(p, "métricas", p.metricas)
    if parada:
        return parada
    export = ws.raiz / "export"
    if _export(ws) in ({}, previo):
        return "fallido", "la auditoría encontró hallazgos y no exportó: mira `novela auditar`"
    return "terminado", f"escrita, auditada y exportada en {export}"
