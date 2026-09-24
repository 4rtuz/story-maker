# Observabilidad

Qué llega a Langfuse de una novela y cómo se lee. Instalación del plugin y claves: `architecture.md` §10.1. Este documento sustituye a §10.2 (agrupación) y §10.4 (versionado de prompts) donde se contradicen.

## 1. Sesión, traza, span y score

| Langfuse | Qué es aquí | Quién lo crea |
|---|---|---|
| sesión | una novela entera: `novela-<slug>`, con su brief, cada paso y cada cambio posterior | `langfuse.sesion_de(slug)` |
| traza | un paso: `brief`, `nueva`, `capitulo NN`, `auditoria`, `cambio`... | `novela traza` o `novela producir` |
| span | el turno (`Conversational Turn`), cada subagente (`Subagent: …`), cada herramienta (`Tool: …`) | el plugin |
| generación | cada llamada al modelo (`LLM Call`, `Subagent LLM Call`), con tokens y coste | el plugin |
| score | cada métrica y validador del capítulo, sobre la traza del paso | `novela checkpoint` |

**Cómo se fija la sesión.** El plugin agrupa por el session id de Claude Code, y hay uno por `claude -p`. No se puede reutilizar un solo id para todas: `--session-id` con un id que ya existe falla, y `--resume` arrastraría el contexto del capítulo anterior, que es justo lo que la sesión por capítulo evita. El plugin no deja sustituir su session id, pero sí colgar la sesión de una traza ajena: si `CC_LANGFUSE_TRACEPARENT` está definida, emite los turnos bajo ese span y deja el nombre, la sesión y las etiquetas de la traza a quien la abrió. `novela traza <slug> <paso>` abre esa traza: manda un span raíz por OTLP/HTTP JSON (`POST /api/public/otel/v1/traces`, con `x-langfuse-ingestion-version: 4`) con `langfuse.session.id = novela-<slug>`, nombre `<slug> · <paso>`, etiquetas `[slug, novela]` y los metadatos `paso`, `slug`, `sha_commit` y `prompt_<rol>`. Después imprime su traceparent.

- `novela producir` abre una traza por paso y la pasa a cada `claude -p`. El paso de `/novela-continuar` es el capítulo siguiente al último cerrado.
- En el bucle desatendido a mano, `export CC_LANGFUSE_TRACEPARENT=$(novela traza <slug> /novela-continuar)` antes de cada sesión (AGENTS.md § Proceso: ejecución).
- En una sesión interactiva (`/novela-brief`, o `novela cambio` cuando exista), antes de abrir `claude`: `export CC_LANGFUSE_TRACEPARENT=$(novela traza <slug> /novela-brief)`, o `… cambio`. Todo lo que pase en esa sesión cae en esa traza.
- `NOVELA_SESSION_ID` no cambia: sigue siendo un UUID por sesión, el que exige la regla 5 del hook y el que `harness.log` escribe como `sesion=`.

Sin `TRACE_TO_LANGFUSE=true`, o si Langfuse no contesta en 5 s, no hay traza padre: `novela traza` no imprime nada y la sesión se traza como antes, una sesión de Langfuse por `claude -p`, con la etiqueta del slug (`CC_LANGFUSE_TRACE_TAGS`). Esas son las **trazas legadas**. `novela costes` lee las dos formas.

**Limitación.** En modo adjunto, las observaciones hijas llegan con `sessionId` vacío y sin etiquetas en `GET /api/public/v2/observations`: la sesión y las etiquetas son de la traza, y las lleva su raíz. Para filtrar por novela se busca la raíz (por etiqueta o sesión) y después se piden las observaciones por `traceId`, que es lo que hace `novela costes`.

**Último turno perdido.** Con `claude -p`, el hook `Stop` retiene el turno final («Holding trailing open turn») hasta que `SessionEnd` lo cierra, y Claude Code cancela `SessionEnd` al salir («Hook cancelled»). Ese último turno no llegaba nunca. `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=30000` le da tiempo: `producir` la exporta, y el bucle de AGENTS.md también.

