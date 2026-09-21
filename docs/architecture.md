# architecture.md

Arquitectura del harness multiagente de generación de novelas de suspense.

Este documento describe **cómo se implementa** la ontología definida en `docs/domain-knowledge.md` (diagramas) y `docs/definitions.md` (diccionario). Toda entidad citada aquí en `mayúsculas` o con ruta de punto existe allí con su definición, mutabilidad y propietario.

**Restricción de partida:** el sistema se ejecuta íntegramente sobre la suscripción de Claude Code. No hay llamadas a la API de Anthropic ni a proveedores externos. Esto tiene dos consecuencias de diseño que atraviesan todo el documento: no hay control de `temperature`, y el orquestador no es un proceso Python que invoca modelos, sino la propia sesión de Claude Code.

---

## 1. Principios

1. **El contexto vive en el sistema de ficheros, no en la conversación.** Cada subagente arranca con contexto vacío. La continuidad la da `estado/state.json` más los resúmenes, nunca el historial.
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
| Esquemas | Pydantic v2 | Modelos tipados que exportan JSON Schema a `schemas/` |
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
├── Bash: novela aplicar-delta 07            → state.json + resumen
└── Bash: novela checkpoint 07
```

El orquestador nunca lee `capitulos/07.md`. Los subagentes leen y escriben ficheros; lo que devuelven a la sesión principal es un informe de dos o tres líneas. Esta disciplina es lo que permite que una sesión cubra varios capítulos sin saturarse.

La lógica del bucle vive en `.claude/commands/novela-continuar.md`, no en código Python. El código Python es el conjunto de operaciones deterministas que el bucle invoca entre delegaciones.

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
│       └── validar-estado.py     # PostToolUse sobre state.json, ver §7.1
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
│   │   ├── cli.py                # Typer
│   │   ├── briefing.py           # ensamblado de contexto (rama 5)
│   │   ├── recipes.py            # MEMORIA.recetas_de_ensamblado
│   │   ├── validate.py           # gates baratos
│   │   ├── delta.py              # aplicación del delta al estado
│   │   ├── checkpoint.py
│   │   ├── budget.py             # ventana de uso y degradación
│   │   ├── audit.py              # pistas huérfanas, hilos abiertos
│   │   ├── models/               # Pydantic: la ontología como código
│   │   │   ├── config.py         # rama 1
│   │   │   ├── canon.py          # rama 2
│   │   │   ├── plan.py           # rama 3
│   │   │   ├── state.py          # rama 4
│   │   │   └── qa.py
│   │   ├── store/
│   │   │   ├── workspace.py
│   │   │   ├── atomic.py         # escritura tmp + rename
│   │   │   └── lock.py
│   │   └── export/
│   │       ├── markdown.py
│   │       └── epub.py
│   │
│   ├── config/
│   │   ├── default.yaml          # valores por defecto de parametros_obra
│   │   └── recipes.yaml          # qué entra en el briefing de cada agente
│   │
│   ├── schemas/                  # JSON Schema generados desde Pydantic, versionados
│   │   ├── state.schema.json
│   │   ├── canon.schema.json
│   │   ├── plan-capitulo.schema.json
│   │   ├── delta.schema.json
│   │   └── qa-informe.schema.json
│   │
│   └── tests/
│       ├── test_gates.py
│       ├── test_briefing.py
│       ├── test_delta.py
│       ├── test_api.py
│       └── fixtures/             # workspaces sintéticos, sin llamadas a modelo
│
├── frontend/                     # Vite + TypeScript + Three.js, solo lectura
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
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
│   ├── state.json                # rama 4 — fuente única de verdad
│   └── state.lock
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
per-elena-vidal      personaje
esc-casa-del-faro    escenario
pis-007              pista
pfa-003              pista falsa
rev-002              revelación
hil-004              hilo
obj-011              objeto o prueba
cap-01 / esc-01-3    capítulo / escena tercera del capítulo 1
```

**Escritura atómica.** Todo fichero se escribe en `.tmp` y se renombra. Un `state.json` a medio escribir es un workspace muerto.

