---
name: validar-visual
description: Valida en un navegador (Playwright MCP) la lectura web de una novela del panel —portada y dedicatoria, índice navegable y ficha de personajes y lugares— y registra el resultado con `novela registrar-visual`. Usar al terminar una novela o tras tocar la lectura, en una sesión de desarrollo del harness, no en una sesión del harness.
---

# Validar visualmente la lectura de `<slug>`

Referencia: `docs/validacion-visual.md` (qué se comprueba y por qué) y `docs/lectura-web.md`.
Nada de esto llama a un modelo salvo tú; no escribas en `novelas/<slug>/` a mano.

## 1. Arrancar API y panel

La API tiene que estar en `127.0.0.1:8000` y el panel en `localhost:5173`: son la URL que el build
lleva por defecto y el único origen que admite el CORS. Si están ocupados por otra sesión, para y
avisa; no cambies los puertos.

```bash
cd backend  && NOVELAS_DIR=<directorio con la novela> uv run uvicorn api.main:app --port 8000   # en segundo plano
cd frontend && npm run build && npx vite preview --port 5173 --strictPort                      # en segundo plano
```

Comprueba `GET http://127.0.0.1:8000/novelas/<slug>/libro` (200) y guarda su JSON: es lo esperado.

## 2. Inspeccionar con el navegador MCP

Servidor `playwright` de `.mcp.json` (`cmd /c npx @playwright/mcp@latest --browser chromium …`).
Si falla con «Browser … is not installed», ejecuta una vez
`cmd /c npx @playwright/mcp@latest install-browser chrome-for-testing`.

1. `browser_resize` 1440 × 900 y `browser_navigate` a `http://localhost:5173/#/novelas/<slug>/lectura`;
   `browser_wait_for` el texto «Personajes y lugares».
2. `browser_snapshot`. En el árbol:
   - **portada**: el heading de nivel 3 de la región «Libro» es el `titulo` del JSON.
   - **dedicatoria**: el párrafo bajo él es la `dedicatoria` del JSON. Si el JSON trae `null` en una
     novela de regalo, es fallo.
   - **índice**: en `navigation "Índice"`, un `link "N. título"` por capítulo cerrado
     (`capitulo` de `GET …/checkpoint`) y con el mismo título.
   - **ficha**: cada personaje y lugar del JSON, con al menos un `link "Capítulo N — título"`.
3. Navegación: `browser_click` recibe `target` (una ref del snapshot o un selector), no `ref`. Los
   `data-testid` son estables: `[data-testid="indice-capitulo"][data-destino="N"]`,
   `[data-testid="ficha-enlace"] >> nth=K`. Para **cada** enlace del índice y el primero de cada
   entrada de la ficha: clic, `browser_snapshot`, comprueba que hay un `dialog` cuyo heading es el
   título del capítulo y que tiene texto, y `browser_press_key` Escape.
4. `browser_take_screenshot` de la portada, de un capítulo abierto y del libro entero
   (`fullPage`). Míralas: el snapshot no ve maquetación (numeración duplicada, listas
   interminables, texto cortado). Pocas y pequeñas; si van a la documentación, a `docs/img/`.
5. `browser_close`.

Si no hay navegador MCP disponible, el equivalente determinista es
`VISUAL_SLUG=<slug> VISUAL_INFORME=<fichero> npx playwright test e2e/libro.spec.ts --project=chromium`
desde `frontend/` (necesita los puertos libres: arranca él los servidores con `CI=1`). Solo sobre
los workspaces sintéticos de `e2e/preparar.ts`: su preparación **borra** `PANEL_NOVELAS_DIR`, así
que nunca lo apuntes a `novelas/` del repo.

## 3. Registrar el resultado

Escribe el informe **fuera del workspace** (en el scratchpad) contra
`backend/schemas/qa-visual.schema.json`:

```json
{"schema_version": "1.0.0", "slug": "<slug>", "herramienta": "playwright-mcp",
 "comprobaciones": [{"id": "portada", "ok": true, "detalle": "…"}, …],
 "capturas": ["docs/img/…png"]}
```

Una comprobación por `id`: `portada`, `dedicatoria`, `indice`, `navegacion`, `ficha`. La que falla
lleva `responsable`, el rol al que se devuelve:

| Síntoma | `responsable` |
|---|---|
| Falta contenido de la novela: capítulo sin título o sin texto, ningún personaje en la ficha | `escritor` |
| El JSON de `/libro` está mal: sin dedicatoria con brief, capítulos de menos, entrada sin capítulos | `exportacion` |
| El JSON está bien y la página no lo pinta o un enlace no abre su capítulo | `frontend` |

Después, desde `backend/`: `NOVELAS_DIR=<…> uv run novela registrar-visual <slug> --fichero <informe>`.
Guarda `qa/visual.json`, emite el score `visual_lectura` y sale con 1 si algo falla, con la línea
`devolver a: <rol> (<id>), …`. Informa de esa línea tal cual; no corrijas tú el capítulo.