Evidencia (2026-09-25, proyecto `cmu40j1d8060qad0d6pkj3jaa`): `novela traza prueba-observabilidad /novela-continuar` abrió la traza `d0166a14030f623563bbd9d2ba2eeda0` con la raíz `853bb0a09414bbf8` (`prueba-observabilidad · capitulo 01`, sesión `novela-prueba-observabilidad`). Un `claude -p` con ese traceparent colgó de ella su `Conversational Turn` `e0a50f41f9265fb1`, dos `LLM Call` y un `Tool: Agent`. El log del plugin pasó de `Processed 0 turns` a `Processed 1 turns` en `SessionEnd`.

## 2. Spans por rol

El plugin nombra cada subagente `Subagent: <description>`, con el `description` que el orquestador da al `Task`, y guarda el rol exacto en `metadata.agent_type`. El `Tool: Agent` que lo lanza lleva `metadata.subagent_type`. Las herramientas son `Tool: <nombre>` (`Tool: Read`, `Tool: Bash`...). `novela costes` atribuye cada generación al `agent_type` más cercano hacia arriba; si no hay, al `orquestador`.

| Rol | Papel | Span real en humo-0003 | id | traza |
|---|---|---|---|---|
| `arquitecto` | planner | `Subagent: Crear canon humo-0003` | `4377e1691e19a7f4` | `85df0a69da0f4cfc1586c14e20289f0b` |
| `trazador` | planner | `Subagent: Trazador crea plan` | `5430f7d758241c1c` | `9c0032d02977bb270e673963f5abc7a4` |
| `escritor` | writer | `Subagent: Escribir capítulo 01` | `9b7b939d7ea7141f` | `9c927d37ae054c18f60c4765e7936e55` |
| `continuista` | critic | `Subagent: Continuidad capítulo 01` | `d7b5a4c8135355ef` | ídem |
| `editor-estilo` | editor | `Subagent: Estilo capítulo 01` | `daa02848ec17de7d` | ídem |
| `lector-suspense` | critic | `Subagent: Suspense capítulo 01` | `93833de5538f7b5b` | ídem |
| `cronista` | registro de estado | `Subagent: Delta capítulo 01` | `f0b90f4210778059` | ídem |
| `entrevistador` | brief | sin traza todavía: ninguna novela trazada ha pasado por `/novela-brief` | | |

El nombre visible depende del `description` que elija el orquestador. El rol, en cambio, siempre está en `agent_type`. Por eso se filtra y se agrega por el metadato, no por el nombre.

## 3. Coste por novela

```
novela costes <slug>              una línea por paso y el total
novela costes <slug> --json       el informe: pasos, roles por paso y total
novela costes <slug> --markdown   escribe docs/evaluacion/costes-<slug>.md
```

Lee `GET /api/public/v2/observations`: primero lo etiquetado con el slug (`filter` `tags any of`) y después todo lo de cada traza con `metadata.paso`. En las organizaciones creadas desde el 2026-09-16 es la única API de lectura de trazas que no devuelve 410. Por paso da llamadas, tokens de entrada (con la caché), de salida y de caché leída, coste USD, latencia de pared de sus trazas sin los huecos entre ellas, latencia media por llamada y el desglose por rol. Por novela da la suma. En una traza legada, el paso sale de `runs/*/harness.log` (`sesion=`) y del `manifest.json` de ese run (`arranque` → `nueva`, `capitulo` → `capitulo NN`); si no, de la etiqueta `skill:novela-auditar` (o brief, o nueva), y si tampoco, `sesión <id>`. El workspace solo se lee.

