#!/usr/bin/env python3
"""Mide el suelo de ruido del Evaluador repitiendo pasadas sobre borradores ya en disco.

Ver docs/pre-registro-automejora.md. Este script mide: no genera ficcion, no lanza un
run, no toca novela/config.json ni .claude/agents/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import config as harness_config  # noqa: E402
from harness.deltas import accepts, computed_mean  # noqa: E402

DEV_RUN = "el-buzon-de-la-planta-baja-2"
HOLDOUT_RUN = "los-ruidos-del-bosque"
DEV = ["01-i0", "01-i1", "01-i2", "02-i0", "03-i0", "03-i1", "03-i2"]
HOLDOUT = ["01-i0", "01-i1", "02-i0", "02-i1", "02-i2", "03-i0", "03-i1"]
CRITERIA = ["tension", "escaleta", "voz", "caracterizacion", "ritmo", "prosa"]
PASSES = 3
HARD_CAP = 42

FIXTURE_PATH = ROOT / "scripts" / "fixture.json"
AGENT_PATH = ROOT / ".claude" / "agents" / "evaluador.md"
JSONL_PATH = ROOT / "docs" / "ruido-evaluador.jsonl"
SUMMARY_PATH = ROOT / "docs" / "ruido-evaluador-resumen.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def draft_path(split: str, name: str) -> Path:
    run = DEV_RUN if split == "dev" else HOLDOUT_RUN
    return ROOT / "runs" / run / "novela" / ".intentos" / f"{name}.md"


def drafts_for(split: str) -> list[tuple[str, str]]:
    items = []
    if split in ("dev", "all"):
        items += [("dev", n) for n in DEV]
    if split in ("holdout", "all"):
        items += [("holdout", n) for n in HOLDOUT]
    return items


def evaluacion_block() -> dict:
    return harness_config.load(ROOT)["evaluacion"]


def build_fixture_manifest() -> dict:
    borradores = {
        f"{split}/{name}": sha256_bytes(draft_path(split, name).read_bytes())
        for split, name in drafts_for("all")
    }
    return {
        "borradores": borradores,
        "evaluador_md": sha256_bytes(AGENT_PATH.read_bytes()),
        "evaluacion_config": sha256_bytes(
            json.dumps(evaluacion_block(), sort_keys=True, ensure_ascii=False).encode("utf-8")
        ),
    }


def check_or_write_fixture() -> dict:
    manifest = build_fixture_manifest()
    if FIXTURE_PATH.exists():
        recorded = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        mismatches = []
        if recorded.get("evaluador_md") != manifest["evaluador_md"]:
            mismatches.append(".claude/agents/evaluador.md")
        if recorded.get("evaluacion_config") != manifest["evaluacion_config"]:
            mismatches.append("bloque evaluacion de novela/config.json")
        for key, h in manifest["borradores"].items():
            if recorded.get("borradores", {}).get(key) != h:
                mismatches.append(f"borrador {key}")
        if mismatches:
            sys.exit(
                "ABORTADO: scripts/fixture.json no coincide con el estado actual.\n"
                f"Ha cambiado: {', '.join(mismatches)}.\n"
                "El fixture es de solo lectura una vez fijado. Si el cambio es "
                "intencional, borra scripts/fixture.json a mano y vuelve a correr."
            )
        print("scripts/fixture.json verificado: coincide con el estado actual.")
        return recorded
    FIXTURE_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"scripts/fixture.json creado ({len(manifest['borradores'])} borradores anclados).")
    return manifest


def build_prompt(split: str, name: str, tmp_dir: Path) -> Path:
    run = DEV_RUN if split == "dev" else HOLDOUT_RUN
    chapter = int(name.split("-")[0])
    out_path = tmp_dir / f"{split}-{name}-prompt.md"
    subprocess.run(
        [
            sys.executable, "-m", "harness", "prompt", "evaluador",
            "--root", str(ROOT / "runs" / run),
            "--chapter", str(chapter),
            "--draft", str(draft_path(split, name)),
            "-o", str(out_path),
        ],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return out_path


def strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def call_evaluador(prompt_path: Path) -> tuple[dict, float]:
    with prompt_path.open("r", encoding="utf-8") as fh:
        proc = subprocess.run(
            ["claude", "-p", "--agent", "evaluador", "--allowedTools", "",
             "--output-format", "json"],
            cwd=ROOT, stdin=fh, capture_output=True, text=True, timeout=240,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr[-500:]}")
    outer = json.loads(proc.stdout)
    if outer.get("is_error"):
        raise RuntimeError(f"is_error: {outer.get('result')}")
    obj = json.loads(strip_fence(outer["result"]))
    if not isinstance(obj.get("puntuaciones"), dict):
        raise RuntimeError(f"JSON sin 'puntuaciones': {obj!r}")
    return obj, outer.get("total_cost_usd", 0.0)


def smoke_test() -> None:
    split, name = drafts_for("all")[0]
    with tempfile.TemporaryDirectory() as td:
        prompt_path = build_prompt(split, name, Path(td))
        obj, cost = call_evaluador(prompt_path)
    print(f"Llamada de humo OK ({split}/{name}): "
          f"media_calculada={computed_mean(obj)}, coste=${cost:.4f}")


def run_measurement(split_arg: str) -> None:
    targets = drafts_for(split_arg)
    total_calls = len(targets) * PASSES
    if total_calls > HARD_CAP:
        sys.exit(f"ABORTADO: {total_calls} llamadas piden mas del tope duro de {HARD_CAP}.")

    cfg = harness_config.load(ROOT)
    check_or_write_fixture()
    smoke_test()

    records = []
    fails = 0
    done = 0
    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        prompt_paths = {(split, name): build_prompt(split, name, tmp_dir) for split, name in targets}

        def run_one(split: str, name: str, pasada: int) -> dict:
            record = {
                "split": split,
                "run": DEV_RUN if split == "dev" else HOLDOUT_RUN,
                "capitulo": int(name.split("-")[0]),
                "iteracion": name,
                "pasada": pasada,
            }
            try:
                obj, cost = call_evaluador(prompt_paths[(split, name)])
                record.update({
                    "puntuaciones": obj["puntuaciones"],
                    "media_calculada": computed_mean(obj),
                    "veredicto": "APROBADO" if accepts(obj, cfg) else "CORREGIR",
                    "coste": cost,
                    "ok": True,
                })
            except Exception as exc:  # noqa: BLE001 - se registra, no se descarta
                record.update({"ok": False, "error": str(exc)})
            return record

        jobs = [(split, name, pasada) for split, name in targets for pasada in range(1, PASSES + 1)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(run_one, *job): job for job in jobs}
            for fut in as_completed(futures):
                split, name, pasada = futures[fut]
                record = fut.result()
                if not record["ok"]:
                    fails += 1
                records.append(record)
                done += 1
                status = "ok" if record["ok"] else f"FALLO: {record.get('error')}"
                print(f"[{done}/{total_calls}] {split}/{name} pasada {pasada}: {status}")

    records.sort(key=lambda r: (r["split"], r["iteracion"], r["pasada"]))

    JSONL_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n",
        encoding="utf-8",
    )
    print(f"{len(records)} llamadas registradas en docs/ruido-evaluador.jsonl ({fails} fallidas).")
    write_summary(records)


def _stats(values: list[float]) -> dict:
    return {
        "valores": values,
        "sigma": round(statistics.stdev(values), 4) if len(values) >= 2 else None,
        "rango": round(max(values) - min(values), 4) if values else None,
    }


def write_summary(records: list[dict]) -> None:
    cfg = harness_config.load(ROOT)
    ev = cfg["evaluacion"]
    bloqueantes = ev["criterios_bloqueantes"]
    umbral_bloqueante = ev["umbral_criterio_bloqueante"]

    summary: dict = {"splits": {}}
    for split in ("dev", "holdout"):
        by_draft: dict[str, list[dict]] = {}
        for r in records:
            if r["split"] == split and r["ok"]:
                by_draft.setdefault(r["iteracion"], []).append(r)

        drafts_summary = {}
        for name, recs in sorted(by_draft.items()):
            bloqueante_por_pasada = [
                tuple(r["puntuaciones"][c] >= umbral_bloqueante for c in bloqueantes)
                for r in recs
            ]
            drafts_summary[name] = {
                "n_pasadas": len(recs),
                "media_calculada": _stats([r["media_calculada"] for r in recs]),
                "criterios": {
                    c: _stats([r["puntuaciones"][c] for r in recs]) for c in CRITERIA
                },
                "veredictos": [r["veredicto"] for r in recs],
                "veredicto_unico": len({r["veredicto"] for r in recs}) == 1,
                "bloqueante_unico": len(set(bloqueante_por_pasada)) == 1,
            }

        sigmas_media = [
            d["media_calculada"]["sigma"] for d in drafts_summary.values()
            if d["media_calculada"]["sigma"] is not None
        ]
        sigmas_criterio = {
            c: [
                d["criterios"][c]["sigma"] for d in drafts_summary.values()
                if d["criterios"][c]["sigma"] is not None
            ]
            for c in CRITERIA
        }
        summary["splits"][split] = {
            "borradores": drafts_summary,
            "agregado": {
                "sigma_media_calculada_promedio": (
                    round(statistics.mean(sigmas_media), 4) if sigmas_media else None
                ),
                "sigma_criterio_promedio": {
                    c: (round(statistics.mean(v), 4) if v else None)
                    for c, v in sigmas_criterio.items()
                },
                "n_borradores": len(drafts_summary),
                "n_borradores_media_distinta_entre_pasadas": sum(
                    1 for d in drafts_summary.values()
                    if len(set(d["media_calculada"]["valores"])) > 1
                ),
                "n_borradores_bloqueante_distinto_entre_pasadas": sum(
                    1 for d in drafts_summary.values() if not d["bloqueante_unico"]
                ),
            },
        }

    n_fail = sum(1 for r in records if not r["ok"])
    summary["llamadas"] = {"total": len(records), "ok": len(records) - n_fail, "fallidas": n_fail}
    summary["umbral_veredicto_preregistro"] = 0.17
    summary["sha256_repuntuar_py"] = sha256_bytes(Path(__file__).read_bytes())

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Resumen escrito en {SUMMARY_PATH.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="dev")
    args = parser.parse_args()
    run_measurement(args.split)


if __name__ == "__main__":
    main()
