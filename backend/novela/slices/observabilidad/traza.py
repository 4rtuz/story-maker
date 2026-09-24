"""Una traza por paso, todas en la sesión de la novela (docs/observabilidad.md §1).

El plugin de Langfuse agrupa por el session id de Claude Code, que es uno por `claude -p`. Pero si
`CC_LANGFUSE_TRACEPARENT` está definida, cuelga la sesión entera de ese span y deja que la traza
sea de quien la abrió. Aquí se abre esa traza: un span OTLP raíz con la sesión de la novela, su
nombre, las etiquetas y los metadatos del paso.
"""

import json
import secrets
import time
import urllib.error
from collections.abc import Mapping

from novela.plataforma.langfuse import sesion_de
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.observabilidad.api import Api

_PASOS = {"/novela-brief": "brief", "/novela-nueva": "nueva", "/novela-auditar": "auditoria"}


def paso_de(ws: WorkspaceRepository, orden: str) -> str:
    """El paso de una orden: `/novela-continuar` es el capítulo siguiente al último cerrado; lo
    que no es una orden conocida se usa tal cual (`cambio`, `brief-2`...)."""
    if orden != "/novela-continuar":
        return _PASOS.get(orden, orden)
    latest = ws.raiz / "checkpoints" / "latest.json"
    try:
        cerrado = int(json.loads(latest.read_text(encoding="utf-8")).get("capitulo", 0))
    except (OSError, ValueError, AttributeError):
        cerrado = 0
    return f"capitulo {cerrado + 1:02d}"


def _atributo(clave: str, valor: str | list[str]) -> dict[str, object]:
    if isinstance(valor, list):
        return {
            "key": clave,
            "value": {"arrayValue": {"values": [{"stringValue": v} for v in valor]}},
        }
    return {"key": clave, "value": {"stringValue": valor}}


def abrir(
    entorno: Mapping[str, str], slug: str, paso: str, metadatos: Mapping[str, str]
) -> str | None:
    """El traceparent W3C de la traza nueva, o None sin `TRACE_TO_LANGFUSE=true` o si Langfuse no
    contesta: el trazado nunca para un paso, que sin padre se traza como antes, en su sesión."""
    if entorno.get("TRACE_TO_LANGFUSE") != "true":
        return None
    traza, span = secrets.token_hex(16), secrets.token_hex(8)
    ahora = time.time_ns()
    atributos = [
        _atributo("langfuse.session.id", sesion_de(slug)),
        _atributo("langfuse.trace.name", f"{slug} · {paso}"),
        _atributo("langfuse.trace.tags", [slug, "novela"]),
        _atributo("langfuse.trace.metadata.slug", slug),
        _atributo("langfuse.trace.metadata.paso", paso),
        *(_atributo(f"langfuse.trace.metadata.{k}", v) for k, v in metadatos.items()),
    ]
    cuerpo = {
        "resourceSpans": [
            {
                "resource": {"attributes": [_atributo("service.name", "novela")]},
                "scopeSpans": [
                    {
                        "scope": {"name": "novela"},
                        "spans": [
                            {
                                "traceId": traza,
                                "spanId": span,
                                "name": f"{slug} · {paso}",
                                "kind": 1,
                                "startTimeUnixNano": str(ahora),
                                "endTimeUnixNano": str(ahora + 1_000_000),
                                "attributes": atributos,
                            }
                        ],
                    }
                ],
            }
        ]
    }
    try:
        Api.de(entorno).pedir(
            "POST",
            "/api/public/otel/v1/traces",
            cuerpo,
            {"x-langfuse-ingestion-version": "4"},
            timeout=5.0,
        )
    except (OSError, urllib.error.URLError, ValueError):
        return None
    return f"00-{traza}-{span}-01"
