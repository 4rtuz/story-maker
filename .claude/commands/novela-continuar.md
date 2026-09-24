---
description: Escribe los siguientes capítulos de una novela con el bucle por capítulo, sus gates y la cuenta de intentos en harness.log. Reanuda desde checkpoints/latest.json.
argument-hint: <slug> [--capitulos N]
---

Eres el orquestador. No escribes prosa y no la lees: nunca abras `capitulos/NN.md`. Todo lo que
decides sale del disco, nunca de la conversación.

## Argumentos

`$ARGUMENTS` es `<slug> [--capitulos N]`. Sin slug, responde
`uso: /novela-continuar <slug> [--capitulos N]` y para sin ejecutar nada. Sin `--capitulos`, un
capítulo. Repite «Por capítulo» hasta hacer `N` o hasta que algo pare.

## Códigos de salida del CLI

| Código | Qué haces |
|---|---|
| 0 | Sigues |
| 1 | Gate fallido: reintento según el paso, con la regla de lectura 1. Un 1 de `novela briefing` o de `novela checkpoint` no tiene reintento: `intervencion.md` y para |
| 2 | Uso incorrecto: el procedimiento está mal. Para sin `intervencion.md` |
| 3 | Lock ocupado: otro proceso trabaja en la novela. Para sin `intervencion.md` |
| 4 | Workspace inválido: `intervencion.md` y para. No es un gate y no se reintenta |

Cada orden `novela` va sola en su llamada a Bash: sin `;`, `&&`, `|`, redirecciones ni
`echo $?`. El `allow` solo autoriza órdenes que empiezan por `novela`, y en el bucle `dontAsk`
deniega cualquier otra forma. El código lo da el resultado de la herramienta: distinto de 0, sale
como error con `Exit code N`; sin error, es 0.

## Reglas de lectura

1. **Un 1 solo es un gate si el log lo dice.** Tras un 1 de `novela validar` o de
   `novela aplicar-delta`, lee la última línea de `novelas/<slug>/runs/<run_id>/harness.log`. Si
   contiene `validar NN -> 1` o `aplicar-delta NN -> 1`, es un gate. Si no (un traceback, un import
   roto, `-> error`), el CLI está roto y ningún agente puede arreglarlo: para sin reintentar y sin
   `intervencion.md`.
2. **Un veredicto ilegible es un rechazo.** Si un informe de `qa/` no existe, no es JSON o no tiene
   `veredicto`, cuenta como `rechazado`. Nunca como aprobado.
3. **Una intervención se resuelve con una línea.** Un `intervencion.md` sin una línea
   `resuelto: <sha o motivo>` está vivo.

## Prompt de cada Task

Exactamente esto, y nada más: ni prosa tuya, ni resúmenes, ni el capítulo.

```
slug: <slug>
capítulo: <NN>
briefing: novelas/<slug>/<ruta que imprimió novela briefing>
salidas: <rutas de salida del agente, relativas a novelas/<slug>/>
reintento: <rutas de qa/ que lo motivan>        ← solo en reintento
causa: <texto tras «·» en la línea de harness.log>  ← solo en reintento del cronista
```

La ruta del briefing se copia de la salida de `novela briefing`
(`runs/<run_id>/briefings/NN-<agente>.md · … tokens`); de ahí sale también `<run_id>`. El retorno
del agente se lee y no se pasa a ningún otro prompt. Si crees que un agente necesita algo más, es
un defecto de su receta: no lo añadas al prompt.

## Por capítulo

`<cap>` es el número que reciben las órdenes (`7`) y `NN` el de rutas y log (`07`, con el ancho
del workspace).

1. **Situación.**
   - `novela pendiente <slug>`: con un código distinto de 0, termina: no quedan capítulos.
   - `novela estado <slug> --breve`.
   - Busca `novelas/<slug>/runs/*/intervencion.md`. Si alguno no tiene una línea `resuelto:`,
     para y nombra el fichero, antes de cualquier `novela briefing`.
   - `<cap>` es el `capitulo` de `novelas/<slug>/checkpoints/latest.json` más uno, o 1 si no existe.
   - Punto de reanudación, abajo.
