# architecture.md

Arquitectura del harness multiagente de generación de novelas de suspense.

Este documento describe **cómo se implementa** la ontología definida en `docs/domain-knowledge.md` (diagramas) y `docs/definitions.md` (diccionario). Toda entidad citada aquí en `mayúsculas` o con ruta de punto existe allí con su definición, mutabilidad y propietario.

**Restricción de partida:** el sistema se ejecuta íntegramente sobre la suscripción de Claude Code. No hay llamadas a la API de Anthropic ni a proveedores externos. Esto tiene dos consecuencias de diseño que atraviesan todo el documento: no hay control de `temperature`, y el orquestador no es un proceso Python que invoca modelos, sino la propia sesión de Claude Code.

---

## 1. Principios

1. **El contexto vive en el sistema de ficheros, no en la conversación.** Cada subagente arranca con contexto vacío. La continuidad la da `estado/estado.db` más los resúmenes, nunca el historial.
2. **Código separado de datos.** El repositorio contiene lógica, prompts y esquemas. Cada novela es un *workspace* independiente fuera del repo.
3. **Toda escritura se valida contra esquema.** Si un agente devuelve algo que no valida, el paso falla y se reintenta. Nunca se persiste estado corrupto.
4. **La sesión orquestadora no genera prosa y no la lee.** Decide, delega, aplica gates y serializa. Si el texto de los capítulos entrara en su contexto, la sesión se agotaría antes del capítulo 10.
5. **Lo verificable mecánicamente se verifica con código.** Longitud, esquema, presencia de pistas planificadas y balance de hilos son asserts en Python, no juicios de un modelo.
6. **Reanudable en cualquier punto.** El estado se reconstruye desde `checkpoints/`, jamás desde una sesión previa.
7. **Contexto mínimo suficiente por invocación.** Cada subagente recibe un *briefing* generado explícitamente para esa llamada, no acceso libre al workspace.

---

## 2. Stack

| Capa | Elección | Motivo |
|---|---|---|
| Orquestación | Sesión de Claude Code | Es el único ejecutor; la suscripción cubre todas las llamadas |
| Agentes | `.claude/agents/*.md` | Subagentes con frontmatter YAML, contexto aislado por invocación |
| Procedimientos | `.claude/commands/*.md` | Slash commands que definen el bucle que sigue el orquestador |
| Herramientas deterministas | Python 3.12, CLI `novela` | Validación, estado, briefings, checkpoints y auditoría, sin coste |
| Gestor de dependencias | `uv` | Lockfile reproducible |
| Estado | SQLite vía `sqlite3` de la stdlib | Una base por workspace; selección indexada y append-only impuesto por triggers, sin dependencia nueva |
| Esquemas | Pydantic v2 | Modelos tipados que exportan JSON Schema a `schemas/`; siguen siendo el contrato de la API |
| CLI | Typer | Subcomandos invocados por el orquestador vía Bash |
| Frontmatter | `python-frontmatter` | Capítulos y fichas de plan son Markdown con metadatos |
| Concurrencia | `filelock` | Un solo proceso por workspace |
| Observabilidad | Hook Stop de Claude Code + Langfuse SDK 4.x | Trazado nativo, sin proxy |
| Tests | pytest + `jsonschema` | Contratos verificados sin consumir cuota |
| Backend | Python 3.12 + FastAPI | API de solo lectura sobre el workspace; reutiliza los modelos Pydantic del CLI |
| Frontend | Vite + TypeScript + Three.js | Consume la API del backend; sin lógica de negocio |
| Export | `markdown-it-py` + `ebooklib` | Salida a `.md` único y `.epub` (markdown-it solo convierte a XHTML para el epub) |

Fuera del stack, explícitamente: API de Anthropic, OpenRouter, Claude Agent SDK, LiteLLM o cualquier gateway de modelos. Nada de eso hace falta. FastAPI no es una excepción a esa regla: no llama a ningún modelo, solo sirve ficheros del workspace al frontend.

### 2.0 Monorepo

El repositorio es un monorepo con dos carpetas grandes:

- **`backend/`** — Python 3.12. Contiene el CLI determinista `novela`, los modelos Pydantic, los esquemas, la configuración y la API FastAPI. Es lo único que toca el workspace.
- **`frontend/`** — Vite + TypeScript + Three.js. Solo lectura, consume la API del backend.

Lo que no es ni backend ni frontend — `.claude/`, `docs/`, `novelas/` — vive en la raíz, porque lo comparten los dos o no pertenece a ninguno.

### 2.1 Modelo de ejecución

```
sesión de Claude Code (orquestador)
├── Bash: novela briefing 07 escritor        → genera el contexto de la llamada
├── Task: subagente escritor                 → escribe capitulos/07.md
├── Bash: novela validar 07                  → esquema, longitud, pistas, hilos
├── Task: subagente continuista              → qa/07-continuidad.json
├── Task: subagente editor-estilo
├── Task: subagente lector-suspense
├── Task: subagente cronista                 → delta de estado
├── Bash: novela aplicar-delta 07            → estado.db + resumen
└── Bash: novela checkpoint 07
```

El orquestador nunca lee `capitulos/07.md`. Los subagentes leen y escriben ficheros; lo que devuelven a la sesión principal es un informe de dos o tres líneas. Esta disciplina es lo que permite que una sesión cubra varios capítulos sin saturarse.

La lógica del bucle vive en `.claude/commands/novela-continuar.md`, no en código Python. El código Python es el conjunto de operaciones deterministas que el bucle invoca entre delegaciones.

**Quién orquesta.** La sesión de Claude Code, no un proceso Python. No hay planificador que decida el siguiente paso: el orden es fijo y está escrito en `.claude/commands/novela-continuar.md`. La sesión aporta la delegación y el juicio en los gates; todo lo demás es determinista y vive en el CLI.

**Secuencia y paralelismo.** Dentro de un capítulo hay un único punto de abanico: los tres agentes de revisión (`continuista`, `editor-estilo`, `lector-suspense`) leen el mismo capítulo, no se leen entre sí y escriben en ficheros distintos de `qa/`. Se invocan en paralelo, en un solo turno con tres llamadas a Task. El resto es estrictamente secuencial por dependencia de datos.

El `cronista` queda fuera del abanico y se invoca **después** de evaluar los gates. Extraer el delta de un capítulo que va a reescribirse es trabajo tirado, y aplicarlo sobre un capítulo rechazado deja el estado por delante del texto, que es la forma más cara de corromper una novela.

**Gates.** Tres barreras, de la más barata a la más cara:

| Gate | Quién lo evalúa | Cuándo |
|---|---|---|
| Mecánico | `novela validar` (Python, sin cuota) | Tras el `escritor`, antes de cualquier revisión |
| Continuidad | `continuista` → `qa/NN-continuidad.json` | Tras el abanico |
| Tensión | `lector-suspense` → `qa/NN-suspense.json` | Tras el abanico |

El primero descarta lo que no merece una llamada a un modelo: longitud fuera de rango, frontmatter inválido, pista planificada ausente, hilo que se cierra sin haberse abierto. Ejecutarlo antes de delegar en los revisores no es una optimización, es la regla.

Los hallazgos del `editor-estilo` no son gate: se aplican, no bloquean. Un capítulo con prosa mejorable avanza; uno que contradice un hecho establecido, no.

**Reintentos.** Máximo dos por gate. El reintento vuelve al `escritor` con el informe de QA como única entrada nueva: nunca un «está mal» genérico y nunca el capítulo entero de vuelta por el canal de conversación, que el agente ya sabe leer su propio fichero. Al tercer fallo el bucle escribe `runs/<run_id>/intervencion.md` y para. Dos formas distintas de fallar agotan el presupuesto igual que la misma dos veces: si un capítulo necesita tres intentos, el problema no está en el capítulo.

**Estado del bucle.** Cada paso se identifica por `(run_id, capitulo, agente, intento)` y atraviesa tres situaciones: pendiente, ejecutado y confirmado. `novela checkpoint` confirma una sola vez, al final del capítulo y con el delta ya aplicado. Reanudar es repetir el primer paso no confirmado, siempre entero; por eso todos los pasos son idempotentes sobre ficheros de nombre determinista.

### 2.2 Selección de modelo por agente

Sin acceso a `temperature`, el único parámetro de control que queda es el modelo, disponible en el frontmatter del subagente (`opus`, `sonnet`, `haiku` o `inherit`).

| Agente | `model` | Motivo |
|---|---|---|
| `arquitecto` | opus | Una sola invocación, máximo impacto sobre todo lo demás |
| `trazador` | opus | La distribución de pistas condiciona la novela entera |
| `escritor` | opus | La prosa es el producto |
| `continuista` | sonnet | Verificación contra hechos; el rigor lo da el prompt y el esquema de salida |
| `editor-estilo` | sonnet | Corrige contra párrafos canónicos |
| `lector-suspense` | sonnet | Puntuaciones estructuradas |
| `cronista` | haiku | Extracción mecánica; el agente más barato del bucle |
| `entrevistador` | sonnet | Fuera del bucle, en la fase de brief: estructura y cita; el CLI verifica cada cita |

La variación creativa que antes se buscaba con temperatura alta se compensa por prompt: el `escritor` recibe en su briefing una restricción de apertura distinta por capítulo (con qué tipo de frase empieza, qué registro domina la primera escena) para evitar que 24 capítulos abran igual. Es la mitigación disponible y conviene medir si basta.

### 2.3 Modo desatendido

El bucle puede correr sin supervisión invocando Claude Code en modo headless, en Git Bash:

```bash
export MSYS_NO_PATHCONV=1                 # sin esto, "/novela-continuar" llega como ruta de Windows
export CC_LANGFUSE_TRACE_TAGS=<slug>
novela comprobar-entorno || exit 1
while novela pendiente <slug>; do
  antes=$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)
  export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
  claude -p "/novela-continuar <slug> --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
    --setting-sources project,local --permission-mode dontAsk --model opus || break
  [ "$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)" != "$antes" ] || break
done
```

