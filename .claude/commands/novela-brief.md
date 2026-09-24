---
description: Construye el brief de una novela de regalo con el entrevistador, a partir de lo que aporta el cliente. Invocar antes de /novela-nueva <slug> --brief, en una sesión interactiva.
argument-hint: <slug> --ocasion hijo|pareja|boda|aniversario|jubilacion
---

Eres el orquestador. No estructuras el brief: lo hace el `entrevistador`, y lo valida el CLI.
Tampoco escribes nada en `brief/`: lo que aporta el cliente entra con `novela brief entrada`.
Todo lo que decides sale del disco, nunca de la conversación.

**Datos personales.** El brief lleva el nombre, la edad y los recuerdos de una persona real. Esta
sesión tiene que estar abierta sin el ámbito `local`, que es el que habilita el trazado a Langfuse:

```bash
export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
claude --session-id "$NOVELA_SESSION_ID" --setting-sources project --model opus
```

Si no lo está, dilo y para. No copies datos del destinatario en `intervencion.md` ni en tus
respuestas más allá de lo imprescindible para preguntar al operador.

## Argumentos

`$ARGUMENTS` es `<slug> --ocasion <ocasión>`. Sin slug o sin `--ocasion`, responde
`uso: /novela-brief <slug> --ocasion hijo|pareja|boda|aniversario|jubilacion` y para sin ejecutar
nada.

## Códigos de salida del CLI

| Código | Qué haces |
|---|---|
| 0 | Sigues |
| 1 | En `validar`, hallazgos: la regla de lectura 1 decide. En `iniciar`, el slug ya existe: para e informa. En `entrada` o `preparar`, informa del motivo al operador y para |
| 2 | Uso incorrecto. En `entrada`, el fichero no existe, no es UTF-8, está vacío o es demasiado largo: pide otro al operador. En otro caso, para |
| 3 | Lock ocupado: otro proceso trabaja en el workspace. Para |
| 4 | Workspace inválido, o una entrada editada a mano: `intervencion.md` y para |

Cada orden `novela` va sola en su llamada a Bash: sin `;`, `&&`, `|`, redirecciones ni
`echo $?`. El código lo da el resultado de la herramienta: distinto de 0, sale como error con
`Exit code N`; sin error, es 0.

## Reglas de lectura

1. **El prefijo de la línea decide.** Tras un 1 de `validar`, lee la última línea de
   `novelas/<slug>/runs/<run_id>/harness.log`. Si contiene `brief validar -> 1 · agente:`, el
   fallo es del borrador y se reintenta al agente. Si contiene `brief validar -> 1 · usuario:`,
   falta un dato o se contradice y se pregunta al operador. Si no contiene ninguna de las dos, el
   CLI está roto: para sin reintentar y sin `intervencion.md`.
2. **Las cuentas salen del log**, nunca de la conversación. Reintentos seguidos del agente: las
   líneas `brief validar -> 1 · agente:` posteriores a la última línea `brief entrada`. Rondas
   con el operador: todas las líneas `brief validar -> 1 · usuario:` del log.

## Prompt de cada Task

Exactamente esto, y nada más: ni prosa tuya, ni resúmenes, ni datos del cliente.

```
slug: <slug>
briefing: novelas/<slug>/<ruta que imprimió novela brief preparar>
salidas: brief/borrador.json
```

La ruta se copia de la salida de `novela brief preparar`
(`runs/<run_id>/briefings/brief-RR-entrevistador.md · … tokens`); de ahí sale también
`<run_id>`. El retorno del agente se lee y no se pasa a ningún otro prompt.

## Pasos

1. `novela brief iniciar <slug> --ocasion <ocasión>`.
2. Pide al operador la ruta de un fichero con las respuestas del cliente y, si las hay, las de sus
   textos libres (una carta, una anécdota). Los ficheros van **fuera del repositorio**: si una ruta
   cae dentro de él, pide otra. Por cada fichero de respuestas,
   `novela brief entrada <slug> --tipo respuesta --fichero <ruta>`, y por cada texto libre,
   `novela brief entrada <slug> --tipo texto-libre --fichero <ruta>`.
3. `novela brief preparar <slug>` → Task `entrevistador` con el prompt de arriba.
4. `novela brief validar <slug>`:
   - Sale con 0 → paso 5.
   - Sale con 1 y la línea es `· agente:` → vuelve al paso 3: el briefing nuevo trae el informe.
     Con **2 reintentos seguidos** ya consumidos, el siguiente fallo escribe
     `novelas/<slug>/runs/<run_id>/intervencion.md` con el gate `entrevistador`, los códigos de la
     línea y la ruta del último briefing, y para.
   - Sale con 1 y la línea es `· usuario:` → lee `brief/informe.json` y muestra al operador los
     faltantes, las contradicciones y las `preguntas`. Pídele un fichero con la respuesta del
     cliente y vuelve al paso 2 con él. Con **5 rondas** ya hechas, en lugar de preguntar escribe
     `novelas/<slug>/runs/<run_id>/intervencion.md` con los códigos de la línea y para.
5. Devuelve la orden siguiente: `/novela-nueva <slug> --brief`.
