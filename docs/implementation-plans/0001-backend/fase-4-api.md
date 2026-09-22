# Fase 4 — API de lectura

**Objetivo.** Que el panel tenga de dónde leer, y de dónde generar sus tipos.

**Al terminar existe**: cinco `GET`, ningún verbo de escritura, y un OpenAPI commiteado que CI
mantiene al día.

**Cierra**: RF-24, RF-25. CA-25, CA-26, CA-29.

**Esta es la fase que puede posponerse.** No bloquea el bucle, y el frontend todavía no existe
(decisión 4 del README). Se implementa ahora porque es la más barata de las cuatro —los modelos
de respuesta ya existen desde la fase 1— y porque el OpenAPI es lo que desbloquea al frontend
cuando llegue. Si hay que recortar, se recorta esta entera; ninguna otra fase depende de ella.

Requiere la fase 1. No requiere las fases 2 ni 3.

---

## 4.1 — La app

**Construye**: `backend/api/main.py`.

**Rojo**: `tests/test_api.py::test_app_arranca`. `TestClient` monta la app y `/docs` responde.

**Verde**: la app FastAPI, con CORS para el dev server de Vite, y la apertura de `estado.db` con
`file:…?mode=ro` — la conexión de solo lectura de la tarea 1.10.

```bash
cd backend && uv run uvicorn api.main:app --reload
```

`fastapi` y `uvicorn` entran como dependencia aquí, no antes.

**Los modelos de respuesta son los de `backend/novela/dominio/`.** Una sola ontología: no hay
DTOs entre dominio y API, y `architecture.md` §3.0 lo descarta explícitamente. Si un campo hace
falta en el panel y no está en el estado, **se añade al estado**, no se calcula en el frontend.

FastAPI no contradice la regla de `AGENTS.md` de no añadir SDKs: esa regla es sobre proveedores
de modelos, y la API no llama a ninguno. CA-28 (tarea 1.17) lo sigue comprobando sobre el árbol
de imports de la API también.

**Commit**: `feat(api): app FastAPI de solo lectura`

---

## 4.2 — Validación del slug

**Va antes que los endpoints, no después.**

**Construye**: el validador de slug, compartido con el CLI.

**Rojo**: `tests/test_api.py::test_path_traversal`. `GET /novelas/..%2F..%2Fetc/estado` devuelve
**422** y **no toca el disco**. El «no toca el disco» se comprueba, no se supone: parchea la
apertura de ficheros y verifica que no se llamó.

**Verde**: el slug se valida contra `^[a-z0-9-]+$` **antes de construir ninguna ruta**.

`validators.md` §3.2 es claro sobre por qué esto va primero: `GET /novelas/{slug}/...` concatena
una cadena que viene de la URL con una ruta de disco, y es **la única superficie de inyección
real del sistema**. No hay usuarios, no hay datos personales y no hay autenticación que romper;
lo que hay es esto.

Es la misma regla que aplica `novela nueva` en la tarea 1.14. Compártela, no la dupliques: dos
copias de una regex de seguridad divergen.

**Cierra**: CA-26, RF-25.

**Commit**: `feat(api): validación de slug antes de construir ruta`

---

## 4.3 — Los cinco GET

**Construye**: `backend/api/routers/novelas.py`, `backend/api/routers/capitulos.py`.

**Rojo**: `tests/test_api.py::test_cinco_get_en_solo_lectura`. `TestClient` recorre los cinco
`GET` sobre el fixture **con el workspace montado en solo lectura durante toda la suite**. Si
algún endpoint intentara escribir, el sistema de ficheros lo impide y el test falla.

**Verde**:

| Método y ruta | Respuesta | Status |
|---|---|---|
| `GET /novelas` | lista de `{slug, cursor}` | 200 |
| `GET /novelas/{slug}/estado` | el documento de `architecture.md` §7.1 | 200 · 404 · 422 |
| `GET /novelas/{slug}/capitulos` | índice con frontmatter | 200 · 404 |
| `GET /novelas/{slug}/capitulos/{n}` | markdown del capítulo | 200 · 404 |
| `GET /novelas/{slug}/runs/{run_id}` | `manifest.json` | 200 · 404 |