Un capítulo por sesión mantiene el contexto del orquestador pequeño y acota el daño de un fallo. El `|| break` es deliberado: ante un error, el sistema para y deja el checkpoint, no insiste. `novela comprobar-entorno` para antes de la primera sesión, y la última línea para el bucle si una sesión termina sin avanzar el checkpoint: un permiso que falte o una confianza no aceptada no se convierten en sesiones sin fin que gastan cuota. `--setting-sources project,local` deja fuera los plugins y hooks del ámbito de usuario, y `--model opus` fija el modelo del orquestador. Las sesiones interactivas del harness se abren igual de aisladas y con `NOVELA_SESSION_ID`, para que la regla 5 del hook y la correlación del log valgan también en ellas.

### 2.4 Higiene de contexto de la sesión orquestadora

Es el riesgo específico de poner el orquestador dentro de Claude Code, y se controla con cuatro reglas:

1. Los subagentes devuelven informes de longitud acotada; los hallazgos completos van a `qa/`, no al canal de retorno.
2. El orquestador lee estado a través de `novela estado --breve`, que imprime cursor, cuota, hilos abiertos y poco más.
3. Un capítulo por sesión en modo desatendido; en modo interactivo, `/clear` entre actos.
4. `CLAUDE.md` se mantiene corto. Se carga en cada sesión y en cada subagente: cada línea superflua se paga muchas veces.

---

## 3. Estructura del repositorio

### 3.0 Metodología

Cuatro decisiones, cada una respondiendo a una pregunta distinta. No se solapan y no hay una quinta.

| Decisión | Qué decide |
|---|---|
| **Vertical slices** / package by feature | Dónde vive cada cosa |
| **Núcleo funcional con cáscara imperativa** | Cómo se estructura por dentro cada slice |
| **DDD táctico** | Qué hay en `dominio/` |
| **Dos puertos**: `WorkspaceRepository` y `ScoreSink` | Lo único que queda del hexágono; viven en `plataforma/` |

**Vertical slices.** Una carpeta por caso de uso, no por capa técnica. Un subcomando del CLI es un slice: su parseo, su lógica y sus tests están juntos. Añadir `novela presupuesto` es crear una carpeta, no tocar siete. Borrarlo es borrar una carpeta. No hay `services/`, `handlers/` ni `utils/` transversales: si dos slices necesitan lo mismo, o baja a `dominio/` porque es una regla del negocio, o a `plataforma/` porque es I/O; si no es ninguna de las dos, se duplica y ya se verá.

En el frontend la misma regla con otro nombre — package by feature: `features/lanzar/`, `features/progreso/`, `features/lectura/`. Las tres pantallas de §11.2 son las tres carpetas.

**Núcleo funcional con cáscara imperativa.** Dentro de cada slice, `cmd.py` es la cáscara: lee argumentos, toma el lock, carga ficheros, imprime y sale con código. Todo lo demás del slice — `gates.py`, `assemble.py`, `apply.py` — son funciones puras: reciben datos, devuelven datos, no tocan disco ni reloj ni red. Esa frontera es la que hace posible lo que ya exige el proceso: tests sin llamadas a modelo, y tests property-based sobre gates y deltas (`docs/validators.md` §3.6). Una función pura se prueba con mil entradas generadas; una que abre ficheros, no.

Regla práctica: si un fichero del núcleo importa `pathlib`, `open`, `datetime.now` o `requests`, está mal colocado.

**DDD táctico en `dominio/`.** Ahí vive la ontología de `docs/definitions.md` como código: `Estado`, `Canon`, `Plan`, `Pista`, `LibroDeHechos`. Entidades con identidad estable (los ids de §5, que no cambian aunque cambie el nombre visible del personaje), objetos de valor inmutables, y las invariantes dentro del propio modelo: `LibroDeHechos` no expone forma de modificar ni borrar una entrada, solo de añadir. Un invariante que se pueda expresar como tipo no se escribe como validación suelta.

`dominio/` no importa nada de `slices/` ni de `plataforma/`, y no sabe que existe un sistema de ficheros. Son los mismos modelos Pydantic que responde la API (§11.1): una sola ontología.

**Los dos puertos.** Del hexágono sobrevive solo lo que tiene más de una implementación real:

- `WorkspaceRepository` — leer y escribir el workspace, con escritura atómica y lock. Segunda implementación: los workspaces sintéticos de `backend/tests/fixtures/`.
- `ScoreSink` — emitir scores y trazas. Segunda implementación: el no-op cuando `TRACE_TO_LANGFUSE` está apagado (§10.1).

Todo lo demás se llama directamente. Nada de repositorio por entidad, capa de casos de uso, DTOs entre dominio y API, ni interfaz con una sola implementación: cuando aparezca la segunda, se extrae entonces.

### 3.1 El árbol

```
novela-harness/                    # monorepo: backend/ + frontend/
├── CLAUDE.md                     # convenciones; corto a propósito, ver §2.4
├── AGENTS.md
├── README.md
│
├── docs/
│   ├── architecture.md           # este fichero
│   ├── domain-knowledge.md       # diagramas Mermaid
│   ├── definitions.md            # diccionario de entidades
│   ├── validators.md             # metodos de verificacion y riesgos aceptados
│   ├── specs/                    # un fichero por cambio concreto, antes de existir
│   │   └── _plantilla.md
│   └── adr/
│       └── 0001-orquestador-en-claude-code.md
│
├── .claude/                      # compartido; vive en la raíz del monorepo
│   ├── settings.json             # permisos y registro del hook; ni claves ni plugins, ver §7.1
│   ├── settings.local.json       # solo enabledPlugins, el de Langfuse — en .gitignore
│   ├── agents/                   # un fichero por subagente
│   │   ├── arquitecto.md
│   │   ├── trazador.md
│   │   ├── escritor.md
│   │   ├── continuista.md
│   │   ├── editor-estilo.md
│   │   ├── lector-suspense.md
│   │   ├── cronista.md
│   │   └── entrevistador.md      # fase de brief de una novela de regalo
│   ├── commands/                 # los procedimientos del orquestador
│   │   ├── novela-brief.md       # la entrevista, antes de novela-nueva --brief
│   │   ├── novela-nueva.md
│   │   ├── novela-continuar.md   # el bucle por capítulo
│   │   └── novela-auditar.md
│   └── hooks/
│       └── denegar-escritura-estado.py   # PreToolUse sobre estado/, ver §7.1
│
├── backend/                      # Python 3.12 — FastAPI + CLI novela
│   ├── pyproject.toml
│   ├── uv.lock
│   │
│   ├── api/                      # FastAPI; solo lectura, ver §11.1
│   │   ├── main.py               # app + CORS para el dev server de Vite
│   │   └── routers/
│   │       ├── novelas.py
│   │       └── capitulos.py
│   │
│   ├── novela/                   # CLI determinista; cero llamadas a modelo
│   │   ├── cli.py                # Typer: solo registra el cmd.py de cada slice
│   │   │
│   │   ├── slices/               # un caso de uso por carpeta, ver §3.0
│   │   │   ├── brief/            # cmd.py · entradas.py · assemble.py · gates.py, con sus tests
│   │   │   ├── briefing/         # cmd.py · assemble.py · recipes.py · test_briefing.py
│   │   │   ├── validacion/       # cmd.py · gates.py · test_gates.py
│   │   │   ├── delta/            # cmd.py · apply.py · violaciones.py · test_delta.py
│   │   │   ├── checkpoint/
│   │   │   ├── auditoria/        # pistas huérfanas, hilos abiertos
│   │   │   ├── entorno/          # comprobar-entorno: hook, python, settings.local.json, .env
│   │   │   ├── presupuesto/      # ventana de uso y degradación
│   │   │   └── export/           # cmd.py · markdown.py · epub.py
│   │   │
│   │   ├── dominio/              # la ontología como código; sin I/O, sin framework
│   │   │   ├── config.py         # rama 1
│   │   │   ├── brief.py          # Brief, BorradorBrief, InformeBrief e idea_semilla
│   │   │   ├── texto.py          # normalizar: qué cuenta como la misma cita
│   │   │   ├── canon.py          # rama 2 — Canon, Pista
│   │   │   ├── plan.py           # rama 3 — Plan
│   │   │   ├── estado.py         # rama 4 — Estado, LibroDeHechos (append-only)
│   │   │   └── qa.py
│   │   │
│   │   └── plataforma/           # los dos puertos y sus adaptadores
│   │       ├── workspace.py      # WorkspaceRepository
│   │       ├── esquema.sql       # DDL de estado.db: tablas y triggers append-only
│   │       ├── estado_db.py      # conexión, PRAGMAs y transacciones
│   │       ├── atomic.py         # escritura tmp + rename, para todo lo que no es el estado
│   │       ├── lock.py           # un proceso por workspace
│   │       └── langfuse.py       # ScoreSink
│   │
│   ├── config/
│   │   ├── default.yaml          # valores por defecto de parametros_obra
│   │   └── recipes.yaml          # qué entra en el briefing de cada agente
│   │
│   ├── schemas/                  # JSON Schema generados desde Pydantic, versionados
│   │   ├── config.schema.json
│   │   ├── state.schema.json
│   │   ├── canon.schema.json
│   │   ├── escaleta.schema.json
│   │   ├── plan-capitulo.schema.json
│   │   ├── capitulo.schema.json      # frontmatter de capítulo (§7.2)
│   │   ├── delta.schema.json         # delta del cronista (§7.6)
│   │   └── qa-informe.schema.json
│   │
│   └── tests/                    # solo lo transversal; el test de un slice vive con él
│       ├── test_api.py
│       ├── test_contratos.py     # Pydantic ↔ schemas/
│       └── fixtures/             # workspaces sintéticos, sin llamadas a modelo
│
├── frontend/                     # Vite + TypeScript + Three.js, solo lectura (spec 0004)
│   ├── package.json              # dependencias de ejecución: three y markdown-it
│   ├── vite.config.ts            # 5173 fijo; /@fs/ limitado a frontend/
│   ├── eslint.config.js          # imports de fuera de src/, HTML sin sanear
│   ├── index.html
│   ├── test/fixtures/            # usos prohibidos para lint.test.ts, fuera de `eslint .`
│   └── src/                      # package by feature, ver §3.0; tests junto a su módulo
│       ├── features/
│       │   ├── lanzar/           # formulario y orden /novela-nueva para copiar
│       │   ├── progreso/         # cursor, curva de tensión, hilos abiertos, runs y actividad
│       │   └── lectura/          # escena Three.js, navegación 3D del libro
│       ├── shared/               # cliente de la API, tipos, componentes base
│       │   ├── marca/            # tokens.css (único fichero con colores), pares, logo, fuente
│       │   ├── iconos/           # trazados de Lucide copiados, con su LICENSE
│       │   └── ui/               # componentes, que solo usan roles de tokens.css
│       └── app/                  # routing, layout
│
└── novelas/                      # workspaces, en .gitignore
    └── <slug>/
```

