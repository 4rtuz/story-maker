# Auditoría del entregable contra el checklist del examen final

Fecha: 2026-09-24 · Rama: `spec-0004` · Checklist: `requisitos.md` del plugin `auditor-entregable` 0.1.0, todas las secciones menos OPT.

Alcance: backend (`backend/`), `docs/`, `.claude/` (agentes, comandos, hooks), CLI, API, tests del backend y ficheros compartidos de la raíz. El frontend (`frontend/`) no se audita: sigue en desarrollo. Ningún requisito depende exclusivamente del frontend; en los que tienen una variante web (LEC-02, LEC-05, LEC-07) se evalúa la parte de backend y la UI queda fuera.

## Recuento

| Estado | Requisitos |
|---|---|
| cumple | 14 |
| parcial | 19 |
| falta | 56 |
| fuera de alcance (frontend) | 0 |
| **Total** | **89** |

Verificadores ejecutados en `backend/`:

- `uv run pytest`: 243 pasan. `CONTRATO` en `backend/tests/test_contratos.py` recoge los modelos actuales de `.claude/agents/` (`haiku` para `trazador`, `continuista`, `editor-estilo` y `lector-suspense`), cambiados a mano por el usuario.
- `uv run mypy --strict .`: sin errores (97 ficheros).
- `uv run ruff check .`: sin hallazgos.
- Escaneo del historial (`git log --all -p`) con los patrones de `.githooks/pre-commit`: solo aparecen valores de prueba (`dummy…`) en tests. No hay claves reales.

Contexto: el repositorio es un harness de novela de suspense de 24 capítulos. El checklist pide novelas personalizadas de regalo (10 capítulos de 1.000 a 1.500 palabras, destinatario, dedicatoria y palabras prohibidas). Casi todo lo que falta viene de ese desfase de producto, no de defectos del harness.

## CFG · Configuración

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| CFG-01 | falta | `backend/novela/slices/nueva/cmd.py` (solo `--idea`) | No hay agente entrevistador ni código que lo invoque. Nada recoge nombre, edad, rasgos, recuerdos, género, tono, extensión ni temas prohibidos |
| CFG-02 | falta | — | No se detectan datos que faltan en el brief, ni hay test |
| CFG-03 | falta | — | No se detecta ninguna contradicción (edad frente a género o tono), ni hay test |
| CFG-04 | falta | — | No se extraen hechos de texto libre, no hay delimitación de contenido no confiable ni test de injection |
| CFG-05 | falta | `backend/novela/dominio/config.py` y `backend/schemas/config.schema.json` (parámetros de obra, no brief) | No hay modelo ni schema del brief del destinatario, ni test de validación |

## LEC · Lectura interactiva

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| LEC-01 | parcial | `backend/novela/slices/export/epub.py` y `markdown.py`, `novela exportar` | No hay web ni PDF interactivo desde el backend (el panel web es frontend). Falta el trade-off web frente a PDF documentado en `/docs` |
| LEC-02 | cumple | `export/epub.py` (`libro.toc`, `EpubNav`), `export/test_export.py::test_epub_reabrible` | — (el índice de la web es frontend, fuera de alcance) |
| LEC-03 | falta | Tabla `personajes` en `backend/novela/plataforma/esquema.sql` | No hay ficha de personajes y lugares generada desde SQLite con enlaces al capítulo de cada aparición, ni test |
| LEC-04 | falta | — | No hay portada ni dedicatoria personalizada |
| LEC-05 | falta | La API es solo de lectura por diseño (`AGENTS.md`) | No hay subcomando del CLI ni formulario para pedir un cambio sobre un hecho. La UI web queda fuera de alcance |
| LEC-06 | falta | `libro_de_hechos` guarda un solo `capitulo` | No hay consulta hecho→capítulos que lo usan ni regeneración selectiva. El invariante 7 de `AGENTS.md` prohíbe hoy reescribir capítulos |
| LEC-07 | falta | — | No hay marca de capítulos cambiados ni página de «novedades» con enlaces internos |
| LEC-08 | falta | — | No se versionan las ediciones de la novela ni se conserva la anterior |

