# Fase 7: e2e, CI e2e, comprobaciones manuales y cierre

Plan: `README.md` · Spec: §5 (RF-40, RF-42, RF-45 y los criterios con parte e2e), §6 (RNF-03 a RNF-09, RNF-12 a RNF-16, RNF-21 a RNF-24), §11, §13 · Decisiones: D19, D27, D29, D30, D33, D35, D37, D54, D55, D56

Orden de la fase: T-16 → T-17 → T-21 → T-18 → T-22 → T-23. T-17 va antes de T-21 (PD1, D30). Los e2e corren contra la API real con `NOVELAS_DIR` apuntando a los workspaces que genera `panel.py` y contra `vite preview` en `localhost:5173`. `page.route` solo retrasa, vacía o hace fallar respuestas, nunca inventa datos. Ningún test llama a un modelo.

---

#### T-16 Generador de workspaces y e2e funcionales

- Descripción:
  - `backend/tests/fixtures/panel.py` con `generar(destino)` y `python -m tests.fixtures.panel <destino>`, con los tres workspaces de la spec §13 (PD6):
    - `demo-24`: `fabrica.construir(destino, "demo-24", fabrica.DEMO, cerrados=7)` y después `fabrica.preparar_capitulo(destino, "demo-24", fabrica.DEMO, 8)`, que deja el 8 en el índice sin aplicar (`fabrica.py:454-470`);
    - `recien-creada`: `fabrica.cli(destino, "nueva", "recien-creada", "--idea", …)`, sin plan ni checkpoints (`nueva` no abre run, `backend/novela/slices/nueva/cmd.py:34-60`);
    - `grande-999`: igual, con `--capitulos 999`.

    Durante la generación, `run.RAIZ_REPO` (`backend/novela/plataforma/run.py:51`) apunta a un directorio temporal sin `.env`, y `TRACE_TO_LANGFUSE` y `LANGFUSE_*` salen del entorno, como `_sin_claves_reales` (`backend/conftest.py:23-32`). Al terminar, los dos vuelven a su valor.
  - `frontend/playwright.config.ts`: proyectos `chromium` y `firefox`; `webServer` para la API (`uv run uvicorn api.main:app` desde `backend/` con `NOVELAS_DIR`) y para `vite preview --port 5173 --strictPort`; generación previa con `panel.py`.
  - Specs `frontend/e2e/recorrido.spec.ts`, `lectura.spec.ts`, `accesibilidad.spec.ts` y `resiliencia.spec.ts`, con escucha de `console.error` y `pageerror` en todas (RNF-16) y un espía de todas las peticiones, registrado en el contexto antes de la primera navegación. La escucha solo excluye, con una lista cerrada, los mensajes que el navegador emite por el fallo provocado a propósito en los escenarios sin WebGL, con `logo.png` que no carga y con la fuente display retrasada o fallida; un error del código del panel, Three.js incluido, cuenta siempre (D54).
