#!/usr/bin/env python3
"""Mide ruido y discriminacion del Evaluador sobre el fixture congelado.

Contrato del experimento: docs/automejora/pre-registro-calibracion-evaluador.md.
Este script MIDE y DICTA EL VEREDICTO. El modelo que escribe candidatos no calcula
ninguna metrica ni decide si un candidato entra: eso lo hace `veredicto()` aqui,
igual que `harness decide` calcula la aceptacion de un capitulo y no se fia del
veredicto que declare el modelo (9.2).

Lo que NO toca nunca: el fixture (`fixtures/evaluador/`), la baseline
(`fixtures/evaluador/baseline.json`), el pre-registro, ni `.claude/agents/
evaluador.md` (salvo `--promover`, que exige META confirmada en holdout).

Uso tipico:
    python scripts/calibrar_evaluador.py --candidato baseline --fijar-baseline
    python scripts/calibrar_evaluador.py --candidato docs/automejora/variantes/02-anclas.md
    python scripts/calibrar_evaluador.py --candidato ... --split holdout --sellar
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import config as harness_config  # noqa: E402
from harness.deltas import computed_mean, validate_evaluation  # noqa: E402

FIXTURE_DIR = ROOT / "fixtures" / "evaluador"
MANIFEST = FIXTURE_DIR / "manifest.json"
BASELINE = FIXTURE_DIR / "baseline.json"
AGENTE = ROOT / ".claude" / "agents" / "evaluador.md"
AUTOMEJORA = ROOT / "docs" / "automejora"
LEDGER = AUTOMEJORA / "candidatos.jsonl"
RESULTADOS = AUTOMEJORA / "resultados"

CRITERIOS = ["tension", "escaleta", "voz", "caracterizacion", "ritmo", "prosa"]
DEGRADACIONES = ["singancho", "barajado"]

# --- Umbrales del pre-registro. No se tocan sin reescribir el pre-registro. ---
META_SIGMA = 0.17            # un criterio de seis vale 1/6 = 0.167
META_GATES = 6               # de 7 pares dev con el gate bloqueante estable
MARGEN_SIGMA = 0.05          # bajada minima para llamar "mejor" a un candidato
TOLERANCIA_AUC = 0.05        # cuanto puede caer la discriminacion (guardarrail)
TOLERANCIA_CRITERIO = 0.10   # cuanto puede subir la sigma de un criterio suelto
MIN_FRACCION_SIGMA_ENTRE = 0.80  # anti-colapso: varianza ENTRE borradores
TOPE_LLAMADAS = 150
TOPE_COSTE_LLAMADA = "0.25"  # --max-budget-usd por llamada

ESQUEMA_SALIDA = {
    "type": "object",
    "properties": {
        "capitulo": {"type": "integer"},
        "puntuaciones": {
            "type": "object",
            "properties": {c: {"type": "integer", "minimum": 1, "maximum": 5}
                           for c in CRITERIOS},
            "required": CRITERIOS,
            "additionalProperties": False,
        },
        "media": {"type": "number"},
        "veredicto": {"type": "string", "enum": ["APROBADO", "CORREGIR"]},
        "parches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "escena": {"type": "integer"},
                    "criterio": {"type": "string", "enum": CRITERIOS},
                    "problema": {"type": "string"},
                    "correccion": {"type": "string"},
                },
                "required": ["escena", "criterio", "problema", "correccion"],
                "additionalProperties": False,
            },
        },
        "observaciones": {"type": "string"},
    },
    "required": ["capitulo", "puntuaciones", "media", "veredicto", "parches",
                 "observaciones"],
    "additionalProperties": False,
}


# --------------------------------------------------------------------------
# fixture y candidato
# --------------------------------------------------------------------------
def sha256_texto(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cargar_fixture(split: str) -> list[dict]:
    if not MANIFEST.exists():
        sys.exit("ABORTADO: no hay fixture. Corre antes "
                 "`python scripts/recuperar_fixture.py --construir`.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entradas = [e for e in manifest["entradas"] if e["split"] == split]
    if not entradas:
        sys.exit(f"ABORTADO: el manifest no tiene entradas del split {split!r}.")
    for e in entradas:
        ruta = FIXTURE_DIR / e["archivo"]
        if not ruta.exists():
            sys.exit(f"ABORTADO: falta {e['archivo']} del fixture.")
        texto = ruta.read_text(encoding="utf-8")
        if sha256_texto(texto) != e["sha256"]:
            sys.exit(f"ABORTADO: {e['archivo']} no coincide con su sha256 del "
                     "manifest. El fixture es de solo lectura; si el cambio es "
                     "intencional hay que reconstruirlo y anotarlo en la bitacora.")
        e["texto"] = texto
    return entradas


def separar_frontmatter(texto: str) -> tuple[dict, str]:
    if not texto.startswith("---"):
        return {}, texto
    _, _, resto = texto.partition("---\n")
    cabecera, sep, cuerpo = resto.partition("---\n")
    if not sep:
        return {}, texto
    meta = {}
    for linea in cabecera.splitlines():
        if ":" in linea:
            k, _, v = linea.partition(":")
            meta[k.strip()] = v.strip()
    return meta, cuerpo.lstrip("\n")


def cargar_candidato(ref: str) -> dict:
    ruta = AGENTE if ref == "baseline" else Path(ref)
    if not ruta.exists():
        sys.exit(f"ABORTADO: no existe el candidato {ruta}.")
    bruto = ruta.read_text(encoding="utf-8")
    meta, cuerpo = separar_frontmatter(bruto)
    esquema = str(meta.get("esquema", "false")).lower() in {"true", "si", "sí", "1"}
    return {
        "ref": ref,
        "etiqueta": meta.get("etiqueta") or ("baseline" if ref == "baseline"
                                             else ruta.stem),
        "prompt": cuerpo.strip(),
        "esquema": esquema,
        "hipotesis": meta.get("hipotesis", ""),
        "sha256": sha256_texto(bruto),
    }


def binario_claude() -> str:
    for candidato in (os.environ.get("CLAUDE_BIN"),
                      str(Path.home() / ".local" / "bin" / "claude.exe"),
                      "claude"):
        if not candidato:
            continue
        if candidato == "claude" or Path(candidato).exists():
            return candidato
    sys.exit("ABORTADO: no encuentro el ejecutable `claude`. Define CLAUDE_BIN.")


# --------------------------------------------------------------------------
# llamada
# --------------------------------------------------------------------------
def quitar_cercos(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1] if "\n" in texto else ""
        if texto.endswith("```"):
            texto = texto.rsplit("```", 1)[0]
    return texto.strip()


def llamar(prompt: str, cand: dict, claude: str) -> tuple[dict, float]:
    agentes = {"evaluador_cal": {
        "description": "Evaluador bajo calibracion. No se instala: vive solo "
                       "en esta llamada.",
        "prompt": cand["prompt"],
        "tools": [],
        "model": "haiku",
    }}
    cmd = [claude, "-p", "--agents", json.dumps(agentes, ensure_ascii=False),
           "--agent", "evaluador_cal", "--allowedTools", "",
           "--output-format", "json", "--max-budget-usd", TOPE_COSTE_LLAMADA]
    if cand["esquema"]:
        cmd += ["--json-schema", json.dumps(ESQUEMA_SALIDA)]
    proc = subprocess.run(cmd, input=prompt, cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr[-400:]}")
    outer = json.loads(proc.stdout)
    if outer.get("is_error"):
        raise RuntimeError(f"is_error: {str(outer.get('result'))[:300]}")
    obj = json.loads(quitar_cercos(outer["result"]))
    return obj, float(outer.get("total_cost_usd") or 0.0)


def medir(entradas: list[dict], cand: dict, pasadas: int, hilos: int,
          cfg) -> list[dict]:
    total = len(entradas) * pasadas
    if total > TOPE_LLAMADAS:
        sys.exit(f"ABORTADO: {total} llamadas superan el tope duro de {TOPE_LLAMADAS}.")
    claude = binario_claude()
    trabajos = [(e, p) for e in entradas for p in range(1, pasadas + 1)]
    registros, hechos = [], 0
    inicio = time.time()

    def uno(entrada: dict, pasada: int) -> dict:
        reg = {k: entrada[k] for k in ("id", "par", "variante", "split", "capitulo")}
        reg["pasada"] = pasada
        gastado, ultimo = 0.0, ""
        # Un fallo transitorio de red invalidaria la tanda entera (la regla del
        # pre-registro descarta cualquier medicion con llamadas fallidas), asi
        # que se reintenta. Un JSON mal formado NO se reintenta: es dato.
        for intento in (1, 2):
            try:
                obj, coste = llamar(entrada["texto"], cand, claude)
                gastado += coste
                problemas = validate_evaluation(obj, cfg)
                reg.update({
                    "ok": True,
                    "valido": not problemas,
                    "problemas": problemas,
                    "puntuaciones": obj.get("puntuaciones", {}),
                    "media_calculada": computed_mean(obj),
                    "media_declarada": obj.get("media"),
                    "veredicto_modelo": obj.get("veredicto"),
                    "intentos": intento,
                    "coste": gastado,
                })
                return reg
            except Exception as exc:  # noqa: BLE001 - se registra, no se descarta
                ultimo = str(exc)[:300]
                if intento == 1:
                    time.sleep(5)
        reg.update({"ok": False, "valido": False, "error": ultimo,
                    "intentos": 2, "coste": gastado})
        return reg

    with ThreadPoolExecutor(max_workers=hilos) as pool:
        futuros = {pool.submit(uno, e, p): (e, p) for e, p in trabajos}
        for fut in as_completed(futuros):
            reg = fut.result()
            registros.append(reg)
            hechos += 1
            estado = "ok" if reg["ok"] else f"FALLO: {reg.get('error')}"
            if reg["ok"] and not reg["valido"]:
                estado = f"JSON INVALIDO: {reg['problemas']}"
            print(f"[{hechos}/{total}] {reg['id']} p{reg['pasada']}: {estado}",
                  flush=True)

    print(f"{total} llamadas en {round(time.time() - inicio)} s.")
    return sorted(registros, key=lambda r: (r["id"], r["pasada"]))


# --------------------------------------------------------------------------
# metricas
# --------------------------------------------------------------------------
def _sigma(valores: list[float]):
    return round(statistics.stdev(valores), 4) if len(valores) >= 2 else None


def metricas(registros: list[dict], cfg) -> dict:
    ev = cfg["evaluacion"]
    umbral = ev["umbral_criterio_bloqueante"]
    bloqueantes = ev["criterios_bloqueantes"]
    buenos = [r for r in registros if r["ok"] and r["valido"]]

    por_variante: dict[str, dict[str, list[dict]]] = {}
    for r in buenos:
        por_variante.setdefault(r["variante"], {}).setdefault(r["par"], []).append(r)
    origs = por_variante.get("orig", {})

    # -- ruido intra-borrador (solo sobre los originales) --
    sigmas_media, gates_estables, detalle = [], 0, {}
    sigmas_criterio: dict[str, list[float]] = {c: [] for c in CRITERIOS}
    for par, regs in sorted(origs.items()):
        medias = [r["media_calculada"] for r in regs]
        s = _sigma(medias)
        if s is not None:
            sigmas_media.append(s)
        gates = {tuple(r["puntuaciones"].get(c, 0) >= umbral for c in bloqueantes)
                 for r in regs}
        estable = len(gates) == 1
        gates_estables += 1 if estable else 0
        crit = {}
        for c in CRITERIOS:
            vals = [r["puntuaciones"].get(c) for r in regs
                    if isinstance(r["puntuaciones"].get(c), int)]
            sc = _sigma(vals)
            if sc is not None:
                sigmas_criterio[c].append(sc)
            crit[c] = {"valores": vals, "sigma": sc}
        detalle[par] = {"medias": medias, "sigma_media": s,
                        "gate_estable": estable, "criterios": crit}

    # -- discriminacion: AUC contra cada degradacion (Mann-Whitney, empates 0.5) --
    discriminacion = {}
    for deg in DEGRADACIONES:
        comparaciones, aciertos = 0, 0.0
        for par, regs_o in origs.items():
            regs_d = por_variante.get(deg, {}).get(par, [])
            for ro in regs_o:
                for rd in regs_d:
                    comparaciones += 1
                    if ro["media_calculada"] > rd["media_calculada"]:
                        aciertos += 1.0
                    elif ro["media_calculada"] == rd["media_calculada"]:
                        aciertos += 0.5
        discriminacion[deg] = {
            "auc": round(aciertos / comparaciones, 4) if comparaciones else None,
            "comparaciones": comparaciones,
        }

    # -- anti-colapso --
    medianas = [statistics.median(d["medias"]) for d in detalle.values() if d["medias"]]
    distintos = {c: len({r["puntuaciones"].get(c) for r in buenos
                         if isinstance(r["puntuaciones"].get(c), int)})
                 for c in CRITERIOS}

    return {
        "n_llamadas": len(registros),
        "n_fallidas": sum(1 for r in registros if not r["ok"]),
        "n_invalidas": sum(1 for r in registros if r["ok"] and not r["valido"]),
        "n_pares": len(origs),
        "sigma_media_promedio": (round(statistics.mean(sigmas_media), 4)
                                 if sigmas_media else None),
        "gates_estables": gates_estables,
        "sigma_criterio_promedio": {
            c: (round(statistics.mean(v), 4) if v else None)
            for c, v in sigmas_criterio.items()},
        "discriminacion": discriminacion,
        "sigma_entre_borradores": _sigma(medianas),
        "valores_distintos_por_criterio": distintos,
        "coste_total": round(sum(r.get("coste", 0.0) for r in registros), 4),
        "detalle_por_par": detalle,
    }


def veredicto(met: dict, base: dict | None) -> tuple[str, list[str]]:
    """Regla determinista del pre-registro. El modelo no la evalua: la lee."""
    if met["n_fallidas"]:
        return "INVALIDO", [f"{met['n_fallidas']} llamadas fallaron; una tanda "
                            "incompleta no compara con nada."]
    if met["sigma_media_promedio"] is None:
        return "INVALIDO", ["no hay suficientes respuestas validas por par para "
                            "calcular una sigma; revisa n_invalidas."]
    if base is None:
        return "BASELINE", ["primera medicion: fija la referencia."]

    razones, rotos = [], []
    s, sb = met["sigma_media_promedio"], base["sigma_media_promedio"]

    for deg in DEGRADACIONES:
        auc = met["discriminacion"][deg]["auc"]
        auc_b = base["discriminacion"][deg]["auc"]
        if auc is None or auc < auc_b - TOLERANCIA_AUC:
            rotos.append(f"discriminacion {deg} {auc} < {round(auc_b - TOLERANCIA_AUC, 4)}")
    entre, entre_b = met["sigma_entre_borradores"], base["sigma_entre_borradores"]
    if entre is None or entre < entre_b * MIN_FRACCION_SIGMA_ENTRE:
        rotos.append(f"colapso: sigma entre borradores {entre} < "
                     f"{round(entre_b * MIN_FRACCION_SIGMA_ENTRE, 4)}")
    for c in CRITERIOS:
        sc, sc_b = met["sigma_criterio_promedio"][c], base["sigma_criterio_promedio"][c]
        if sc is not None and sc_b is not None and sc > sc_b + TOLERANCIA_CRITERIO:
            rotos.append(f"criterio {c} empeora: {sc} > {round(sc_b + TOLERANCIA_CRITERIO, 4)}")
    for c, n in met["valores_distintos_por_criterio"].items():
        if n < 2:
            rotos.append(f"criterio {c} colapsado a un solo valor")
    if met["n_invalidas"] > base["n_invalidas"]:
        rotos.append(f"{met['n_invalidas']} respuestas invalidas > {base['n_invalidas']}")

    if rotos:
        return "DESCARTADO", rotos

    razones.append(f"sigma {s} vs baseline {sb}")
    if s <= META_SIGMA and met["gates_estables"] >= META_GATES:
        return "META_ALCANZADA", razones + [
            f"gates estables {met['gates_estables']}/{met['n_pares']}"]
    if s <= sb - MARGEN_SIGMA:
        return "MEJOR", razones + [f"baja {round(sb - s, 4)} (minimo {MARGEN_SIGMA})"]
    return "SIN_MEJORA", razones + [
        f"no baja {MARGEN_SIGMA}; guardarrailes intactos"]


# --------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------
def leer_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


def anotar(entrada: dict) -> None:
    AUTOMEJORA.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entrada, ensure_ascii=False, sort_keys=True) + "\n")


def promover(cand: dict) -> None:
    ledger = leer_ledger()
    hechos = {(e["candidato_sha256"], e["split"]): e["veredicto"] for e in ledger}
    dev = hechos.get((cand["sha256"], "dev"))
    hold = hechos.get((cand["sha256"], "holdout"))
    if dev != "META_ALCANZADA" or hold != "META_ALCANZADA":
        sys.exit("ABORTADO: solo se promueve un candidato con META_ALCANZADA en "
                 f"dev Y en holdout. Ahora: dev={dev}, holdout={hold}.")
    original = AGENTE.read_text(encoding="utf-8")
    # El frontmatter del agente (name, description, tools, model) no es del
    # candidato: lo fija el binding (Anexo A) y se conserva tal cual.
    cabecera = original.split("---\n")[1] if original.startswith("---") else ""
    nuevo = f"---\n{cabecera}---\n\n{cand['prompt']}\n"
    AGENTE.write_text(nuevo, encoding="utf-8", newline="\n")
    print(f"Promovido {cand['etiqueta']} a {AGENTE.relative_to(ROOT)}. "
          "No se ha commiteado nada: revisa el diff.")


# --------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidato", required=True,
                   help="'baseline' o ruta a docs/automejora/variantes/*.md")
    p.add_argument("--split", choices=["dev", "holdout"], default="dev")
    p.add_argument("--pasadas", type=int, default=3)
    p.add_argument("--hilos", type=int, default=6)
    p.add_argument("--pares", type=int, default=0,
                   help="limita a los N primeros pares. Solo para pruebas de humo: "
                        "fuerza --sin-anotar, porque una medicion parcial no es "
                        "comparable con una baseline medida sobre el split entero")
    p.add_argument("--sin-anotar", action="store_true")
    p.add_argument("--fijar-baseline", action="store_true")
    p.add_argument("--sellar", action="store_true",
                   help="obligatorio para medir holdout; se mide una sola vez")
    p.add_argument("--promover", action="store_true")
    args = p.parse_args()

    cfg = harness_config.load(ROOT)
    cand = cargar_candidato(args.candidato)

    if args.promover:
        promover(cand)
        return

    if args.split == "holdout":
        if not args.sellar:
            sys.exit("ABORTADO: el holdout se mide una vez y al final. Si de "
                     "verdad toca, pasa --sellar.")
        previos = [e for e in leer_ledger() if e["split"] == "holdout"]
        if previos:
            sys.exit(f"ABORTADO: el holdout ya se midio {len(previos)} vez/veces "
                     f"({[e['candidato'] for e in previos]}). Volver a medirlo lo "
                     "convierte en dev y el experimento pierde su unica prueba "
                     "limpia. Si es inevitable, anotalo en la bitacora y borra "
                     "esta guarda a mano.")

    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    if base is not None and args.fijar_baseline:
        sys.exit(f"ABORTADO: ya existe {BASELINE.relative_to(ROOT)}. La baseline "
                 "se fija una vez; reescribirla borra la referencia de todas las "
                 "comparaciones anteriores.")

    entradas = cargar_fixture(args.split)
    parcial = args.pares > 0
    if parcial:
        pares = sorted({e["par"] for e in entradas})[:args.pares]
        entradas = [e for e in entradas if e["par"] in pares]
        args.sin_anotar = True
        if args.fijar_baseline:
            sys.exit("ABORTADO: no se fija una baseline con una medicion parcial.")
        print(f"MEDICION PARCIAL ({len(pares)} pares): no se anota ni compara.")
    print(f"Candidato: {cand['etiqueta']} (esquema={cand['esquema']}, "
          f"sha256={cand['sha256'][:12]})")
    print(f"Fixture {args.split}: {len(entradas)} prompts verificados por hash, "
          f"{args.pasadas} pasadas = {len(entradas) * args.pasadas} llamadas.")

    registros = medir(entradas, cand, args.pasadas, args.hilos, cfg)
    met = metricas(registros, cfg)
    ref = base if not args.fijar_baseline else None
    dictamen, razones = veredicto(met, ref if args.split == "dev" else base)

    RESULTADOS.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Un crudo sin linea en el ledger no es una tanda: se marca para que nadie
    # lo confunda con una medicion comparable.
    sello = "parcial-" if args.sin_anotar else ""
    crudo = RESULTADOS / f"{sello}{marca}-{cand['etiqueta']}-{args.split}.jsonl"
    with crudo.open("w", encoding="utf-8", newline="\n") as fh:
        for r in registros:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    if args.fijar_baseline:
        if met["n_fallidas"]:
            sys.exit(f"ABORTADO: {met['n_fallidas']} llamadas fallaron; una "
                     "baseline incompleta contamina todas las comparaciones "
                     f"posteriores. El crudo queda en {crudo.relative_to(ROOT)}.")
        BASELINE.write_text(json.dumps(met, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")
        print(f"Baseline fijada en {BASELINE.relative_to(ROOT)}.")

    if args.sin_anotar:
        print("(--sin-anotar: no se toca el ledger)")
    else:
        anotar({
            "fecha": marca,
            "candidato": cand["etiqueta"],
            "candidato_ref": cand["ref"],
            "candidato_sha256": cand["sha256"],
            "esquema": cand["esquema"],
            "hipotesis": cand["hipotesis"],
            "split": args.split,
            "pasadas": args.pasadas,
            "veredicto": dictamen,
            "razones": razones,
            "metricas": {k: v for k, v in met.items() if k != "detalle_por_par"},
            "crudo": str(crudo.relative_to(ROOT)).replace("\\", "/"),
        })

    print("\n=== RESULTADO ===")
    print(f"sigma(media) promedio ....... {met['sigma_media_promedio']}")
    print(f"gates bloqueantes estables .. {met['gates_estables']}/{met['n_pares']}")
    for deg in DEGRADACIONES:
        print(f"discriminacion {deg:11} {met['discriminacion'][deg]['auc']}")
    print(f"sigma entre borradores ...... {met['sigma_entre_borradores']}")
    print(f"invalidas / fallidas ........ {met['n_invalidas']} / {met['n_fallidas']}")
    print(f"coste ....................... ${met['coste_total']}")
    print(f"VEREDICTO: {dictamen}")
    for r in razones:
        print(f"  - {r}")
    destino = ("sin anotar (medicion parcial)" if args.sin_anotar
               else f"anotado en {LEDGER.relative_to(ROOT)}")
    gastado = round(sum(e["metricas"]["coste_total"] for e in leer_ledger()), 2)
    print(f"{destino}; crudo en {crudo.relative_to(ROOT)}.")
    print(f"Gasto acumulado del experimento (ledger): ${gastado}")


if __name__ == "__main__":
    main()
