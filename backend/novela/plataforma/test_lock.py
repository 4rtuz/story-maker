from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest

from novela.plataforma import lock
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica


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


def test_aplicar_delta_con_lock_ajeno_sale_3(
    novelas: Callable[[str], WorkspaceRepository],
    lock_ajeno: Callable[[Path], AbstractContextManager[None]],
) -> None:
    """CA-03: con el lock en manos de otro proceso, aplicar-delta sale con 3 y la base no cambia."""
    ws = novelas("demo-24")
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    antes = ws.estado_db.read_bytes()
    with lock_ajeno(ws.lock):
        resultado = fabrica.cli(
            ws.raiz.parent, "aplicar-delta", ws.slug, "8", run=fabrica.run_id(8)
        )
    assert resultado.exit_code == 3
    assert ws.estado_db.read_bytes() == antes