- Orden TDD:
  1. Rojo, `backend/tests/test_fixtures_panel.py::test_generador_sin_claves`: con el autouse `_sin_claves_reales` desactivado para este test, `TRACE_TO_LANGFUSE=true` y `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` y `LANGFUSE_BASE_URL` fijados a `dummy-publica`, `dummy-secreta` y `http://ejemplo.invalid`, `run.RAIZ_REPO` apuntando a un directorio temporal con un `.env` de prueba con esos valores, y `langfuse.desde_entorno` sustituido por un registrador (patrón de `backend/novela/slices/checkpoint/test_checkpoint.py:157-181`). Primero, el control positivo: el test afirma que `os.environ["TRACE_TO_LANGFUSE"] == "true"` y que `run.RAIZ_REPO` tiene el `.env` de prueba. Después, ningún entorno registrado contiene esas claves, `run.RAIZ_REPO` apunta a un directorio sin `.env` durante la generación, y los dos se restauran al final (CA-42, D56). Para verlo en rojo por la razón correcta, se comprueba también con el aislamiento de `panel.py` quitado temporalmente.
  2. Rojo, `backend/tests/test_fixtures_panel.py::test_generador_como_orden`: un servidor HTTP local en `127.0.0.1` que cuenta las peticiones; `uv run python -m tests.fixtures.panel <tmp>` en un subproceso con las mismas variables y `LANGFUSE_BASE_URL` apuntando a ese servidor sale con 0, crea los tres workspaces y el servidor recibe 0 peticiones (CA-42, parte de la orden; D56).
  3. Verde: `panel.py`.
  4. Rojo, e2e, escritos antes de ajustar lo que falle en el panel:
     - `recorrido.spec.ts`: Inicio con dos entradas y sus enlaces (CA-08); recarga con `/lectura/3` (CA-10); recorrido de Lanzar sin descargas y solo `GET /novelas` (CA-16); `recien-creada` sin escaleta (CA-19); 0 peticiones no `GET` y 0 a otros orígenes, con el espía viendo `favicon.png`, el `.woff2` y `GET /novelas` como control positivo (RNF-06, RNF-08); almacenamiento y cookies vacíos (RNF-09); fuentes `.woff2` desde 5173 (CA-56, parte e2e); petición del favicon a 5173 (CA-61, parte e2e); ≤ 60 peticiones por minuto con `page.clock`, sin peticiones propias del estado de la API (RNF-05, D50).
     - `lectura.spec.ts`: `data-volumenes="24"` y estados de CA-24; abrir el 3 con `GET /novelas/demo-24/capitulos/3` y el `titulo` de su índice (CA-25); el capítulo hostil de CA-26 en un workspace sintético, sin elementos activos y sin peticiones a `ejemplo.invalid` (CA-26, parte e2e); Chromium sin WebGL (CA-29); cámara con `prefers-reduced-motion` emulado (CA-30); `data-draw-calls` entre 1 y 5 con `demo-24` y `grande-999`, leído tras dos `requestAnimationFrame`, solo en Chromium (RNF-03).
     - `accesibilidad.spec.ts`: axe con reglas WCAG 2.1 A y AA, 0 `serious` y 0 `critical` en Inicio, Lanzar, Progreso y Lectura con el lector abierto (RNF-12); recorrido completo solo con teclado (RNF-13, CA-28).
     - `resiliencia.spec.ts`: rutas abortadas 60 s con `page.clock`; al volver la API, datos nuevos en ≤ 1 ronda sin recargar (RNF-15); aviso de CA-04 con datos conservados.
  5. Verde: los ajustes del panel que los e2e destapen, cada uno con su unitario si es lógica.
- Archivos: `backend/tests/fixtures/panel.py` (nuevo) · `backend/tests/test_fixtures_panel.py` (nuevo) · `frontend/playwright.config.ts` (nuevo) · `frontend/e2e/{recorrido,lectura,accesibilidad,resiliencia}.spec.ts` (nuevos) · `frontend/package.json` (modificar: script `e2e` y devDependencies de Playwright y axe) · `docs/validators.md` §3.5 y §5 (modificar)
- Cubre: RF-04, RF-08, RF-10, RF-16, RF-19, RF-24, RF-25, RF-26, RF-28, RF-29, RF-30, RF-42, RF-45, RF-56, RF-61, RNF-03, RNF-05, RNF-06, RNF-07, RNF-08, RNF-09, RNF-12, RNF-13, RNF-14, RNF-15, RNF-16
- Criterios: CA-08, CA-10, CA-16, CA-19, CA-24, CA-25, CA-26, CA-28, CA-29, CA-30, CA-42; CA-04, CA-56 y CA-61 en su parte e2e
- Documentación: `docs/validators.md` §3.5, con los e2e del panel sobre workspaces sintéticos, y §5, con los riesgos U de la spec §13: calidad de la escena, WebGL por software en CI, API sin autenticación y colisión con escrituras atómicas en Windows. Cada uno con su condición de revisión.
- Depende de: T-09, T-11, T-12, T-14, T-15
- Hecho cuando: `test_generador_sin_claves` y `test_generador_como_orden` se han visto en rojo y pasan; `npx playwright test` en verde en Chromium y Firefox en local; `uv run pytest`, `mypy --strict` y `ruff` en verde en `backend/`; `npm run verificar` en verde.
- Complejidad: L

#### T-17 Job `frontend-e2e` en CI

