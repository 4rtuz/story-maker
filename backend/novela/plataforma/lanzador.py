"""`novelas/.lanzador/`: qué lanzó el panel, por dónde va y cómo pedirle que pare.

Un lanzamiento a la vez en toda la máquina: `novela producir` sostiene `activo.lock` mientras
vive, y quien quiera saber si hay uno en marcha intenta tomarlo. Un pid se reutiliza; un cerrojo
del sistema de ficheros muere con su proceso. El directorio empieza por punto, así que ningún
slug lo alcanza y `GET /novelas` lo salta.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock, Timeout

from novela.dominio.lanzamiento import Lanzamiento
from novela.plataforma import atomic
from novela.plataforma.run import RAIZ_REPO
from novela.plataforma.workspace import raiz_de_novelas, validar_slug

BACKEND = RAIZ_REPO / "backend"
REGISTRO_LINEAS = 40


def raiz_del_harness() -> Path:
    """Donde trabajan las sesiones: los procedimientos nombran `novelas/<slug>/` desde la raíz."""
    return RAIZ_REPO / "novelas"


def raiz_correcta() -> str | None:
    """None si el CLI y el harness ven las mismas novelas; si no, qué hacer."""
    if raiz_de_novelas().resolve() == raiz_del_harness().resolve():
        return None
    return (
        f"la API sirve {raiz_de_novelas().resolve()}, pero el harness escribe en "
        f"{raiz_del_harness().resolve()}: arranca la API con NOVELAS_DIR={raiz_del_harness()}"
    )


def directorio() -> Path:
    return raiz_de_novelas() / ".lanzador"


def cerrojo() -> Path:
    return directorio() / "activo.lock"


def estado_de(slug: str) -> Path:
    return directorio() / f"{validar_slug(slug)}.json"


def registro_de(slug: str) -> Path:
    return directorio() / f"{validar_slug(slug)}.log"


def detener_de(slug: str) -> Path:
    return directorio() / f"{validar_slug(slug)}.detener"


def en_marcha() -> bool:
    if not cerrojo().exists():
        return False
    sonda = FileLock(cerrojo(), timeout=0)
    try:
        sonda.acquire()
    except Timeout:
        return True
    sonda.release()
    return False


def nuevo(slug: str, paso: str, detalle: str) -> Lanzamiento:
    return Lanzamiento(
        slug=slug, estado="en_marcha", paso=paso, detalle=detalle, actualizado=datetime.now(UTC)
    )


def escribir(lanzamiento: Lanzamiento) -> None:
    datos = lanzamiento.model_dump_json(exclude={"registro", "detener_pedido"}, indent=2)
    atomic.escribir(estado_de(lanzamiento.slug), datos)


def leer(slug: str) -> Lanzamiento | None:
    ruta = estado_de(slug)
    if not ruta.is_file():
        return None
    guardado = Lanzamiento.model_validate_json(ruta.read_bytes())
    cambios: dict[str, object] = {"detener_pedido": detener_de(slug).exists()}
    if guardado.estado == "en_marcha" and not en_marcha():
        cambios |= {"estado": "interrumpido", "detalle": f"{guardado.detalle}; el proceso murió"}
    registro = registro_de(slug)
    if registro.is_file():
        lineas = registro.read_text(encoding="utf-8", errors="replace").splitlines()
        cambios["registro"] = lineas[-REGISTRO_LINEAS:]
    return guardado.model_copy(update=cambios)


def listar() -> list[Lanzamiento]:
    rutas = sorted(directorio().glob("*.json")) if directorio().is_dir() else []
    return [x for x in (leer(r.stem) for r in rutas) if x is not None]


def pedir_detener(slug: str) -> None:
    atomic.escribir(detener_de(slug), "")


def lanzar(argumentos: list[str]) -> None:
    """`novela producir` en segundo plano, fuera del grupo de la API: un reinicio de uvicorn no
    lo mata. Sin shell: los argumentos viajan en lista y nada los interpreta."""
    directorio().mkdir(parents=True, exist_ok=True)
    slug = argumentos[1]
    # En Windows, grupo propio y sin ventana: las sesiones de claude heredan la consola oculta.
    grupo = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    sin_ventana = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with registro_de(slug).open("a", encoding="utf-8") as salida:
        subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "novela", *argumentos],
            cwd=BACKEND,
            env={**os.environ, "NOVELAS_DIR": str(raiz_de_novelas().resolve())},
            stdin=subprocess.DEVNULL,
            stdout=salida,
            stderr=subprocess.STDOUT,
            creationflags=grupo | sin_ventana,
            start_new_session=sys.platform != "win32",
        )
