"""Genera docs/presupuesto.md: el modelo económico de la propuesta, reproducible.

Uso: python docs/presupuesto/calcular.py <coste_novela_usd> <coste_revision_usd> <fuente_revision>
Los dos costes salen de `novela costes <slug>` (Langfuse); el resto son supuestos declarados abajo.
"""

import sys
from pathlib import Path

NOVELA_USD, REVISION_USD, FUENTE_REVISION = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]

# --- Supuestos (cada uno con su porqué en el documento) -----------------------------------------
EUR_POR_USD = 0.92  # tipo de cambio de referencia; cambiarlo aquí recalcula todo
PRECIO = 79.0  # € por novela, IVA aparte, hasta 3 revisiones incluidas
REVISIONES_MEDIAS = 1.0  # revisiones que pide de media un cliente
REVISION_HUMANA = 10.0  # 20 min de un editor a 30 €/h por novela
SOPORTE = 2.5  # 5 min de atención al cliente a 30 €/h
PASARELA = lambda precio: 0.014 * precio + 0.25  # noqa: E731 — tarifa europea típica de tarjeta
INFRA_MES = {50: 100.0, 200: 100.0, 1000: 350.0}  # € al mes: servidor, copias, Langfuse, dominio
HORAS = {"Diseño y specs": 60, "Desarrollo": 280, "Validación y evaluación": 110, "Despliegue": 40}
TARIFA = 55.0  # € por hora
EXTRA_REVISION = 15.0  # precio propuesto de la 4.ª revisión en adelante

tokens = NOVELA_USD * EUR_POR_USD
revision = REVISION_USD * EUR_POR_USD


def unitario(volumen: int, factor_tokens: float = 1.0, revisiones: float = REVISIONES_MEDIAS) -> dict[str, float]:
    return {
        "tokens": tokens * factor_tokens,
        "revisiones": revision * factor_tokens * revisiones,
        "infraestructura": INFRA_MES[volumen] / volumen,
        "revisión editorial": REVISION_HUMANA,
        "soporte": SOPORTE,
        "pasarela de pago": PASARELA(PRECIO),
    }


def e(x: float) -> str:
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float) -> str:
    return f"{100 * x:.1f} %".replace(".", ",")


base = unitario(200)

coste = sum(base.values())
margen = PRECIO - coste
lineas = [
    "# Presupuesto y coste",
    "",
    "Propuesta económica de Story Maker para el cliente (ficticio) Cuentalia Regalos. Generado por",
    "`python docs/presupuesto/calcular.py`: cambiar un supuesto y relanzarlo recalcula todo.",
    "",
    "## De dónde sale cada número",
    "",
    f"- **Tokens por novela: {NOVELA_USD:.2f} USD** medidos en Langfuse sobre la novela de ejemplo "
    "completa (`novela costes ejemplo-carmen`, 511 llamadas, 10 capítulos, auditoría, Lean y juez; "
    "[costes-ejemplo-carmen.md](evaluacion/costes-ejemplo-carmen.md)). Es el coste a precio de API "
    "que calcula Langfuse; en desarrollo corre sobre una suscripción de Claude Code.",
    f"- **Tokens por revisión: {REVISION_USD:.2f} USD**, {FUENTE_REVISION}.",
    f"- Tipo de cambio: 1 USD = {EUR_POR_USD} € (supuesto).",
    f"- Revisión editorial humana: {e(REVISION_HUMANA)} (20 min a 30 €/h): una persona hojea el PDF "
    "antes de enviarlo, porque es un regalo.",
    f"- Soporte: {e(SOPORTE)}; pasarela de pago: 1,4 % + 0,25 €.",
    "- Infraestructura mensual (supuesto): servidor para API, panel y trabajos, copias de seguridad, "
    "Langfuse Cloud y dominio; " + ", ".join(f"{e(v)} a {k} novelas/mes" for k, v in INFRA_MES.items())
    + ".",
    f"- Media de {REVISIONES_MEDIAS:g} revisión por novela (supuesto); el precio incluye hasta 3.",
    "",
    "## Coste unitario (200 novelas/mes)",
    "",
    "| Concepto | € por novela |",
    "|---|---:|",
    *[f"| {k} | {e(v)} |" for k, v in base.items()],
    f"| **coste total** | **{e(coste)}** |",
    f"| precio de venta (IVA aparte) | {e(PRECIO)} |",
    f"| **margen** | **{e(margen)} ({pct(margen / PRECIO)})** |",
    "",
    "## Escenarios de volumen",
    "",
    "| Novelas/mes | Coste unitario | Margen unitario | Ingresos/mes | Margen/mes |",
    "|---:|---:|---:|---:|---:|",
]
for v in INFRA_MES:
    c = sum(unitario(v).values())
    lineas.append(f"| {v} | {e(c)} | {e(PRECIO - c)} ({pct((PRECIO - c) / PRECIO)}) | {e(PRECIO * v)} | {e((PRECIO - c) * v)} |")

sube = sum(unitario(200, factor_tokens=1.5).values())
tres = sum(unitario(200, revisiones=3).values())
cuatro = sum(unitario(200, revisiones=4).values())
cinco = sum(unitario(200, revisiones=5).values())
meses = f"{sum(HORAS.values()) * TARIFA / (margen * 200):.1f}".replace(".", ",")
lineas += [
    "",
    "## Análisis de sensibilidad (200 novelas/mes)",
    "",
    "| Escenario | Coste unitario | Margen |",
    "|---|---:|---:|",
    f"| base | {e(coste)} | {e(margen)} ({pct(margen / PRECIO)}) |",
    f"| tokens +50 % | {e(sube)} | {e(PRECIO - sube)} ({pct((PRECIO - sube) / PRECIO)}) |",
    f"| 3 revisiones, todas incluidas | {e(tres)} | {e(PRECIO - tres)} ({pct((PRECIO - tres) / PRECIO)}) |",
    f"| 4 revisiones, sin cobrar la 4.ª | {e(cuatro)} | {e(PRECIO - cuatro)} ({pct((PRECIO - cuatro) / PRECIO)}) |",
    f"| 4 revisiones, cobrando {e(EXTRA_REVISION)} la 4.ª | {e(cuatro)} | {e(PRECIO + EXTRA_REVISION - cuatro)} |",
    f"| 5 revisiones, cobrando {e(EXTRA_REVISION)} desde la 4.ª | {e(cinco)} | "
    f"{e(PRECIO + 2 * EXTRA_REVISION - cinco)} |",
    "",
    f"Cada revisión cuesta {e(revision)} en tokens. Cobrar {e(EXTRA_REVISION)} por revisión a partir "
    f"de la 4.ª deja {e(EXTRA_REVISION - revision)} por revisión extra.",
    "",
    "## Coste del proyecto de desarrollo",
    "",
    "| Fase | Horas | Importe |",
    "|---|---:|---:|",
    *[f"| {f} | {h} | {e(h * TARIFA)} |" for f, h in HORAS.items()],
    f"| **total** | **{sum(HORAS.values())}** | **{e(sum(HORAS.values()) * TARIFA)}** |",
    "",
    f"Tarifa: {e(TARIFA)}/h. A 200 novelas/mes, el margen mensual ({e(margen * 200)}) recupera el "
    "desarrollo en " + meses + " meses.",
]
Path(__file__).parents[1].joinpath("presupuesto.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
print("\n".join(lineas))
