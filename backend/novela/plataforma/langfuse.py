"""`ScoreSink`: el segundo puerto del sistema (architecture.md §3.0, §10.5).

Dos implementaciones: el no-op, que es lo que hay salvo con `TRACE_TO_LANGFUSE` exactamente igual
a "true", y el de Langfuse, por HTTP de la stdlib contra `POST /api/public/scores`. Es la única
salida de red del CLI. El trazado nunca puede ser la razón por la que un capítulo no cierra: los
fallos se devuelven, no se lanzan. Las claves salen del entorno del proceso o de `.env` en la raíz
del repo, que git ignora (spec 0003 §5.3); el entorno manda.
"""

import base64
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

TIMEOUT_S = 5.0


def id_de_score(slug: str, run_id: str, capitulo: int, nombre: str, version: int) -> str:
    """Determinista: reemitir el capítulo sustituye el score en vez de duplicarlo. Con una versión
    mayor que 1 lleva `-vN`, para no pisar los de la anterior (spec 0007, D20)."""
    base = f"{slug}-{run_id}-{capitulo:02d}-{nombre}"
    return base if version == 1 else f"{base}-v{version}"


class ScoreSink(Protocol):
    def emitir(
        self,
        slug: str,
        capitulo: int,
        run_id: str,
        scores: Mapping[str, float],
        version: int = 1,
    ) -> list[str]:
        """Devuelve los fallos, vacío si todo llegó."""
        ...


class SinkNulo:
    def emitir(
        self,
        slug: str,
        capitulo: int,
        run_id: str,
        scores: Mapping[str, float],
        version: int = 1,
    ) -> list[str]:
        return []


@dataclass(frozen=True)
class SinkLangfuse:
    base_url: str
    publica: str
    secreta: str

    def emitir(
        self,
        slug: str,
        capitulo: int,
        run_id: str,
        scores: Mapping[str, float],
        version: int = 1,
    ) -> list[str]:
        credencial = base64.b64encode(f"{self.publica}:{self.secreta}".encode()).decode()
        for nombre, valor in scores.items():
            cuerpo = {
                "id": id_de_score(slug, run_id, capitulo, nombre, version),
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


_LINEA = re.compile(r"(?:export\s+)?([A-Za-z_]\w*)\s*=\s*(.*)")


def fusionar(entorno: Mapping[str, str], texto_env: str | None) -> dict[str, str]:
    """`entorno` más las claves del emisor de un `.env`: `TRACE_TO_LANGFUSE` y `LANGFUSE_*`, y nada
    más. Lo ya definido no se pisa. Una línea que no entiende se salta sin error y sin citarla."""
    fusion = dict(entorno)
    for linea in (texto_env or "").splitlines():
        casa = _LINEA.fullmatch(linea.strip())
        if casa is None:
            continue
        clave, valor = casa.groups()
        if clave != "TRACE_TO_LANGFUSE" and not clave.startswith("LANGFUSE_"):
            continue
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "'\"":
            valor = valor[1:-1]
        fusion.setdefault(clave, valor)
    return fusion


def entorno_efectivo(raiz: Path) -> dict[str, str]:
    """Lo que ve el emisor: el entorno del proceso más `raiz/.env`. Nunca toca `os.environ`, así
    que las claves no llegan a ningún hijo del CLI (RNF-07)."""
    env = raiz / ".env"
    texto = env.read_text(encoding="utf-8", errors="replace") if env.is_file() else None
    return fusionar(os.environ, texto)


def desde_entorno(entorno: Mapping[str, str]) -> ScoreSink:
    if entorno.get("TRACE_TO_LANGFUSE") != "true":
        return SinkNulo()
    base = entorno.get("LANGFUSE_BASE_URL") or entorno.get("LANGFUSE_HOST")
    return SinkLangfuse(
        base_url=base or "https://cloud.langfuse.com",
        publica=entorno.get("LANGFUSE_PUBLIC_KEY", ""),
        secreta=entorno.get("LANGFUSE_SECRET_KEY", ""),
    )
