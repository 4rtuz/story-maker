# Fase 2: Cimientos del frontend y contrato de tipos

Plan: `README.md` · Spec: §5 (RF-01, RF-02, RF-39, RF-41, RF-43, RF-44), §8.2, §8.4 (scripts, configuración, pre-commit) · Decisiones: D13, D15, D18, D20, D33, D35, D36, D40, D56

T-04 puede empezar en paralelo con la fase 1; T-05 necesita el OpenAPI final de T-03. Desde T-04, cada commit que toque `frontend/` pasa `npm run verificar`. Si toca también `backend/`, pasa además la tríada del backend.

Nada de lo que la spec afirma sobre las herramientas npm está en el repositorio todavía (no hay `package.json`). Cada suposición —`strictPort`, `server.fs.strict`/`allow`, el formato de `openapi-typescript`— queda cubierta por un test en rojo antes de la configuración, sobre Node 24 LTS (D35).

---

#### T-04 Esqueleto de `frontend/`, pre-commit y convención

- Descripción: crea el proyecto con `dependencies` exactamente `three` y `markdown-it` y `"engines": {"node": ">=24 <25"}` (D35). Incluye:
  - `vite.config.ts`: `server` y `preview` en `localhost:5173` con `strictPort`, `server.fs.strict` y `server.fs.allow: ['.']`, y la configuración de Vitest.
  - `tsconfig.json` con `strict: true`.
  - `eslint.config.js` solo con las reglas que prueba esta tarea (PD2, D33): imports fuera de `src/` (en particular de `novelas/` y `backend/`) y `eslint-plugin-no-unsanitized`, sin excepciones por fichero (D56).
  - `index.html` con `lang="es"` (RF-59, parte estática) y `src/main.ts` mínimo.
  - Scripts `dev`, `build`, `preview`, `lint`, `typecheck`, `test` y `verificar` de la spec §8.4. `verificar` encadena `lint`, `typecheck` y `test`; gana `tipos:comprobar` en T-05 y `build` y `presupuesto` en T-08, de modo que es lo único que se ejecuta antes de commitear (D40).
  - Cliente con `VITE_API_URL` o `http://127.0.0.1:8000` por defecto, solo la resolución de la URL; el cliente completo es de T-06.
  - Fuera de `frontend/`: `.gitignore` gana `frontend/node_modules/`, `frontend/dist/`, `frontend/.env*`, `frontend/test-results/` y `frontend/playwright-report/`; `.githooks/pre-commit` gana el paso 3 (spec §8.4, detrás de `ruff`, `.githooks/pre-commit:14-17`); `AGENTS.md` gana una línea en el paso 5.
- Orden TDD:
  1. Rojo, `frontend/src/servidor.test.ts`: con el puerto 5173 ocupado, el arranque falla; libre, escucha en `http://localhost:5173`. Con `createServer` sobre `frontend/vite.config.ts`, arrancado una vez desde `frontend/` y otra desde la raíz del repositorio: `/@fs/<raíz>/frontend/src/main.ts` responde 200 (control positivo, D56); `/@fs/<raíz>/AGENTS.md` responde 403; y las variantes de CA-43 —`/@fs/<raíz>/novelas/demo-24/canon/misterio.md` sobre un workspace sintético, `/@fs/<raíz>/backend/api/main.py`, `/@fs/<raíz>/frontend/../AGENTS.md`, `/%2e%2e/AGENTS.md`, `/../AGENTS.md` y `/src/../../AGENTS.md?raw`— no responden 200 y ningún cuerpo contiene `# AGENTS.md` ni texto del canon (CA-01, CA-43 segunda mitad, RNF-10). Una prueba unitaria de la URL base sin `VITE_API_URL` (CA-01, tercera parte), en `frontend/src/shared/api/cliente.test.ts`.
  2. Rojo, `frontend/src/lint.test.ts`: la API de ESLint sobre fixtures de `frontend/test/fixtures/lint/` —un import de `../../novelas/demo/canon/misterio.md?raw`, otro de `../../backend/` y una asignación a `innerHTML`— da error (CA-43).
  3. Rojo, `frontend/src/configuracion.test.ts`: `dependencies` es exactamente `three` y `markdown-it`, y ni `dependencies` ni `devDependencies` contienen los paquetes de CA-44.
  4. Rojo, `backend/tests/test_contratos.py::test_pre_commit_frontend`: con el patrón de `test_sin_claves_versionadas` (`test_contratos.py:36-57`), un repositorio temporal con `.githooks/pre-commit` y un `npm` falso delante en el `PATH` que registra sus argumentos y sale con 1; un commit con un fichero de `frontend/` se aborta y registra `--prefix frontend run lint`; otro sin ficheros de `frontend/` no invoca `npm`; el test comprueba que el registro del `npm` falso existe, para no pasar con el `npm` real (CA-41). Debe pasar en local en Windows con Git Bash en el `PATH`, no solo en CI (D36).
  5. Verde: configuración, scripts, hook, `.gitignore` y línea de `AGENTS.md`.
