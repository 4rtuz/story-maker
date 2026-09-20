#!/usr/bin/env python3
"""Recupera de Langfuse los prompts del Evaluador de los runs historicos y los
congela como fixture versionado.

Por que Langfuse y no `runs/`: `.gitignore` excluye `runs/*`, los dos runs que
anclaba `scripts/fixture.json` (`el-buzon-de-la-planta-baja-2`,
`los-ruidos-del-bosque`) nunca se commitearon y ya no estan en disco. Langfuse si
conserva cada llamada al Evaluador con su prompt ensamblado completo en `input`.

Un fixture de *prompts congelados* (no de borradores + run root) es ademas lo que
pide el experimento: lo unico que varia entre candidatos es el system prompt del
Evaluador; el prompt de usuario tiene que ser byte a byte el mismo.

Modos:
    --listar (por defecto)  inventario de lo que hay en Langfuse, no escribe nada
    --construir             escribe fixtures/evaluador/ (prompts + manifest.json)

Ver docs/automejora/pre-registro-calibracion-evaluador.md.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from panel.tracing import load_env  # noqa: E402

FIXTURE_DIR = ROOT / "fixtures" / "evaluador"
PROMPTS_DIR = FIXTURE_DIR / "prompts"
MANIFEST = FIXTURE_DIR / "manifest.json"

MARCA_CAPITULO = "## Capitulo a evaluar".replace("Capitulo", "Capítulo")
RE_CAPITULO = re.compile(r"TAREA: eval[úu]a el cap[íi]tulo (\d+)")
RE_FRASE = re.compile(r"[^.!?…]+[.!?…]+\s*|[^.!?…]+$")
RE_ESCENA = re.compile(r"(<!--\s*ESCENA\s*\d+\s*-->)")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def api(path: str, params: dict) -> dict:
    load_env(ROOT)
    base = os.environ["LANGFUSE_BASE_URL"].rstrip("/")
    raw = f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}"
    token = base64.b64encode(raw.encode()).decode()
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{base}{path}?{query}",
                                 headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch(desde: str, hasta: str, limite: int) -> list[dict]:
    filtro = json.dumps([{"column": "name", "operator": "=",
                          "value": "evaluador", "type": "string"}])
    data = api("/api/public/v2/observations", {
        "fromStartTime": desde, "toStartTime": hasta,
        "limit": limite, "fields": "core,basic,io", "filter": filtro,
    })["data"]
    if len(data) >= limite:
        sys.exit(f"ABORTADO: la pagina viene llena ({limite}); sube --limite, "
                 "hay observaciones sin recuperar y el fixture quedaria parcial.")
    return data


def usable(obs: dict) -> bool:
    return (obs.get("environment") == "development"
            and isinstance(obs.get("input"), str)
            and MARCA_CAPITULO in obs["input"]
            and RE_CAPITULO.search(obs["input"]) is not None)


def inventario(obs_list: list[dict]) -> list[dict]:
    """Dedup por hash del prompt y orden determinista por (instante, hash)."""
    vistos: dict[str, dict] = {}
    for obs in sorted(obs_list, key=lambda o: (o["startTime"], o["id"])):
        if not usable(obs):
            continue
        h = sha256(obs["input"])
        if h in vistos:
            continue
        vistos[h] = {
            "sha256": h,
            "traza": obs["traceId"][:8],
            "observacion": obs["id"],
            "instante": obs["startTime"],
            "capitulo": int(RE_CAPITULO.search(obs["input"]).group(1)),
            "prompt": obs["input"],
        }
    return sorted(vistos.values(), key=lambda r: (r["instante"], r["sha256"]))


def partir(texto: str) -> tuple[str, str]:
    """Separa el prompt en (cabecera, borrador). El borrador es el ultimo bloque."""
    cabecera, marca, borrador = texto.partition(MARCA_CAPITULO + "\n")
    if not marca:
        raise ValueError("prompt sin bloque de capitulo")
    return cabecera + marca, borrador


def frases(texto: str) -> list[str]:
    return [f for f in RE_FRASE.findall(texto) if f.strip()]


def sin_gancho(borrador: str) -> str:
    """Borra la ultima frase del capitulo. La rubrica pregunta explicitamente
    '¿cierra en gancho?' dentro de `tension`, que es criterio bloqueante."""
    cuerpo, marca_fin, resto = borrador.partition("<!-- FIN -->")
    fs = frases(cuerpo)
    if len(fs) < 2:
        raise ValueError("borrador demasiado corto para degradar sin gancho")
    return "".join(fs[:-1]).rstrip() + "\n\n" + marca_fin + resto


def barajado(borrador: str, semilla: str) -> str:
    """Baraja las frases dentro de cada escena con semilla fija. No toca los
    marcadores ni el recuento de palabras: degrada ritmo/prosa/escaleta y deja
    intacto todo lo demas."""
    rng = random.Random(semilla)
    piezas = RE_ESCENA.split(borrador)
    salida = []
    for pieza in piezas:
        if RE_ESCENA.fullmatch(pieza) or not pieza.strip():
            salida.append(pieza)
            continue
        cuerpo, marca_fin, resto = pieza.partition("<!-- FIN -->")
        fs = [f.strip() for f in frases(cuerpo)]
        if len(set(fs)) > 1:
            orden = fs[:]
            for _ in range(20):
                rng.shuffle(orden)
                if orden != fs:
                    break
            cuerpo = " ".join(orden)
        salida.append(cuerpo + ("\n\n" if marca_fin else "") + marca_fin + resto)
    return "".join(salida)


def construir(registros: list[dict], corte: str) -> None:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    for viejo in PROMPTS_DIR.glob("*.md"):
        viejo.unlink()

    entradas = []
    for i, reg in enumerate(registros, 1):
        split = "dev" if reg["instante"] < corte else "holdout"
        base = f"{i:02d}-c{reg['capitulo']:02d}-{reg['traza']}"
        cabecera, borrador = partir(reg["prompt"])
        variantes = {
            "orig": reg["prompt"],
            "singancho": cabecera + sin_gancho(borrador),
            "barajado": cabecera + barajado(borrador, reg["sha256"]),
        }
        for nombre, texto in variantes.items():
            ruta = PROMPTS_DIR / f"{base}-{nombre}.md"
            with ruta.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(texto)
            entradas.append({
                "id": f"{base}-{nombre}",
                "archivo": f"prompts/{ruta.name}",
                "variante": nombre,
                "par": base,
                "split": split,
                "capitulo": reg["capitulo"],
                "traza": reg["traza"],
                "observacion": reg["observacion"],
                "instante": reg["instante"],
                "sha256": sha256(texto),
                "palabras_borrador": len(partir(texto)[1].split()),
            })

    manifest = {
        "_documentacion": (
            "Fixture congelado de prompts del Evaluador, recuperado de Langfuse "
            "por scripts/recuperar_fixture.py. Es de solo lectura: "
            "scripts/calibrar_evaluador.py aborta si un sha256 no coincide. Ver "
            "docs/automejora/pre-registro-calibracion-evaluador.md."
        ),
        "variantes": {
            "orig": "prompt tal cual lo ensamblo el nucleo en el run historico",
            "singancho": "sin la ultima frase del capitulo (degrada `tension`)",
            "barajado": "frases barajadas dentro de cada escena, semilla fija "
                        "(degrada `ritmo`/`prosa`/`escaleta`)",
        },
        "corte_dev_holdout": corte,
        "entradas": entradas,
    }
    with MANIFEST.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    porsplit: dict[str, int] = {}
    for e in entradas:
        porsplit[e["split"]] = porsplit.get(e["split"], 0) + 1
    print(f"{len(entradas)} prompts escritos en {PROMPTS_DIR.relative_to(ROOT)} "
          f"({porsplit}). Manifest: {MANIFEST.relative_to(ROOT)}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--desde", default="2026-09-01T00:00:00Z")
    p.add_argument("--hasta", default="2026-09-21T00:00:00Z")
    p.add_argument("--limite", type=int, default=500)
    p.add_argument("--corte-dev", default="2026-09-17T00:00:00Z",
                   help="instante que separa dev (antes) de holdout (despues)")
    p.add_argument("--construir", action="store_true")
    args = p.parse_args()

    registros = inventario(fetch(args.desde, args.hasta, args.limite))
    if not registros:
        sys.exit("ABORTADO: Langfuse no devolvio ninguna observacion `evaluador` usable.")

    print(f"{len(registros)} prompts unicos del Evaluador:")
    print(f"{'#':>3}  {'traza':8}  {'cap':>3}  {'palabras':>8}  {'split':8}  instante")
    for i, reg in enumerate(registros, 1):
        split = "dev" if reg["instante"] < args.corte_dev else "holdout"
        palabras = len(partir(reg["prompt"])[1].split())
        print(f"{i:3}  {reg['traza']:8}  {reg['capitulo']:3}  {palabras:8}  "
              f"{split:8}  {reg['instante']}")

    if args.construir:
        construir(registros, args.corte_dev)


if __name__ == "__main__":
    main()
