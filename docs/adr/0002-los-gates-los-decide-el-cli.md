---
adr: 0002
titulo: "Los gates y la cuenta de intentos los decide el CLI, no la sesión"
estado: aceptada
fecha: 2026-09-24
decide: "arturo.soto"
specs: [0002]
---

# 0002 — Los gates y la cuenta de intentos los decide el CLI, no la sesión

## Contexto

El ADR 0001 puso el orquestador en una sesión de Claude Code y le dio «la delegación y el juicio
en los gates» (`architecture.md` §2.1). La spec 0001 descartó un `novela gate` por la misma razón
(0001 §15), y la 0003 dejó la cuenta de intentos en la sesión, que la saca de `harness.log` con
tres reglas de lectura escritas en `.claude/commands/novela-continuar.md`.

La novela de humo `humo-0003` mostró el coste. En el capítulo 3, la sesión informó 1 de 2
reintentos de revisión cuando el log daba 2, y la sesión reanudada volvió a revisar un capítulo
ya rechazado antes de reintentar al `escritor` (F-31). Nada falló, porque el capítulo aprobó en el
último intento permitido. Pero la regla que decide cuándo para una novela dependía de que un
modelo contara bien unas líneas de texto. Y una sesión que se compacta a mitad de capítulo puede
perder la cuenta sin que nada lo note.

## Decisión

**Un subcomando, `novela gate <slug> <cap> <plan|mecanico|final|revision|delta>`, decide cada gate.**
Lee los informes de `qa/`, la ficha, la curva y el cursor, y sale con 0 para avanzar, 1 para
reintentar o 5 para intervenir. Cuenta los intentos, escribe `intervencion.md` y se niega a un
cuarto intento. La sesión sigue invocando a los agentes y llamando al CLI, pero ya no juzga ni
cuenta: obedece un código de salida.

La cuenta vive en `harness.log` del run, no en `estado.db`. El gate cuenta sus propias líneas
`gate NN <tipo> -> 1`, que escribe él mismo. `cursor.intento` no cambia: escribirlo desde el gate
rompería el invariante 1, que reserva `estado.db` a `aplicar-delta`.

Lo que sigue siendo verdad del ADR 0001: el orquestador es una sesión, el orden del bucle está en
el procedimiento y el CLI no llama a modelos. Lo que cambia es quién decide en las fronteras.

## Alternativas descartadas

**Mantener el juicio en la sesión y endurecer las reglas de lectura.** Es lo que hizo la 0003, y
F-31 ocurrió con esas reglas. Una regla más en prosa sigue sin ejecutarse ni probarse.

**Contar en `cursor.intento`.** El campo existe y se persiste para eso (`definitions.md` §4). Pero
lo escribe `aplicar-delta`, y hacer que otro subcomando escriba la base es abrir una segunda vía
de escritura de la única fuente de verdad. Además, un solo contador no distingue los cinco gates.

**Un registro de decisiones aparte (`runs/<run_id>/gates.jsonl`).** Sería un segundo fichero con
lo mismo que ya dicen las líneas del log, y dos registros de lo mismo acaban divergiendo.

**Que el gate lo decida `validar` o `aplicar-delta`.** Los dos saben si su comprobación pasa, pero
no cuántas veces se ha intentado, ni pueden juzgar el gate de revisión, que junta tres informes.

## Consecuencias

**Lo que ganamos.** La parada al tercer intento pasa a ser código con tests: se prueba con el
agente falso, entra en el model checking de `validators.md` §4.10 y sobrevive a una compactación y
a una reanudación. El gate de revisión puede aplicar reglas que la sesión no podía, como la banda
de tensión y la tendencia, que necesitan la curva y el estado. Y `intervencion.md` sale siempre
con el mismo formato.

**Lo que aceptamos.**

- **Un código de salida nuevo, el 5**, que los procedimientos tienen que tratar como parada.
- **La sesión puede no llamar al gate.** Saltárselo no lo impide nada en el momento; lo detecta
  la auditoría de trayectoria de la spec 0002 al terminar la sesión.
- **El gate depende del formato de `harness.log`**, que es texto. Lo escribe solo el CLI, y el
  test de CA-12 de la 0003 ya fija sus líneas.

## Cuándo reabrirla

Si el bucle necesitara que el gate decidiera algo más que avanzar, reintentar o intervenir, por
ejemplo qué agente reintentar según el hallazgo, el gate estaría planificando. Eso es lo que el
ADR 0001 descartó, y habría que reabrir los dos.