**La regla de separación:** `backend/`, `frontend/`, `.claude/agents/` y `.claude/commands/` son el harness y se versionan. `novelas/` son datos y no. Si una novela merece versionarse, es un repositorio propio.

---

## 4. Estructura de un workspace

Reflejo literal de la rama 6 de la ontología.

```
novelas/<slug>/
├── config.yaml                   # rama 1, inmutable tras el arranque
│
├── brief/                        # solo en novelas de regalo, antes de config.yaml
│   ├── inicio.json               # CLI: ocasión y fecha
│   ├── entradas/
│   │   └── ent-01.md             # CLI: lo que aporta el cliente, normalizado, frontmatter EntradaMeta
│   ├── borrador.json             # entrevistador: el único fichero que escribe
│   ├── informe.json              # CLI
│   └── brief.json                # CLI, solo si el borrador valida
│
├── canon/                        # rama 2 — VERSIONADO
│   ├── premisa.md
│   ├── mundo.md
│   ├── estilo.md
│   ├── misterio.md               # acceso restringido, ver §6.3
│   └── personajes/
│       ├── per-elena-vidal.md
│       └── per-tomas-reyes.md    # un fichero por personaje: permite cargar solo los presentes
│
├── plan/                         # rama 3 — VERSIONADO
│   ├── escaleta.md
│   └── capitulos/
│       ├── 01.md
│       └── 02.md
│
├── estado/
│   ├── estado.db                 # rama 4 — fuente única de verdad, SQLite
│   ├── estado.db-wal             # journal de SQLite; efímero, no se respalda
│   ├── state.lock
│   └── deltas/                   # salida del cronista, entrada de aplicar-delta
│       └── 01.json
│
├── memoria/                      # rama 5 — DERIVADO, reconstruible
│   └── resumenes/
│       ├── 01.md                 # tres granularidades en un fichero
│       └── 02.md
│
├── capitulos/                    # salida final
│   ├── 01.md
│   └── 02.md
│
├── qa/
│   ├── 01-continuidad.json
│   └── 01-suspense.json
│
├── checkpoints/
│   ├── 01.json                   # cursor, versiones, run_id y capitulos_sha256 (el sello)
│   └── latest.json
│
├── runs/
│   └── <run_id>/
│       ├── manifest.json         # sha de commit, recetas, canon, plan, fase y hashes de .claude/
│       ├── briefings/            # el contexto exacto de cada invocación, ver §6.1
│       │   ├── 01-escritor.md
│       │   └── 01-continuista.md
│       └── harness.log           # una línea por subcomando, con sesion=<uuid> si la hay
│
└── export/
    ├── novela.md
    └── novela.epub
```

`brief/` lleva los datos personales del destinatario. Lo crea `novela brief iniciar` y, en cuanto existe `config.yaml`, queda cerrado: ningún subcomando lo vuelve a escribir.

`memoria/` y `runs/` son reconstruibles o desechables. `canon/`, `plan/`, `estado/` y `capitulos/` son los cuatro directorios que importa respaldar.

---

## 5. Convenciones

**Numeración.** Capítulos con dos dígitos (`01`, `02`) hasta 99; si `num_capitulos > 99`, tres dígitos en todo el workspace desde el inicio. No se mezcla.

**Identificadores.** Prefijo de tipo más slug o secuencia. Son claves estables: el nombre visible de un personaje puede cambiar en la trama, su id no.

```
per-elena-vidal      personaje          ^per-[a-z0-9-]+$
esc-casa-del-faro    escenario          ^esc-[a-z][a-z0-9-]*$
esc-01-3             escena             ^esc-\d{2,3}-\d+$
pis-007              pista              ^pis-\d{3}$
pfa-003              pista falsa        ^pfa-\d{3}$
rev-002              revelación         ^rev-\d{3}$
hil-004              hilo               ^hil-\d{3}$
obj-011              objeto o prueba    ^obj-\d{3}$
hec-014              hecho              ^hec-\d{3}$
cap-01               capítulo           ^cap-\d{2,3}$
ent-01               entrada del brief  ^ent-\d{2}$
```

`esc-` sirve a escenario y a escena, y las dos expresiones son disjuntas por construcción: la de
escenario exige letra tras el guion, la de escena exige dígito. Sin esa distinción el validador de
escenario acepta ids de escena y el error no aparece hasta una consulta vacía sobre
`linea_temporal`.

**Escritura atómica.** Todo fichero se escribe en `.tmp` y se renombra. El estado es la excepción y por el mismo motivo: `estado.db` se escribe dentro de una transacción `BEGIN IMMEDIATE` … `COMMIT`, de modo que un corte a mitad de `aplicar-delta` deja la base en el punto anterior al delta. Un estado a medio escribir es un workspace muerto, con fichero o con base.

**Bloqueo.** `filelock` sobre `estado/state.lock`. El WAL de SQLite serializa los escritores de la base, pero no protege `capitulos/`, `qa/` ni `runs/`: el lock es del workspace, no del estado. Dos sesiones de Claude Code sobre la misma novela se pisarían.

**Idempotencia.** Cada paso se identifica por `(run_id, capitulo, agente, intento)`. Reanudar tras un fallo repite el paso, nunca lo salta.

---

## 6. Gestión de contexto

Es la pieza que decide si la novela se sostiene a 80.000 palabras o se desmorona. Materializa la rama 5.

### 6.1 Briefings

Un subagente de Claude Code puede leer el workspace entero con sus herramientas. No debe. Antes de cada delegación, el orquestador ejecuta `novela briefing <cap> <agente>`, que escribe `runs/<run_id>/briefings/NN-<agente>.md` con exactamente el contexto de esa llamada. El prompt del subagente le instruye a trabajar sobre ese briefing y sobre la lista cerrada de rutas que se le autorizan.

Tres beneficios: el consumo de contexto es predecible, el contexto de cualquier invocación pasada es auditable, y una regresión de calidad puede atribuirse a un cambio concreto de receta.

Hay además una razón de observabilidad: el trazado por hooks **no captura el contexto ensamblado** — qué aportaron `CLAUDE.md`, las skills o la carga automática al system prompt efectivo no forma parte de lo que los hooks pueden leer. Los ficheros de briefing son, por tanto, el único registro fiel de qué vio cada agente. Sin ellos, las trazas muestran la conversación y las llamadas a herramientas, pero no el contexto que las produjo.

### 6.2 Recetas

`config/recipes.yaml` define, por agente, qué capas entran y con qué presupuesto:

```yaml
escritor:
  presupuesto_tokens: 60000
  capas:
    - permanente: [canon/premisa, canon/mundo, canon/estilo]
    - personajes: presentes_en_escena       # resuelto desde plan/capitulos/NN
    - estado: [personajes, conocimiento, hilos_abiertos, objetos]
    - inmediata: capitulo_anterior_completo
    - reciente: {n: 3, granularidad: parrafo}
    - remota: {granularidad: una_linea, desde: 1}
    - plan: capitulo_actual
    - variacion: restriccion_de_apertura     # ver §2.2
  excluir: [canon/misterio]

continuista:
  presupuesto_tokens: 65000
  capas:
    - permanente: [canon/*, canon/misterio]
    - estado: [libro_de_hechos, linea_temporal, coartadas]
    - objetivo: capitulo_recien_escrito
```

La receta se versiona y su identificador se escribe en `runs/<run_id>/manifest.json`.

### 6.3 Aislamiento del secreto

`canon/misterio.md` está excluido por receta del `escritor` y del `editor-estilo`. Dos capas de refuerzo, porque una regla en el prompt no basta:

1. `novela briefing` aborta si el contenido resultante contiene texto procedente de ese fichero.
2. Ningún agente tiene `Glob` ni `Grep` en su frontmatter. Sin herramientas de búsqueda, un agente solo alcanza las rutas que su briefing le nombra, y al `escritor` y al `editor-estilo` el briefing nunca le nombra el misterio.

Conviene ser exacto sobre qué hace `tools`, porque de ello depende el invariante 3: restringe **capacidad y descubrimiento**, no rutas. `Read` no lleva lista blanca de ficheros, así que un agente que conozca la ruta puede leerla. Restringir por ruta exige una regla `deny`, y `.claude/settings.json` la tiene: `Read(./novelas/*/canon/misterio.md)`. Los permisos valen para la sesión entera y no por subagente; la regla sirve para los siete porque `novela briefing` incrusta el misterio en el briefing de los tres que lo necesitan, y ninguno tiene que abrir el fichero.

El escritor recibe solo el contenido de las pistas listadas en `plan/capitulos/NN.md` para su capítulo. Un modelo que conoce la solución la filtra en el subtexto mucho antes de tiempo, y es un fallo invisible en revisión capítulo a capítulo.

### 6.4 Memoria de corto y largo plazo

`estado/estado.db` (rama 4) y `memoria/` (rama 5) resuelven dos problemas distintos y se confunden con facilidad. El estado es lo que ha pasado, en forma de datos. La memoria es ese mismo material comprimido a varias resoluciones para que quepa en un briefing.

| Horizonte | Qué contiene | Dónde vive | Ciclo de vida |
|---|---|---|---|
| Trabajo | El briefing de una invocación concreta | Contexto del subagente | Muere con la invocación |
| Corto plazo | Capítulo anterior completo, resúmenes a párrafo de los 3 anteriores, hilos abiertos, posición temporal y espacial | `memoria/resumenes/` y las tablas mutables de `estado.db` | Se desplaza con el cursor |
| Largo plazo | `libro_de_hechos`, `conocimiento`, `canon/`, resúmenes a una línea desde el capítulo 1 | `estado/estado.db` y `canon/` | Append-only, no caduca |

