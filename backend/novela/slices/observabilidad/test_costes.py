"""`novela costes`: tokens, coste y latencia por paso, por rol y por novela, desde las
observaciones de Langfuse. Sin red: las respuestas son las que la API v2 devolvió en real."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from novela.cli import app
from novela.slices.observabilidad import costes
from novela.slices.observabilidad.api import Api

SID = "34d4bf3c-2ad3-4fa3-83ea-0446b3c188d9"


def _obs(id: str, traza: str, tipo: str, inicio: str, fin: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": id,
        "traceId": traza,
        "type": tipo,
        "name": extra.pop("name", tipo),
        "startTime": f"2026-09-24T10:{inicio}Z",
        "endTime": f"2026-09-24T10:{fin}Z",
        "parentObservationId": extra.pop("padre", None),
        "sessionId": extra.pop("sesion", ""),
        "tags": extra.pop("tags", []),
        "metadata": extra.pop("metadata", {}),
        **extra,
    }


def _gen(
    id: str, traza: str, padre: str, entrada: int, salida: int, coste: float, **extra: Any
) -> dict[str, Any]:
    return _obs(
        id,
        traza,
        "GENERATION",
        extra.pop("inicio", "00:00.000"),
        extra.pop("fin", "00:02.000"),
        padre=padre,
        usageDetails={
            "input": entrada,
            "cache_read_input_tokens": 1000,
            "output": salida,
            "total": 0,
        },
        totalCost=coste,
        latency=2.0,
        **extra,
    )


# Traza nueva: la raíz de `producir` y, colgados, el turno del plugin, el subagente y sus llamadas.
NUEVA = [
    _obs(
        "r1",
        "t1",
        "SPAN",
        "00:00.000",
        "00:00.001",
        name="demo · capitulo 01",
        sesion="novela-demo",
        tags=["demo", "novela"],
        metadata={"paso": "capitulo 01"},
    ),
    _obs("turno", "t1", "SPAN", "00:00.000", "01:40.000", padre="r1", name="Conversational Turn"),
    _gen("g1", "t1", "turno", 10, 100, 0.5),
    _obs(
        "sub",
        "t1",
        "SPAN",
        "00:10.000",
        "01:00.000",
        padre="turno",
        name="Subagent: Escribir 01",
        metadata={"agent_type": "escritor"},
    ),
    _gen("g2", "t1", "sub", 20, 2000, 1.25, name="Subagent LLM Call"),
]
# Traza legada: sin padre, en la sesión de Claude Code y con la etiqueta del bucle.
LEGADA = [
    _obs(
        "turno2",
        "t2",
        "SPAN",
        "10:00.000",
        "10:30.000",
        name="Conversational Turn",
        sesion=SID,
        tags=["claude-code", "demo"],
    ),
    _gen(
        "g3",
        "t2",
        "turno2",
        5,
        50,
        0.25,
        sesion=SID,
        tags=["claude-code", "demo"],
        inicio="10:01.000",
        fin="10:03.000",
    ),
]


def test_agrega_por_paso_rol_y_novela() -> None:
    informe = costes.agregar("demo", NUEVA + LEGADA, {SID: "capitulo 02"})
    pasos = {p["paso"]: p for p in informe["pasos"]}
    assert list(pasos) == ["capitulo 01", "capitulo 02"]
    uno = pasos["capitulo 01"]
    assert (uno["llamadas"], uno["tokens_entrada"], uno["tokens_salida"]) == (2, 2030, 2100)
    assert uno["tokens_cache_lectura"] == 2000
    assert uno["coste_usd"] == pytest.approx(1.75)
    assert uno["latencia_s"] == pytest.approx(100.0)
    assert uno["latencia_media_llamada_s"] == pytest.approx(2.0)
    assert uno["roles"]["escritor"]["coste_usd"] == pytest.approx(1.25)
    assert uno["roles"]["orquestador"]["tokens_salida"] == 100
    assert informe["total"]["coste_usd"] == pytest.approx(2.0)
    assert informe["total"]["llamadas"] == 3
    assert informe["total"]["latencia_s"] == pytest.approx(130.0)
    assert informe["sesion"] == "novela-demo"


def test_una_sesion_legada_sin_run_se_nombra_por_su_skill_o_su_id() -> None:
    legada = [dict(o, tags=["claude-code", "demo", "skill:novela-auditar"]) for o in LEGADA]
    assert [p["paso"] for p in costes.agregar("demo", legada, {})["pasos"]] == ["auditoria"]
    assert [p["paso"] for p in costes.agregar("demo", LEGADA, {})["pasos"]] == ["sesión 34d4bf3c"]


def test_sesiones_del_workspace(tmp_path: Path) -> None:
    """La sesión de Claude Code de cada paso legado: la de `harness.log`, el paso del manifiesto."""
    otra = "0d64a8fb-0798-4764-b185-4138c968ec89"
    for run, capitulo, fase, sesion in (("r-1", 1, "arranque", otra), ("r-2", 2, "capitulo", SID)):
        d = tmp_path / "runs" / run
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"capitulo": capitulo, "fase": fase}), "utf-8")
        (d / "harness.log").write_text(
            f"2026-09-24T10:49:40+02:00 sesion={sesion} validar -> 0\n", "utf-8"
        )
    assert costes.sesiones_del_workspace(tmp_path) == {otra: "nueva", SID: "capitulo 02"}


def test_cli_descarga_pagina_y_escribe_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rutas: list[str] = []

    def pedir(self: Api, metodo: str, ruta: str, *_: object, **__: object) -> Any:
        rutas.append(ruta)
        if "traceId=t1" in ruta:
            return {"data": NUEVA, "meta": {}}
        if "cursor=" in ruta:
            return {"data": LEGADA, "meta": {}}
        return {"data": NUEVA[:1], "meta": {"cursor": "c2"}}

    monkeypatch.setattr(Api, "pedir", pedir)
    monkeypatch.setattr(costes, "DESTINO", tmp_path)
    entorno = {"NOVELAS_DIR": str(tmp_path / "novelas"), "LANGFUSE_PUBLIC_KEY": "p"}
    r = CliRunner().invoke(app, ["costes", "demo", "--json"], env=entorno)
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["total"]["coste_usd"] == pytest.approx(2.0)
    assert any("filter=" in ruta for ruta in rutas)

    r = CliRunner().invoke(app, ["costes", "demo", "--markdown"], env=entorno)
    assert r.exit_code == 0, r.output
    texto = (tmp_path / "costes-demo.md").read_text(encoding="utf-8")
    assert "| capitulo 01 |" in texto and "escritor" in texto and "2.0000" in texto


def test_la_latencia_de_un_paso_no_cuenta_la_espera_entre_trazas() -> None:
    """Un reintento del mismo capítulo horas después suma lo que duró, no el hueco."""
    otro_turno = _obs("turno3", "t3", "SPAN", "20:00.000", "20:10.000", sesion=SID, tags=["demo"])
    informe = costes.agregar("demo", [*LEGADA, otro_turno], {SID: "capitulo 02"})
    assert informe["pasos"][0]["latencia_s"] == pytest.approx(40.0)