**Coste.** Langfuse lo calcula con su tabla de precios para los modelos de Claude: cada generación trae `totalCost` y `costDetails` (entrada, salida, caché leída, escritura de caché por TTL). Ejemplo real: `claude-opus-5-5` a `inputPrice 0.000004` y `outputPrice 0.00002` USD por token. Por eso no hay `backend/config/precios.yaml`: sería una segunda tabla que desfasar. Si algún día llega una generación con `totalCost` nulo, cuenta 0, y ese es el momento de añadirla.

Ejemplo contra el Langfuse real, humo-0003 (trazas legadas; el informe entero está en `docs/evaluacion/costes-humo-0003.md`):

```
$ novela costes humo-0003
nueva: 32 llamadas · 956785 entrada · 63572 salida · 2.6220 USD · 3086.254 s
sesión 8f18d74d: 4 llamadas · 130274 entrada · 791 salida · 0.1848 USD · 16.053 s
capitulo 01: 55 llamadas · 1863713 entrada · 98416 salida · 2.0441 USD · 732.947 s
capitulo 02: 64 llamadas · 2315748 entrada · 161600 salida · 3.5569 USD · 1131.635 s
capitulo 03: 87 llamadas · 3196013 entrada · 177570 salida · 4.4518 USD · 1199.571 s
auditoria: 4 llamadas · 118206 entrada · 541 salida · 0.1522 USD · 14.377 s
novela: 246 llamadas · 8580739 entrada · 502490 salida · 13.0118 USD · 6180.837 s
```

`sesión 8f18d74d` es una sesión que no escribió en ningún `harness.log`. Por rol, en el capítulo 03 el orquestador hizo 37 llamadas y costó 0,79 USD, el escritor 1,10 y el continuista 0,96.

Y la traza nueva de §1, con `--json`:

```json
{"slug": "prueba-observabilidad", "sesion": "novela-prueba-observabilidad",
 "pasos": [{"paso": "capitulo 01", "llamadas": 2, "tokens_entrada": 78277, "tokens_salida": 422,
            "tokens_cache_lectura": 69806, "coste_usd": 0.026015,
            "latencia_media_llamada_s": 2.979, "latencia_s": 32.66,
            "roles": {"orquestador": {"llamadas": 2, "coste_usd": 0.026015, "...": "..."}}}],
 "total": {"llamadas": 2, "coste_usd": 0.026015, "latencia_s": 32.66, "...": "..."}}
```

## 4. Scores

`novela checkpoint` emite los seis agregados y un binario por validador (`architecture.md` §10.5) con `POST /api/public/scores`. La API admite exactamente uno entre `traceId` y `sessionId`: con los dos responde 400.

- Si el entorno trae `CC_LANGFUSE_TRACEPARENT`, el score va con `traceId` a la traza del paso, que ya está en la sesión de la novela. La sesión de `claude -p` lo hereda y lo pasa a cada `Bash`, así que `novela checkpoint` lo ve.
- Si no, va con `sessionId = novela-<slug>`. Antes iba con `sessionId = run_id`, una sesión que no existía en Langfuse.
- `metadata`: `run_id` y `capitulo`. El id sigue siendo `<slug>-<run_id>-<NN>-<nombre>`: reemitir sustituye.

La interfaz `ScoreSink.emitir(slug, capitulo, run_id, scores)` no cambia. `SinkLangfuse` gana un campo `traza: str | None = None`, que rellena `desde_entorno`. Un validador nuevo que emita por `desde_entorno(...)` hereda la asociación sin tocar nada.

Evidencia: el score `prueba-observabilidad-r-20260925-0000-01-vp_schema` está en la traza `d0166a14030f623563bbd9d2ba2eeda0`. Se lee con `GET /api/public/v3/scores?traceId=…`; la v2 devuelve 410 en esta organización.

## 5. Versionado de prompts

```
novela prompts publicar
```