**La memoria de trabajo no persiste.** Es la consecuencia directa del principio 1: un subagente no recuerda la invocación anterior y no debe recordarla. Lo que tiene que sobrevivir se escribe en disco por el contrato de salida del agente; lo que se queda en el canal de retorno se pierde, y está bien que se pierda.

**El corto plazo es una ventana deslizante de coste constante.** El `escritor` del capítulo 12 ve el 11 entero, el 9-10-11 a párrafo y el 1-8 a una línea. El del 13 ve la misma forma desplazada un lugar. Ningún capítulo cuesta más contexto que el anterior, y eso es lo que hace viable el capítulo 24.

**El largo plazo no se carga, se consulta.** `libro_de_hechos` y `conocimiento` son append-only precisamente para ser indexables por id: el briefing del `continuista` no trae el libro entero, trae las entradas que tocan a los personajes, objetos y hilos presentes en el capítulo que revisa. Es una consulta con índice sobre `estado.db`, no un recorrido del estado en Python; el coste de seleccionar no crece con lo escrito. Recordar aquí es seleccionar, no acumular.

**La compresión ocurre una sola vez, al aplicar el delta.** `novela aplicar-delta` escribe `memoria/resumenes/NN.md` con las tres granularidades a la vez —escena, párrafo y una línea— a partir de la salida del `cronista`. No hay un segundo pase de resumido, ni se vuelve a abrir un capítulo cerrado para comprimirlo más. Degradar la resolución con la distancia es elegir qué granularidad entra en el briefing, no reescribir nada.

**La memoria es derivada; el estado no.** Si `memoria/` se pierde, se regenera pasando el `cronista` por los capítulos ya escritos: cuesta cuota, no corrompe nada. Si `estado.db` se pierde, se restaura del último checkpoint. Ante una discrepancia entre un resumen y el estado gana el estado, siempre y sin discusión.

### 6.5 El techo de 100.000 tokens

**Regla dura: ninguna invocación —ni la del orquestador ni la de un subagente— ensambla más de 100.000 tokens de contexto vivo.** Es un techo por invocación, no un presupuesto acumulado: cuenta cuánto hay simultáneamente en la ventana, no cuánto ha pasado por ella a lo largo de la novela. Está por debajo de la ventana real del modelo a propósito; ese margen es lo que absorbe el error de estimación.

El presupuesto de briefing de una receta sale de restar lo que no es negociable:

```
briefing ≤ 100.000 − fijo − salida_esperada − margen
           fijo   = 10.000   CLAUDE.md + AGENTS.md (~4.000) + prompt del agente y herramientas (~6.000)
           margen = 15.000   sin asignar
```

| Agente | Salida esperada | Techo de briefing | Receta (§6.2) |
|---|---|---|---|
| `escritor` | ~15.000 (capítulo de 3.300 palabras ≈ 4.700, resto razonamiento) | 60.000 | 60.000 |
| `continuista` | ~10.000 (JSON de hallazgos) | 65.000 | 65.000 |
| `cronista` | ~5.000 (delta) | 70.000 | — |

`CLAUDE.md` y `AGENTS.md` se pagan en cada subagente: por eso no ampliarlos es una regla y no una preferencia.

Reparto interno del briefing del `escritor` en un capítulo 12 de 24:

| Capa | Tokens | ¿Crece con la novela? |
|---|---|---|
| `canon/` permanente (premisa, mundo, estilo) | ~6.000 | No |
| Personajes presentes en escena | ~3.000 | No, se filtra por escena |
| Estado filtrado (hilos abiertos, conocimiento, objetos) | ~8.000 | Sí, sublinealmente |
| Capítulo anterior completo | ~4.700 | No |
| Resúmenes a párrafo (3) | ~450 | No |
| Resúmenes a una línea (1..8) | ~200 | Sí, ~25 tokens por capítulo |
| Ficha del capítulo actual y restricción de apertura | ~1.500 | No |

Unos 24.000 sobre 60.000. El margen no sobra: es lo que permite que un capítulo con doce personajes en escena y cinco hilos abiertos siga cabiendo sin tocar la receta.

**Dónde se aplica.** `novela briefing` cuenta lo que acaba de ensamblar y **falla** si supera el `presupuesto_tokens` de la receta. Nunca trunca en silencio: un briefing truncado es un agente que no sabe lo que no sabe.

**Degradación cuando no cabe.** Orden fijo, de menos a más doloroso:

1. Se recortan los resúmenes a una línea más antiguos.
2. Los resúmenes a párrafo bajan a una línea.
3. La lista de personajes se reduce a los que tienen diálogo en el capítulo.
4. Se para y se pide intervención.

`canon/` y el estado filtrado no se degradan nunca: son las dos capas cuya ausencia produce contradicción en vez de imprecisión.

**El orquestador está sujeto al mismo techo y es quien va más justo,** porque su contexto es el único que no se vacía entre pasos. Acumula del orden de 6.000 a 8.000 tokens por capítulo entre salidas de Bash, informes de subagente y sus propias decisiones. Contra los ~90.000 útiles eso da unos diez capítulos por sesión, pero el coste real depende de cuántos reintentos haya habido y eso no se sabe de antemano: de ahí que el modo desatendido (§2.3) fije un capítulo por sesión y deje el margen sin gastar.

**Cómo se cuenta.** Sin endpoint de conteo, `novela briefing` estima desde caracteres con una ratio conservadora para español —3,5 caracteres por token— y trata el resultado como cota superior. El error ronda el 10% y siempre por exceso, que es el lado correcto en el que equivocarse. Si algún día se mide y sobra margen sistemáticamente, la palanca es subir el presupuesto de las recetas, no el techo.

---

## 7. Contratos de datos

### 7.1 `estado/estado.db`

Una tabla por colección de la rama 4. El DDL vive en `backend/novela/plataforma/esquema.sql` y la tabla `meta` guarda su `schema_version`.

Lo que sigue no es el formato de almacenamiento, es la **vista serializada**: lo que devuelven `novela estado --json` y `GET /novelas/{slug}/estado`, generada desde los modelos Pydantic de `backend/novela/dominio/estado.py`. Es también el contrato que valida `backend/schemas/state.schema.json`, y no cambia con este soporte.

```json
{
  "schema_version": "1.0.0",
  "cursor": { "capitulo": 7, "fase": "revision", "ultimo_paso": "continuista", "intento": 1 },
  "linea_temporal": [
    { "escena": "esc-07-2", "capitulo": 7, "inicio": "dia 3, 21:40", "duracion_min": 35, "cita": null }
  ],
  "personajes": {
    "per-elena-vidal": {
      "ubicacion": "esc-casa-del-faro",
      "estado_fisico": "herida leve",
      "estado_emocional": "paranoia creciente",
      "condicion": "viva",
      "objetivo_activo": "llegar al archivo antes del amanecer",
      "ultima_aparicion": 7
    }
  },
  "conocimiento": {
    "per-elena-vidal": [ { "hecho": "hec-014", "desde_capitulo": 5, "cita": "..." } ]
  },
  "relaciones": [
    { "de": "per-elena-vidal", "a": "per-tomas-reyes", "tipo": "sospecha", "intensidad": 0.8, "desde": 6 }
  ],
  "objetos": [
    { "id": "obj-011", "poseedor": "per-tomas-reyes", "ubicacion": null, "capitulo_intro": 3, "relevancia": "alta" }
  ],
  "libro_de_hechos": [
    { "id": "hec-014", "texto": "El faro lleva nueve años sin funcionar.", "capitulo": 5, "cita": "..." }
  ],
  "hilos": [ { "id": "hil-004", "estado": "abierto", "abierto_en": 2, "cerrado_en": null, "descripcion": "..." } ],
  "pistas": { "pis-007": { "estado": "plantada", "plantada_en": 4, "pagada_en": null } },
  "conocimiento_lector": [ { "hecho": "hec-014", "desde_capitulo": 5, "cita": null } ],
  "tension_real": [ 4, 5, 6, 5, 7, 8, 7 ],
  "metricas": { "palabras_totales": 21840, "desviacion_vs_plan": -0.04 }
}
```

`cita` es obligatoria en `libro_de_hechos` y opcional en `linea_temporal`, `conocimiento` y `conocimiento_lector`; si está, `novela aplicar-delta` exige que sea literal del capítulo (spec 0001, RF-33).

Las cinco colecciones que `docs/definitions.md` declara append-only —`libro_de_hechos`, `conocimiento`, `linea_temporal`, `conocimiento_lector` y `tension_real`— lo son porque lo impone el esquema, no porque lo compruebe el código:

```sql
CREATE TRIGGER libro_de_hechos_no_update BEFORE UPDATE ON libro_de_hechos
BEGIN SELECT RAISE(ABORT, 'libro_de_hechos es append-only'); END;
```

Modificar o eliminar una entrada existente no es una corrección, es reescribir la historia, y rompe toda verificación posterior. Con el trigger no hay ruta —ni un delta mal formado, ni un subcomando nuevo que se olvide de comprobarlo, ni un `sqlite3` abierto a mano— por la que llegue a ocurrir.

`novela aplicar-delta` aplica el delta entero dentro de una única transacción: si alguna fila viola una restricción, no queda nada escrito y el capítulo se reintenta sobre el estado anterior.

Refuerzo adicional, preventivo en lugar de detectivo: el hook `PreToolUse` de `.claude/hooks/denegar-escritura-estado.py`, registrado en `.claude/settings.json` para `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell|Agent|Task`. Un agente que lo intente no llega a escribir, en vez de descubrirse después de haberlo hecho. Deniega con exit 2, también ante una entrada que no entiende, porque cualquier otro código deja pasar la acción:

