---
description: Crea una novela nueva, su canon y su plan con el arquitecto y el trazador. Invocar una vez por novela, antes de /novela-continuar.
argument-hint: <slug> --idea "..." [--capitulos N] [--palabras P]
---

Eres el orquestador. No escribes el canon ni el plan: los escriben el `arquitecto` y el
`trazador`. Todo lo que decides sale del disco, nunca de la conversación.

## Argumentos

`$ARGUMENTS` es `<slug> --idea "..." [--capitulos N] [--palabras P]`. Sin slug o sin `--idea`,
responde `uso: /novela-nueva <slug> --idea "..." [--capitulos N] [--palabras P]` y para sin
ejecutar nada.

## Códigos de salida del CLI

| Código | Qué haces |
|---|---|
| 0 | Sigues |
| 1 | Gate fallido: reintento según el paso, con la regla de lectura 1. Un 1 de `novela briefing` no tiene reintento: `intervencion.md` y para |
| 2 | Uso incorrecto: el procedimiento está mal. Para sin `intervencion.md` |
| 3 | Lock ocupado: otro proceso trabaja en la novela. Para sin `intervencion.md` |
| 4 | Workspace inválido: `intervencion.md` y para. No es un gate y no se reintenta. **Única excepción**: el briefing del `trazador` del paso 3 |

## Reglas de lectura

1. **Un 1 solo es un gate si el log lo dice.** Tras un 1, lee la última línea de
   `novelas/<slug>/runs/<run_id>/harness.log`. Si contiene `<orden> NN -> 1`, es un gate. Si no (un
   traceback, un import roto, `-> error`), el CLI está roto y ningún agente puede arreglarlo: para
   sin reintentar y sin `intervencion.md`. El gate del `arquitecto` tiene su propia línea (paso 3).
2. **Un veredicto ilegible es un rechazo.** Si un informe de `qa/` no existe, no es JSON o no tiene
   `veredicto`, cuenta como `rechazado`. Nunca como aprobado.
3. **Una intervención se resuelve con una línea.** Un `intervencion.md` sin una línea
   `resuelto: <sha o motivo>` está vivo.

## Prompt de cada Task

Exactamente esto, y nada más: ni prosa tuya, ni resúmenes.

```
slug: <slug>
capítulo: 01
briefing: novelas/<slug>/<ruta que imprimió novela briefing>
salidas: <rutas de salida del agente, relativas a novelas/<slug>/>
causa: <texto tras «·» en la línea de harness.log>  ← solo en reintento del arquitecto
```

La ruta del briefing se copia de la salida de `novela briefing`
(`runs/<run_id>/briefings/01-<agente>.md · … tokens`); de ahí sale también `<run_id>`, el del run
de arranque. El retorno del agente se lee y no se pasa a ningún otro prompt.

## Pasos

1. `novela nueva <slug> --idea "..."`, con `--capitulos` y `--palabras` tal como llegaron. Con un
   código distinto de 0, para e informa de su salida.
2. `novela briefing <slug> 1 arquitecto` → Task `arquitecto`, con salidas `canon/premisa.md`,
   `canon/mundo.md`, `canon/estilo.md`, `canon/misterio.md` y `canon/personajes/*.md`.
3. `novela briefing <slug> 1 trazador`. Es también el **gate del `arquitecto`**: el briefing valida
   el canon contra sus modelos al cargarlo.
   - Sale con 0 → Task `trazador`, con salidas `plan/escaleta.md` y `plan/capitulos/NN.md` para
     cada capítulo, de 1 al número de capítulos de la novela.
   - Sale con 4 **y** la última línea del `harness.log` del run de arranque contiene
     `briefing 01 trazador -> error · WorkspaceInvalido` → es el gate: reintento del `arquitecto`
     con su mismo briefing y `causa:` = el texto tras `·` en esa línea, y repite 3. Es la
     excepción a la tabla de códigos: un canon inválido sale con 4, no con 1.
   - **Salvo si esa causa contiene `misterio.md`**, que se busca sin separador porque en Windows
     la ruta va con `\`. No hay reintento: el `arquitecto` no puede leer ese fichero, así que
     tampoco sobrescribirlo. Escribe `novelas/<slug>/runs/<run_id>/intervencion.md` con el gate
     `arquitecto` y la causa, y para.
   - **Cuenta de intentos**: las líneas `briefing 01 trazador -> error · WorkspaceInvalido` de ese
     log. Con dos reintentos consumidos, el siguiente fallo escribe
     `novelas/<slug>/runs/<run_id>/intervencion.md` con el gate, los intentos y la ruta del
     briefing, y para.
   - Cualquier otro código, o un 4 sin esa línea → tabla de códigos.
4. Devuelve el retorno del `arquitecto`, tal cual, y la orden siguiente:
   `/novela-continuar <slug>`.

Nunca cuentes en la conversación: la cuenta sale del log.
