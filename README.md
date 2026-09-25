# story-maker

Un harness multiagente sobre Claude Code que escribe una **novela de suspense personalizada de
regalo**: 10 capítulos de 1.000 a 1.500 palabras sobre un destinatario real (nombre, edad, rasgos
y recuerdos), entregada como **PDF interactivo** con portada y dedicatoria, índice navegable y
ficha de personajes y lugares, y corregible después («el perro se llama Nala») sin romper la
continuidad ni perder la versión anterior.

- Novela de ejemplo generada con el brief de abajo: [`ejemplos/novela-ejemplo.pdf`](ejemplos/novela-ejemplo.pdf).
- Documentación de proceso: [`docs/proceso/README.md`](docs/proceso/README.md).
- Resultados de la evaluación: [`docs/evaluacion/resultados.md`](docs/evaluacion/resultados.md).
- Presentación y demo: [`presentacion/`](presentacion/).

## Cómo funciona

```
cliente → /novela-brief (entrevistador) → brief.json validado
        → /novela-nueva --brief (arquitecto: canon · trazador: plan) → validar-plan
        → por capítulo: escritor → validar (hook + gate) → continuista · editor-estilo · lector-suspense
                        → cronista → aplicar-delta (story bible SQLite) → checkpoint
        → /novela-auditar: auditar → verificar-lean → juez → exportar (md, epub, pdf)
        → novela cambio → regenera solo los capítulos que usan el hecho → versión nueva + novedades
```

| Rol (rúbrica) | Agentes | Modelo |
|---|---|---|
| Entrevistador | `entrevistador` | sonnet |
| Planner | `arquitecto`, `trazador` | opus, haiku |
| Writer | `escritor` | opus |
| Editor / critic | `continuista`, `editor-estilo`, `lector-suspense`, `juez` | haiku, haiku, haiku, sonnet |
| Memoria | `cronista` | sonnet |