**Bloqueo.** `filelock` sobre `estado/state.lock`. Dos sesiones de Claude Code sobre la misma novela corromperían el estado.

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
  presupuesto_tokens: 80000
  capas:
    - permanente: [canon/*, canon/misterio]
    - estado: [libro_de_hechos, linea_temporal, coartadas]
    - objetivo: capitulo_recien_escrito
```

La receta se versiona y su identificador se escribe en `runs/<run_id>/manifest.json`.

### 6.3 Aislamiento del secreto

`canon/misterio.md` está excluido por receta del `escritor` y del `editor-estilo`. Dos capas de refuerzo, porque una regla en el prompt no basta:

1. `novela briefing` aborta si el contenido resultante contiene texto procedente de ese fichero.
2. El frontmatter de `escritor.md` restringe `tools` para que no pueda leer rutas arbitrarias fuera de las autorizadas.

El escritor recibe solo el contenido de las pistas listadas en `plan/capitulos/NN.md` para su capítulo. Un modelo que conoce la solución la filtra en el subtexto mucho antes de tiempo, y es un fallo invisible en revisión capítulo a capítulo.

---

## 7. Contratos de datos

### 7.1 `estado/state.json`

Forma abreviada; la definitiva se genera desde `backend/novela/models/state.py`.

```json
{
  "schema_version": "1.0.0",
  "cursor": { "capitulo": 7, "fase": "revision", "ultimo_paso": "continuista", "intento": 1 },
  "linea_temporal": [
    { "escena": "esc-07-2", "capitulo": 7, "inicio": "dia 3, 21:40", "duracion_min": 35 }
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
    "per-elena-vidal": [ { "hecho": "hec-014", "desde_capitulo": 5 } ]
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
  "hilos": [ { "id": "hil-004", "estado": "abierto", "abierto_en": 2, "descripcion": "..." } ],
  "pistas": { "pis-007": { "estado": "plantada", "plantada_en": 4, "pagada_en": null } },
  "conocimiento_lector": [ { "hecho": "hec-014", "desde_capitulo": 5 } ],
  "tension_real": [ 4, 5, 6, 5, 7, 8, 7 ],
  "metricas": { "palabras_totales": 21840, "desviacion_vs_plan": -0.04 }
}
```

`libro_de_hechos` y `conocimiento` son append-only. `novela aplicar-delta` rechaza cualquier delta que modifique o elimine una entrada existente: eso no es una corrección, es reescribir la historia, y rompe toda verificación posterior.

Refuerzo adicional: un hook `PostToolUse` en `.claude/hooks/validar-estado.py` valida `state.json` contra su esquema tras cualquier escritura. Si un subagente lo toca por su cuenta, se detecta en el acto en vez de dos capítulos después.

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

Reglas transversales del cuerpo de cada agente:

- Lee solo el briefing indicado y las rutas listadas en él.
- Escribe solo en las rutas listadas como salida.
- Devuelve a la sesión principal un informe de tres líneas como máximo.
- Ante ambigüedad, falla explícitamente en lugar de inventar.

Solo el `cronista` tiene `Write` sobre el delta de estado, y ningún agente escribe `state.json` directamente: lo aplica `novela aplicar-delta`.

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
novela estado <slug> --breve
novela briefing <slug> <cap> <agente>
novela validar <slug> <cap>
novela aplicar-delta <slug> <cap>
novela checkpoint <slug> <cap>
novela pendiente <slug>            # código de salida: 0 si quedan capítulos
novela exportar <slug> --formato epub
```

**Reanudación.** `/novela-continuar` empieza leyendo `checkpoints/latest.json` y repite el último paso no confirmado. Regla dura: el estado nunca se reconstruye desde una conversación previa, ni siquiera desde la sesión anterior de Claude Code.

**Parada.** Agotados los intentos de un gate, el procedimiento escribe `runs/<run_id>/intervencion.md` con el hallazgo y el briefing que lo produjo, y termina. No degrada la calidad en silencio.

---

## 9. Presupuesto

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
- **API FastAPI** (`backend/api/`): solo lectura, para el frontend. Sirve `state.json`, los capítulos y los manifiestos tal cual están en disco.

La API **no lanza agentes ni escribe en el workspace**. No hay verbo de escritura: mutar una novela es trabajo del orquestador a través del CLI. Si un endpoint pareciera necesitar escribir, lo correcto es añadir un subcomando al CLI, no un `POST` a la API.

Los modelos de respuesta son los mismos Pydantic de `backend/novela/models/`. Una sola ontología, un solo sitio donde cambiarla.

```
GET /novelas                              slugs con su cursor
GET /novelas/{slug}/estado                state.json
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
3. **Contexto de la sesión orquestadora.** Las cuatro reglas de §2.4 son la hipótesis de que un capítulo por sesión basta. Si en la práctica el orquestador aguanta tres o cuatro, el modo desatendido se abarata; si no aguanta ni uno completo, hay que partir el bucle en dos comandos.
4. **`index_recuperable` pospuesto.** El índice vectorial sobre escenas queda fuera de la v1. Con 24 capítulos los resúmenes jerárquicos bastan; se justifica a partir de unas 40.
5. **El escritor no reescribe capítulos anteriores.** Si un gate detecta que un problema del capítulo 7 nace del 5, el harness para y pide intervención. La reescritura retroactiva automática invalidaría el estado y los resúmenes de todo lo intermedio.
