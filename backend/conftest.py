import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pytest
from hypothesis import settings

from novela.plataforma import run
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica

# Sin deadline: en Windows el primer ejemplo de una estrategia compuesta tarda lo que tarda el
# antivirus, y un deadline ahí da rojos que no son del código. CI puede subir max_examples.
settings.register_profile("default", deadline=None, max_examples=50)
settings.register_profile("ci", deadline=None, max_examples=200)
settings.load_profile("default")


@pytest.fixture(scope="session", autouse=True)
def _sin_claves_reales(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Ningún test emite scores de verdad (validators.md §3.5): ni el `.env` del repo ni el entorno
    del operador llegan al emisor. Los tests que lo necesitan fijan los suyos."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(run, "RAIZ_REPO", tmp_path_factory.mktemp("repo-sin-env"))
        for clave in list(os.environ):
            if clave == "TRACE_TO_LANGFUSE" or clave.startswith("LANGFUSE_"):
                mp.delenv(clave)
        yield


_TOMA_LOCK = (
    "import sys\n"
    "from filelock import FileLock\n"
    "lock = FileLock(sys.argv[1])\n"
    "lock.acquire()\n"
    "print('tomado', flush=True)\n"
    "sys.stdin.read()\n"
)


@pytest.fixture
def lock_ajeno() -> Callable[[Path], AbstractContextManager[None]]:
    """Otro proceso toma el lock y lo retiene mientras dura el with."""

    @contextmanager
    def tomar(ruta: Path) -> Iterator[None]:
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", _TOMA_LOCK, str(ruta)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert proc.stdin is not None and proc.stdout is not None
        try:
            assert proc.stdout.readline().strip() == "tomado"
            yield
        finally:
            proc.stdin.close()
            proc.wait(timeout=10)

    return tomar


@pytest.fixture(scope="session")
def plantillas(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Los workspaces de la tarea 1.13b y demo-cambio (spec 0007 §7), construidos una vez por
    sesión con el bucle real y agentes falsos. demo-24 es la instantánea de demo-terminado al
    cerrar el capítulo 7."""
    base = tmp_path_factory.mktemp("plantillas")
    fabrica.construir(
        base, "demo-terminado", fabrica.DEMO, cerrados=24, instantaneas={7: "demo-24"}
    )
    fabrica.construir(base, "demo-huerfana", fabrica.HUERFANA, cerrados=3)
    fabrica.construir(base, "demo-cambio", fabrica.CAMBIO, cerrados=6)
    return base


@pytest.fixture(scope="session")
def regenerada(plantillas: Path) -> str:
    """demo-cambio tras CA-29: cam-001 pedido y la versión 2 completa. Devuelve el slug de la
    plantilla, que se copia con `novelas`."""
    raiz = plantillas / "demo-cambio-v2"
    shutil.copytree(plantillas / "demo-cambio", raiz)
    assert fabrica.pedir_cambio(plantillas, raiz.name).exit_code == 0
    fabrica.completar(raiz, fabrica.CAMBIO)
    return raiz.name


@pytest.fixture
def novelas(
    plantillas: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[str], WorkspaceRepository]:
    """Copia una plantilla a tmp_path y apunta NOVELAS_DIR ahí: cada test puede escribir."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))

    def copiar(slug: str) -> WorkspaceRepository:
        shutil.copytree(plantillas / slug, tmp_path / slug)
        return WorkspaceRepository(tmp_path / slug)

    return copiar
