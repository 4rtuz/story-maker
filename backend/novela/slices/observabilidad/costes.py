"""`novela costes`: tokens, coste y latencia por llamada, por paso (capítulo) y por novela.

Lee `GET /api/public/v2/observations`, la única API de lectura viva en las organizaciones nuevas
(architecture.md §10.1). El coste lo calcula Langfuse con su tabla de precios de los modelos de
Claude (`totalCost` de cada generación); aquí solo se suma.

Dos formas de traza conviven. La nueva: `producir` o `novela traza` abren una raíz por paso con
`metadata.paso` y todo cuelga de ella. La legada: cada turno es una traza en la sesión de Claude
Code, con la etiqueta del slug; su paso sale del `harness.log` del run donde escribió esa sesión.
"""

import json
import re
import urllib.parse
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from novela.plataforma import run
from novela.plataforma.langfuse import sesion_de
from novela.slices.observabilidad.api import Api

DESTINO = run.RAIZ_REPO / "docs" / "evaluacion"
CAMPOS = "core,basic,usage,model,metadata,metrics,trace_context"
_SESION = re.compile(r" sesion=([0-9a-f-]{36}) ")
_SKILLS = {"novela-brief": "brief", "novela-nueva": "nueva", "novela-auditar": "auditoria"}

Obs = dict[str, Any]


def _paginas(api: Api, consulta: Mapping[str, str]) -> Iterator[Obs]:
    cursor = None
    while True:
        q = {**consulta, "limit": "1000", "fields": CAMPOS}
        if cursor:
            q["cursor"] = cursor
        pagina = api.pedir("GET", "/api/public/v2/observations?" + urllib.parse.urlencode(q))
        yield from pagina["data"]
        cursor = (pagina.get("meta") or {}).get("cursor")
        if not cursor or not pagina["data"]:
            return


def descargar(api: Api, slug: str) -> list[Obs]:
    """Todo lo etiquetado con el slug, más lo que cuelga de las raíces nuevas, que no lleva
    etiquetas: en modo adjunto, el plugin deja la traza a quien la abrió."""
    filtro = [{"type": "arrayOptions", "column": "tags", "operator": "any of", "value": [slug]}]
    vistas = {o["id"]: o for o in _paginas(api, {"filter": json.dumps(filtro)})}
    raices = {o["traceId"] for o in vistas.values() if (o.get("metadata") or {}).get("paso")}
    for traza in sorted(raices):
        vistas |= {o["id"]: o for o in _paginas(api, {"traceId": traza})}
    return list(vistas.values())


def sesiones_del_workspace(raiz: Path) -> dict[str, str]:
    """Sesión de Claude Code → paso, de los runs de una novela: `harness.log` lleva `sesion=` en
    cada línea, y el manifiesto del run dice de qué capítulo y fase es."""
    pasos: dict[str, str] = {}
    for directorio in sorted(raiz.glob("runs/*")):
        manifiesto, log = directorio / "manifest.json", directorio / "harness.log"
        if not (manifiesto.is_file() and log.is_file()):
            continue
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        paso = "nueva" if datos.get("fase") == "arranque" else f"capitulo {datos['capitulo']:02d}"
        for sesion in _SESION.findall(log.read_text(encoding="utf-8", errors="replace")):
            pasos.setdefault(sesion, paso)
    return pasos


