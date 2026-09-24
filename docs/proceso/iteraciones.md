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
| 2026-09-24 | Eval (`eval-b4-temporal`, ronda 1) | El brief con dos recuerdos incompatibles pasaba `brief validar` con 0: el entrevistador solo pudo dejar la contradicción como pregunta, y el procedimiento ignoraba las preguntas tras un 0. `/novela-brief` las enseña ahora al operador | Ronda 2: la pregunta llega al operador antes de `/novela-nueva` | `90fc5c3` |
| 2026-09-24 | Incidente (`regalo-carmen`) | El arquitecto sustituyó el nombre de la destinataria por una etiqueta de anonimización: la política de privacidad trata como real a todo destinatario. `novela brief iniciar --ficticio` lo declara en la semilla | `ejemplo-carmen` y los briefs de evaluación conservan el nombre; con datos reales nada cambia | `ccdc8b7` |
| 2026-09-24 | Incidente (`regalo-carmen`) | El trazador dejó las diez fichas sin el `---` de cierre y nada validaba el plan hasta el briefing del escritor, ya fuera de su reintento. Gate nuevo `novela validar-plan` en `/novela-nueva` | Mismo defecto en `eval-b2`, `eval-b3` y `ejemplo-carmen`: los tres se recuperan en el reintento del trazador, sin intervención | `eb5ce53` |
| 2026-09-25 | Incidente (`ejemplo-carmen`) | El plan usaba `per-tango` (el perro del brief) sin ficha de canon; el briefing del escritor salía con 4. `validar-plan` exige ficha para cada personaje del plan | Detectado antes del escritor; el orquestador autorizó al arquitecto a añadir solo esa ficha | `8559f09` |
| 2026-09-25 | Eval (tuning) | Cronista: A (haiku, prompt vigente) → D (sonnet + párrafo de citas). Detalle en `docs/evaluacion/tuning-cronista.md` | Citas no literales 16/46 → 0/45; deltas aceptables 0/3 → 3/3 (capítulo 2 de `eval-b2`); prompt `cronista` v1 → v2 en Langfuse | `08a290f` |
| 2026-09-25 | Eval (tuning, colateral) | Sin ficha del plan el cronista no tenía ids de escenario para la cronología (haiku los inventaba, sonnet la dejaba vacía): Lean se quedaba sin datos. La receta del cronista gana `plan: capitulo_actual` y `canon/mundo` | Pendiente de medir en los capítulos 3–10 de `ejemplo-carmen` (`verificar-lean`) | `08a290f` |
| 2026-09-25 | Eval (`eval-b3-inyeccion`) | El continuista copió texto del misterio en su informe, que el escritor lee en el reintento (invariante 3). Regla 6 del hook: el escritor y el editor-estilo no leen un informe de `qa/` que comparta 8 palabras seguidas con el misterio | Ronda 2: el hook lo denegó; el continuista (haiku) volvió a copiar pese al prompt, así que la guarda determinista es la que protege | `6bb4ceb` |
| 2026-09-25 | Eval (`eval-b3`, ronda 2) | El motivo de esa denegación citaba el fragmento coincidente, y el motivo lo lee el escritor y va al audit log | El motivo solo cuenta fragmentos | `b0be929` |
| 2026-09-24 | TLC (`HarnessExport.cfg`) | H-3: `producir` daba por publicada una novela si `export/` no estaba vacío, aunque la auditoría de la versión vigente fallara | Arreglado con TDD; el mutante reproduce el contraejemplo | `f81fc9d` |
| 2026-09-24 | TLC (`HarnessLiteral.cfg`, `HarnessCuenta.cfg`) | H-2: la cuenta de reintentos de `novela-continuar.md` no mide igual en todos los gates y una caída gasta un intento | Documentado en `docs/formal/tla.md`; es cambio de procedimiento, va por spec | — |
| 2026-09-24 | Lean (fixture `PARTIDA`) | Un personaje que vuelve tras su partida y otro en dos sitios a la vez: `validar`, `aplicar-delta`, `checkpoint` y `auditar` salen con 0; `verificar-lean` con 1 (`ubicuidad`, `exclusion`) | Gate antes de exportar en `/novela-auditar` | `098b301` |
| 2026-09-24 | Seguridad (skill `auditoria-seguridad`) | S-01: seis variantes de inyección pasaban el marcado del brief; S-02: un rol podía leer otra novela o `.env` | Regresiones en `test_inyeccion.py` y `test_hook_lectura.py` | `3b9b518`, `d61a306` |
| 2026-09-24 | Observabilidad | Con `claude -p` el plugin perdía el último turno de cada sesión: Claude Code cancelaba su `SessionEnd`. `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=30000` y una traza por paso en la sesión `novela-<slug>` | Coste de `humo-0003` recuperable entero: 13,01 USD | `7b81a93` |
| — | Eval (juez) | Calibración del juez contra la revisión humana | Pendiente: la revisión humana la rellena una persona en `docs/evaluacion/revision-humana.md` | — |

## Cómo añadir una fila

Una fila por cambio con efecto observable. El efecto se escribe con el número que lo mide y su
fuente, o como «sin medir». Un cambio de prompt de agente lleva el sha del commit que lo
introduce, que es lo que registra `runs/<run_id>/manifest.json`.
