# Registro de iteraciones

Cada fila es una decisión causa → efecto. **Disparador** dice qué la provocó: eval, TLC, Lean,
incidente (un run real que falló) o auditoría. **Efecto medido** es solo lo que consta en git o
en docs; donde no hay medida, se dice.

Las filas de 2026-09-15 a 2026-09-20 son de la primera implementación, en la rama `main`.

| Fecha | Disparador | Cambio | Efecto medido | Commit |
|---|---|---|---|---|
| 2026-09-15 | Diseño | Arquitectura con un gateway de modelos desde Claude Code | Descartada en la reimplementación: todo corre sobre la suscripción (ADR 0001) | `e77e815` (`main`) |
| 2026-09-16 | Coste | Haiku para parte de los agentes y trazado a Langfuse | Sin medida aislada; dio las trazas del diagnóstico siguiente | `6773aa9` (`main`) |
| 2026-09-17 | Eval (6 trazas de Langfuse) | Diagnóstico del run `el-buzon-de-la-planta-baja-2`: 18,13 $ y 56 min por 3 capítulos; la reescritura cuesta 3,2× y termina peor; el `Continuista` gasta el 27 % del reloj y devuelve OK 7 de 7 | Es la medida de partida | `9ab245e` (`main`) |
| 2026-09-17 | Eval | Parada por estancamiento (M1), `Continuista` solo sobre el intento aceptado (M3), una orden por llamada (M5), dedup de generations por `request_id` (M7) | `dry_run` de 40 a 46 comprobaciones. El ahorro (7 → 3 llamadas al `Continuista`, escritura de 14,16 $ a ≈ 6-7 $) quedó como proyección, sin run posterior que lo midiera | `f27933f` (`main`) |
| 2026-09-18 | Eval | Medida del ruido del juez: 3 pasadas × 14 borradores | Cambia de veredicto en 8 de 14 borradores solo por relanzarlo; σ media de 0,39 (dev) y 0,42 (holdout). Consecuencia: los gates que bloquean pasan a ser deterministas | `75f0a28` (`main`) |
| 2026-09-21 | Las dos anteriores | Reimplementación desde cero, documentación y specs antes del código | — | `97c9e7f` |
| 2026-09-24 | Incidente (`humo-0003`, 1.er arranque) | Corte de red en mitad del `arquitecto` (F-37) | Registrado como riesgo; sin cambio de código | — |
| 2026-09-24 | Incidente (2.º arranque) | Orden compuesta denegada por el `allow` (F-25): cada orden `novela`, sola en su llamada | El arranque siguiente pasó ese punto | `71b8fc9` |
| 2026-09-24 | Incidente (3.er arranque) | El misterio no se podía escribir por el `deny` de `Read` (F-28) y el gate no lo vio (F-48): el `arquitecto` escribe un borrador que el briefing del `trazador` promueve | Canon y plan a la primera en el 4.º arranque | `5034601`, `55f0ccf`, `9a89427` |
| 2026-09-23 | Incidente (canario) | Primera ejecución en rojo: los agentes se negaban a intentar lo prohibido (F-64). Prompts que presentan la prueba, y un intento sin `tool_use` es no concluyente (F-65) | Canario en verde desde el 2026-09-24 con Claude Code 2.1.281 | `8c5fbd3`, `89d6fe9`, `461f214` |
| 2026-09-24 | Eval (`humo-0003`, baseline) | Novela de humo de 3 capítulos sobre `9a89427` | tension 7 / 8 / 9, fair_play 9, coherencia 9, longitud 0,88 / 0,94 / 0,87; reintentos (mecánico · revisión · delta) 0·0·2, 0·1·1, 0·2·0. Una sola ejecución | `a1d7132` |
| 2026-09-24 | Incidente (`humo-0003`, cap. 3) | La sesión contó 1 de 2 reintentos cuando el log daba 2, y revisó otra vez un capítulo rechazado (F-31): los gates y la cuenta pasan al CLI | Decisión tomada (ADR 0002); `novela gate` sin implementar | `9e840e6` |
| 2026-09-24 | Auditoría | 14 de 89 requisitos cumplidos contra el checklist: specs 0005 a 0014 | Ver la auditoría tras la integración | `af65fb4` |
| 2026-09-24 | Auditoría (HAR-04) | Hook `PostToolUse` que valida el capítulo en cuanto se escribe | El gate mecánico corre siempre, lo llame o no el orquestador; tests en `test_hook_validacion.py` | `e4af84d` |
| 2026-09-24 | Coste | `trazador` de opus a haiku; `continuista`, `editor-estilo` y `lector-suspense` de sonnet a haiku | **Sin medir**: falta comparar contra el baseline de `humo-0003` | `a414903` |
| pendiente | Eval (spec 0014) | Cinco briefs de evaluación y una iteración de tuning de prompt | Rellenar con `docs/evals.md` y `docs/tuning.md` tras la integración | — |
| pendiente | TLC | Contraejemplos de TLC sobre el modelo del flujo | Rellenar con el registro de `docs/formal/tla.md` | — |
| pendiente | Lean | Fallos de `lean_cronologia` en una novela real | Rellenar con `docs/formal/lean.md` | — |
| pendiente | Eval (juez) | Calibración del `juez-narrativo` contra la revisión humana | Rellenar con `docs/evaluacion/juez.md` | — |

## Cómo añadir una fila

Una fila por cambio con efecto observable. El efecto se escribe con el número que lo mide y su
fuente, o como «sin medir». Un cambio de prompt de agente lleva el sha del commit que lo
introduce, que es lo que registra `runs/<run_id>/manifest.json`.