1. Cualquier escritura bajo `novelas/*/estado/` salvo `estado/deltas/NN.json`, que es la salida del `cronista`. La ruta se normaliza antes de comparar —contra `cwd`, sin `..`, sin mayúsculas, sin el prefijo `\\?\` ni los puntos y espacios finales que Win32 quita al escribir— y lo que no sabe normalizar, como un flujo alternativo, se deniega.
2. A cada rol de `.claude/agents/`, cualquier escritura fuera de sus salidas de §7.5.
3. A la sesión principal, cualquier escritura en el workspace salvo `runs/*/intervencion.md`.
4. Toda orden `Bash` o `PowerShell` que nombre `canon/…misterio` o `estado.db`.
5. Con `NOVELA_SESSION_ID` definida, que solo exportan el bucle y las sesiones del harness, cualquier subagente que no sea uno de los roles o el `canario` de `validators.md` §4.9.

Debajo quedan los `deny` de `settings.json` sobre `estado.db*`, `state.lock` y `sqlite3`, y los triggers, que cubren lo que el hook no normaliza: nombres cortos 8.3, uniones y enlaces simbólicos.

### 7.2 Frontmatter de capítulo

```yaml
---
capitulo: 7
titulo: "Lo que el agua no devuelve"
pov: per-elena-vidal
palabras: 3180
escenas: [esc-07-1, esc-07-2, esc-07-3]
pistas_plantadas: [pis-009]
pistas_pagadas: [pis-004]
hilos_abiertos: [hil-007]
hilos_cerrados: [hil-002]
version_canon: 3
version_plan: 2
run_id: r-20260921-0942
---
```

### 7.3 Informe de QA

Salida estructurada, nunca prosa libre: es lo único que se le pasa al escritor en un reintento.

```json
{
  "capitulo": 7,
  "agente": "continuista",
  "veredicto": "rechazado",
  "hallazgos": [
    {
      "tipo": "contradiccion_hecho",
      "gravedad": "alta",
      "referencia": "hec-014",
      "ubicacion": "escena esc-07-2, párrafo 4",
      "descripcion": "El faro aparece encendido; el libro de hechos lo declara inoperativo desde el capítulo 5.",
      "correccion_sugerida": "..."
    }
  ]
}
```

El subagente escribe el JSON en `qa/` y devuelve a la sesión orquestadora únicamente `veredicto` y el número de hallazgos por gravedad.

`veredicto` es `aprobado | rechazado | aprobado_con_reservas` y `gravedad` es `alta | media | baja`. `tipo` es un vocabulario cerrado, uno por productor: `novela validar` (`frontmatter_invalido`, `longitud_fuera_de_rango`, `pista_ausente`, `hilo_cerrado_sin_abrir`, `id_inexistente`), `continuista` (`contradiccion_hecho`, `contradiccion_temporal`, `contradiccion_personaje`, `contradiccion_canon`), `editor-estilo` (`prohibicion_estilo`, `desviacion_ritmo`, `voz_de_personaje`), `lector-suspense` (`tension_insuficiente`, `fair_play`, `previsibilidad`, `gancho_debil`) y `novela auditar` (`pista_huerfana`, `hilo_sin_cerrar`, `pista_falsa_sin_desmontar`, `revelacion_sin_pista`). Dos campos opcionales más: `puntuaciones`, que solo rellena el `lector-suspense` (`tension` de 1 a 10, `fair_play`, `coherencia` y `previsibilidad`), y `capitulo_sha256`, que no escribe ningún agente —un modelo no calcula un hash— sino `novela validar` en `qa/NN-validacion.json`, también cuando el capítulo pasa (RF-31).

### 7.4 Contrato de subagente

Cada fichero de `.claude/agents/` declara en su frontmatter lo permitido, y su cuerpo lo repite en prosa para el modelo:

```yaml
---
name: escritor
description: Escribe un capítulo a partir de su ficha de plan y del briefing generado. Invocar una vez por capítulo, después de novela briefing.
tools: Read, Write
model: opus
---
```

`tools` por agente:

| Agente | `tools` | Por qué |
|---|---|---|
| `arquitecto`, `trazador`, `escritor`, `continuista`, `lector-suspense`, `cronista`, `entrevistador` | `Read, Write` | Leen rutas que el briefing nombra y crean ficheros nuevos |
| `editor-estilo` | `Read, Edit, Write` | Único que modifica un fichero existente, `capitulos/NN.md` |

Ninguno tiene `Glob`, `Grep`, `Bash`, `Task`, `Skill`, `WebFetch` ni `WebSearch`. Cada ausencia hace mecánica una regla que si no sería solo una petición en el prompt:

- Sin `Glob` ni `Grep`, «no explores el workspace por tu cuenta» deja de depender de la obediencia del modelo (§6.3).
- Sin `Bash`, un agente no puede ejecutar el CLI y saltarse el orden del bucle.
- Sin `Task`, no puede delegar y crear un árbol de invocaciones fuera del presupuesto de §6.5.
- Sin `Skill`, no alcanza los plugins del repositorio, que son herramientas para desarrollar el harness y no forman parte del sistema que escribe novelas.

Reglas transversales del cuerpo de cada agente:

- Lee solo el briefing indicado y las rutas listadas en él.
- Escribe solo en las rutas listadas como salida.
- Devuelve a la sesión principal un informe de tres líneas como máximo.
- Ante ambigüedad, falla explícitamente en lugar de inventar.

Solo el `cronista` tiene `Write` sobre el delta de estado, y ningún agente escribe `estado.db` directamente: lo aplica `novela aplicar-delta`.

### 7.5 Entradas y salidas por subagente

Qué recibe cada agente en su briefing y qué escribe. El briefing lo compone `novela briefing` a partir de la receta del agente (§6.2); ninguna entrada se lee por exploración libre del workspace. El briefing no incrusta esquemas: el cuerpo de cada agente en `.claude/agents/` nombra el suyo, relativo a la raíz del repo, y `test_contratos.py` comprueba que existe (spec 0003, RF-24).

| Agente | Entradas | Salidas en disco | Retorno a la sesión |
|---|---|---|---|
| `arquitecto` | `config.yaml` (idea semilla, `parametros_obra`); su esquema, `backend/schemas/canon.schema.json` | `canon/premisa.md`, `canon/mundo.md`, `canon/estilo.md`, `canon/misterio.borrador.md`, `canon/personajes/*.md`. El `deny` de `Read` del misterio también deniega escribirlo, así que el briefing del `trazador`, que es su gate, valida el borrador con el resto del canon y lo promueve a `canon/misterio.md` | Lista de ids creados y conteo por tipo |
| `trazador` | `config.yaml`, `canon/*` **incluido** `misterio.md`; sus esquemas, `backend/schemas/escaleta.schema.json` y `plan-capitulo.schema.json` | `plan/escaleta.md`, `plan/capitulos/NN.md` | Nº de capítulos planificados, pistas plantadas/pagadas por acto |
| `escritor` | `plan/capitulos/NN.md`, `canon/premisa`, `canon/mundo`, `canon/estilo`, fichas de los personajes en escena, estado (personajes, conocimiento, hilos abiertos, objetos), resúmenes (§6.2), restricción de apertura. En reintento, además `qa/NN-*.json`. Su esquema, `backend/schemas/capitulo.schema.json`. **Nunca** `canon/misterio.md` | `capitulos/NN.md` con su frontmatter (§7.2) | Título, palabras, escenas |
| `continuista` | `capitulos/NN.md`, `canon/*` incluido `misterio.md`, estado (`libro_de_hechos`, `linea_temporal`, coartadas); su esquema, `backend/schemas/qa-informe.schema.json` | `qa/NN-continuidad.json` (§7.3) | `veredicto` y hallazgos por gravedad |
| `editor-estilo` | `capitulos/NN.md`, `canon/estilo.md` con sus párrafos canónicos y prohibiciones; su esquema, `backend/schemas/qa-informe.schema.json`. **Nunca** `canon/misterio.md` | `capitulos/NN.md` reescrito y `qa/NN-estilo.json` | `veredicto` y hallazgos por gravedad |
| `lector-suspense` | `capitulos/NN.md`, `canon/misterio.md`, `plan/escaleta.md`, estado (`pistas`, `conocimiento_lector`, `tension_real`); su esquema, `backend/schemas/qa-informe.schema.json` | `qa/NN-suspense.json` | Puntuaciones de tensión, fair play y previsibilidad |
| `cronista` | `capitulos/NN.md` aprobado, estado vigente; su esquema, `backend/schemas/delta.schema.json` | `estado/deltas/NN.json` | Nº de hechos e hilos del delta (no lleva pistas, §7.6) |
| `entrevistador` | El briefing de `novela brief preparar` (no el de `novela briefing`: no tiene receta ni está en `Agente`): ocasión, vocabularios, límites, reglas de procedencia, fragmentos marcados, borrador e informe anteriores y las entradas delimitadas; su esquema, `backend/schemas/brief-borrador.schema.json` | `brief/borrador.json` | Campos a `null` y preguntas, sin datos del destinatario |

`estado/deltas/NN.json` es la única entrada de `novela aplicar-delta`; ningún agente escribe `estado/estado.db`.

Las dos asimetrías de la tabla son deliberadas: `trazador`, `continuista` y `lector-suspense` ven el misterio porque su trabajo es verificarlo contra él; `escritor` y `editor-estilo` no, por §6.3. Y `editor-estilo` es el único agente además del `escritor` que reescribe `capitulos/NN.md` — por eso su salida de QA acompaña al texto en vez de sustituirlo.

### 7.6 Delta del cronista

`estado/deltas/NN.json` es la única entrada de `novela aplicar-delta`. Lo valida `backend/schemas/delta.schema.json`.

```json
{
  "schema_version": "1.0.0",
  "capitulo": 7,
  "linea_temporal": [
    { "escena": "esc-07-1", "capitulo": 7, "inicio": "dia 7, 21:00", "duracion_min": 40,
      "cita": "Aquella escena 1 del capítulo 7 empezó con el viento del norte." }
  ],
  "personajes": {
    "per-elena-vidal": { "ubicacion": "esc-puerto", "estado_fisico": "cansada", "estado_emocional": "alerta",
                         "condicion": "viva", "objetivo_activo": "saber quién apagó el faro", "ultima_aparicion": 7 }
  },
  "conocimiento": {
    "per-elena-vidal": [ { "hecho": "hec-007", "desde_capitulo": 7, "cita": "..." } ]
  },
  "conocimiento_lector": [ { "hecho": "hec-007", "desde_capitulo": 7 } ],
  "relaciones": [ { "de": "per-elena-vidal", "a": "per-tomas-reyes", "tipo": "sospecha", "intensidad": 0.3, "desde": 1 } ],
  "objetos": [ { "id": "obj-001", "poseedor": "per-tomas-reyes", "ubicacion": null, "capitulo_intro": 1, "relevancia": "alta" } ],
  "libro_de_hechos": [
    { "id": "hec-007", "texto": "La puerta de la linterna estaba forzada.", "capitulo": 7, "cita": "..." }
  ],
  "hilos": [
    { "id": "hil-003", "estado": "abierto", "abierto_en": 7, "cerrado_en": null, "descripcion": "..." }
  ],
  "resumen": {
    "linea": "Capítulo 7: Elena vuelve a la linterna.",
    "parrafo": "Elena sube al faro, discute con Tomás y oye a Inés.",
    "escena": { "esc-07-1": "Elena y Tomás en la casa del faro.", "esc-07-2": "Inés habla de más en el puerto." }
  }
}
```

Las colecciones append-only —`linea_temporal`, `conocimiento`, `conocimiento_lector`, `libro_de_hechos`— traen solo altas. Las mutables —`personajes`, `relaciones`, `objetos`— traen el estado nuevo de lo que el capítulo toca. `hilos` trae solo los que se abren o se cierran en el capítulo, y tiene que coincidir con `hilos_abiertos` e `hilos_cerrados` del frontmatter (RF-34).

No vienen `pistas` ni `metricas`, que `aplicar-delta` deriva del frontmatter y de los capítulos; ni `tension_real`, que la puntúa el `lector-suspense` en `qa/NN-suspense.json`; ni el cursor, que avanza `aplicar-delta` desde `capitulo`. `resumen` es obligatorio y trae las tres granularidades, con `escena` indexado por id de escena. Es lo que `aplicar-delta` renderiza a `memoria/resumenes/NN.md`.

Toda `cita` presente tiene que ser literal del cuerpo del capítulo tras normalizar a NFC y colapsar espacios (RF-33). En `libro_de_hechos` es obligatoria; en las otras tres, opcional.

---

## 8. Ciclo de vida

Slash commands, en `.claude/commands/`:

```
/novela-brief <slug> --ocasion boda     # solo novelas de regalo, en una sesión --setting-sources project
/novela-nueva <slug> --idea "..." --capitulos 24 --palabras 80000
/novela-nueva <slug> --brief
/novela-continuar <slug> [--capitulos N]
/novela-auditar <slug>
```

Herramientas Bash, invocadas por los anteriores o por ti directamente:

```
novela nueva <slug> --idea "..."   # árbol del workspace, config.yaml y estado.db
novela nueva <slug> --brief        # lo mismo, desde brief/brief.json
novela estado <slug> --breve
novela estado <slug> --json        # estado completo serializado, para inspección
novela briefing <slug> <cap> <agente>
novela validar <slug> <cap>
novela aplicar-delta <slug> <cap>
novela checkpoint <slug> <cap>
novela pendiente <slug>            # código de salida: 0 si quedan capítulos
novela auditar <slug>              # pistas huérfanas, hilos sin cerrar, fair play
novela exportar <slug> --formato epub
novela comprobar-entorno [--limpio]   # hook, python, settings.local.json y .env antes de lanzar
```

Fase de brief de una novela de regalo, antes de `novela nueva`. Cada subcomando toma el lock y deja una línea en el `harness.log` del run de arranque `(1, "arranque")`, sin valores del brief ni texto de las entradas; con `config.yaml` presente, salen con 1 y «brief cerrado: la novela ya existe»:

```
novela brief iniciar <slug> --ocasion hijo|pareja|boda|aniversario|jubilacion
novela brief entrada <slug> --tipo respuesta|texto-libre --fichero <ruta>   # imprime ent-NN
novela brief preparar <slug>       # runs/<run_id>/briefings/brief-RR-entrevistador.md · N tokens
novela brief validar <slug>        # brief/informe.json y, sin hallazgos, brief/brief.json
```

`preparar` ensambla el briefing del `entrevistador`: ocasión, vocabularios de `genero`, `tono` y `extension`, límites, reglas de procedencia, fragmentos marcados, borrador e informe anteriores si los hay, y las entradas. Cada entrada va entre `<<<ENTRADA ent-NN tipo=… marca=…>>>` y `<<<FIN ENTRADA ent-NN marca=…>>>`, precedida de un aviso fijo de que es dato y no instrucción; la marca son los 16 primeros hexadecimales del sha256 de `run_id`, id y texto, así que el texto no puede anticiparla, y si la contiene, `preparar` sale con 1. Las entradas `texto_libre` se parten en frases por línea y las que casan la lista cerrada de patrones de `slices/brief/entradas.py` («ignora», «a partir de ahora», «eres un», `novelas/`…) se listan como `ent-NN: líneas a, b`, sin su texto. Sale con 1 sin entradas o si el briefing pasa de 40.000 tokens a 3,5 caracteres por token. `RR` sube uno por briefing distinto dentro del run; si nada cambió desde el último, imprime su ruta sin escribir otro.

`novela nueva <slug> --brief` cierra la fase: sobre un workspace con `brief/brief.json` válido y sin `config.yaml` ni `estado.db`, completa el árbol y escribe `config.yaml` con 10 capítulos, `palabras_por_capitulo` `{objetivo, 1000, 1500}` según la extensión (`corta` 1.000, `media` 1.250, `larga` 1.500), `longitud_total_palabras` = 10 × objetivo, `subgenero` = `genero`, `restricciones_contenido` = `prohibidos.terminos` e `idea_semilla` generada del brief por `dominio/brief.py::idea_semilla`, sin texto de modelo. Con `--idea`, `--capitulos`, `--palabras` o `--subgenero` sale con 2; sin `brief.json`, con uno que no valida o con la novela ya creada, con 1, y ningún mensaje lleva valores del brief. Sin `--brief` nada cambia, y `--idea` sobre un workspace de brief sale con 1 como ante cualquier workspace existente. `nueva` no abre run: el primer `novela briefing <slug> 1 arquitecto` reutiliza el run de arranque de la entrevista, con su manifiesto de entonces, y comparte su `harness.log`.

`validar` comprueba primero la custodia: si el cuerpo de una entrada no casa con el sha256 de su frontmatter, sale con 4 sin escribir nada. Después pasa `brief/borrador.json` por cuatro gates de `slices/brief/gates.py`, en orden: esquema (`borrador_ausente` o `esquema_invalido` con la ruta del campo; si falla, nada más), faltantes (cada obligatorio a `null` y `rasgos` o `recuerdos` vacíos; `prohibidos.terminos: []` no falta), contradicciones (edad menor de 12 con `noir` o `thriller_psicologico`, o con tono `oscuro`, y un término vetado como palabra completa en un recuerdo o un rasgo) y procedencia (la entrada existe, la cita es literal tras NFC, espacios colapsados y minúsculas, nombre, rasgos y términos salen de su cita, los campos cerrados citan una `respuesta` y ninguna cita toca un fragmento marcado). Siempre escribe `brief/informe.json`; sin hallazgos, además `brief/brief.json` con la ocasión y las entradas, y sale con 0. Con hallazgos sale con 1 sin tocar el `brief.json` que hubiera, y la línea de log es `brief validar -> 1 · agente: <codigo>@<campo>; …` si el fallo es del borrador (esquema o procedencia) o `· usuario: …` si falta un dato o se contradice: el procedimiento decide con ese prefijo.

`iniciar` reclama el slug (1 si ya existe, 2 con otra ocasión) y crea `brief/entradas/`, `estado/`, `runs/` y `brief/inicio.json`. `entrada` lee el fichero como UTF-8 estricto sin BOM, lo normaliza (NFC, `\n`, sin caracteres de control salvo `\n` y `\t`) y lo escribe como `brief/entradas/ent-NN.md` con su sha256; sale con 2 si el fichero no existe, no es UTF-8, queda vacío o pasa de 20.000 caracteres, y con 1 si ya hay 20 entradas.

**Reanudación.** `/novela-continuar` empieza leyendo `checkpoints/latest.json` y repite el último paso no confirmado. Regla dura: el estado nunca se reconstruye desde una conversación previa, ni siquiera desde la sesión anterior de Claude Code.

**Parada.** Agotados los intentos de un gate, el procedimiento escribe `runs/<run_id>/intervencion.md` con el hallazgo y el briefing que lo produjo, y termina. No degrada la calidad en silencio.

---

## 9. Presupuesto

Dos límites distintos que conviene no mezclar: el techo de contexto por invocación (§6.5) y la cuota de uso por ventana, que es de lo que trata esta sección.

Con la suscripción desaparece el coste por llamada, pero no el límite: hay topes de uso por ventana. La consecuencia operativa es idéntica a la anterior, y por eso el diseño no cambia — checkpoint por capítulo y reanudación limpia siguen siendo el mecanismo central.

`novela budget` registra en `runs/quota.json` invocaciones y capítulos completados por ventana, para estimar cuánto queda antes del corte y decidir si merece la pena empezar otro capítulo o parar en un punto limpio.

Política de degradación, si se acerca el límite:

1. Normal: los cinco agentes del bucle por capítulo.
2. `editor-estilo` en lote, cada 3 capítulos.
3. `lector-suspense` solo en fronteras de acto y capítulos con revelación.
4. Solo `escritor` + `continuista` + `cronista`; edición y evaluación diferidas al cierre.
5. Parada limpia en checkpoint.

`continuista` y `cronista` no se degradan nunca. Sin el primero se acumulan contradicciones invisibles; sin el segundo se pierde el estado y el capítulo siguiente se escribe a ciegas.

---

## 10. Observabilidad

### 10.1 Instalación

La vía corta es el plugin de marketplace de Langfuse: se añade el marketplace, se instala el plugin y, al habilitarlo, pide `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` y `LANGFUSE_BASE_URL`, guardando la clave secreta en el llavero del sistema operativo. Requiere Python 3.9+ y `langfuse>=4.0,<5`.

```bash
claude plugin marketplace add langfuse/Claude-Observability-Plugin
claude plugin install langfuse-observability@langfuse-observability
```

El plugin está instalado en el ámbito de usuario y se habilita solo para el proyecto, en `.claude/settings.local.json` (`"enabledPlugins": {"langfuse-observability@langfuse-observability": true}`), que está en `.gitignore`: el opt-in es estar habilitado. Sus hooks son `Stop` y `SessionEnd`, y su log está en `~/.claude/state/langfuse_hook.log`. Necesita `uv` en el PATH, porque si no cae a `python3`, que en Windows puede ser el alias de la Microsoft Store. El bucle exporta `CC_LANGFUSE_TRACE_TAGS=<slug>`, que el plugin lee, para filtrar las trazas por novela. Con `--setting-sources project,local` el plugin carga, pero sus `pluginConfigs` solo se leen del ámbito de usuario, de `--settings` o de managed. Por eso la clave pública, y la URL si no es la de EU, van en el entorno de usuario de Windows (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL`); la secreta la sigue dando el llavero. En una organización de Langfuse creada desde el 2026-09-16, las APIs de lectura legadas (trazas, sesiones, scores) devuelven 410: las trazas se comprueban con `GET /api/public/v2/observations`, filtrando por `sessionId` y `tags`. `POST /api/public/scores`, el de §10.5, sí funciona.

`TRACE_TO_LANGFUSE` ya no habilita el trazado. Lo sigue leyendo el `ScoreSink` de `novela checkpoint` (§10.5), junto con las claves, del entorno del proceso o de `.env` en la raíz del repo, que git ignora. El entorno manda, y el `.env` no se carga en `os.environ`: sus claves no llegan a ningún hijo del CLI ni a la sesión de Claude Code. Ningún fichero versionado lleva claves.

### 10.2 Qué se traza realmente

El hook Stop se ejecuta después de cada respuesta, lee el transcript de la conversación, lo convierte en trazas y agrupa todos los turnos de una sesión bajo un `session_id` compartido. La estructura que llega a Langfuse es:

```
session          = una sesión de Claude Code
└── trace        = un turno  ("Claude Code - Turn N")
    └── generation = un mensaje del asistente
        └── tool   = cada llamada a herramienta, anidada
```

Esto **no** coincide con el mapa ideal de la rama 9 de la ontología (`session` = novela, `trace` = capítulo, `span` = agente). El diseño se adapta así:

- **Una sesión de Claude Code por capítulo**, en modo desatendido. Con eso, `session` ≈ capítulo y el turno principal contiene el bucle completo.
- **Cada delegación a un subagente aparece como un span de herramienta `Task`** anidado bajo la generación que lo invocó. Es el equivalente práctico del «span por agente».
- **Agrupación por novela** mediante etiquetas: el procedimiento añade `slug` y `run_id` al primer prompt del turno, de modo que la búsqueda a texto completo y los filtros reconstruyan la ejecución completa.

El `session_id` se fija desde fuera: el bucle genera un UUID por sesión, lo pasa como `claude --session-id` y lo exporta como `NOVELA_SESSION_ID`, y `novela` lo escribe en cada línea de `harness.log` (`sesion=<uuid>`). Cada paso del log enlaza así con su traza.

### 10.3 Lo que el trazado no cubre

Los ficheros de contexto de sesión no se capturan: lo que `CLAUDE.md`, las skills o el contexto autocargado aportaron al system prompt efectivo queda fuera. Se ve la conversación y las llamadas a herramientas, no el contexto ensamblado.

Por eso los briefings de §6.1 no son un lujo: son el registro de contexto que Langfuse no puede darte, y `runs/<run_id>/manifest.json` es lo que permite correlacionar una traza con la versión de receta, el sha de commit y las versiones de canon y plan vigentes en ese momento.

### 10.4 Versionado de prompts

Los prompts de los agentes son `.claude/agents/*.md` y se versionan con git. El manifiesto de cada run registra el sha del commit; comparar dos ejecuciones es comparar dos shas. No hace falta Langfuse Prompt Management para esto, y añadirlo introduciría una segunda fuente de verdad sobre el mismo texto.

### 10.5 Evaluación

Los scores no los emite el hook: los escribe `novela` contra la API de Langfuse al cerrar cada capítulo, tomándolos de `qa/NN-suspense.json` y del resultado de los gates. Métricas por capítulo: `coherencia`, `continuidad`, `tension`, `longitud`, `fair_play`, `estilo`. `tension`, `fair_play` y `coherencia` son las `puntuaciones` del `lector-suspense`; `continuidad` y `estilo` salen del veredicto de `qa/NN-continuidad.json` y `qa/NN-estilo.json` (1, 0,5 o 0); `longitud` es `1 − |palabras/objetivo − 1|`. Los emite `novela checkpoint` después de escribir el checkpoint, con un id por capítulo y métrica para que reemitir sustituya, y un fallo de Langfuse queda en `harness.log` sin impedir el cierre. Las claves, del entorno o de `.env` (§10.1).

El evaluador de sesión (LLM como juez) compara ejecuciones completas y devuelve puntos a mejorar y mejoras propuestas.

---

## 11. Backend y frontend

### 11.1 Backend (`backend/`)

Python 3.12. Dos caras sobre el mismo código:

- **CLI `novela`** (Typer): lo que invoca el orquestador. Es quien escribe en el workspace.
- **API FastAPI** (`backend/api/`): solo lectura, para el frontend. Sirve el estado, los capítulos, los manifiestos y lo que el panel necesita de la configuración, del plan y de los checkpoints. Los capítulos y los manifiestos salen del disco tal cual; el estado se serializa desde `estado.db` con los mismos modelos Pydantic, abriendo la base en modo lectura.

La API **no lanza agentes ni escribe en el workspace**. No hay verbo de escritura: mutar una novela es trabajo del orquestador a través del CLI. Si un endpoint pareciera necesitar escribir, lo correcto es añadir un subcomando al CLI, no un `POST` a la API.

Los modelos de respuesta son los mismos Pydantic de `backend/novela/dominio/`. Una sola ontología, un solo sitio donde cambiarla.

```
GET /novelas                              slugs con su cursor
GET /novelas/{slug}/estado                estado serializado desde estado.db
GET /novelas/{slug}/capitulos             índice con frontmatter
GET /novelas/{slug}/capitulos/{n}         markdown del capítulo
GET /novelas/{slug}/runs/{run_id}         manifest.json
GET /novelas/{slug}/config                Config de config.yaml, validado
GET /novelas/{slug}/escaleta              Escaleta de plan/escaleta.md; 404 si falta o no valida
GET /novelas/{slug}/checkpoint            checkpoints/latest.json, o null
GET /novelas/{slug}/runs                  manifiestos por run_id ascendente
GET /novelas/{slug}/runs/{run_id}/log     TramoDeLog de harness.log desde ?desde=<byte>
```

`…/escaleta` se valida con el `num_capitulos` de `config.yaml` y se devuelve ya serializada: la validación de respuesta de FastAPI no lleva ese contexto y rechazaría el modelo. `…/log` salta a `desde` y lee como mucho 1 MiB: devuelve líneas completas desde el primer límite de línea igual o posterior, hasta 65 536 bytes salvo una línea sola mayor, y `hasta` es el siguiente `desde`. Responde 422 a un `desde` negativo o no entero, 416 si pasa del tamaño del log, 404 si el run no existe, y un tramo vacío con `modificado: null` si el run aún no tiene log.

Se arranca desde `backend/` con `uv run uvicorn api.main:app --reload`.

**Puesta en marcha del harness**, una vez por máquina. Cada paso tiene su comprobación, porque si falla en silencio el síntoma aparece más tarde con otra cara:

| # | Paso | Comprobación | Si no se hace |
|---|---|---|---|
| 1 | `uv` en el PATH de usuario, de forma persistente | `uv --version` en una terminal nueva, en Git Bash y en PowerShell | El hook del plugin de Langfuse cae a `python3` y falla; `uv tool` no existe |
| 2 | `uv tool install --editable ./backend` desde la raíz | `novela --help` en Git Bash y en PowerShell | Toda orden `novela` del procedimiento falla |
| 3 | Abrir `claude` en la raíz del repo y aceptar el diálogo de confianza | `hasTrustDialogAccepted: true` para el proyecto en `~/.claude.json` | `claude -p` ignora el `allow` y el bucle no avanza |
| — | `python` resuelve a un intérprete real, no al alias de la Microsoft Store | `python -c "import sys; print(sys.executable)"` | El hook falla abierto: sale con un código distinto de 2 y la escritura pasa |
| — | Con Git para Windows instalado por usuario, `CLAUDE_CODE_GIT_BASH_PATH` en el entorno de usuario, apuntando a su `bin\bash.exe` | `claude -p "responde ok" --output-format stream-json --verbose`: el evento `init` lista `Bash` | La sesión solo tiene PowerShell: `Bash(novela:*)` no casa, y los hooks corren en PowerShell y fallan |
| — | Con App Control (Device Guard), `novela --help` responde | `novela --help` | El `novela.exe` de `uv tool` sale con «Permission denied». El de `backend\.venv\Scripts` sí corre, y esa carpeta va por delante en el PATH |

Si `python` no resuelve, se desactiva el alias en «Alias de ejecución de aplicaciones» o se pone Python 3.12 por delante en el PATH; el comando del hook no se cambia a una ruta absoluta. `novela comprobar-entorno` comprueba `python`, el script del hook, `settings.local.json` y `.env` antes de cada bucle.

### 11.2 Frontend (`frontend/`)

Vite + TypeScript + Three.js. Es **solo lectura**: no lanza agentes ni escribe en el workspace.

- **Lanzar novela**: formulario que prepara la orden `/novela-nueva` —la idea entre comillas simples, con cada `'` como `'\''`, y capítulos y palabras solo si se rellenan— y las órdenes que abren la sesión del harness, para copiarlas. No escribe ningún fichero ni pide a la API nada distinto de `GET /novelas`: el `config.yaml` lo escribe `novela nueva` desde `config/default.yaml` y los flags.
- **Progreso**: consulta la API por *polling*; muestra cursor, capítulos cerrados según el checkpoint, palabras, curva de tensión real contra objetivo con actos y puntos de giro —y su tabla—, hilos abiertos y runs.
- **Lectura**: una estantería 3D con un volumen por capítulo —cerrado, en curso o pendiente según el checkpoint y el índice—, y su lista HTML equivalente, con el estado también como texto y el mismo teclado; sin WebGL queda solo la lista. Solo se leen los capítulos cerrados: el lector quita el frontmatter y muestra el markdown sin HTML, enlaces ni imágenes, que quedan como texto.

**Identidad visual** (spec 0004, D21 a D28). El panel lleva la marca de Qaracter con WCAG 2.1 AA. Todos los colores, familias tipográficas, radios, sombras y medidas son propiedades CSS de `frontend/src/shared/marca/tokens.css`, el único fichero con colores literales; los componentes solo usan roles semánticos, y la escena y la gráfica leen esos mismos roles de las propiedades computadas. Los tonos vivos de la marca quedan para lo decorativo y el texto usa tonos derivados que cumplen AA; `pares.ts` declara los pares en uso y un test recalcula su contraste desde `tokens.css`. El logo es el PNG oficial, sin retocar, y se muestra siempre dentro de un contenedor con las esquinas redondeadas al 22 % del lado: solo `logo.ts` puede importarlo, y el favicon se deriva de él con las esquinas ya recortadas. La fuente display y los iconos se sirven desde `frontend/`, con su licencia al lado. Sin modo oscuro ni selector de idioma.

Contrato de acoplamiento: el frontend consume lo que la API devuelve tal cual. Si necesita un dato que no está en el estado —la configuración, la escaleta, el checkpoint—, se sirve desde la API con su modelo de dominio, no se calcula en el frontend ni se mete en el estado, que es otra rama de contexto.

---

## 12. Supuestos y decisiones abiertas

1. **Sin temperatura, la variación depende del prompt.** La restricción de apertura por capítulo (§2.2) es una mitigación no probada. Si tras seis o siete capítulos la prosa converge, la siguiente palanca es variar el modelo del `escritor` entre capítulos o inyectar una consigna de estilo rotatoria desde el plan.
2. **Cerrado (spec 0003): el `session_id` se fija desde fuera.** `claude --session-id <uuid>` existe. El bucle genera un UUID por sesión, se lo pasa a `claude` y lo exporta como `NOVELA_SESSION_ID`, y `novela` añade `sesion=<uuid>` a cada línea de `harness.log`: cada paso enlaza con su traza. No va al manifiesto, porque un capítulo reanudado tiene varias sesiones y un solo manifiesto.
3. **Contexto de la sesión orquestadora.** Las cuatro reglas de §2.4 y la aritmética de §6.5 son la hipótesis de que un capítulo por sesión basta. Si en la práctica el orquestador aguanta tres o cuatro, el modo desatendido se abarata; si no aguanta ni uno completo, hay que partir el bucle en dos comandos.
4. **`indice_recuperable` no existe.** La rama 5 de `docs/definitions.md` lo nombra y nada lo materializa. La consulta puntual y retrospectiva —«¿en qué escena se vio por última vez `obj-011`?», «¿dónde se habló de una llave oxidada?»— solo se responde hoy cargando capítulos en el briefing, dejando que el agente explore por su cuenta (contra el principio 7) o conformándose con resúmenes que ya han perdido el detalle que la pregunta busca. Con 24 capítulos los resúmenes jerárquicos bastan y no hay presión de contexto medida: el índice se justificaría por **capacidad de consulta, no por ahorro de tokens**, y mal usado los aumenta. La dirección acordada, si se aborda, es híbrida sobre `estado.db` y por fases, porque esas preguntas no son la misma: exacta (tabla `menciones(entidad_id, escena_id, capitulo)` que el `cronista` emite en el delta), léxica (FTS5 sobre `memoria/resumenes/`) y semántica (un vector por escena con un modelo de embeddings **local** —la regla de «ningún proveedor ni SDK de modelos» se mantiene— y producto escalar en numpy, que sobre ~200 escenas no necesita índice vectorial). Las dos primeras no añaden dependencias; la tercera sí, y es la única que conviene medir antes de darla por buena. Los aciertos exactos van primero y sin fusionar; el resto se ordena con Reciprocal Rank Fusion, que suma rangos y no obliga a normalizar `bm25()` contra un coseno. Quien consulta es el orquestador, mediante un subcomando con tope de resultados y de tokens que deja rastro en `runs/`: dar a los agentes una herramienta de búsqueda libre rompe el techo de §6.5 y la regla de no explorar el workspace. **El orden es exacta y léxica primero, semántica solo después de medir** cuántas consultas reales se quedan sin responder: de las tres preguntas de ejemplo, la primera la cierra la exacta y la segunda la léxica, y solo la tercera necesita embeddings. Si esa medición la justifica, la elección acordada es `multilingual-e5-small` (384 dimensiones) servido por `fastembed` sobre `onnxruntime`, no por `sentence-transformers`: la vía habitual arrastra PyTorch, unos 2 GB, que sería con diferencia la dependencia más pesada del sistema y entraría para la capa más prescindible; ONNX deja el coste en unos 200 MB, en CPU y sin GPU. Dos detalles que no se ven hasta que fallan: los modelos E5 exigen el prefijo `query: ` al consultar y `passage: ` al indexar —omitirlos degrada la calidad sin dar ningún error— y el modelo va fijado por versión en el lockfile, porque un vector calculado con otra revisión no es comparable con los ya guardados; por eso `novela reindexar` existe desde el primer día. La elección concreta conviene revisarla en el momento de implementarla: lo que no cambia son los criterios —local, multilingüe, pequeño y sin torch—.
5. **El escritor no reescribe capítulos anteriores.** Si un gate detecta que un problema del capítulo 7 nace del 5, el harness para y pide intervención. La reescritura retroactiva automática invalidaría el estado y los resúmenes de todo lo intermedio.
6. **Cerrado (spec 0004): el panel ve la actividad del bucle.** `estado.db` solo cambia en `aplicar-delta`, así que el estado no distingue un capítulo en curso de un bucle colgado. Lo distingue `runs/<run_id>/harness.log`, que el CLI vuelca línea a línea (spec 0001, RF-27): la API sirve `GET …/runs` y `GET …/runs/{run_id}/log?desde=<byte>` (§11.1), y el panel encadena tramos guardando el `hasta` devuelto. Leer así un fichero que crece no deja estado en el servidor ni suscripción que caducar; SSE o WebSocket serían un segundo transporte para el patrón que el panel ya usa en todo lo demás.
7. **Cerrado (spec 0003): las tres barreras de contención están puestas.** Los siete `.claude/agents/*.md` con el `tools` de §7.4 y un test de contrato que falla si derivan; el `deny` de `Read` sobre `canon/misterio.md` en `.claude/settings.json`, viable porque `novela briefing` incrusta el misterio; y el hook `PreToolUse` de §7.1, que se dispara también para las llamadas de un subagente (experimento E-1 de la spec 0003). Los plugins de desarrollo viven en el ámbito de usuario. Lo que sigue es el razonamiento que llevó ahí. **Antes, enunciadas y no puestas.** `.claude/` contiene hoy un único fichero, `settings.json`, con plugins de desarrollo: no hay definiciones de agente, ni hooks, ni permisos. El invariante 3 se sostiene solo sobre el aborto de `novela briefing`, y el 1 solo sobre los triggers append-only de `estado.db`. La dificultad es que los permisos de Claude Code valen para la sesión entera y no por subagente, así que un `deny` sobre `canon/misterio.md` rompería a los tres agentes que sí lo necesitan —`trazador`, `continuista` y `lector-suspense`—; lo que lo hace viable es que `novela briefing` **incruste** el contenido del misterio en el briefing de esos tres, con lo que ningún agente necesita abrir el fichero y la regla pasa a ser una línea igual para los siete, con el coste de contexto contando además dentro del presupuesto que §6.5 verifica antes de invocar. El resto de la contención es material: los siete `.claude/agents/*.md` con el `tools` de §7.4, los dos hooks que `CLAUDE.md` da por existentes (`PreToolUse` de escritura, `Stop` de trazado), los plugins de desarrollo fuera del fichero versionado y un test de contrato que falle si un agente gana una herramienta prohibida. Queda por verificar si `PreToolUse` se dispara para las llamadas de herramienta de un subagente: si no lo hiciera, el invariante 1 se queda solo con los triggers. Mientras nada de esto exista, §6.3 y §7.4 describen el contrato de los agentes, no lo que hay en disco.
8. **El arranque pasa por un humano.** El formulario del panel prepara la orden `/novela-nueva` para copiar en la sesión del harness, porque la API no escribe y FastAPI no puede invocar modelos (§2, «fuera del stack»); el `config.yaml` lo escribe `novela nueva` desde los flags, así que no hay dos fuentes de los mismos parámetros (spec 0004). Es la única costura manual del diseño y está en el primer paso que da cualquiera. La dirección acordada es una cola en disco fuera de los workspaces —`novelas/_cola/`, con `pendientes/`, `en-curso/` y `hechas/`, donde el prefijo `_` no es un slug válido y la separación se sostiene por construcción—: la API gana un `POST /cola` que valida y encola de forma atómica, su única escritura, con tope de pendientes porque cada solicitud aceptada acabará gastando cuota; el CLI gana `novela cola tomar` y `novela cola cerrar`; y el `config.yaml` lo escribe siempre el backend, venga de la cola o de los flags. Quien vacía la cola es un supervisor de quince líneas de shell, el bucle desatendido de §2.3 con una fuente de trabajo delante: se queda en shell porque solo decide **qué novela empieza**, no qué paso sigue a un gate, y meterlo en el CLI borraría esa frontera. Un `run.sh` levanta API y supervisor juntos, de modo que no exista el estado «panel en pie, nadie ejecutando» ni, con él, un segundo camino de arranque que mantener. Si se adopta, la frase «no hay verbo de escritura» de §11.1 pasa a «la API no muta una novela», y con ella la regla equivalente de `AGENTS.md`.