- Descripción: job `frontend-e2e` en `.github/workflows/ci.yml` dentro de la imagen oficial de Playwright (la de la versión fijada en el lockfile): `astral-sh/setup-uv` y `uv sync --locked` en `backend/`, `actions/setup-node` con `node-version: 24` (D35), `npm ci`, `npx playwright install` si la imagen no trae los navegadores de la versión fijada, generación de workspaces con `python -m tests.fixtures.panel`, `npm run build` y `npm run e2e`. El workflow falla si falla cualquier paso.
- Orden: tarea de infraestructura sin lógica propia. Se verifica con un e2e roto a propósito en una rama de prueba, que hace fallar el job; se anota en el PR y la rama no se fusiona.
- Archivos: `.github/workflows/ci.yml` (modificar) · `docs/validators.md` §6 y §2 (modificar)
- Cubre: RF-40, RF-45, RNF-14
- Criterios: CA-40 en su parte e2e
- Documentación: `docs/validators.md` §6, fila «CI del harness» con el job `frontend-e2e`, y párrafo de estado de §2 (D33).
- Depende de: T-08, T-16
- Hecho cuando: el job sale verde en la rama y rojo en la rama de prueba; los jobs `backend` y `frontend` siguen en verde.
- Complejidad: M

#### T-21 e2e de marca y regresión visual

- Descripción:
  - `frontend/e2e/marca.spec.ts` (solo Chromium): barra lateral con su contenido, `aria-current` y estado de la API, también con la API caída (CA-48); plegado y recarga con el almacenamiento vacío (CA-50); cada `img` de `logo.png` con `alt="Qaracter"`, `--q-tamano-logo`, cuatro radios iguales al 22 % del lado y `overflow` `hidden` o `clip`, más el píxel de la esquina superior izquierda con el color del fondo de la barra, con la barra desplegada y plegada (CA-51); caja del texto del banner en su mitad izquierda (CA-53); rejilla de dos columnas a 1440 px, una a 1024 px y ningún desplazamiento horizontal (CA-54); ningún elemento de RF-59, con `lang="es"` y `color-scheme: light` (CA-59); `getComputedStyle` de cada medida de la spec §8.4 (RNF-23); Tab por todos los interactivos con `outline` ≥ 2 px en `--q-foco` o `--q-foco-sobre-oscuro` (RNF-24); CLS ≤ 0,1 por vista con `PerformanceObserver` de `layout-shift` (RNF-21); foco visible con `forced-colors: active` y `transition-duration` 0 s con reduced motion (CA-57).
  - `frontend/e2e/visual.spec.ts` (solo Chromium, 1440 × 900, canvas y horas enmascarados, reloj fijo): una captura por vista en datos, carga, vacío y error (CA-58) y por componente interactivo en cada estado (CA-57), más el banner (CA-53), con `maxDiffPixelRatio` de 0,001 (RNF-22). Las referencias se generan y validan en la imagen de Playwright del job `frontend-e2e` (PD1) y solo muestran los workspaces sintéticos (RF-60).
- Orden TDD:
  1. Rojo: `marca.spec.ts` antes de cualquier ajuste de estilo.
  2. Primera ejecución de `visual.spec.ts` en el contenedor: genera las referencias; una segunda ejecución sin cambios pasa y una con un token alterado a propósito falla (se comprueba y se revierte).
  3. Verde: ajustes de CSS que destapen las medidas, siempre con roles de `tokens.css`.
- Archivos: `frontend/e2e/marca.spec.ts` (nuevo) · `frontend/e2e/visual.spec.ts` (nuevo) · referencias de `visual.spec.ts` (nuevas, en la carpeta que fije Playwright) · `frontend/src/**/*.css` y `frontend/src/shared/ui/*` (modificar si hace falta) · `docs/validators.md` §3.5 y §5 (modificar)
- Cubre: RF-45, RF-48, RF-50, RF-51, RF-53, RF-54, RF-57, RF-58, RF-59, RNF-21, RNF-22, RNF-23, RNF-24
- Criterios: CA-48, CA-50, CA-51, CA-53, CA-54, CA-57, CA-58, CA-59
- Documentación: `docs/validators.md` §3.5, con la regresión visual y el e2e de marca, y §5, con el riesgo U del juicio estético y su condición de revisión.
- Depende de: T-16, T-17
- Hecho cuando: `marca.spec.ts` se ha visto en rojo y pasa; `visual.spec.ts` pasa en el job `frontend-e2e` y falla con el token alterado; `configuracion.test.ts` (CA-60) sigue en verde con las referencias nuevas; referencias pendientes de aprobación en T-22.
- Complejidad: L

#### T-18 Demostración en la máquina de desarrollo (manual)

