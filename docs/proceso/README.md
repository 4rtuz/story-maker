# Documentación de proceso

Cómo se razonó y se construyó el harness, no cómo funciona hoy. Para eso, la documentación de
referencia: `AGENTS.md`, `docs/architecture.md`, `docs/definitions.md`,
`docs/domain-knowledge.md` y `docs/validators.md`.

Algunas rutas de esta tabla las escriben otras ramas (`feat/lean`, `feat/tla`,
`feat/guardrails`, `feat/juez`, `feat/visual`, `feat/mcp`, `feat/prosa`, `feat/langfuse`) y
existen después de integrarlas en `entrega`.

## Mapa contra la rúbrica

| Apartado | Documento | Qué contiene |
|---|---|---|
| Spec inicial | [`spec-inicial.md`](spec-inicial.md) | Qué se decidió construir antes de la primera línea de código, y por qué |
| | [`docs/specs/0001-backend-cli-estado-y-api.md`](../specs/0001-backend-cli-estado-y-api.md), [`0002`](../specs/0002-verificacion-a-escala-de-novela.md), [`0003`](../specs/0003-contencion-y-bucle-en-claude.md) | Las tres specs fundacionales |
| | [`docs/specs/0004/`](../specs/0004/) … [`0014/`](../specs/0014/) | Una carpeta por cambio: `spec.md` y `decisions.md` |
| Trade-offs | [`trade-offs.md`](trade-offs.md) | Cada decisión relevante: opciones, criterios, elección y consecuencia |
| | [`docs/adr/`](../adr/) | ADR 0001 a 0004, las decisiones caras de revertir |
| Explainers | [`explainers.md`](explainers.md) | Un explainer por concepto del curso, con su ruta en el repo |
| | [`docs/formal/lean.md`](../formal/lean.md), [`docs/formal/tla.md`](../formal/tla.md) | Métodos formales, en detalle |
| | [`docs/guardrails.md`](../guardrails.md) | Guardrail de palabras prohibidas y su audit log |
| | [`docs/evaluacion/juez.md`](../evaluacion/juez.md) | LLM-as-judge y revisión humana con la misma rúbrica |
| | [`docs/observabilidad.md`](../observabilidad.md) | Langfuse: sesión por novela, costes, prompts versionados |
| | [`docs/mcp.md`](../mcp.md) | Servidor MCP propio (FastMCP) |
| | [`docs/lectura-web.md`](../lectura-web.md), [`docs/validacion-visual.md`](../validacion-visual.md) | Lectura web y validación visual con Playwright MCP |
| | [`docs/linters-prosa.md`](../linters-prosa.md), [`docs/security-report.md`](../security-report.md) | Linters de prosa y auditoría de seguridad |
| Diagramas | [`diagramas.md`](diagramas.md) | Arquitectura, bucle por capítulo, esquema SQLite, máquina de estados y tabla de validadores |
| | [`docs/camino.md`](../camino.md), [`docs/domain-knowledge.md`](../domain-knowledge.md) | Camino de la información y diagramas del dominio |
| Registro de iteraciones | [`iteraciones.md`](iteraciones.md) | Causa → cambio → efecto medido → commit |
| | [`docs/auditoria-entregable.md`](../auditoria-entregable.md) | Auditoría contra el checklist, que disparó las specs 0005 a 0014 |
| Red-team log | [`red-team.md`](red-team.md) | Caso adversarial, vector, validador que lo detectó y resolución |
| | [`docs/validators.md`](../validators.md) §4.9 y §4.17 | Modelo de amenaza, canario y catálogo de fallos de la contención |
| Uso de Claude Code | [`claude-code.md`](claude-code.md) | Agentes, slash commands, hooks, skills, plugins, MCP y memoria |
| | [`.claude/memory/`](../../.claude/memory/) | La memoria de proyecto, commiteada |
| | [`.claude/skills/novela-regalo/SKILL.md`](../../.claude/skills/novela-regalo/SKILL.md) | Skill del operador: una novela de regalo de principio a fin |
