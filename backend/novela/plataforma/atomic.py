"""Escritura atómica: `.tmp` y `os.replace` para todo fichero del workspace (invariante 6).

`estado.db` es la excepción porque su atomicidad la da la transacción, y `harness.log` porque es
un log que se lee en vivo: se añade línea a línea. `os.replace` es atómico porque el workspace
vive en un solo disco local (spec 0001 §4); en un disco de red esta garantía no existe.
"""

import os
import time
from pathlib import Path

# En Windows, os.replace falla con PermissionError si otro proceso tiene abierto el destino —la
# API sirviendo ese capítulo, un antivirus—. Se reintenta con espera acotada.
_REINTENTOS = 10
_ESPERA_S = 0.05


def escribir(ruta: Path, contenido: str | bytes) -> None:
    """Bytes tal cual: sin traducir saltos de línea, que es lo que hashea la custodia."""
    datos = contenido.encode("utf-8") if isinstance(contenido, str) else contenido
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(datos)
            f.flush()
            os.fsync(f.fileno())
        for intento in range(_REINTENTOS):
            try:
                os.replace(tmp, ruta)
                break
            except PermissionError:
                if intento == _REINTENTOS - 1:
                    raise
                time.sleep(_ESPERA_S)
    finally:
        tmp.unlink(missing_ok=True)
