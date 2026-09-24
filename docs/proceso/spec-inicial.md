# Spec inicial

Qué se decidió construir antes de escribir código, y por qué. Las fuentes son las specs 0001 a
0003 y la historia de git.

## De dónde se partía

La primera implementación vive en `main` (del 2026-09-15 al 2026-09-20). Era una POC con un
núcleo `harness/`, una skill `novela` y un panel propio. Escribió novelas de 3 capítulos y dejó
dos mediciones que condicionaron todo lo posterior:

- **El bucle de reescritura era caro y no mejoraba.** El run `el-buzon-de-la-planta-baja-2`
  costó 18,13 $ y 56 min por 3 capítulos de ≤ 90 palabras. La reescritura multiplicaba el coste
  por 3,2 y el capítulo que más iteró terminó peor. El `Continuista` gastaba el 27 % del reloj y
  devolvió OK las 7 veces (`9ab245e`, `docs/analisis-run-el-buzon-2.md` en `main`).
- **El juez LLM no era estable.** Relanzar la misma evaluación sobre el mismo texto cambió el
  veredicto en 8 de 14 borradores (`75f0a28`, `docs/ruido-evaluador.md` en `main`).

Conclusión: un gate que depende del juicio de un modelo no se puede usar para decidir si un
capítulo avanza. El 2026-09-21 se abrió una rama vacía (`97c9e7f`) para reimplementar desde
cero, con la documentación primero.

## Qué se decidió construir

Tres días de documentación y specs antes de la primera línea de Python (`3ec551c` a `06aed55`):
definiciones del dominio, arquitectura, techo de contexto y validadores. Después, tres specs con
fronteras nítidas.

| Spec | Decide | Por qué así |
|---|---|---|
| [0001](../specs/0001-backend-cli-estado-y-api.md) · implementada | Un CLI `novela` determinista, la ontología en Pydantic, el estado en SQLite con triggers append-only y una API de solo lectura | Separar lo que necesita juicio (agentes) de lo que no (CLI). Lo determinista se prueba sin cuota. SQLite porque el append-only lo impone el motor, no la disciplina de cada ruta de escritura |
| [0003](../specs/0003-contencion-y-bucle-en-claude.md) · implementada | Los siete subagentes, los procedimientos del orquestador, permisos y el hook `PreToolUse` | Sin `tools` por rol y sin hook, el invariante 3 (el `escritor` no ve el misterio) no tiene contención estructural. Un prompt que pide no leer un fichero no es una barrera |
| [0002](../specs/0002-verificacion-a-escala-de-novela.md) · aceptada | Los cinco fallos que ningún gate por capítulo ve: fuga del misterio, contaminación del estado, deriva de estilo, colapso de tensión y degradación del orquestador | Cada capítulo puede pasar sus gates mientras la novela falla en conjunto |

El orden de implementación fue 0001 → 0003 → novela de humo `humo-0003` → 0002 aceptada con los
datos de esa novela. La 0002 dependía de medir antes de decidir.

## Principios que salieron de ahí

- **El orquestador es una sesión de Claude Code**, no un proceso Python ni un framework
  ([ADR 0001](../adr/0001-orquestador-en-claude-code.md)).
- **El CLI no llama a ningún modelo.** La suite corre sin cuota (`4e86457` lo fija con un test).
- **El contexto vive en disco.** Cada invocación recibe un briefing generado por el CLI, y ese
  fichero es el registro de lo que vio.
- **Gate barato antes que caro.** `novela validar` antes de cualquier revisión con modelo.
- **Máximo dos reintentos, después un humano.** `intervencion.md` y parada.
- **TDD sin excepciones**, y property-based en los gates y en `delta.py`.

## Lo que cambió después

El producto pasó de «novela de suspense de 24 capítulos» a «novela de regalo personalizada de 10
capítulos». La [auditoría del entregable](../auditoria-entregable.md) contó 14 de 89 requisitos
cumplidos, y casi todo lo que faltaba venía de ese desfase. De ahí salieron las specs 0004 a
0014 (panel, brief, PDF, versiones, hooks, validadores, visual, juez, Lean, TLA+ y evaluación).
El núcleo de las tres primeras no cambió: se amplió.
