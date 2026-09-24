# Servidor MCP

Un servidor [MCP](https://modelcontextprotocol.io) de solo lectura para consultar y descargar las
novelas de `novelas/`. Está hecho con FastMCP (`backend/api/mcp/`) y se sirve de dos formas:

- **Streamable HTTP**, montado en la API: `http://127.0.0.1:8000/mcp/` cuando corre
  `uvicorn api.main:app`.
- **stdio**: `uv run python -m api.mcp` desde `backend/`, para Claude Desktop, Claude Code o el
  MCP Inspector.

Las dos leen los workspaces de `NOVELAS_DIR` (por defecto `novelas/` relativo al directorio de
trabajo), como la API.

## Tools

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

## Trazas en Langfuse

Cada llamada deja una traza `mcp.<tool>` con los argumentos, la duración y el error si lo hubo. No
se envía ni la prosa ni el PDF. La configuración es la de los scores
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

## Validadores y verificadores

- **Solo lectura.** `test_ninguna_tool_escribe` llama a todas las tools sobre dos workspaces, uno
  con versiones y otro sin ellas, y comprueba que la `huella` de cada uno no cambia. También
  comprueba que todas llevan `readOnlyHint`. La base se abre con `mode=ro` y el PDF no pasa por
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
- **Langfuse.** Cada llamada, también las que fallan, emite una traza `mcp.<tool>`. Sin claves no
  hay ninguna salida de red, y con Langfuse caído la tool no se rompe.
- **Riesgo aceptado.** La traza se envía antes de devolver la respuesta, en un hilo aparte. Si
  Langfuse va lento, la respuesta puede tardar hasta `TIMEOUT_S` (5 s) más.
- **Riesgo aceptado.** `download_novel` importa `novela.slices.export` dentro de la función, para
  que `api.main` siga sin cargar `slices/` (`test_api_no_importa_slices`). De ese módulo solo usa
  lectores y `pdf.construir`, que devuelve bytes.

Los tests están en `backend/tests/test_mcp.py`. Usan el cliente en memoria de FastMCP contra
workspaces de `tests/fixtures/fabrica.py` y no llaman a ningún modelo.
