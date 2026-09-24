# Explainers

Un concepto por apartado: qué es, dónde está en este repo y por qué aquí.

## Harness y orquestador

- **Qué es.** El harness es todo lo que rodea al modelo para que haga un trabajo largo: roles,
  contexto, gates, estado y parada. El orquestador decide el orden de los pasos.
- **Dónde.** `.claude/commands/novela-continuar.md` (el orden), `backend/novela/` (el CLI
  `novela`), `novela producir` (`backend/novela/slices/producir/`) para el desatendido.
- **Por qué aquí.** Una novela no cabe en una conversación. El orquestador es una sesión de
  Claude Code que no lee prosa y delega todo ([ADR 0001](../adr/0001-orquestador-en-claude-code.md)).

## Subagentes y roles

- **Qué es.** Un subagente es una invocación con prompt, herramientas y modelo propios, y
  contexto limpio. Un rol es un contrato de entradas y salidas.
- **Dónde.** `.claude/agents/*.md`, uno por rol. Su contrato se prueba en
  `backend/tests/test_contratos.py`.
- **Por qué aquí.** El `escritor` no debe ver el misterio. Solo un subagente con `tools: Read,
  Write`, sin `Glob` ni `Grep`, lo garantiza por construcción.

## Context engineering

- **Qué es.** Decidir qué entra en la ventana de cada invocación, en qué orden y con qué
  presupuesto.
- **Dónde.** `novela briefing` ensambla `runs/<run_id>/briefings/NN-<agente>.md` por capas según
  `backend/config/recipes.yaml`. Techo de 100.000 tokens (`architecture.md` §6.5).
- **Por qué aquí.** El contexto vive en disco, no en la conversación: el briefing es a la vez la
  entrada del agente y el registro de lo que vio, que Langfuse no captura.

## Memoria

- **Qué es.** Lo que el sistema recuerda entre invocaciones y sesiones.
- **Dónde.** Largo plazo: `estado/estado.db`, la story bible en SQLite, con tablas append-only.
  Corto plazo: `memoria/resumenes/NN.md`, derivados y reconstruibles. Reanudación:
  `checkpoints/latest.json`.
- **Por qué aquí.** Una sesión por capítulo olvida todo. `estado.db` es la única fuente de
  verdad, y solo `novela aplicar-delta` la escribe.

## Tools con schema validado

- **Qué es.** Que la salida de un agente sea un contrato tipado, no texto libre.
- **Dónde.** `backend/schemas/*.schema.json`, generados desde los modelos Pydantic de
  `backend/novela/dominio/`. `novela validar` y `aplicar-delta` los aplican. Score `vp_schema`.
- **Por qué aquí.** El delta del `cronista` alimenta la base. Un JSON mal formado ahí corrompe
  todo lo posterior.

## Hooks

- **Qué es.** Código que Claude Code ejecuta antes o después de una herramienta, y que puede
  denegarla o devolver feedback.
- **Dónde.** `.claude/hooks/denegar-escritura-estado.py` (`PreToolUse`, policy: quién escribe
  dónde) y `.claude/hooks/validar-capitulo.py` (`PostToolUse`, valida `capitulos/NN.md` en cuanto
  se escribe). Registro en `.claude/settings.json`. Tests en `backend/tests/test_hook*.py`.
- **Por qué aquí.** Un permiso es de sesión, no de rol. El hook distingue por `agent_type` y
  falla cerrado.

## Skills y slash commands

- **Qué es.** Un slash command es un procedimiento que se invoca por nombre. Una skill es un
  paquete de instrucciones reutilizable, con frontmatter.
- **Dónde.** `.claude/commands/novela-{brief,nueva,continuar,auditar}.md`;
  `.claude/skills/novela-regalo/`, `validar-visual/` y `auditoria-seguridad/`.
- **Por qué aquí.** Los procedimientos son el orquestador. Las skills son para el operador y el
  desarrollo; ningún agente lleva la herramienta `Skill`.

## Retries con límite y human-in-the-loop

- **Qué es.** Reintentar con la causa concreta, un número acotado de veces, y parar pidiendo una
  decisión humana.
- **Dónde.** Máximo dos reintentos por gate. El reintento recibe solo las rutas de `qa/`. Al
  tercero, `runs/<run_id>/intervencion.md`, que se resuelve con una línea `resuelto:`.
  `novela producir` no se salta un `intervencion.md` vivo.
- **Por qué aquí.** En `main` el bucle de reescritura costaba 3,2 veces más y terminaba peor. Si
  un capítulo necesita tres intentos, el problema no está en el capítulo.

## Guardrails

