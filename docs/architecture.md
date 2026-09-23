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
| Export | `markdown` + `ebooklib` | Salida a `.md` único y `.epub` |

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

La variación creativa que antes se buscaba con temperatura alta se compensa por prompt: el `escritor` recibe en su briefing una restricción de apertura distinta por capítulo (con qué tipo de frase empieza, qué registro domina la primera escena) para evitar que 24 capítulos abran igual. Es la mitigación disponible y conviene medir si basta.

### 2.3 Modo desatendido

El bucle puede correr sin supervisión invocando Claude Code en modo headless:

```bash
while novela pendiente <slug>; do
  claude -p "/novela-continuar <slug> --capitulos 1" || break
done
```

Un capítulo por sesión mantiene el contexto del orquestador pequeño y acota el daño de un fallo. El `|| break` es deliberado: ante un error, el sistema para y deja el checkpoint, no insiste.

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
│   ├── settings.json             # permisos; TRACE_TO_LANGFUSE y claves van en el local, ver §10
│   ├── settings.local.json       # claves de Langfuse — en .gitignore
│   ├── agents/                   # un fichero por subagente
│   │   ├── arquitecto.md
│   │   ├── trazador.md
│   │   ├── escritor.md
│   │   ├── continuista.md
│   │   ├── editor-estilo.md
│   │   ├── lector-suspense.md
│   │   └── cronista.md
│   ├── commands/                 # los procedimientos del orquestador
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
│   │   │   ├── briefing/         # cmd.py · assemble.py · recipes.py · test_briefing.py
│   │   │   ├── validacion/       # cmd.py · gates.py · test_gates.py
│   │   │   ├── delta/            # cmd.py · apply.py · violaciones.py · test_delta.py
│   │   │   ├── checkpoint/
│   │   │   ├── auditoria/        # pistas huérfanas, hilos abiertos
│   │   │   ├── presupuesto/      # ventana de uso y degradación
│   │   │   └── export/           # cmd.py · markdown.py · epub.py
│   │   │
│   │   ├── dominio/              # la ontología como código; sin I/O, sin framework
│   │   │   ├── config.py         # rama 1
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
│   │   └── qa-informe.schema.json
│   │
│   └── tests/                    # solo lo transversal; el test de un slice vive con él
│       ├── test_api.py
│       ├── test_contratos.py     # Pydantic ↔ schemas/
│       └── fixtures/             # workspaces sintéticos, sin llamadas a modelo
│
├── frontend/                     # Vite + TypeScript + Three.js, solo lectura
│   ├── package.json
│   ├── vite.config.ts
│   └── src/                      # package by feature, ver §3.0
│       ├── features/
│       │   ├── lanzar/           # formulario, generación de config.yaml
│       │   ├── progreso/         # cursor, curva de tensión, hilos abiertos, cuota
│       │   └── lectura/          # escena Three.js, navegación 3D del libro
│       ├── shared/               # cliente de la API, tipos, componentes base
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
│   ├── 01.json
│   └── latest.json
│
├── runs/
│   └── <run_id>/
│       ├── manifest.json         # sha de commit, versión de recetas, sesión de Claude Code
│       ├── briefings/            # el contexto exacto de cada invocación, ver §6.1
│       │   ├── 01-escritor.md
│       │   └── 01-continuista.md
│       └── harness.log
│
└── export/
    ├── novela.md
    └── novela.epub