## HAR · Harness

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| HAR-01 | cumple | `.claude/agents/trazador.md` (planner), `escritor.md` (writer), `editor-estilo.md`, `continuista.md` y `lector-suspense.md` (editor/critic) | — |
| HAR-02 | cumple | `CLAUDE.md`, `AGENTS.md` | — |
| HAR-03 | parcial | `.claude/commands/novela-*.md` | No hay `.claude/skills/*/SKILL.md` ni plugin propio. Los comandos son slash commands, no una skill reutilizable |
| HAR-04 | falta | `novela validar` lo invoca el orquestador (`.claude/commands/novela-continuar.md`) | Ningún hook de `.claude/settings.json` valida el capítulo: el único hook es de policy |
| HAR-05 | cumple | `.claude/settings.json` (PreToolUse), `.claude/hooks/denegar-escritura-estado.py`, `backend/tests/test_hook.py` | — |
| HAR-06 | cumple | `backend/schemas/*.json`, `backend/tests/test_contratos.py`, validación en `slices/validacion` y `slices/delta` | — |
| HAR-07 | cumple | `dominio/config.py` (`PoliticaReintentos.max_intentos ≤ 3`), `dominio/estado.py` (`Cursor.intento`), `tests/test_bucle.py` | — |
| HAR-08 | parcial | Plugin `langfuse-observability` descrito en `docs/architecture.md` §10 | Ver OBS: no hay agregado de tokens ni coste por novela, y la configuración del plugin no está versionada |

## MEM · Memoria

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| MEM-01 | parcial | `esquema.sql`: `libro_de_hechos(id, texto, capitulo, cita)` | Cada hecho guarda el capítulo en que nace, no todos los capítulos que lo usan. Falta una relación hecho↔capítulo N:M |
| MEM-02 | parcial | `esquema.sql`: `linea_temporal(escena, capitulo, inicio, duracion_min, cita)` | Faltan personajes y lugar por evento, y ningún generador Lean la lee |
| MEM-03 | cumple | `slices/briefing/assemble.py` (`_resumenes`), `config/recipes.yaml`, `test_assemble.py` | — |
| MEM-04 | cumple | `slices/checkpoint/cmd.py`, `checkpoints/latest.json`, `novela pendiente`, `test_checkpoint.py`, `tests/test_bucle.py::test_bucle_completo_con_agente_falso` | — |

## VP · Validadores programáticos

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| VP-01 | parcial | `backend/schemas/` (capítulo, delta, qa-informe, canon, plan), `slices/validacion/gates.py`, `test_contratos.py` | No hay brief ni schema del brief. La salida de los roles se valida, la del brief no puede validarse |
| VP-02 | parcial | `gates.py::_ids` valida ids contra el canon | No se comprueba que el nombre del destinatario y de los personajes esté escrito exactamente como en la story bible |
| VP-03 | cumple | `gates.py::_longitud`, `test_gates.py`, score `longitud` en `checkpoint/cmd.py` | El rango actual es el de la novela de 24 capítulos, no 1.000–1.500 palabras (solo configuración) |
| VP-04 | falta | — | No se comprueba que cada elemento personalizado obligatorio del brief aparezca en algún capítulo según la tabla de hechos |
| VP-05 | falta | Spec 0002 RF-10 (`lexico_vetado`), aceptada y sin implementar | Ver GRD |
| VP-06 | falta | — | No hay procedimiento ni agente de validación visual con browser MCP ni registro del resultado |
| VP-07 | parcial | `docs/validators.md` §2 y §6 (qué corre en cada punto), `plataforma/langfuse.py`, `checkpoint/cmd.py` (6 scores) | Solo se emiten 6 métricas agregadas. No hay un score por validador con su nombre, ni una tabla validador → punto de ejecución → score |

## VS · Validadores semánticos

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| VS-01 | parcial | `.claude/agents/lector-suspense.md`, `continuista.md`, `backend/schemas/qa-informe.schema.json`, `dominio/qa.py` | La rúbrica es de suspense (tensión, fair play). No cubre tono, calidad narrativa ni personalización natural con puntuación y justificación por criterio. No hay rúbrica versionada como fichero propio |
| VS-02 | falta | `docs/validators.md` §4.5 (describe revisión humana) | No hay procedimiento ni plantilla de revisión humana con la misma rúbrica |
| VS-03 | falta (M) | — | No hay revisión humana de una novela completa comparada con el LLM |

