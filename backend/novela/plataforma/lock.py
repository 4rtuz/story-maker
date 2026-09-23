"""Un proceso por workspace (invariante 8): `filelock` sobre `estado/state.lock`.

El WAL serializa escritores de la base, pero no protege `capitulos/`, `qa/` ni `runs/`: el lock
es del workspace, no del estado. Lo toma todo subcomando que escribe; no espera.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout


class WorkspaceOcupado(Exception):
    """Otro proceso trabaja sobre el workspace. Salida 3."""


@contextmanager
def bloquear(ruta: Path) -> Iterator[None]:
    cerrojo = FileLock(ruta, timeout=0)
    try:
        cerrojo.acquire()
    except Timeout as exc:
        raise WorkspaceOcupado(f"{ruta}: otro proceso trabaja sobre el workspace") from exc
    try:
        yield
    finally:
        cerrojo.release()