- Descripción: sin código ni TDD, y una sola vez, al cerrar la spec (D55). Con la API y el panel arrancados sobre un workspace de `panel.py` en la máquina de desarrollo (Windows), Progreso y Lectura abiertos mientras un conductor a mano, desde `backend/` con `uv run python` y sin versionar, cierra capítulos con `fabrica.cerrar_capitulo` y el CLI real (D33). Se mide la mediana de fps de la escena durante 10 s navegando `demo-24` y se busca `PermissionError` en los `harness.log` del workspace.
- Archivos: `docs/specs/0004/spec.md` §13, «Resultados de las comprobaciones manuales» (modificar: solo el resultado, con la fecha y sin nombres de persona). Las únicas ediciones de la spec que prevé este plan son las de T-18, T-22 y T-23, y las prevé la propia spec.
- Cubre: RF-22, RF-24, RNF-04
- Criterios: RNF-04 ≥ 30 fps; ninguna escritura agota sus reintentos de `backend/novela/plataforma/atomic.py`
- Depende de: T-16
- Hecho cuando: el resultado está anotado en la spec §13 con la orden exacta del conductor, los fps medidos, la versión del navegador, el recuento de `PermissionError` y la fecha. Si RNF-04 no se cumple, se abre el riesgo U correspondiente de `docs/validators.md` §5 en lugar de darlo por bueno.
- Complejidad: S

#### T-22 Revisión visual manual (manual)

- Descripción: sin código ni TDD. Un revisor consulta la captura de referencia fuera del repositorio y marca M-01 a M-12 (spec §13) como conforme, no conforme o desviación aceptada con su motivo, y aprueba las referencias de T-21. Si hay no conformidades, se corrigen en un ciclo TDD nuevo (T-21 o la tarea de la vista) y se repite la revisión. Se repite también cada vez que cambian `tokens.css`, `shared/ui/` o `shared/marca/`, también después de cerrar la spec; no entra en `docs/validators.md` §6, porque es manual (D55).
- Archivos: `docs/specs/0004/spec.md` §13, «Resultados de las comprobaciones manuales» (modificar: cada punto, el rol del revisor —sin su nombre— y la fecha de aprobación de las referencias)
- Cubre: RF-47, RF-48, RF-51, RF-53, RF-54, RF-57, RF-60, RNF-22
- Criterios: M-01 a M-12
- Depende de: T-21
- Hecho cuando: los 12 puntos están conformes o con la desviación aceptada y su motivo, y las referencias de T-21 constan como aprobadas.
- Complejidad: S

#### T-23 Cierre de la spec

- Descripción: el commit que cierra la spec, según `AGENTS.md` § Proceso: modificar documentación (D29, D37):
  - sube a `docs/validators.md` lo que perdura de `docs/specs/0004/validators.md` § Al implementar: los métodos de §2 y §3.1 a §3.8, incluida §3.6 (propiedades del entrecomillado de la idea y de `cortar_tramo`); §4.4 (`server.fs.allow` y `strictPort`, el cliente único de `GET`, el único sumidero de HTML en `lector.ts` y la importación de `logo.png` reservada a `logo.ts`); §4.7 (presupuestos y versión de la imagen de Playwright); §4.9 (la amenaza 2 llevada al navegador, con el capítulo hostil ampliado); y los riesgos U de §5, incluidos el de la orden pegada en el prompt de Claude Code y el de la línea de log de más de 1 MiB;
  - borra `docs/specs/0004/plan/` y `docs/specs/0004/validators.md`;
  - pasa la spec a estado `implementada`, con el sha del commit en el frontmatter.
- Orden: tarea de documentación sin código ni TDD.
- Archivos: `docs/validators.md` (modificar) · `docs/specs/0004/spec.md` (modificar: frontmatter) · `docs/specs/0004/plan/` (borrar) · `docs/specs/0004/validators.md` (borrar)
- Cubre: RF-45
- Criterios: CA-45, parte de cierre
- Depende de: T-18, T-22
- Hecho cuando: `docs/validators.md` §3.6, §4.4, §4.7 y §4.9 nombran lo anterior; `grep` en `docs/validators.md` de «no hay `frontend/`» y en `docs/architecture.md` de «produce un `config.yaml`» y «se añade al estado» no encuentra nada; `plan/` y `validators.md` ya no existen; la spec está en `implementada` con su sha.
- Complejidad: S
