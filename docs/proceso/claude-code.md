# Uso de Claude Code

Claude Code es el runtime del harness y la herramienta con que se desarrolló. Este documento
recoge las dos cosas: lo que está versionado en `.claude/` y lo que se usó para construirlo.

## Instrucciones del proyecto

| Fichero | Qué es |
|---|---|
| `AGENTS.md` | Convenciones del harness: invariantes, ramas de contexto, CLI, TDD, ciclo de las specs. Lo cargan la sesión y cada subagente |
| `CLAUDE.md` | Importa `AGENTS.md` y añade lo propio de Claude: el papel de orquestador, el bucle por capítulo, hooks, claves y permisos |

Los dos se pagan en cada invocación, así que crecer es una decisión, no un hábito
(`architecture.md` §6.5).

## Subagentes (`.claude/agents/`)

Todos con `tools: Read, Write` salvo el `editor-estilo`, que añade `Edit`. Ninguno tiene
`Bash`, `Glob`, `Grep`, `Task` ni `Skill`: alcanzan solo lo que su briefing nombra.

| Agente | Modelo | Propósito | Resultado |
|---|---|---|---|
| `entrevistador` | sonnet | Estructura lo que cuenta el cliente del destinatario | `brief/borrador.json` |
| `arquitecto` | opus | Canon de la novela y su misterio | `canon/premisa.md`, `mundo.md`, `estilo.md`, `misterio.borrador.md`, `personajes/*.md` |
| `trazador` | haiku | Escaleta, curva de tensión y una ficha por capítulo | `plan/escaleta.md`, `plan/capitulos/NN.md` |
| `escritor` | opus | Escribe el capítulo desde su ficha; nunca ve el misterio | `capitulos/NN.md` |
| `continuista` | haiku | Compara el capítulo con hechos, línea temporal y canon | `qa/NN-continuidad.json` |
| `editor-estilo` | haiku | Corrige el estilo contra `canon/estilo.md` sin tocar la trama | `capitulos/NN.md`, `qa/NN-estilo.json` |
| `lector-suspense` | haiku | Puntúa tensión, fair play y previsibilidad | `qa/NN-suspense.json` |
| `cronista` | haiku | Extrae el delta de estado del capítulo aprobado | `estado/deltas/NN.json` |

Las ramas `feat/juez` y `feat/visual` añaden `juez-narrativo` y `revisor-visual`. El contrato de
cada agente (nombre, modelo, herramientas y salidas) está en `backend/tests/test_contratos.py`.

## Slash commands (`.claude/commands/`)

| Comando | Propósito | Resultado |
|---|---|---|
| `/novela-brief <slug> --ocasion …` | Brief de una novela de regalo con el `entrevistador` y `novela brief` | `brief/brief.json` validado, o preguntas al operador |
| `/novela-nueva <slug> --idea "…"` · `--brief` | Canon y plan con `arquitecto` y `trazador` | `canon/`, `plan/` y la orden siguiente |
| `/novela-continuar <slug> [--capitulos N]` | El bucle por capítulo con gates y reintentos; reanuda desde el checkpoint | Capítulos cerrados con `checkpoints/NN.json`, o `intervencion.md` |
| `/novela-auditar <slug>` | Auditoría final y exportación | `export/` si está limpia; los hallazgos si no |

`novela producir` encadena `/novela-nueva`, un `/novela-continuar` por capítulo y
`/novela-auditar`, cada uno en su sesión de `claude -p`.

## Hooks (`.claude/hooks/`)

| Hook | Evento | Qué hace | Tests |
|---|---|---|---|
| `denegar-escritura-estado.py` | `PreToolUse` | Cinco reglas: nada bajo `estado/` salvo `estado/deltas/NN.json`; cada rol solo en sus salidas; la sesión principal solo `intervencion.md`; ninguna orden que nombre el misterio o la base; en una sesión del harness, solo los roles de `.claude/agents/`. Falla cerrado | `backend/tests/test_hook.py` |
| `validar-capitulo.py` | `PostToolUse` | Ejecuta `novela validar --origen hook` cuando `escritor` o `editor-estilo` escriben `capitulos/NN.md` y devuelve los hallazgos como feedback bloqueante | `backend/tests/test_hook_validacion.py` |

Registro y permisos (`allow`, `deny`) en `.claude/settings.json`. El plugin de Langfuse aporta
dos hooks más, `Stop` y `SessionEnd`, habilitados solo en `.claude/settings.local.json`.

## Skills del repositorio (`.claude/skills/`)

| Skill | Para qué |
|---|---|
| [`novela-regalo`](../../.claude/skills/novela-regalo/SKILL.md) | Guía al operador por una novela de regalo de principio a fin: brief, canon, producción, auditoría y gates formales, PDF y cambio con regeneración |
| `validar-visual` | Validación visual de la lectura con Playwright MCP (`feat/visual`, [`docs/validacion-visual.md`](../validacion-visual.md)) |
| `auditoria-seguridad` | Auditoría de seguridad del repo (`feat/prosa`, [`docs/security-report.md`](../security-report.md)) |

Son para el operador y el desarrollo. Ningún agente del harness lleva la herramienta `Skill`.

## Plugins y skills usados durante el desarrollo

Instalados en el ámbito de usuario (`~/.claude/plugins/`), fuera del harness.

| Plugin | Para qué se usó aquí |
|---|---|
| `sdd-spec-writer` | Redactar las specs 0004 a 0014 con el formato `docs/specs/NNNN/spec.md` + `decisions.md` |
| `spec-tools` (`spec-planner`) | Los planes de implementación: `docs/implementation-plans/` para 0001 a 0003, y `plan/` dentro de cada spec desde la 0004 |
| `spec-validators` | Los `validators.md` de cada spec y los catálogos de fallos de `docs/validators.md` (§4.17, §4.18) |
| `auditor-entregable` | [`docs/auditoria-entregable.md`](../auditoria-entregable.md): 89 requisitos contra el checklist del examen |
| `mattpocock-skills` | `tdd` para el ciclo rojo-verde, `writing-for-agents` para `CLAUDE.md`, prompts de agentes y skills, `diagnosing-bugs` para los fallos del bucle |
| `ponytail` | El diff más corto que funciona; evitar abstracciones sin segunda implementación |
| `langfuse-observability` | Trazas de cada sesión del harness; las del run de `main` alimentaron el diagnóstico del bucle |
| `taste-skill`, `design` | El panel (spec 0004): identidad visual, componentes y revisión WCAG 2.1 AA |
| `find-skills` | Descubrir skills para cada tarea |

## MCP (`.mcp.json`)

Versionado en la raíz tras integrar `feat/visual` y `feat/mcp`:

- **Playwright MCP**: el `revisor-visual` y la skill `validar-visual` abren la previa HTML del
  libro en un navegador y registran lo que ven ([`docs/validacion-visual.md`](../validacion-visual.md)).
- **Servidor propio en FastMCP**: expone el estado de una novela como herramientas de solo
  lectura ([`docs/mcp.md`](../mcp.md)).

## Memoria de proyecto

La auto-memoria de Claude Code para este repo está copiada en
[`.claude/memory/`](../../.claude/memory/): `MEMORY.md` es el índice y cada fichero, una
fricción de la máquina de desarrollo que `AGENTS.md` no cubre (Git Bash y Device Guard, la regla
4 del hook en los commits, el entorno del frontend). Las sesiones del harness también la cargan,
así que tiene que decir la verdad actual. La copia no lleva claves; menciona que existe un `.env`
con ellas, no sus valores.