```

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

Conviene ser exacto sobre qué hace `tools`, porque de ello depende el invariante 3: restringe **capacidad y descubrimiento**, no rutas. `Read` no lleva lista blanca de ficheros, así que un agente que conozca la ruta puede leerla. Restringir por ruta exige una regla `deny` en los permisos, que hoy no existe. §12.7 recoge por qué no basta añadirla y qué la hace viable para los siete agentes a la vez.

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

Refuerzo adicional: un hook `PreToolUse` en `.claude/hooks/denegar-escritura-estado.py` **deniega** cualquier `Write` o `Edit` cuya ruta caiga bajo `estado/`. Es preventivo en lugar de detectivo: un subagente que lo intente no llega a escribir, en vez de descubrirse después de haberlo hecho.

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
| `arquitecto`, `trazador`, `escritor`, `continuista`, `lector-suspense`, `cronista` | `Read, Write` | Leen rutas que el briefing nombra y crean ficheros nuevos |
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

Qué recibe cada agente en su briefing y qué escribe. El briefing lo compone `novela briefing` a partir de la receta del agente (§6.2); ninguna entrada se lee por exploración libre del workspace.

| Agente | Entradas | Salidas en disco | Retorno a la sesión |
|---|---|---|---|
| `arquitecto` | `config.yaml` (idea semilla, `parametros_obra`) | `canon/premisa.md`, `canon/mundo.md`, `canon/estilo.md`, `canon/misterio.md`, `canon/personajes/*.md` | Lista de ids creados y conteo por tipo |
| `trazador` | `config.yaml`, `canon/*` **incluido** `misterio.md` | `plan/escaleta.md`, `plan/capitulos/NN.md` | Nº de capítulos planificados, pistas plantadas/pagadas por acto |
| `escritor` | `plan/capitulos/NN.md`, `canon/premisa`, `canon/mundo`, `canon/estilo`, fichas de los personajes en escena, estado (personajes, conocimiento, hilos abiertos, objetos), resúmenes (§6.2), restricción de apertura. En reintento, además `qa/NN-*.json`. **Nunca** `canon/misterio.md` | `capitulos/NN.md` con su frontmatter (§7.2) | Título, palabras, escenas |
| `continuista` | `capitulos/NN.md`, `canon/*` incluido `misterio.md`, estado (`libro_de_hechos`, `linea_temporal`, coartadas) | `qa/NN-continuidad.json` (§7.3) | `veredicto` y hallazgos por gravedad |
| `editor-estilo` | `capitulos/NN.md`, `canon/estilo.md` con sus párrafos canónicos y prohibiciones. **Nunca** `canon/misterio.md` | `capitulos/NN.md` reescrito y `qa/NN-estilo.json` | `veredicto` y hallazgos por gravedad |
| `lector-suspense` | `capitulos/NN.md`, `canon/misterio.md`, `plan/escaleta.md`, estado (`pistas`, `conocimiento_lector`, `tension_real`) | `qa/NN-suspense.json` | Puntuaciones de tensión, fair play y previsibilidad |
| `cronista` | `capitulos/NN.md` aprobado, estado vigente | `estado/deltas/NN.json` | Nº de hechos, hilos y pistas del delta |

`estado/deltas/NN.json` es la única entrada de `novela aplicar-delta`; ningún agente escribe `estado/estado.db`.

Las dos asimetrías de la tabla son deliberadas: `trazador`, `continuista` y `lector-suspense` ven el misterio porque su trabajo es verificarlo contra él; `escritor` y `editor-estilo` no, por §6.3. Y `editor-estilo` es el único agente además del `escritor` que reescribe `capitulos/NN.md` — por eso su salida de QA acompaña al texto en vez de sustituirlo.

---

## 8. Ciclo de vida

Slash commands, en `.claude/commands/`:

```
/novela-nueva <slug> --idea "..." --capitulos 24 --palabras 80000
/novela-continuar <slug> [--capitulos N]
/novela-auditar <slug>
```

Herramientas Bash, invocadas por los anteriores o por ti directamente:

```
novela nueva <slug> --idea "..."   # árbol del workspace, config.yaml y estado.db
novela estado <slug> --breve
novela estado <slug> --json        # estado completo serializado, para inspección
novela briefing <slug> <cap> <agente>
novela validar <slug> <cap>
novela aplicar-delta <slug> <cap>
novela checkpoint <slug> <cap>
novela pendiente <slug>            # código de salida: 0 si quedan capítulos
novela auditar <slug>              # pistas huérfanas, hilos sin cerrar, fair play
novela exportar <slug> --formato epub
```

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

La alternativa manual es un script en `~/.claude/hooks/langfuse_hook.py` registrado como hook `Stop` en `~/.claude/settings.json`, con las claves en el `settings.json` del proyecto. El trazado es opt-in por proyecto mediante `TRACE_TO_LANGFUSE`, que debe ser exactamente la cadena `"true"`.

El fichero con las claves va en `.gitignore`.

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

Merece la pena verificar si tu instalación permite fijar el `session_id` desde el entorno; si es así, usar `<slug>-<run_id>` y recuperar el mapa original de la ontología sin más.

### 10.3 Lo que el trazado no cubre

Los ficheros de contexto de sesión no se capturan: lo que `CLAUDE.md`, las skills o el contexto autocargado aportaron al system prompt efectivo queda fuera. Se ve la conversación y las llamadas a herramientas, no el contexto ensamblado.

Por eso los briefings de §6.1 no son un lujo: son el registro de contexto que Langfuse no puede darte, y `runs/<run_id>/manifest.json` es lo que permite correlacionar una traza con la versión de receta, el sha de commit y las versiones de canon y plan vigentes en ese momento.

### 10.4 Versionado de prompts

Los prompts de los agentes son `.claude/agents/*.md` y se versionan con git. El manifiesto de cada run registra el sha del commit; comparar dos ejecuciones es comparar dos shas. No hace falta Langfuse Prompt Management para esto, y añadirlo introduciría una segunda fuente de verdad sobre el mismo texto.

### 10.5 Evaluación

Los scores no los emite el hook: los escribe `novela` contra la API de Langfuse al cerrar cada capítulo, tomándolos de `qa/NN-suspense.json` y del resultado de los gates. Métricas por capítulo: `coherencia`, `continuidad`, `tension`, `longitud`, `fair_play`, `estilo`.

El evaluador de sesión (LLM como juez) compara ejecuciones completas y devuelve puntos a mejorar y mejoras propuestas.

---

## 11. Backend y frontend

### 11.1 Backend (`backend/`)

Python 3.12. Dos caras sobre el mismo código:

- **CLI `novela`** (Typer): lo que invoca el orquestador. Es quien escribe en el workspace.
- **API FastAPI** (`backend/api/`): solo lectura, para el frontend. Sirve el estado, los capítulos y los manifiestos. Los capítulos y los manifiestos salen del disco tal cual; el estado se serializa desde `estado.db` con los mismos modelos Pydantic, abriendo la base en modo lectura.

La API **no lanza agentes ni escribe en el workspace**. No hay verbo de escritura: mutar una novela es trabajo del orquestador a través del CLI. Si un endpoint pareciera necesitar escribir, lo correcto es añadir un subcomando al CLI, no un `POST` a la API.

Los modelos de respuesta son los mismos Pydantic de `backend/novela/dominio/`. Una sola ontología, un solo sitio donde cambiarla.

```
GET /novelas                              slugs con su cursor
GET /novelas/{slug}/estado                estado serializado desde estado.db
GET /novelas/{slug}/capitulos             índice con frontmatter
GET /novelas/{slug}/capitulos/{n}         markdown del capítulo
GET /novelas/{slug}/runs/{run_id}         manifest.json
```

Se arranca desde `backend/` con `uv run uvicorn api.main:app --reload`.

### 11.2 Frontend (`frontend/`)

Vite + TypeScript + Three.js. Es **solo lectura**: no lanza agentes ni escribe en el workspace.

- **Lanzar novela**: formulario que produce un `config.yaml` y deja preparado el comando `/novela-nueva` para copiar.
- **Progreso**: consulta la API por *polling*; muestra cursor, curva de tensión real contra objetivo, hilos abiertos y capítulos completados.
- **Lectura**: navegación 3D sobre los capítulos generados.

Contrato de acoplamiento: el frontend consume lo que la API devuelve tal cual. Si necesita un dato que no está en el estado, se añade al estado, no se calcula en el frontend.

---

## 12. Supuestos y decisiones abiertas

1. **Sin temperatura, la variación depende del prompt.** La restricción de apertura por capítulo (§2.2) es una mitigación no probada. Si tras seis o siete capítulos la prosa converge, la siguiente palanca es variar el modelo del `escritor` entre capítulos o inyectar una consigna de estilo rotatoria desde el plan.
2. **El `session_id` del hook.** El mapa de §10.2 asume que no se puede fijar desde fuera. Compruébalo: si se puede, la correlación con la ontología es directa y el apartado se simplifica.
3. **Contexto de la sesión orquestadora.** Las cuatro reglas de §2.4 y la aritmética de §6.5 son la hipótesis de que un capítulo por sesión basta. Si en la práctica el orquestador aguanta tres o cuatro, el modo desatendido se abarata; si no aguanta ni uno completo, hay que partir el bucle en dos comandos.
4. **`indice_recuperable` no existe.** La rama 5 de `docs/definitions.md` lo nombra y nada lo materializa. La consulta puntual y retrospectiva —«¿en qué escena se vio por última vez `obj-011`?», «¿dónde se habló de una llave oxidada?»— solo se responde hoy cargando capítulos en el briefing, dejando que el agente explore por su cuenta (contra el principio 7) o conformándose con resúmenes que ya han perdido el detalle que la pregunta busca. Con 24 capítulos los resúmenes jerárquicos bastan y no hay presión de contexto medida: el índice se justificaría por **capacidad de consulta, no por ahorro de tokens**, y mal usado los aumenta. La dirección acordada, si se aborda, es híbrida sobre `estado.db` y por fases, porque esas preguntas no son la misma: exacta (tabla `menciones(entidad_id, escena_id, capitulo)` que el `cronista` emite en el delta), léxica (FTS5 sobre `memoria/resumenes/`) y semántica (un vector por escena con un modelo de embeddings **local** —la regla de «ningún proveedor ni SDK de modelos» se mantiene— y producto escalar en numpy, que sobre ~200 escenas no necesita índice vectorial). Las dos primeras no añaden dependencias; la tercera sí, y es la única que conviene medir antes de darla por buena. Los aciertos exactos van primero y sin fusionar; el resto se ordena con Reciprocal Rank Fusion, que suma rangos y no obliga a normalizar `bm25()` contra un coseno. Quien consulta es el orquestador, mediante un subcomando con tope de resultados y de tokens que deja rastro en `runs/`: dar a los agentes una herramienta de búsqueda libre rompe el techo de §6.5 y la regla de no explorar el workspace. **El orden es exacta y léxica primero, semántica solo después de medir** cuántas consultas reales se quedan sin responder: de las tres preguntas de ejemplo, la primera la cierra la exacta y la segunda la léxica, y solo la tercera necesita embeddings. Si esa medición la justifica, la elección acordada es `multilingual-e5-small` (384 dimensiones) servido por `fastembed` sobre `onnxruntime`, no por `sentence-transformers`: la vía habitual arrastra PyTorch, unos 2 GB, que sería con diferencia la dependencia más pesada del sistema y entraría para la capa más prescindible; ONNX deja el coste en unos 200 MB, en CPU y sin GPU. Dos detalles que no se ven hasta que fallan: los modelos E5 exigen el prefijo `query: ` al consultar y `passage: ` al indexar —omitirlos degrada la calidad sin dar ningún error— y el modelo va fijado por versión en el lockfile, porque un vector calculado con otra revisión no es comparable con los ya guardados; por eso `novela reindexar` existe desde el primer día. La elección concreta conviene revisarla en el momento de implementarla: lo que no cambia son los criterios —local, multilingüe, pequeño y sin torch—.
5. **El escritor no reescribe capítulos anteriores.** Si un gate detecta que un problema del capítulo 7 nace del 5, el harness para y pide intervención. La reescritura retroactiva automática invalidaría el estado y los resúmenes de todo lo intermedio.
6. **El progreso que ve el panel es de grano grueso.** `estado.db` solo cambia en `aplicar-delta`, al final del capítulo: durante los minutos que dura uno, el *polling* de §11.2 devuelve lo mismo una y otra vez, y un capítulo en curso no se distingue de un bucle colgado. El dato que falta ya está en disco —`runs/<run_id>/harness.log` se escribe durante la ejecución— y nadie lo sirve. La dirección acordada son dos `GET` más: el listado de `run_id` del workspace, porque hoy no hay forma de descubrir el vigente, y un tramo del log desde un desplazamiento en bytes, con tope por respuesta, que el cliente encadena guardando el desplazamiento devuelto y descartando la línea incompleta del final. Leer así un fichero que crece no deja estado en el servidor ni suscripción que caducar; SSE o WebSocket serían un segundo transporte para el patrón que el panel ya usa en todo lo demás. Antes de escribir nada hay que comprobar que el harness vacía el buffer línea a línea: si volcara el log al final, esto no sirve de nada.
7. **Las tres barreras de contención están enunciadas, no puestas.** `.claude/` contiene hoy un único fichero, `settings.json`, con plugins de desarrollo: no hay definiciones de agente, ni hooks, ni permisos. El invariante 3 se sostiene solo sobre el aborto de `novela briefing`, y el 1 solo sobre los triggers append-only de `estado.db`. La dificultad es que los permisos de Claude Code valen para la sesión entera y no por subagente, así que un `deny` sobre `canon/misterio.md` rompería a los tres agentes que sí lo necesitan —`trazador`, `continuista` y `lector-suspense`—; lo que lo hace viable es que `novela briefing` **incruste** el contenido del misterio en el briefing de esos tres, con lo que ningún agente necesita abrir el fichero y la regla pasa a ser una línea igual para los siete, con el coste de contexto contando además dentro del presupuesto que §6.5 verifica antes de invocar. El resto de la contención es material: los siete `.claude/agents/*.md` con el `tools` de §7.4, los dos hooks que `CLAUDE.md` da por existentes (`PreToolUse` de escritura, `Stop` de trazado), los plugins de desarrollo fuera del fichero versionado y un test de contrato que falle si un agente gana una herramienta prohibida. Queda por verificar si `PreToolUse` se dispara para las llamadas de herramienta de un subagente: si no lo hiciera, el invariante 1 se queda solo con los triggers. Mientras nada de esto exista, §6.3 y §7.4 describen el contrato de los agentes, no lo que hay en disco.
8. **El arranque pasa por un humano.** El formulario del panel produce un `config.yaml` y un comando `/novela-nueva` para copiar en una terminal, porque la API no escribe y FastAPI no puede invocar modelos (§2, «fuera del stack»). Es la única costura manual del diseño y está en el primer paso que da cualquiera; además nadie ha decidido quién manda, si ese `config.yaml` o los flags del comando, que llevan los mismos parámetros. La dirección acordada es una cola en disco fuera de los workspaces —`novelas/_cola/`, con `pendientes/`, `en-curso/` y `hechas/`, donde el prefijo `_` no es un slug válido y la separación se sostiene por construcción—: la API gana un `POST /cola` que valida y encola de forma atómica, su única escritura, con tope de pendientes porque cada solicitud aceptada acabará gastando cuota; el CLI gana `novela cola tomar` y `novela cola cerrar`; y el `config.yaml` lo escribe siempre el backend, venga de la cola o de los flags. Quien vacía la cola es un supervisor de quince líneas de shell, el bucle desatendido de §2.3 con una fuente de trabajo delante: se queda en shell porque solo decide **qué novela empieza**, no qué paso sigue a un gate, y meterlo en el CLI borraría esa frontera. Un `run.sh` levanta API y supervisor juntos, de modo que no exista el estado «panel en pie, nadie ejecutando» ni, con él, un segundo camino de arranque que mantener. Si se adopta, la frase «no hay verbo de escritura» de §11.1 pasa a «la API no muta una novela», y con ella la regla equivalente de `AGENTS.md`.
