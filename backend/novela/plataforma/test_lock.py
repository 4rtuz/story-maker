from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest

from novela.plataforma import lock


def test_lock_ocupado_sale_3(
    tmp_path: Path, lock_ajeno: Callable[[Path], AbstractContextManager[None]]
) -> None:
    """RF-03: con el lock en manos de otro proceso, no se espera: se falla al momento. La salida 3
    del CLI la comprueba CA-03 sobre aplicar-delta."""
    ruta = tmp_path / "estado" / "state.lock"
    ruta.parent.mkdir()
    with lock_ajeno(ruta):
        with pytest.raises(lock.WorkspaceOcupado):
            with lock.bloquear(ruta):
                pass
    with lock.bloquear(ruta):  # liberado, se toma
        pass