## LEAN · Validador formal de la historia

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| LEAN-01 | falta | — | No hay generador SQLite → Lean |
| LEAN-02 | falta | — | No hay ficheros `.lean` ni invariantes |
| LEAN-03 | falta | — | No hay gate `lake build`/`lean` ni vuelta al editor |
| LEAN-04 | falta | — | No hay documento del caso detectado por Lean ni justificación |

## TLA · Validador formal del sistema

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| TLA-01 | falta | `tests/test_bucle.py::test_maquina_del_bucle_y_sus_invariantes` (enumeración en Python), `docs/validators.md` §4.10, que descarta TLA+ | No hay fichero `.tla` ni PlusCal del flujo |
| TLA-02 | falta | Invariantes equivalentes en `test_bucle.py` | Faltan tres invariantes de seguridad en `.tla` |
| TLA-03 | falta | — | Falta la propiedad de liveness |
| TLA-04 | falta | — | Faltan el `.cfg` de TLC y las instrucciones para ejecutarlo |
| TLA-05 | falta | — | Falta el README que mapea cada acción a su código |
| TLA-06 | falta | — | Falta el registro de contraejemplos de TLC |

## EVAL · Evaluación del sistema

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| EVAL-01 | falta | `backend/tests/canario/fixtures/` (del orquestador, no briefs) | No hay cinco briefs de prueba, ni uno adversarial, ni uno con incoherencia temporal |
| EVAL-02 | falta | — | No hay tabla por brief con los validadores que pasan y fallan |
| EVAL-03 | falta | — | No hay iteración de tuning documentada con antes, después y versión de prompt |

## OBS · Observabilidad

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| OBS-01 | parcial | `docs/architecture.md` §10.1–10.2 (plugin, `CC_LANGFUSE_TRACE_TAGS`, `NOVELA_SESSION_ID`) | Hay una sesión por capítulo, no por novela, y no hay entrevista ni regeneraciones. La configuración del plugin vive en `settings.local.json`, que no se versiona |
| OBS-02 | parcial | §10.2: subagente = span de herramienta `Task` | Lo nombra el plugin. No hay nombre identificable por rol ni código propio que lo garantice |
| OBS-03 | parcial | Generaciones del plugin | No hay agregado por capítulo ni por novela, ni captura |
| OBS-04 | parcial | `plataforma/langfuse.py`, `checkpoint/cmd.py`, `test_checkpoint.py::test_checkpoint_emite_los_seis_scores` | No se emiten todos los validadores (gates de `validar`, `aplicar-delta`) ni Lean como scores |
| OBS-05 | falta | `docs/architecture.md` §10.4 descarta Langfuse Prompt Management | Faltan prompts versionados en Langfuse |

## GRD · Guardrails

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| GRD-01 | falta | Spec 0002 RF-10 (`validar --final`), aceptada y sin implementar | No hay guardrail de palabras prohibidas en el camino de aceptación |
| GRD-02 | falta | — | No hay listas globales ni por novela en SQLite |
| GRD-03 | falta | — | No se normalizan mayúsculas, acentos ni plurales |
| GRD-04 | falta | — | La coincidencia no devuelve el capítulo al writer con límite |
| GRD-05 | falta | — | Las coincidencias no quedan en un audit log ni en Langfuse |
| GRD-06 | falta | — | No hay tests por nivel ni de variante |
| GRD-07 | falta | `harness.log` registra pasos, no decisiones del policy engine | No hay audit log de las decisiones del hook de policy |
| GRD-08 | cumple | `slices/briefing/recipes.py` (`TECHO_TOKENS = 100_000`), `assemble.py`, `test_assemble.py`, `docs/architecture.md` §6.5 | — |