- **Qué es.** Una barrera preventiva: actúa antes de la acción, a diferencia de un gate.
- **Dónde.** `deny` de `.claude/settings.json`, el hook `PreToolUse`, los triggers de
  `esquema.sql`, el guardarraíl del secreto en `novela briefing` y la lista de palabras
  prohibidas con audit log ([`docs/guardrails.md`](../guardrails.md)). Catálogo en
  `docs/validators.md` §4.4.
- **Por qué aquí.** Es más barato que un gate y no quema un reintento. Un guardrail silenciado es
  peor que ausente.

## Prompt injection y contenido no confiable

- **Qué es.** Texto que intenta pasar por instrucción. Aquí llega por la carta del cliente o por
  ficheros que escribió otro agente.
- **Dónde.** `novela brief preparar` delimita cada entrada con una marca derivada de su sha256 y
  lista los fragmentos sospechosos; `novela brief validar` exige cita literal y que los campos
  cerrados salgan de respuestas, no de texto libre (`backend/novela/slices/brief/`). Caso de
  prueba: `backend/tests/fixtures/brief/carta-inyectada.md`.
- **Por qué aquí.** La barrera es el CLI, no el juicio del `entrevistador`.

## LLM-as-judge

- **Qué es.** Un modelo que puntúa una salida contra una rúbrica.
- **Dónde.** `lector-suspense` (tensión, fair play, coherencia) y el `juez-narrativo` con rúbrica
  versionada de seis criterios y su plantilla humana
  ([`docs/evaluacion/juez.md`](../evaluacion/juez.md)).
- **Por qué aquí.** Lo que no es mecánico necesita juicio. Pero en `main` el juez cambió de
  veredicto en 8 de 14 borradores al relanzarlo: por eso sus scores informan y los gates que
  bloquean son deterministas.

## Evals

- **Qué es.** Medir el sistema entero sobre casos fijos y comparar versiones.
- **Dónde.** Spec 0014: cinco briefs de prueba, `novela eval sembrar` y `novela eval informe`, y
  los resultados en `docs/evals.md`. Baseline de `humo-0003` en la spec 0003 §13.
- **Por qué aquí.** Un cambio de prompt no tiene TDD. Se valida comparando scores, con el sha del
  commit en cada `manifest.json`.

## Observabilidad

- **Qué es.** Trazas (qué pasó), spans (cada paso), scores (qué tal salió) y la versión de prompt
  que lo produjo.
- **Dónde.** Plugin `langfuse-observability` para las trazas; `novela checkpoint` emite los
  scores; `runs/<run_id>/manifest.json` guarda sha, `sucio` y hash de cada prompt. Sesión por
  novela y costes en [`docs/observabilidad.md`](../observabilidad.md).
- **Por qué aquí.** Los prompts se versionan con git, no en Langfuse: una sola fuente de verdad.

## Métodos formales

- **Qué es.** Demostrar una propiedad en vez de probar ejemplos. Lean 4 comprueba teoremas sobre
  datos; TLA+ explora todos los estados de un diseño con TLC.
- **Dónde.** `formal/lean/` ([`docs/formal/lean.md`](../formal/lean.md)): la cronología de la
  novela que sale de `estado.db`. `formal/tla/` ([`docs/formal/tla.md`](../formal/tla.md)): el
  flujo del harness con gates, reintentos y reanudación.
- **Por qué aquí.** Lean bloquea publicar una historia donde alguien está en dos sitios a la vez.
  TLA+ vigila que un cambio del procedimiento no publique sin validar.

## MCP

- **Qué es.** Model Context Protocol: un servidor expone herramientas a un cliente como Claude
  Code.
- **Dónde.** `.mcp.json`: Playwright MCP para la validación visual
  ([`docs/validacion-visual.md`](../validacion-visual.md)) y el servidor propio en FastMCP
  ([`docs/mcp.md`](../mcp.md)).
- **Por qué aquí.** Ver el libro como lo verá el lector, y consultar el estado sin dar a nadie
  acceso de escritura.

## Spec-driven development

- **Qué es.** Escribir qué se construye y cómo se acepta antes del código.
- **Dónde.** `docs/specs/NNNN/spec.md` y `decisions.md`; al aceptarse, `plan/` y
  `validators.md`. Ciclo de vida en `AGENTS.md`.
- **Por qué aquí.** La conversación se pierde; el fichero lo lee el siguiente agente. Cada
  criterio de aceptación es un test.

## TDD y property-based testing

- **Qué es.** Test en rojo antes del código. Property-based: el test genera entradas y comprueba
  una propiedad, no un ejemplo.
- **Dónde.** `uv run pytest` en `backend/`, sin modelo. Hypothesis en los gates, el delta y el
  guardarraíl del secreto (`backend/tests/estrategias.py`); mutación con `mutmut` sobre gates y
  `apply`.
- **Por qué aquí.** En un gate los ejemplos no cubren: un gate que deja pasar un caso raro no
  avisa. `docs/validators.md` §3.6.