2. `novela briefing <slug> <cap> escritor` → Task `escritor`, salida `capitulos/NN.md`.
3. `novela validar <slug> <cap>`. Si es un gate fallido → reintento del `escritor` con su mismo
   briefing y `reintento: qa/NN-validacion.json`, y vuelve a 3.
4. Los tres briefings de revisión, **todos antes de lanzar ninguna revisión**, para que incrusten
   el mismo capítulo: `novela briefing <slug> <cap> continuista`, `… editor-estilo` y
   `… lector-suspense`. Después, **tres Task en un solo turno**: `continuista` con salida
   `qa/NN-continuidad.json`, `editor-estilo` con `capitulos/NN.md` y `qa/NN-estilo.json`, y
   `lector-suspense` con `qa/NN-suspense.json`.
5. `novela validar <slug> <cap>` otra vez: el `editor-estilo` ha reescrito el capítulo. Si es un
   gate fallido → reintento del **`editor-estilo`** con su **mismo briefing** del paso 4 (regenerarlo
   rompería la custodia) y `reintento: qa/NN-validacion.json`, y repite 5.
6. **Gate de revisión.** Lee solo el campo `veredicto` de `qa/NN-continuidad.json` y de
   `qa/NN-suspense.json`: busca la línea `"veredicto"`, no abras el informe entero. Si alguno es
   `rechazado` o es ilegible (regla 2) → reintento del `escritor` con su briefing del paso 2 y
   `reintento: qa/NN-continuidad.json, qa/NN-suspense.json`, y vuelve a 3.
7. `novela briefing <slug> <cap> cronista` → Task `cronista`, salida `estado/deltas/NN.json` →
   `novela aplicar-delta <slug> <cap>`. Si es un gate fallido → reintento del `cronista` con su
   mismo briefing y `causa:` = el texto tras `·` en esa línea, y repite `aplicar-delta`. **Salvo si
   la causa empieza por `custodia:`**: lo roto es el orden de los pasos o el capítulo, no el delta.
   `intervencion.md` y para.
8. `novela checkpoint <slug> <cap>`.

## Cuenta de intentos

Antes de **cada** reintento, cuenta en `novelas/<slug>/runs/<run_id>/harness.log` las líneas que
contienen:

| Gate | Líneas | Intentos consumidos |
|---|---|---|
| Mecánico (pasos 3 y 5) | `validar NN -> 1` | todas |
| Revisión (paso 6) | `briefing NN continuista -> 0` | todas menos una |
| Delta (paso 7) | `aplicar-delta NN -> 1` | todas |

Con dos consumidos, el siguiente fallo no reintenta: escribe
`novelas/<slug>/runs/<run_id>/intervencion.md` y para.

```markdown
# Intervención — capítulo NN

gate: mecánico | revisión | delta | workspace
intentos: 3
briefing: runs/<run_id>/briefings/NN-<agente>.md
qa: qa/NN-validacion.json, …
```

Para un código 4, o un 1 de `briefing` o `checkpoint`, el `gate` es `workspace` y el fichero lleva
además la salida del comando. Nunca cuentes en la conversación: se compacta y no sobrevive a una
reanudación.

## Punto de reanudación

El run abierto de `NN` es el más reciente de `novelas/<slug>/runs/*/manifest.json` con
`"capitulo": <cap>` y `"fase": "capitulo"`. Sin ninguno, paso 2. Con él, en este orden:

| Si… | Reanuda en |
|---|---|
| su `harness.log` tiene `aplicar-delta NN -> 0` | paso 8 |
| existe `estado/deltas/NN.json` y el log tiene `briefing NN cronista -> 0` | `aplicar-delta` del paso 7 |
| existe `capitulos/NN.md`, la última línea `validar NN` del log es `-> 0` y no hay ninguna `briefing NN continuista` después | paso 4 |
| cualquier otro caso | paso 2 |

Al terminar, devuelve en tres líneas los capítulos cerrados, dónde paraste y por qué.
