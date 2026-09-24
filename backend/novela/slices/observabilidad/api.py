"""La API pública de Langfuse por HTTP de la stdlib, con las claves de `entorno_efectivo`.

Solo la usan los subcomandos de observabilidad; el `ScoreSink` sigue en `plataforma/langfuse.py`.
"""

import base64
import json
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

TIMEOUT_S = 30.0


@dataclass(frozen=True)
class Api:
    base_url: str
    publica: str
    secreta: str

    @classmethod
    def de(cls, entorno: Mapping[str, str]) -> "Api":
        base = entorno.get("LANGFUSE_BASE_URL") or entorno.get("LANGFUSE_HOST")
        return cls(
            (base or "https://cloud.langfuse.com").rstrip("/"),
            entorno.get("LANGFUSE_PUBLIC_KEY", ""),
            entorno.get("LANGFUSE_SECRET_KEY", ""),
        )

    def pedir(
        self,
        metodo: str,
        ruta: str,
        cuerpo: object = None,
        cabeceras: Mapping[str, str] | None = None,
        timeout: float = TIMEOUT_S,
    ) -> Any:
        """JSON de la respuesta. Los errores de HTTP y de red se lanzan: decide quien llama."""
        credencial = base64.b64encode(f"{self.publica}:{self.secreta}".encode()).decode()
        peticion = urllib.request.Request(  # noqa: S310 — la URL la fija la configuración
            self.base_url + ruta,
            data=None if cuerpo is None else json.dumps(cuerpo).encode(),
            headers={
                "Authorization": f"Basic {credencial}",
                "Content-Type": "application/json",
                **(cabeceras or {}),
            },
            method=metodo,
        )
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:  # noqa: S310
            return json.loads(respuesta.read() or b"null")