Los capítulos y los manifiestos salen del disco tal cual. El estado se serializa desde
`estado.db` con los modelos del dominio.

**No hay ningún verbo de escritura, y no se añade ninguno.** Mutar una novela es trabajo del
orquestador por el CLI. Si un endpoint pareciera necesitar escribir, lo correcto es añadir un
subcomando al CLI, no un `POST` a la API (`architecture.md` §11.1).

El montaje en solo lectura durante toda la suite es lo que convierte esa regla en algo
comprobado en vez de acordado.

**Cierra**: CA-25, RF-24.

**Commit**: `feat(api): los cinco GET de lectura`

---

## 4.4 — OpenAPI commiteado

**Construye**: `backend/api/openapi.json` y su test.

**Rojo**: `tests/test_contratos.py::test_openapi_al_dia`. El OpenAPI commiteado coincide con el
que genera el código; falla porque el fichero no existe.

**Verde**: generar, commitear, y que CI falle si difieren.

Es el mismo mecanismo que `test_state_schema_al_dia` de la tarea 1.8, aplicado al otro contrato.
`validators.md` §3.8 explica por qué basta: para dos partes que viven en el mismo repo, el
esquema commiteado y un test de igualdad hacen el trabajo de Pact sin traerlo.

De aquí saldrán los tipos del frontend, generados — no escritos a mano. Es lo que impide que
deriven por su cuenta (`validators.md` §3.1).

**Cierra**: CA-29, RNF-05.

**Commit**: `test(contratos): OpenAPI commiteado al día`

---

## 4.5 — La API no importa nada de `slices/`

**Construye**: `tests/test_contratos.py::test_api_no_importa_slices`.

**Rojo**: recorre el árbol de imports de `api/` y falla si aparece cualquier módulo de
`novela/slices/`. Si pasa a la primera, añade temporalmente un import a un router y compruébalo
en rojo.

**Verde**: la comprobación.

**No es un criterio de aceptación de la spec: lo añade este plan.** La spec §5.5 afirma que no
hay ruta de código desde un `GET` a una escritura, y lo apoya en el montaje de solo lectura de la
tarea 4.3. Ese test cubre el efecto; este cubre la causa, y es el que da un mensaje de error
útil el día que alguien importe `delta/apply.py` desde un router «solo para reutilizar la
serialización».

La API puede importar `dominio/` y las partes de lectura de `plataforma/`. `slices/` es
escritura.

Cuesta cinco líneas y convierte una regla de disciplina en una regla comprobada. Es la misma
forma del test de la tarea 1.17.

**Commit**: `test(contratos): la API no alcanza ningún slice de escritura`

---

## Al cerrar la fase

```bash
cd backend && uv run pytest && uv run mypy --strict . && uv run ruff check .
uv run uvicorn api.main:app --reload    # y abrir /docs
```

Con esto la spec 0001 queda implementada. Lo que toca entonces:

1. Actualizar la tabla de trazabilidad de la spec §12: las 29 filas pasan de `pendiente` a
   `verde`.
2. Poner la spec en estado `implementada` con el sha del commit en el frontmatter.
3. Comprobar que los cuatro desfases de documentación del [README](README.md) se corrigieron en
   su commit y no quedó ninguno suelto.
4. Borrar este directorio. Un plan de ejecución de una spec implementada es ruido: lo que vale a
   partir de ahí es el código y la documentación de referencia.

Y queda pendiente lo que la spec deja fuera por diseño: `.claude/` está vacío —cero agentes, cero
hooks, cero slash commands—, así que el harness tiene backend pero no tiene quien lo invoque. Esa
es la spec 0002.
