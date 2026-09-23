import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pytest
from hypothesis import settings

# Sin deadline: en Windows el primer ejemplo de una estrategia compuesta tarda lo que tarda el
# antivirus, y un deadline ahí da rojos que no son del código. CI puede subir max_examples.
settings.register_profile("default", deadline=None, max_examples=50)
settings.register_profile("ci", deadline=None, max_examples=200)
settings.load_profile("default")


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