La sesión principal orquesta y no lee prosa ([`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md)).
El CLI `novela` hace todo lo determinista: validadores, story bible, checkpoints, guardrails, Lean,
exportación y scores a Langfuse. Ningún código Python llama a un modelo.

## Brief de ejemplo

Datos **ficticios**, inventados para la novela de ejemplo (`novela brief iniciar --ficticio`).

Respuestas del cliente (`respuestas.md`):

```
Pregunta: ¿Cómo se llama la persona que recibe el regalo?
Respuesta: Se llama Carmen Robles.
Pregunta: ¿Qué edad tiene?
Respuesta: Tiene 63 años.
Pregunta: ¿Qué género de novela prefieres?
Respuesta: Suspense doméstico.
Pregunta: ¿Qué tono quieres?
Respuesta: Intrigante, pero con cariño.
Pregunta: ¿Qué extensión?
Respuesta: Corta.
Pregunta: ¿Cómo es ella?
Respuesta: Es meticulosa, curiosa y un poco cabezota. Ha sido bibliotecaria municipal durante treinta años.
Pregunta: ¿Algún recuerdo que quieras incluir?
Respuesta: El invierno en que catalogó sola el archivo del faro de Cabo Mayor. Su perro Tango, que la acompañaba a la biblioteca. El viaje en tren a Lisboa con sus hermanas.
Pregunta: ¿Hay temas que no quieres que aparezcan?
Respuesta: Nada de cáncer ni de divorcios, y que no salga el nombre de Julián.
```

Texto libre, tratado como contenido no confiable (`carta.md`):

```
Querida Carmen:
Treinta años abriendo la biblioteca a las nueve en punto.
Nunca olvidaremos el día que encontraste una carta de 1952 escondida en un atlas.
Tango dormía bajo el mostrador de préstamos y nadie se atrevía a despertarlo.
Siempre decías que cada libro guarda un secreto de quien lo leyó antes.
Tus compañeros de la Biblioteca Municipal
```

Ocasión: `jubilacion`. Slug: `ejemplo-carmen`.

## Puesta en marcha

Una vez por máquina (Windows + Git Bash, ver [`AGENTS.md` § Proceso: ejecución](AGENTS.md)):

```bash
cd backend  && uv sync                   # Python 3.12
cd frontend && npm install
uv tool install --editable ./backend     # deja `novela` en el PATH
cp .env.example .env                     # claves de Langfuse para los scores (opcional)
claude                                   # abrir una vez en la raíz y aceptar la confianza
```

Herramientas formales (opcionales para generar, obligatorias para los gates formales):
Lean 4 con [elan](https://github.com/leanprover/elan) (`~/.elan/bin`), Java 17+ y
[`tla2tools.jar`](https://github.com/tlaplus/tlaplus/releases) para TLC.

## Escribir la novela de ejemplo

```bash
export CLAUDE_CODE_GIT_BASH_PATH="$LOCALAPPDATA/Programs/Git/bin/bash.exe"   # si Git es por usuario
novela brief iniciar ejemplo-carmen --ocasion jubilacion --ficticio
novela brief entrada ejemplo-carmen --tipo respuesta   --fichero /fuera/del/repo/respuestas.md
novela brief entrada ejemplo-carmen --tipo texto-libre --fichero /fuera/del/repo/carta.md
# en una sesión de claude: /novela-brief ejemplo-carmen --ocasion jubilacion (entrevistador + validar)
claude -p "/novela-nueva ejemplo-carmen --brief" --setting-sources project,local --permission-mode dontAsk --model opus
novela producir ejemplo-carmen           # capítulo a capítulo, auditoría, Lean, juez y exportación
novela exportar ejemplo-carmen --formato pdf
```

También desde el panel (`#/lanzar`): `cd backend && NOVELAS_DIR=../novelas uv run uvicorn api.main:app`
y `cd frontend && npm run dev`.

## Pedir un cambio y generar la versión nueva

```bash
novela estado ejemplo-carmen --json          # o la tool MCP query_story_bible: el id del hecho
novela cambio ejemplo-carmen --hecho hec-012 --texto "El perro se llama Nala" --simular   # qué capítulos lo usan
novela cambio ejemplo-carmen --hecho hec-012 --texto "El perro se llama Nala" --motivo "petición del cliente"
novela producir ejemplo-carmen               # regenera solo los afectados
novela exportar ejemplo-carmen --formato pdf # PDF nuevo con página de novedades y enlaces
novela versiones ejemplo-carmen              # la versión anterior queda intacta en versiones/
```

## Validar

| Qué | Cómo |
|---|---|
| Tests (sin modelos) | `cd backend && uv run pytest && uv run python -m mypy --strict . && uv run ruff check .` |
| Panel | `cd frontend && npm run verificar` |
| Validador formal de la historia (Lean 4) | `novela verificar-lean <slug>` → `qa/lean.json` · [docs/formal/lean.md](docs/formal/lean.md) |
| Validador formal del sistema (TLA+) | `bash formal/tla/tlc.sh` · [formal/tla/README.md](formal/tla/README.md) |
| Guardrail de palabras prohibidas | `novela prohibidas comprobar <slug>` · [docs/guardrails.md](docs/guardrails.md) |
| LLM-as-judge y revisión humana | `novela juicio <slug>`, `novela comparar-juicios` · [docs/evaluacion/juez.md](docs/evaluacion/juez.md) |
| Validación visual (Playwright MCP) | skill `validar-visual`, `novela registrar-visual` · [docs/validacion-visual.md](docs/validacion-visual.md) |
| Linters de prosa | `novela lint-prosa <slug>` · [docs/linters-prosa.md](docs/linters-prosa.md) |
| Coste por novela (Langfuse) | `novela costes <slug> --markdown` · [docs/observabilidad.md](docs/observabilidad.md) |

## Servidor MCP

De lectura: `list_novels`, `get_chapter`, `list_versions`, `query_story_bible` y
`download_novel`. De escritura, deshabilitada salvo con `STORY_MAKER_MCP_ESCRITURA=1`:
`request_change`, que pide un cambio del lector con simulación y confirmación. Ya está en [`.mcp.json`](.mcp.json) junto al Playwright MCP. A mano:

```bash
claude mcp add story-maker -- uv run --directory backend python -m api.mcp
npx @modelcontextprotocol/inspector uv run --directory backend python -m api.mcp
```

Detalle y Claude Desktop: [`docs/mcp.md`](docs/mcp.md).

## Estructura

| Carpeta | Qué hay |
|---|---|
| `backend/` | CLI `novela`, API FastAPI de solo lectura, servidor MCP, esquemas JSON |
| `frontend/` | Panel Vite + TypeScript: lanzamiento, progreso y lectura web |
| `.claude/` | Agentes, slash commands, hooks, skills y memoria del proyecto |
| `formal/` | Lean 4 (`lean/`) y TLA+ (`tla/`) |
| `docs/` | Referencia, specs, ADR, proceso, evaluación y seguridad |
| `novelas/` | Workspaces de novela (git los ignora) |

Sin claves en el repo: usa [`.env.example`](.env.example).
