---
adr: 0001
titulo: "El orquestador es una sesión de Claude Code, no un proceso"
estado: aceptada
fecha: 2026-09-22
decide: "arturo.soto"
specs: [0001]
---

# 0001 — El orquestador es una sesión de Claude Code, no un proceso

## Contexto

El sistema reparte la escritura de una novela entre siete roles y necesita algo que los invoque en
orden, aplique los gates entre paso y paso y decida cuándo reintentar y cuándo parar. Ese algo
puede ser un proceso que escribimos nosotros o puede ser la propia sesión interactiva.

La elección condiciona todo lo demás: qué se puede probar, qué cuesta cuota, qué contención existe
entre agentes y qué se puede automatizar. `architecture.md` §3.1 ya nombraba este ADR; se escribe
ahora porque la spec 0001 construye el backend sobre la decisión y conviene que el motivo esté
donde se busca.

## Decisión

**El orquestador es una sesión de Claude Code.** El orden del bucle vive en
`.claude/commands/novela-continuar.md`, no en código Python. Los siete roles son subagentes
invocados con Task. El backend aporta operaciones deterministas —el CLI `novela`— que la sesión
llama entre delegaciones.

De ahí salen dos reglas que el resto del sistema da por ciertas:

- **No hay planificador.** El orden es fijo y está escrito en un procedimiento, no calculado.
- **El CLI no llama a ningún modelo.** Todo lo que necesita juicio lo hace un agente; todo lo que
  es determinista lo hace el CLI, y por eso la suite de tests corre sin cuota.

## Alternativas descartadas

**Un orquestador en Python con un SDK de proveedor.** Es la forma habitual, da control total sobre
temperatura, reintentos y paralelismo, y permitiría probar el bucle de punta a punta con un doble
del modelo. Descartada porque `AGENTS.md` lo prohíbe explícitamente en su sección «Nunca»: todo
corre sobre la suscripción de Claude Code. Añadir un SDK de modelos convierte el proyecto en otro
con otro modelo de coste.

**Un framework de agentes —LangGraph, CrewAI o equivalente.** Aporta grafo de ejecución,
reintentos y estado. Descartada por dos motivos: arrastra un framework y, en la práctica, un
gateway de modelos; y no aporta lo único que de verdad necesitamos, que es el aislamiento por
subagente. El grafo de este sistema son nueve pasos en línea recta con un único punto de abanico:
no justifica un motor de grafos.

**Un bucle de shell que lanza prompts.** Lo más simple que podría funcionar. Descartada porque sin
subagentes no hay `tools` restringido por rol, y sin eso el invariante 3 —el `escritor` no ve el
misterio— se queda sin su única contención estructural. Un prompt que pide no leer un fichero no
es una barrera.

## Consecuencias

**Lo que ganamos.** Contención por construcción: cada subagente lleva sus herramientas en el
frontmatter y alcanza solo lo que su briefing le nombra. Cero coste de infraestructura. Y una
frontera limpia entre lo determinista y lo que necesita juicio, que es lo que hace testable la
mitad de Python sin tocar un modelo.

**Lo que aceptamos.**

- **Sin control de temperatura.** La interfaz de suscripción no lo expone, así que la variación
  entre capítulos depende del prompt. `architecture.md` §12.1 lo recoge como decisión abierta, y
  `validators.md` §5.5 como riesgo aceptado permanente: sin `temperature` no hay palanca.
- **Techo de contexto por sesión.** El orquestador está sujeto al mismo límite que los agentes y
  acumula por capítulo, de ahí que el modo desatendido fije una sesión por capítulo (§6.5).
- **El bucle no se prueba como se prueba una función.** Lo que se prueba es el CLI con un agente
  falso; la trayectoria real del orquestador se observa por trazas, no por asserts.
- **La lógica del bucle es un documento en markdown.** No tiene tipos, no tiene tests y no falla
  al compilar. Su control de calidad son las trazas y los ficheros de `runs/`.

## Cuándo reabrirla

Si el bucle necesitara ramas condicionales por acto, paralelismo real entre capítulos o reintentos
con política dependiente del historial, el procedimiento en markdown dejaría de bastar. La señal
concreta: que `novela-continuar.md` tenga que expresar una condición que no se puede escribir como
una lista de pasos.
