"""Los workspaces sintéticos del panel (spec 0004 §13), sin una sola llamada a modelo:

- `demo-24`: 7 capítulos cerrados con el bucle real y el 8 preparado, en el índice sin aplicar;
- `recien-creada`: solo `novela nueva`, sin plan ni checkpoints;
- `grande-999`: igual, con 999 capítulos.

Mientras genera, `run.RAIZ_REPO` apunta a un directorio sin `.env` y `TRACE_TO_LANGFUSE` y
`LANGFUSE_*` salen del entorno, como hace `_sin_claves_reales` en los tests; al terminar, los dos
vuelven a su valor (RF-42, D56). Uso: `uv run python -m tests.fixtures.panel <destino>` desde
`backend/`.
"""

import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from novela.plataforma import run
from tests.fixtures import fabrica

_IDEA = ("--idea", "Un faro apagado.")


@contextmanager
def _sin_claves() -> Iterator[None]:
    raiz = run.RAIZ_REPO
    claves = {
        k: v for k, v in os.environ.items() if k == "TRACE_TO_LANGFUSE" or k.startswith("LANGFUSE_")
    }
    with tempfile.TemporaryDirectory(prefix="panel-sin-env-") as vacio:
        for clave in claves:
            del os.environ[clave]
        run.RAIZ_REPO = Path(vacio)
        try:
            yield
        finally:
            run.RAIZ_REPO = raiz
            os.environ.update(claves)


def generar(destino: Path) -> None:
    with _sin_claves():
        _generar(destino)


def _generar(destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    fabrica.construir(destino, "demo-24", fabrica.DEMO, cerrados=7)
    fabrica.preparar_capitulo(destino, "demo-24", fabrica.DEMO, 8)
    for slug, extra in (("recien-creada", ()), ("grande-999", ("--capitulos", "999"))):
        r = fabrica.cli(destino, "nueva", slug, *_IDEA, *extra, run="r-20260101-0900")
        assert r.exit_code == 0, r.output


if __name__ == "__main__":
    generar(Path(sys.argv[1]))