- Archivos: `frontend/package.json` (nuevo) · `frontend/package-lock.json` (nuevo) · `frontend/vite.config.ts` (nuevo) · `frontend/tsconfig.json` (nuevo) · `frontend/eslint.config.js` (nuevo) · `frontend/index.html` (nuevo) · `frontend/src/main.ts` (nuevo) · `frontend/src/shared/api/cliente.ts` (nuevo, solo la URL base) · `frontend/src/servidor.test.ts` (nuevo) · `frontend/src/lint.test.ts` (nuevo) · `frontend/src/configuracion.test.ts` (nuevo) · `frontend/src/shared/api/cliente.test.ts` (nuevo) · `frontend/test/fixtures/lint/*` (nuevo) · `.gitignore` (modificar) · `.githooks/pre-commit` (modificar) · `backend/tests/test_contratos.py` (modificar) · `AGENTS.md` (modificar) · `docs/architecture.md` §3.1 (modificar) · `docs/validators.md` §2, §3.1, §3.2, §6 (modificar)
- Cubre: RF-01, RF-41, RF-43, RF-44, RF-45, RF-59 (parte estática), RNF-10
- Criterios: CA-01, CA-41, CA-43, CA-44
- Documentación:
  - `docs/architecture.md` §3.1 (`:266-275`): árbol real de `frontend/`; `lanzar/` sin «generación de config.yaml» (D5) y `progreso/` sin «cuota» (D3).
  - `docs/validators.md` §2: el párrafo de estado ya no dice que no hay `frontend/` (CA-45); §3.1: `tsc --noEmit`; §3.2: patrones de eslint del frontend (imports de fuera, `no-unsanitized`); §6: fila de pre-commit con el paso de eslint.
  - `AGENTS.md` § Proceso: generar código, paso 5: «en `frontend/`, `npm run verificar`» (una línea; D20). Basta porque `verificar` encadena todo lo que se ejecuta antes de commitear (D40).
- Depende de: —
- Hecho cuando: los cuatro tests se han visto en rojo y pasan, también en Windows con Git Bash; `npm ci && npm run verificar` sale con 0 desde `frontend/` con Node 24 (sin `tipos:comprobar` hasta T-05); `uv run pytest`, `mypy --strict` y `ruff` en verde en `backend/`; con `git config core.hooksPath .githooks`, un commit real que toca `frontend/` ejecuta eslint.
- Complejidad: L

#### T-05 Tipos generados desde el OpenAPI

- Descripción: scripts `tipos` (`openapi-typescript ../backend/api/openapi.json -o src/shared/api/esquema.gen.ts`) y `tipos:comprobar` (`tipos` más `git diff --exit-code src/shared/api/esquema.gen.ts`), `esquema.gen.ts` generado y commiteado, y `tipos:comprobar` al principio de `verificar` (D40). El fichero generado queda fuera de eslint y de la regla de CA-02.
- Orden TDD:
  1. Rojo, `frontend/src/contrato.test.ts`: fuera de `esquema.gen.ts`, ninguna declaración `interface` ni `type` de `frontend/src/` lleva el nombre de un esquema de `components.schemas` de `backend/api/openapi.json` (CA-02, segunda mitad). Para verlo en rojo hace falta un fichero de fixture con una declaración prohibida.
  2. Rojo, CA-39: con `openapi.json` alterado en una copia de trabajo, `npm run tipos:comprobar` sale con código distinto de 0 y nombra `src/shared/api/esquema.gen.ts`. Se comprueba aquí a mano; en CI corre desde T-08.
  3. Verde: scripts y fichero generado.
- Archivos: `frontend/package.json` (modificar) · `frontend/src/shared/api/esquema.gen.ts` (nuevo, generado) · `frontend/src/contrato.test.ts` (nuevo) · `frontend/eslint.config.js` (modificar: ignora el generado) · `docs/validators.md` §3.8 (modificar)
- Cubre: RF-02, RF-39, RF-45
- Criterios: CA-02, CA-39
- Documentación: `docs/validators.md` §3.8 (`:141`), contrato API ↔ frontend: `npm run tipos:comprobar` y en qué job de CI corre.
- Depende de: T-03 (OpenAPI final de la fase 1), T-04
- Hecho cuando: `npm run tipos:comprobar` sale con 0 sobre el árbol limpio y con distinto de 0 tras tocar `openapi.json`; `contrato.test.ts` se ha visto en rojo y pasa; `npm run verificar` en verde.
- Complejidad: S
