"""Los prompts de los roles en Langfuse Prompt Management (docs/observabilidad.md §4).

Git sigue siendo la fuente de verdad: Langfuse recibe una copia de cada `.claude/agents/*.md`,
etiquetada con el sha corto del commit y `production`, y solo cuando el texto cambia. Cada versión
lleva en `config.sha256` la huella del fichero, la misma que la traza de cada paso registra por
rol: así se sabe qué versión produjo cada resultado.
"""

import urllib.error
import urllib.parse
from pathlib import Path

from novela.plataforma import run
from novela.plataforma.workspace import sha256
from novela.slices.observabilidad.api import Api

AGENTES = run.RAIZ_REPO / ".claude" / "agents"


def huellas(agentes: Path = AGENTES) -> dict[str, str]:
    """rol → sha256 del fichero del agente, tal como está en disco."""
    return {p.stem: sha256(p) for p in sorted(agentes.glob("*.md"))}


def metadatos_de_version(agentes: Path = AGENTES) -> dict[str, str]:
    """Lo que la traza de un paso registra de las versiones: el commit y la huella de cada rol."""
    return {"sha_commit": run._sha_commit()} | {
        f"prompt_{rol}": h[:12] for rol, h in huellas(agentes).items()
    }


def publicar(api: Api, agentes: Path, sha_corto: str) -> dict[str, str]:
    """rol → "igual" o "vN". Idempotente: si la versión `production` ya tiene este texto, no crea
    otra. Un error de HTTP se lanza: publicar es una orden explícita, no un efecto colateral."""
    resultado: dict[str, str] = {}
    for ruta in sorted(agentes.glob("*.md")):
        rol, texto = ruta.stem, ruta.read_text(encoding="utf-8")
        try:
            actual = api.pedir(
                "GET", f"/api/public/v2/prompts/{urllib.parse.quote(rol)}?label=production"
            )
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            actual = None
        if actual and actual.get("prompt") == texto:
            resultado[rol] = "igual"
            continue
        nueva = api.pedir(
            "POST",
            "/api/public/v2/prompts",
            {
                "name": rol,
                "type": "text",
                "prompt": texto,
                "labels": [sha_corto, "production"],
                "config": {"sha256": sha256(ruta), "fichero": f".claude/agents/{ruta.name}"},
                "commitMessage": f".claude/agents/{ruta.name} en {sha_corto}",
            },
        )
        resultado[rol] = f"v{nueva['version']}"
    return resultado