def _instante(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _paso(traza: list[Obs], sesiones: Mapping[str, str]) -> str:
    for o in traza:
        if paso := (o.get("metadata") or {}).get("paso"):
            return str(paso)
    sesion = next((o["sessionId"] for o in traza if o.get("sessionId")), "")
    if sesion in sesiones:
        return sesiones[sesion]
    for etiqueta in (e for o in traza for e in o.get("tags") or []):
        if (skill := etiqueta.removeprefix("skill:")) in _SKILLS:
            return _SKILLS[skill]
    return f"sesión {sesion[:8]}"


def _rol(o: Obs | None, por_id: Mapping[str, Obs]) -> str:
    """El `agent_type` del span de subagente más cercano hacia arriba; si no hay, la sesión
    principal."""
    while o is not None:
        meta = o.get("metadata") or {}
        if rol := meta.get("agent_type") or meta.get("subagent_type"):
            return str(rol)
        o = por_id.get(o.get("parentObservationId") or "")
    return "orquestador"


def _sumar(generaciones: Iterable[Obs]) -> dict[str, Any]:
    gens = list(generaciones)
    uso = [o.get("usageDetails") or {} for o in gens]
    llamadas = len(gens)
    latencias = sum(float(o.get("latency") or 0) for o in gens)
    return {
        "llamadas": llamadas,
        "tokens_entrada": sum(v for u in uso for k, v in u.items() if k not in ("output", "total")),
        "tokens_salida": sum(u.get("output", 0) for u in uso),
        "tokens_cache_lectura": sum(v for u in uso for k, v in u.items() if "cache_read" in k),
        "coste_usd": round(sum(float(o.get("totalCost") or 0) for o in gens), 6),
        "latencia_media_llamada_s": round(latencias / llamadas, 3) if llamadas else 0.0,
    }


def _duracion(traza: list[Obs]) -> float:
    inicio = min(_instante(o["startTime"]) for o in traza)
    fin = max(_instante(o.get("endTime") or o["startTime"]) for o in traza)
    return (fin - inicio).total_seconds()


def agregar(slug: str, observaciones: Iterable[Obs], sesiones: Mapping[str, str]) -> dict[str, Any]:
    """Por paso, con el desglose por rol, y el total de la novela. La latencia de un paso es el
    tiempo de pared de sus trazas, sin los huecos entre ellas; la de la novela, la suma."""
    por_id = {o["id"]: o for o in observaciones}
    trazas: dict[str, list[Obs]] = defaultdict(list)
    for o in por_id.values():
        trazas[o["traceId"]].append(o)
    grupos: dict[str, list[Obs]] = defaultdict(list)
    duracion: dict[str, float] = defaultdict(float)
    for traza in trazas.values():
        paso = _paso(traza, sesiones)
        grupos[paso].extend(traza)
        duracion[paso] += _duracion(traza)

    pasos = []
    for paso, obs in sorted(grupos.items(), key=lambda g: min(o["startTime"] for o in g[1])):
        gens = [o for o in obs if o["type"] == "GENERATION"]
        roles: dict[str, list[Obs]] = defaultdict(list)
        for g in gens:
            roles[_rol(g, por_id)].append(g)
        pasos.append(
            {
                "paso": paso,
                **_sumar(gens),
                "latencia_s": round(duracion[paso], 3),
                "roles": {rol: _sumar(g) for rol, g in sorted(roles.items())},
            }
        )
    total = _sumar(o for o in por_id.values() if o["type"] == "GENERATION")
    total["latencia_s"] = round(sum(p["latencia_s"] for p in pasos), 3)
    return {"slug": slug, "sesion": sesion_de(slug), "pasos": pasos, "total": total}


_CABECERA = "| {} | llamadas | entrada | salida | caché leída | coste USD | latencia s |"
_FILA = (
    "| {} | {llamadas} | {tokens_entrada} | {tokens_salida} | {tokens_cache_lectura} "
    "| {coste_usd:.4f} | {lat} |"
)
_ALINEA = "|---|---:|---:|---:|---:|---:|---:|"


def markdown(informe: dict[str, Any]) -> str:
    total = informe["total"]
    lineas = [
        f"# Costes de {informe['slug']}",
        "",
        f"Sesión de Langfuse `{informe['sesion']}`. Generado por `novela costes {informe['slug']} "
        "--markdown` desde `GET /api/public/v2/observations`; el coste es el `totalCost` que "
        "Langfuse calcula por generación. La entrada incluye la caché leída. Latencia de un "
        "paso: tiempo de pared de sus trazas; de la novela: la suma de sus pasos.",
        "",
        "## Por paso",
        "",
        _CABECERA.format("paso"),
        _ALINEA,
        *(_FILA.format(p["paso"], lat=p["latencia_s"], **p) for p in informe["pasos"]),
        _FILA.format("**novela**", lat=total["latencia_s"], **total),
        "",
        "## Por rol y paso",
        "",
        "La latencia es la media por llamada.",
        "",
        _CABECERA.format("paso · rol"),
        _ALINEA,
    ]
    for p in informe["pasos"]:
        for rol, r in p["roles"].items():
            lineas.append(
                _FILA.format(f"{p['paso']} · {rol}", lat=r["latencia_media_llamada_s"], **r)
            )
    return "\n".join(lineas) + "\n"
