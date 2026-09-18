# Veredicto: RSI sobre `temperatura` del Evaluador

Sigue a `docs/pre-registro-automejora.md`, `docs/ruido-evaluador.md` e
`docs/informe-repeticion-automejora.md`. Responde al encargo (`/goal`, 2026-09-18): variar
`agentes.evaluador.temperatura`, medir σ de `media_calculada` a 3 pasadas por valor, y
comprobar que el borrador `01-i2` (chapter 1, iteración 3) sigue puntuando por encima de
`01-i0` (iteración 1) sin que empeore ninguno de los seis criterios.

**No se ha ejecutado ningún barrido de temperatura.** El motivo es de arquitectura, no de
resultado: no hay ningún punto del binding actual (Anexo A) por el que un valor de
`temperatura` distinto llegue a la llamada real al modelo. El resto de este documento
detalla la comprobación y dónde queda esto en la metodología de RSI del repo
(`rsi-evaluador-metodologia` en memoria).

## Comprobación (qué se verificó antes de gastar ninguna llamada)

1. `claude -p --help` no tiene ninguna opción de temperatura/sampling — ni `--temperature`
   ni equivalente. Las únicas palancas de muestreo expuestas por el CLI son `--model` y
   `--effort`.
2. `.claude/agents/evaluador.md` (frontmatter): `name`, `description`, `tools: []`,
   `model: haiku`. Sin campo `temperature`.
3. `scripts/repuntuar.py::call_evaluador` — el único código de este repo que de verdad
   invoca al Evaluador para medir ruido — lanza `claude -p --agent evaluador --allowedTools
   "" --output-format json` sin pasar ningún parámetro de temperatura.
4. `novela/config.json` sí declara `agentes.evaluador.temperatura: 0.2` (línea 99), y el
   núcleo (`harness/config.py`) lo carga sin quejarse. Pero ningún punto del binding lee ese
   valor y lo traslada a la llamada: es un campo que la spec pide declarar (§6.0) y que el
   núcleo transporta, pero que el binding de Claude Code (Anexo A, puerto P1) no consume.

**Conclusión de la comprobación:** hoy, cambiar `agentes.evaluador.temperatura` en
`novela/config.json` no cambia nada en el comportamiento real del Evaluador. Cualquier
"barrido de temperatura" ejecutado tal cual (editar el JSON entre tandas de
`repuntuar.py --split all`) mediría exactamente lo mismo tres veces: ruido de relanzar la
misma llamada, no efecto de temperatura. Ejecutarlo igualmente habría gastado el tope de 42
llamadas por brazo sin poder atribuir ningún cambio a la variable que el encargo pide
optimizar.

## Por qué no se ha rodeado el bloqueo

La única forma de controlar temperatura de verdad sería dejar de invocar al Evaluador vía
`claude -p --agent evaluador` y llamar directamente a la API de Anthropic con un
`temperature=` explícito. Eso no es un ajuste de parámetro: es sustituir el puerto P1 para
un solo rol, lo cual `CLAUDE.md` marca expresamente como la línea que no se cruza sola
("Binding... implementa solo P1 y P4. No reimplementa lógica del núcleo" / "Romper ese
reparto en cualquier dirección es el error caro del proyecto"). Decidir si el Evaluador deja
de pasar por Claude Code es una decisión de arquitectura para una persona, no algo que este
ciclo de auto-mejora deba resolver por su cuenta.

## STOP

El criterio STOP del encargo pide detenerse y avisar a una persona en vez de seguir
probando en solitario si, tras un par de intentos, algo no mejora o empeora. Este caso es
anterior a eso: no hay ningún intento posible con el binding actual, así que se aplica el
mismo criterio por la razón más fuerte — **se para aquí y se avisa** en vez de simular un
barrido editando un JSON que no está conectado a nada.

## MEMORY (listón vigente, sin cambios)

No hay una segunda medición con la que comparar, así que el listón sigue siendo el único
dato real que existe hoy, ya registrado en `docs/ruido-evaluador.md` y reconfirmado en
`docs/informe-repeticion-automejora.md`:

| | dev | holdout |
|---|---|---|
| σ(`media_calculada`) promedio | 0.39 | 0.42 |
| hueco de discriminación `01-i0` vs `01-i2` (histórico, primera tanda) | +0.50 (no solapa) | — |
| hueco de discriminación `01-i0` vs `01-i2` (repetición independiente) | −0.34 (solapa) | — |

Los seis criterios de la rúbrica (tensión, escaleta, voz, caracterización, ritmo, prosa) no
tienen una segunda medición con la que comparar "empeora / no empeora" — la regla de
no-daño no se puede evaluar todavía porque no existe un segundo brazo.

## Valores óptimos

**Ninguno.** No hay ningún valor de temperatura que se pueda recomendar porque ningún valor
distinto de la temperatura por defecto de Claude Code para `haiku` ha llegado nunca a
producir una llamada real — el campo `0.2` en `novela/config.json` no ha estado nunca en
vigor.

## Hallazgo aparte, ya apuntado en `informe-repeticion-automejora.md`

El commit `75f0a28` ("RSI(temp): optimizar temperatura...") no tocó ninguna temperatura —
cambió `perfiles.poc.capitulos.palabras_objetivo` (150→60). A la luz de esta comprobación,
la lectura más probable es que ese intento anterior chocó con el mismo bloqueo (no hay
manera de tocar la temperatura real) y pivotó a otro parámetro sin corregir el mensaje del
commit. Queda como aviso para cualquier tanda futura: si un brazo de RSI dice tocar
temperatura, verificar primero que el binding la consume antes de fiarse del mensaje del
commit.

## Veredicto final

**Bloqueado por arquitectura, no medido.** No se ha gastado ninguna llamada del Evaluador en
esta tanda (el tope de 42 sigue intacto). Antes de reabrir este experimento hace falta una
decisión humana explícita sobre una de estas dos vías, ninguna de las cuales corresponde
resolver a un ciclo de auto-mejora en solitario:

1. **Retirar `temperatura` de `agentes.*` en `novela/config.json`** como documentación
   engañosa (no vinculante), y aceptar que la temperatura del Evaluador es la que Claude Code
   fija por defecto para `haiku`, sin palanca. RSI futura se centraría en otras palancas que sí
   están conectadas (rúbrica, `mejora_minima`, número de pasadas de puntuación).
2. **Escribir un anexo de binding nuevo** para el rol Evaluador que llame a la API de
   Anthropic directamente (fuera de Claude Code) con `temperature=` explícito, aceptando que
   eso separa a ese rol del resto del binding P1 y necesita su propia gestión de credenciales,
   cuota y P6.

Ninguna de las dos se ha aplicado en esta sesión.
