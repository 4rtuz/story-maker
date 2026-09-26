"""`novela producir <slug> [--idea ...]`: la cáscara de `flujo.producir` con sesiones reales.

Lo lanza el panel por `POST /lanzamientos`, y se puede lanzar a mano desde la raíz del repo. Sin
`--idea` reanuda. Cada sesión es la de AGENTS.md § Proceso: ejecución, con el prompt como argumento
de `claude.exe` —nunca de un `.cmd`, que pasaría por cmd.exe— y sin shell de por medio.
"""

import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated

import typer

from novela.plataforma import langfuse, lanzador
from novela.plataforma.lock import bloquear
from novela.plataforma.run import RAIZ_REPO
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.observabilidad import prompts, traza
from novela.slices.observabilidad.cmd import guardar_metricas
from novela.slices.portada.cmd import generar as generar_portada
from novela.slices.producir.flujo import Puertos, orden_nueva
from novela.slices.producir.flujo import producir as flujo

# ponytail: plazo fijo por sesión; un capítulo con dos reintentos cabe de sobra. Si no, a config.
PLAZO_S = 3 * 3600
SESION = ["--setting-sources", "project,local", "--permission-mode", "dontAsk", "--model", "opus"]


def _entorno(claude: str | None) -> str | None:
    if claude is None:
        return "no encuentro `claude` en el PATH"
    if claude.lower().endswith((".cmd", ".bat")):
        return f"{claude} es un script de cmd.exe: instala el binario nativo de Claude Code"
    if shutil.which("novela") is None:
        return "no encuentro `novela` en el PATH: las sesiones no podrían llamar al CLI"
    if error := lanzador.raiz_correcta():
        return error
    r = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "novela", "comprobar-entorno"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return None if r.returncode == 0 else (r.stdout + r.stderr).strip() or "comprobar-entorno: 1"


# Sin esto, `claude -p` cancela el SessionEnd del plugin al salir y el último turno no llega.
SESSIONEND_MS = "30000"


def entorno_sesion(
    ws: WorkspaceRepository,
    prompt: str,
    sid: str,
    base: Mapping[str, str],
    efectivo: Mapping[str, str],
) -> dict[str, str]:
    """El entorno de un `claude -p`: `base` sin claves del `.env` (RNF-07), más la traza del paso,
    abierta con `efectivo`, en la sesión de Langfuse de la novela."""
    paso = traza.paso_de(ws, prompt.split()[0])
    entorno = {
        **base,
        "NOVELA_SESSION_ID": sid,
        "CC_LANGFUSE_TRACE_TAGS": ws.slug,
        "NOVELA_SLUG": ws.slug,  # acota las lecturas de los roles a esta novela (regla 6 del hook)
        "CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS": SESSIONEND_MS,
    }
    if padre := traza.abrir(efectivo, ws.slug, paso, prompts.metadatos_de_version()):
        entorno["CC_LANGFUSE_TRACEPARENT"] = padre
    return entorno


def _pendiente(slug: str) -> bool:
    r = subprocess.run([sys.executable, "-m", "novela", "pendiente", slug], check=False)  # noqa: S603
    if r.returncode not in (0, 1):
        raise RuntimeError(f"novela pendiente {slug} salió con {r.returncode}")
    return r.returncode == 0


def producir(
    slug: str,
    idea: Annotated[str | None, typer.Option(help="Sin idea, reanuda una novela existente")] = None,
    capitulos: Annotated[int | None, typer.Option()] = None,
    palabras: Annotated[int | None, typer.Option()] = None,
) -> None:
    """La novela de principio a fin, una sesión de claude por paso. Uno a la vez en la máquina."""
    ws = WorkspaceRepository.resolver(slug)
    lanzador.directorio().mkdir(parents=True, exist_ok=True)
    claude = shutil.which("claude")
    registro = lanzador.registro_de(slug)

    def sesion(prompt: str) -> int:
        sid = str(uuid.uuid4())
        efectivo = langfuse.entorno_efectivo(RAIZ_REPO)
        entorno = entorno_sesion(ws, prompt, sid, os.environ, efectivo)
        with registro.open("a", encoding="utf-8") as salida:
            salida.write(f"\n[{datetime.now(UTC):%H:%M:%S}] {prompt.split()[0]} · sesión {sid}\n")
            salida.flush()
            try:
                return subprocess.run(  # noqa: S603
                    [str(claude), "-p", prompt, "--session-id", sid, *SESION],
                    cwd=RAIZ_REPO,
                    env=entorno,
                    stdin=subprocess.DEVNULL,
                    stdout=salida,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=PLAZO_S,
                ).returncode
            except subprocess.TimeoutExpired:
                salida.write(f"sin respuesta en {PLAZO_S} s\n")
                return 124

    actual = lanzador.nuevo(slug, "entorno", "arrancando")

    def informar(paso: str, detalle: str) -> None:
        nonlocal actual
        actual = lanzador.nuevo(slug, paso, detalle)
        lanzador.escribir(actual)

    def anotar(linea: str) -> None:
        with registro.open("a", encoding="utf-8") as salida:
            salida.write(f"[{datetime.now(UTC):%H:%M:%S}] {linea}\n")

    def portada() -> None:
        generar_portada(ws)

    with bloquear(lanzador.cerrojo()):
        lanzador.detener_de(slug).unlink(missing_ok=True)
        puertos = Puertos(
            sesion=sesion,
            entorno=lambda: _entorno(claude),
            pendiente=lambda: _pendiente(slug),
            detener=lanzador.detener_de(slug).exists,
            informar=informar,
            portada=portada,
            metricas=lambda: guardar_metricas(ws),
            anotar=anotar,
        )
        nueva = orden_nueva(slug, idea, capitulos, palabras) if idea else None
        try:
            estado, detalle = flujo(ws, nueva, puertos)
        except Exception as exc:
            estado, detalle = "fallido", f"{type(exc).__name__}: {exc}"
            raise
        finally:
            lanzador.escribir(
                actual.model_copy(
                    update={"estado": estado, "detalle": detalle, "actualizado": datetime.now(UTC)}
                )
            )
            lanzador.detener_de(slug).unlink(missing_ok=True)
    typer.echo(f"{slug}: {estado} · {detalle}")
    if estado != "terminado":
        raise typer.Exit(1)