Sube cada `.claude/agents/*.md` (el fichero entero, frontmatter incluido, porque `model` y `tools` también cambian la conducta) a `POST /api/public/v2/prompts` como prompt `text` con nombre = rol, etiquetas `[<sha corto de HEAD>, production]`, `config = {sha256, fichero}` y `commitMessage`. Es idempotente: si la versión `production` ya tiene el mismo texto, no crea otra. Cada traza de paso lleva `sha_commit` y `prompt_<rol>`, los 12 primeros hex del sha256 del fichero, que es el `config.sha256` de la versión publicada. Así se ve qué versión produjo cada resultado, y cada score de la traza queda con ella.

Ejecución real (2026-09-25, HEAD `f0d341c`): la primera vez, `v1` para los ocho roles; la segunda, `igual` para los ocho.

**Por qué ahora sí** (`architecture.md` §10.4 lo descartaba). §10.4 temía una segunda fuente de verdad. Sigue sin haberla: git manda, Langfuse recibe una copia marcada con el sha, y nada lee el prompt de Langfuse para ejecutarlo. Los agentes siguen cargando `.claude/agents/*.md`. Lo que se gana es que la iteración de tuning se ve en la misma herramienta que los scores: versión, diff entre versiones y resultados por versión, sin cruzar a mano manifiestos y shas. El coste es un paso más, `novela prompts publicar` tras cambiar un prompt y commitear, que si se olvida solo deja la copia atrasada; la huella de la traza sigue siendo la verdad. Lo que no se consigue: enlazar el prompt a cada generación (`promptName`/`promptVersion`). Esas generaciones las crea el plugin, y el prompt de un subagente no pasa por el SDK de Langfuse.

## 6. Variables

| Variable | Quién la lee | Para qué |
|---|---|---|
| `TRACE_TO_LANGFUSE` | CLI | `true` exactamente: scores y traza por paso |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | CLI (entorno o `.env`); plugin (su configuración) | credenciales y host |
| `CC_LANGFUSE_TRACEPARENT` | plugin; `novela checkpoint` | colgar la sesión de la traza del paso; `traceId` de los scores |
| `CC_LANGFUSE_TRACE_TAGS` | plugin | etiqueta el slug en las trazas legadas |
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | Claude Code | que `SessionEnd` envíe el último turno |
| `NOVELA_SESSION_ID` | hook, `harness.log` | sin cambios |

Nombres sin valores en `.env.example`. Las claves del `.env` no pasan a ningún `claude -p`: `producir` abre la traza con el entorno efectivo y lanza la sesión con `os.environ`.

## 7. Validadores y verificadores

| Qué se comprueba | Test |
|---|---|
| Sin traza, el score va a `novela-<slug>`; con traceparent, a su `traceId` y nunca a los dos | `plataforma/test_langfuse.py` |
| La traza del paso lleva sesión, nombre, etiquetas y metadatos; sin `TRACE_TO_LANGFUSE` no hay red, y con Langfuse caído devuelve None | `slices/observabilidad/test_traza.py` |
| `paso_de` da el mismo paso a `producir` y a `novela traza` | ídem |
| `producir` pasa el traceparent, `NOVELA_SESSION_ID` y el timeout de `SessionEnd` a cada sesión | `slices/producir/test_producir.py` |
| Agregación por paso, rol y novela; trazas nuevas y legadas; latencia sin huecos; paginación por cursor; markdown | `slices/observabilidad/test_costes.py` |
| Publicar es idempotente y mueve `production` a la versión nueva | `slices/observabilidad/test_prompts.py` |

Riesgos aceptados:

- La traza padre se abre antes de la sesión. Si Langfuse la pierde, los turnos cuelgan de un span que no existe y la traza sale sin nombre ni sesión.
- `metadata` llega truncada a 200 caracteres. `agent_type` y `paso` caben.
- El paso de una traza legada depende de que su sesión escribiera en algún `harness.log`.
- Coste 0 si Langfuse no conoce un modelo (§3).
