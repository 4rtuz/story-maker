"""`ScoreSink`: el segundo puerto del sistema (architecture.md §3.0, §10.5).

Dos implementaciones: el no-op, que es lo que hay salvo con `TRACE_TO_LANGFUSE` exactamente igual
a "true", y el de Langfuse, por HTTP de la stdlib contra `POST /api/public/scores`. Es la única
salida de red del CLI. El trazado nunca puede ser la razón por la que un capítulo no cierra: los
fallos se devuelven, no se lanzan. Las claves llegan por entorno desde settings.local.json.
"""

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

TIMEOUT_S = 5.0


class ScoreSink(Protocol):
    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        """Devuelve los fallos, vacío si todo llegó."""
        ...


class SinkNulo:
    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        return []


@dataclass(frozen=True)
class SinkLangfuse:
    base_url: str
    publica: str
    secreta: str

    def emitir(
        self, slug: str, capitulo: int, run_id: str, scores: Mapping[str, float]
    ) -> list[str]:
        credencial = base64.b64encode(f"{self.publica}:{self.secreta}".encode()).decode()
        for nombre, valor in scores.items():
            cuerpo = {
                # Id determinista: reemitir el capítulo sustituye el score en vez de duplicarlo.
                "id": f"{slug}-{run_id}-{capitulo:02d}-{nombre}",
                "sessionId": run_id,
                "name": nombre,
                "value": valor,
                "dataType": "NUMERIC",
                "comment": f"{slug}, capítulo {capitulo}",
            }
            peticion = urllib.request.Request(  # noqa: S310 — la URL la fija la configuración
                f"{self.base_url.rstrip('/')}/api/public/scores",
                data=json.dumps(cuerpo).encode(),
                headers={
                    "Authorization": f"Basic {credencial}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(peticion, timeout=TIMEOUT_S):  # noqa: S310
                    pass
            except (OSError, urllib.error.URLError) as exc:
                # Al primer fallo se para: seis timeouts seguidos retendrían el checkpoint.
                return [f"Langfuse no recibió {nombre}: {exc}"]
        return []


def desde_entorno(entorno: Mapping[str, str]) -> ScoreSink:
    if entorno.get("TRACE_TO_LANGFUSE") != "true":
        return SinkNulo()
    base = entorno.get("LANGFUSE_BASE_URL") or entorno.get("LANGFUSE_HOST")
    return SinkLangfuse(
        base_url=base or "https://cloud.langfuse.com",
        publica=entorno.get("LANGFUSE_PUBLIC_KEY", ""),
        secreta=entorno.get("LANGFUSE_SECRET_KEY", ""),
    )
