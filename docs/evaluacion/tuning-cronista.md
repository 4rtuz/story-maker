# Iteración de tuning: el cronista y las citas literales

Fecha: 2026-09-25 · Commit del cambio: `08a290f` · Prompts en Langfuse: `cronista` v1 → v2
(`novela prompts publicar`, labels con el sha).

## Disparador

`aplicar-delta` rechaza un delta si una sola `cita` no aparece literal en el capítulo
(`backend/novela/slices/delta/violaciones.py`, `normalizar` solo iguala espacios). En las novelas
de humo y de evaluación era el gate que más reintentos consumía:

- 18 rechazos de `aplicar-delta` en los `harness.log` de `humo-0003` y `eval-b2-nino`; 16 por
  «la cita de hec-N no es literal del capítulo».
- `eval-b2-nino` paró en el capítulo 2 con `intervencion.md` tras agotar los tres intentos del gate.

## Método

Un capítulo fijo (`eval-b2-nino`, capítulo 2) y su briefing real del cronista
(`runs/r-20260925-0047/briefings/02-cronista.md`). Tres ejecuciones independientes por variante,
cada una escribe su delta fuera del workspace. `puntuar.py` cuenta las citas no literales con la
misma normalización que `aplicar-delta`. Un delta «pasaría» si tiene 0 citas no literales.

| Variante | Prompt | Modelo |
|---|---|---|
| A | `.claude/agents/cronista.md` vigente (`prompt-A.md`) | haiku |
| B | A + párrafo **Citas** (`prompt-B.md`) | haiku |
| C | B + regla de incisos de diálogo entre rayas (`prompt-C.md`) | haiku |
| D | B | sonnet |

## Resultados

| Ejecución | Citas | No literales | Pasaría |
|---|---|---|---|
| A1 | 15 | 3 | no |
| A2 | 14 | 3 | no |
| A3 | 17 | 10 | no |
| B1 | 9 | 0 | sí |
| B2 | 4 | 1 | no |
| B3 | 4 | 1 | no |
| C1 | 9 | 2 | no |
| C2 | 14 | 7 | no |
| C3 | 10 | 4 | no |
| D1 | 12 | 0 | sí |
| D2 | 18 | 0 | sí |
| D3 | 15 | 0 | sí |

| Variante | Citas no literales | Deltas que pasarían |
|---|---|---|
| A (antes) | 16/46 (35 %) | 0/3 |
| B | 2/17 (12 %) | 1/3 |
| C | 13/33 (39 %) | 0/3 |
| **D (después)** | **0/45 (0 %)** | **3/3** |

Lectura:

- El párrafo de citas ayuda con haiku (A → B), pero no basta. El fallo que queda es sistemático:
  un inciso de narrador entre rayas (`—Irene se colgó … de la calle—.`) que el modelo cierra con
  un punto que el texto no tiene.
- Añadir la regla explícita de incisos (C) **empeora** con haiku: más instrucciones, más ruido.
  Se descarta.
- El modelo es la palanca que funciona: sonnet con el prompt B no falla ninguna cita.
- Hallazgo colateral: sin la ficha del plan en el briefing, el cronista no tiene los ids de
  escenario. Haiku rellenaba el `lugar` de la cronología con ids inventados; sonnet la dejaba
  vacía (D1–D3: 0 eventos). Cualquiera de las dos cosas deja a Lean sin datos fiables.

## Cambio

- `cronista`: `model: sonnet` y el párrafo **Citas** de B.
- Receta del cronista (`backend/config/recipes.yaml`): `permanente: [canon/mundo]` y
  `plan: capitulo_actual`, y el prompt pide que `lugar` sea el escenario de la ficha.
- Coste: sonnet cuesta más por llamada que haiku, pero la variante A necesitaba de media más de
  tres intentos por capítulo y a menudo acababa en intervención humana. Con D, uno.

## Después, en el bucle real

`eval-b2-nino` se reanudó desde su intervención del capítulo 2 con el cambio. Los intentos de
`aplicar-delta` por capítulo cerrado antes y después están en
[resultados.md](resultados.md) (tabla de gates por brief).

## Reproducir

```bash
cd backend
uv run python ../docs/evaluacion/tuning-cronista/puntuar.py <delta.json> ../novelas/eval-b2-nino/capitulos/02.md
```

## Coste del cambio (Langfuse, `ejemplo-carmen`)

El cronista con sonnet cuesta más por capítulo: 0,16–0,30 USD en los capítulos 1–2 (haiku) frente a
0,61–0,76 USD en los capítulos 3–10 (sonnet), unos +0,40 USD por capítulo, +4 USD por novela sobre
24,52 USD. A cambio, los intentos de `aplicar-delta` por capítulo bajan de 2,5 a 1,125 y no hubo más
intervenciones por citas. Detalle por rol en [costes-ejemplo-carmen.md](costes-ejemplo-carmen.md).
