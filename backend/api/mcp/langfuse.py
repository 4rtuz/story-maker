"""Una traza `mcp.<tool>` en Langfuse por llamada, con la configuración de los scores
(`novela.plataforma.langfuse`): sin `TRACE_TO_LANGFUSE=true` no sale nada. Solo viajan el nombre,
los argumentos, la duración y el error; nunca la prosa ni el PDF. Un fallo de red no rompe la
tool: se descarta, como en el emisor de scores."""

import asyncio
import base64
import json
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from typing import Any

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult

from novela.plataforma import langfuse, run


def _sink() -> langfuse.ScoreSink:
    return langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))


def emitir(traza: dict[str, Any]) -> None:
    sink = _sink()
    if not isinstance(sink, langfuse.SinkLangfuse):
        return
    ahora = datetime.now(UTC).isoformat()
    cuerpo = {"id": str(uuid.uuid4()), "timestamp": ahora, "tags": ["mcp"], **traza}
    evento = {"id": str(uuid.uuid4()), "timestamp": ahora, "type": "trace-create", "body": cuerpo}
    credencial = base64.b64encode(f"{sink.publica}:{sink.secreta}".encode()).decode()
    peticion = urllib.request.Request(  # noqa: S310 — la URL la fija la configuración
        f"{sink.base_url.rstrip('/')}/api/public/ingestion",
        data=json.dumps({"batch": [evento]}).encode(),
        headers={"Authorization": f"Basic {credencial}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=langfuse.TIMEOUT_S):  # noqa: S310
            pass
    except OSError:
        pass  # el trazado nunca es la razón por la que una consulta falla


def _recortar(argumentos: dict[str, Any]) -> dict[str, Any]:
    """Un texto largo (el de `request_change`) viaja recortado, con su longitud."""
    return {
        k: f"{v[:80]}… ({len(v)} caracteres)" if isinstance(v, str) and len(v) > 120 else v
        for k, v in argumentos.items()
    }


class TrazaLangfuse(Middleware):
    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        inicio, error = time.perf_counter(), None
        try:
            return await call_next(context)
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            traza = {
                "name": f"mcp.{context.message.name}",
                "input": _recortar(context.message.arguments or {}),
                "metadata": {"duracion_ms": round((time.perf_counter() - inicio) * 1000)},
                "error": error,
            }
            # ponytail: síncrono en un hilo; con Langfuse lento la respuesta espera hasta
            # TIMEOUT_S. Cola en segundo plano si llega a notarse.
            await asyncio.to_thread(emitir, traza)