## ENT · Entregables del repositorio

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| ENT-01 | falta | — | No hay `README.md` en la raíz ni brief de ejemplo |
| ENT-02 | falta | `.env` ignorado en `.gitignore` | No hay `.env.example` |
| ENT-03 | cumple | `.githooks/pre-commit` (patrones de clave), escaneo del historial sin claves reales | Conviene activar `core.hooksPath` en el clon |
| ENT-04 | falta (M) | — | Falta `ejemplos/novela-ejemplo.pdf` |
| ENT-05 | falta (M) | — | No se puede verificar desde el repo |
| ENT-06 | falta (M) | — | Queda fuera del repo, no verificable |

## DOC · Documentación de proceso

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| DOC-01 | cumple | `docs/specs/0001-backend-cli-estado-y-api.md` (implementada) | — |
| DOC-02 | parcial | `docs/adr/0001-*.md`, `0002-*.md`, `docs/specs/0004/decisions.md`, «Alternativas descartadas» de las specs | Faltan decisiones sobre formato de la story bible, modelo de lectura, integración TLA+ e invariantes Lean |
| DOC-03 | parcial | `docs/validators.md` (clasificación por método) | No hay un explainer breve por concepto del curso |
| DOC-04 | parcial | `docs/domain-knowledge.md` (mermaid de orquestación y trazas), `docs/camino.md`, `docs/validators.md` §6 | Faltan el diagrama de la máquina de estados TLA+ y el del esquema SQLite |
| DOC-05 | falta | — | No hay registro de iteraciones causa → efecto |
| DOC-06 | parcial | `docs/validators.md` §4.9 (modelo de amenaza y canario) | No hay log de casos adversariales con detección y resolución |

## CC · Uso de Claude Code

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| CC-01 | cumple | `CLAUDE.md` | — |
| CC-02 | parcial | `git ls-files .claude`: agents, commands, hooks, settings.json | Falta memoria de proyecto commiteada |
| CC-03 | falta | — | No hay `.mcp.json` con servidor de browser |
| CC-04 | falta | — | No hay documento del uso real del browser MCP |
| CC-05 | parcial | Comandos en `.claude/commands/` referenciados en `CLAUDE.md` y `docs/architecture.md` §1 | No hay skills en el repo ni referencias desde `/docs` a las usadas (p. ej. `sdd-spec-writer`) |
| CC-06 | cumple | `docs/architecture.md` §2.1, §7.4–7.5, `CLAUDE.md` (subagentes y slash commands) | — |

## PRE · Presentación

| ID | Estado | Evidencia | Qué falta |
|---|---|---|---|
| PRE-01 | falta (M) | — | No existe `presentacion/` |
| PRE-02 | falta (M) | — | Faltan los anexos |
| PRE-03 | falta | — | Falta `presentacion/README.md` |
| PRE-04 | falta (M) | — | Falta el deck |
| PRE-05 | falta (M) | — | Faltan la portada y la contraportada |
| PRE-06 | falta (M) | — | Faltan los bloques del deck |
| PRE-07 | falta (M) | — | No hay script ni documento de costes desde Langfuse |
| PRE-08 | falta (M) | — | Faltan las evidencias en el deck |
| PRE-09 | falta (M) | — | Falta el vídeo de demo |
| PRE-10 | falta (M) | — | La presentación no está commiteada |

## Manuales pendientes

- VS-03: revisión humana de al menos una novela completa, comparada con el juicio del LLM.
- ENT-04: novela de ejemplo de 10 capítulos generada con el brief del README (`ejemplos/novela-ejemplo.pdf`).
- ENT-05: repositorio MyFactory con las herramientas del curso, accesible.
- ENT-06: entrega por email con enlaces a los commits finales y la frase de diseño.
- PRE-01: deck principal en PDF y en formato editable.
- PRE-02: anexos como ficheros individuales.
- PRE-04: imagen corporativa consistente.
- PRE-05: portada y contraportada.
- PRE-06: bloques de 10 minutos.
- PRE-07: datos de la slide de presupuesto desde Langfuse.
- PRE-08: evidencias en el deck.
- PRE-09: vídeo de demo.
- PRE-10: presentación commiteada antes del plazo.
