# Servidor MCP

Un servidor [MCP](https://modelcontextprotocol.io) para consultar y descargar las novelas de
`novelas/` y, si se habilita, pedir un cambio del lector (`request_change`). Está hecho con FastMCP (`backend/api/mcp/`) y se sirve de dos formas:

- **Streamable HTTP**, montado en la API: `http://127.0.0.1:8000/mcp/` cuando corre
  `uvicorn api.main:app`.
- **stdio**: `uv run python -m api.mcp` desde `backend/`, para Claude Desktop, Claude Code o el
  MCP Inspector.

Las dos leen los workspaces de `NOVELAS_DIR` (por defecto `novelas/` relativo al directorio de
trabajo), como la API.

## Tools de lectura

Todas llevan `readOnlyHint: true`. Los parámetros se validan contra su JSON Schema antes de
ejecutar nada: `slug` usa el mismo patrón que la API y el CLI (`^[a-z0-9-]+$`), así que un
`../etc` se rechaza sin tocar el disco.

| Tool | Parámetros | Devuelve |
|---|---|---|
| `list_novels` | — | `[{slug, cursor, capitulos_hechos, version}]` |
| `get_chapter` | `slug`, `capitulo` (1–999), `version` (≥1, opcional; por defecto la vigente) | el Markdown del capítulo, con su frontmatter |
| `list_versions` | `slug` | `[{numero, cambio, creada, estado, capitulos_cambiados}]` |
| `query_story_bible` | `slug`, `tipo` (`personajes` \| `lugares` \| `hechos` \| `cronologia`), `filtro` (opcional, ≤200 caracteres) | lista de filas |
| `download_novel` | `slug` | el PDF como recurso embebido (`application/pdf`, base64) |

Detalle:

- **`list_novels`**: las mismas novelas que `GET /novelas`. `capitulos_hechos` es el capítulo del
  último checkpoint; `version`, la vigente.
- **`get_chapter`**: la versión vigente se lee de `capitulos/NN.md`; una anterior, de
  `versiones/vN/capitulos/NN.md`. Un capítulo sin escribir o una versión inexistente dan error.
- **`list_versions`**: sigue el formato en disco de la spec 0007. La versión vigente es
  `meta.version` de la base de estado, o la 1 si no existe. El registro sale de
  `versiones/versiones.json` y los capítulos cambiados, de comparar los sellos sha256: los del
  último checkpoint para la vigente y los de `versiones/vN/version.json` para las guardadas. Sin
  `versiones/` hay una sola versión, la original, con `capitulos_cambiados: []`.
- **`query_story_bible`**: abre la base con `mode=ro` y usa los lectores de
  `novela/plataforma/estado_db.py`:
  - `personajes`: el estado de cada personaje, los capítulos en que aparece y, del canon, su nombre
    y sus alias.
  - `lugares`: los escenarios de `canon/mundo.md` (id, nombre y descripción) con sus capítulos.
  - `hechos`: el libro de hechos.
  - `cronologia`: la línea temporal.

  `filtro` se busca como subcadena en cada fila serializada, sin distinguir mayúsculas. Del canon
  no sale nada que no imprima ya el libro de regalo: ni secretos ni `canon/misterio.md`.
- **`download_novel`**: el libro de la spec 0006 (`novela/slices/export/pdf.py`) con los capítulos
  cerrados. Se construye en memoria y no escribe nada en el workspace. El título es el slug y no
  lleva dedicatoria.

## Tool de escritura: `request_change`

Pide que un hecho de una novela terminada sea otro: es `novela cambio` (spec 0007) desde un cliente
MCP. La tool no toca el disco; lanza el CLI del propio venv como proceso (`python -m novela`, sin
shell y con los argumentos en lista, como `lanzador`), y es el CLI quien escribe.

| Parámetro | Validación |
|---|---|
| `slug` | el patrón de la API y el CLI, `^[a-z0-9-]+$` |
| `hecho` | `^hec-[0-9]{3}$` |
| `texto` | 1–500 caracteres, como `--texto` |
| `motivo` | opcional, ≤500, como `--motivo` |
| `confirmacion` | opcional, el token de una llamada anterior |

Devuelve `{plan, confirmacion, aplicado, salida, siguiente}`.

**Permisos.** Está deshabilitada por defecto: sin `STORY_MAKER_MCP_ESCRITURA=1` en el entorno del
proceso que sirve el MCP, no aparece en `tools/list` y, si se llama, falla antes de ejecutar nada.
Se admite por stdio y por HTTP solo desde loopback. Por HTTP pasa primero la guarda de Host/Origin
del montaje y la tool comprueba además la IP del cliente, porque un `Host: 127.0.0.1` se puede
mandar desde otra máquina si uvicorn escucha en `0.0.0.0`. Lleva `readOnlyHint: false` y
`destructiveHint: true`, así que un cliente que respete las anotaciones pide permiso antes de
llamarla.

**Confirmación.** Nunca se aplica a ciegas:

1. Cada llamada ejecuta primero `novela cambio … --simular`, que no escribe, y calcula el token:
   los 16 primeros hex del sha256 de `slug`, `hecho`, `texto`, `motivo` y el plan simulado.
2. Si el cliente soporta elicitation (la era del handshake de MCP), la tool enseña el plan y pide
   confirmar. Si el usuario acepta, aplica; si rechaza o cancela, devuelve el plan con
   `aplicado: false`.
3. Si el cliente no soporta elicitation, o la conexión es de la era 2026-07-28, que no tiene canal
   de vuelta, devuelve el plan y el token con `aplicado: false`. Para aplicar, se repite la llamada
   con `confirmacion` igual a ese token. Un token de otra petición, o de un plan que ha cambiado
   porque el estado se movió entre las dos llamadas, se rechaza sin escribir.

Con confirmación, ejecuta `novela cambio` sin `--simular`. Esa orden guarda la versión vigente en
`versiones/vN/`, registra la petición en `cambios/cam-NNN.json` y restablece la raíz. Las
precondiciones (novela terminada, sin cambio en curso, sin intervención viva) y sus mensajes son
los del CLI y vuelven como error de la tool.

**No regenera.** Devuelve `siguiente: "novela producir <slug>"`. Regenerar gasta cuota y dura
horas, así que no se dispara desde un cliente MCP. El panel lo hace con «reanudar», que pasa por
las guardas de `/lanzamientos`; a mano, con esa misma orden.

## Trazas en Langfuse

Cada llamada deja una traza `mcp.<tool>` con los argumentos, la duración y el error si lo hubo. No
se envía ni la prosa ni el PDF. Un argumento de más de 120 caracteres (el `texto` de
`request_change`) viaja recortado a 80 y con su longitud. La configuración es la de los scores
(`novela/plataforma/langfuse.py`): `TRACE_TO_LANGFUSE=true` y `LANGFUSE_*`, del entorno o de `.env`
en la raíz. Sin ellas no se envía nada. Si Langfuse falla, la tool responde igual. La traza se
envía con `POST /api/public/ingestion` y un evento `trace-create`.

## Conectarlo

**Claude Code.** El `.mcp.json` de la raíz ya declara `story-maker` por stdio. Basta con abrir
`claude` en la raíz y aprobar el servidor. Si lo prefieres a mano:

```bash
claude mcp add story-maker --env NOVELAS_DIR=../novelas -- uv run --directory backend python -m api.mcp
```

Para el transporte HTTP, con la API arrancada:

```bash
claude mcp add --transport http story-maker-http http://127.0.0.1:8000/mcp/
```

**Claude Desktop.** En `claude_desktop_config.json`, con rutas absolutas porque Desktop no arranca
en el repositorio:

```json
{
  "mcpServers": {
    "story-maker": {
      "command": "uv",
      "args": ["run", "--directory", "C:/ruta/al/repo/backend", "python", "-m", "api.mcp"],
      "env": { "NOVELAS_DIR": "C:/ruta/al/repo/novelas" }
    }
  }
}
```

**MCP Inspector.**

```bash
cd backend
NOVELAS_DIR=../novelas npx @modelcontextprotocol/inspector uv run python -m api.mcp
```

Para probar el HTTP, elige el transporte «Streamable HTTP» y pon la URL
`http://127.0.0.1:8000/mcp/`.

Para probar `request_change`, sobre una copia de una novela terminada y nunca sobre una que esté
generando:

```bash
cd backend
STORY_MAKER_MCP_ESCRITURA=1 NOVELAS_DIR=/tmp/novelas-prueba   npx @modelcontextprotocol/inspector uv run python -m api.mcp
```

En «Tools», `request_change` con `slug`, `hecho` y `texto`. El Inspector soporta elicitation, así
que enseña el plan y pide confirmar. Para el camino sin ella, copia el `confirmacion` de la
respuesta y repite la llamada con ese valor. Por HTTP, arranca uvicorn con la misma variable.

## Validadores y verificadores

- **Solo lectura.** `test_ninguna_tool_de_lectura_escribe` llama a las cinco tools de lectura
  sobre dos workspaces, uno con versiones y otro sin ellas, y comprueba que la `huella` de cada
  uno no cambia. También comprueba que todas llevan `readOnlyHint`. La base se abre con `mode=ro` y el PDF no pasa por
  el disco.
- **Esquema.** `test_get_chapter_rechaza` y `test_story_bible_rechaza_un_tipo_desconocido`
  prueban que la validación rechaza un slug con `..`, un capítulo fuera de rango, un tipo
  desconocido, una versión inexistente y una novela que no existe.
- **Versiones.** Hay un fixture con el formato en disco de la spec 0007: `versiones/v1/`,
  `versiones.json` y `meta.version = 2`. Con él se comprueba la lectura por versión y los
  capítulos cambiados. Si la spec 0007 cambia ese formato al fusionarse, este fixture es lo
  primero que debe fallar.
- **HTTP.** El servidor está montado en `/mcp/` y responde a `initialize`. Como `/lanzamientos`,
  rechaza un `Host` o un `Origin` ajenos (421 o 403), así que un ataque de DNS rebinding no llega
  a leer las novelas.
- **Escritura.** Los tests `test_request_change_*` corren el CLI de verdad como subproceso contra
  una copia de `demo-cambio` en un `NOVELAS_DIR` temporal. Comprueban que la tool está
  deshabilitada por defecto y sin la variable; que es destructiva; que valida los parámetros; que
  la simulación no cambia la huella; que un token incorrecto o de otra petición no aplica; que con
  el token correcto, o con la elicitation aceptada, existen `versiones/v1/` y
  `cambios/cam-001.json`; que la elicitation rechazada no escribe; que en la era sin canal de
  vuelta pide el token; que por HTTP rechaza un cliente que no es de loopback, y que la traza
  lleva el texto recortado.
- **Riesgo aceptado.** El token es un hash sin secreto: un cliente podría calcularlo sin haber
  visto el plan. No es autenticación. Obliga a que la aplicación sea una segunda llamada
  deliberada sobre un plan concreto, y quien puede llamar a la tool ya ha pasado la variable de
  entorno y el loopback.
- **Riesgo aceptado.** Si una preparación anterior se cortó (`estado: preparando`) y se repite la
  misma petición, `novela cambio --simular` la completa en vez de simular (RF-20). En ese caso la
  «simulación» escribe, pero solo termina una petición que ya se confirmó.
- **Langfuse.** Cada llamada, también las que fallan, emite una traza `mcp.<tool>`. Sin claves no
  hay ninguna salida de red, y con Langfuse caído la tool no se rompe.
- **Riesgo aceptado.** La traza se envía antes de devolver la respuesta, en un hilo aparte. Si
  Langfuse va lento, la respuesta puede tardar hasta `TIMEOUT_S` (5 s) más.
- **Riesgo aceptado.** `download_novel` importa `novela.slices.export` dentro de la función, para
  que `api.main` siga sin cargar `slices/` (`test_api_no_importa_slices`). De ese módulo solo usa
  lectores y `pdf.construir`, que devuelve bytes.

Los tests están en `backend/tests/test_mcp.py`. Usan el cliente en memoria de FastMCP contra
workspaces de `tests/fixtures/fabrica.py` y no llaman a ningún modelo.
