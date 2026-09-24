# Fase 4: Cliente, sondeo, `app/` y CI del frontend

Plan: `README.md` · Spec: §5 (RF-03 a RF-10, RF-39, RF-40, RF-48 a RF-50, RF-58, RF-59), §8.4 (cliente, rutas, recursos por vista, mensajes, estructura) · Decisiones: D10, D13, D15, D18, D24, D27, D33, D35, D40, D41, D45, D50, D52

Los unitarios usan Vitest con jsdom, `fetch` sustituido por un espía y el reloj simulado de Vitest; nunca esperas por tiempo real.

---

#### T-06 Cliente `GET`, sondeo y aviso de error

- Descripción:
  - `frontend/src/shared/api/cliente.ts`: una función por `GET` —los diez de la spec §8.4—, tipada desde `esquema.gen.ts`, con `method: 'GET'`, solo la cabecera `Accept` y una señal que combina la de la vista con un plazo de 5 s.
  - `frontend/src/shared/api/errores.ts`: `ErrorDeApi = {tipo: 'red' | 'tiempo' | 'http', status?, detalle}`, con los textos fijos de la spec §8.4 («API no disponible en <url>», «la API no respondió en 5 s») y el `detail` de la respuesta cuando lo trae.
  - `frontend/src/shared/sondeo.ts`: cadencias por recurso (10 s y 3 s), sin solapar peticiones del mismo recurso, pausa con `document.visibilityState === 'hidden'`, ronda inmediata al volver y cancelación de temporizadores y señales al desmontar la vista. Cada ronda informa si es correcta: lo es solo si todos sus recursos han respondido bien, con el 404 de `…/escaleta` y el 416 del log como respuestas correctas (D45). De ese resultado se derivan, sin peticiones propias, la hora de «Actualizado a las …» y el estado de la API de la barra lateral (D50).
  - Aviso de error que conserva los últimos datos válidos y desaparece en la siguiente ronda correcta (RF-04, D45).
  - Regla de eslint que prohíbe `fetch`, `XMLHttpRequest`, `WebSocket` y `EventSource` fuera de `src/shared/api/` (PD2, D33).
- Orden TDD:
  1. Rojo, `frontend/src/shared/api/cliente.test.ts`: cada función llama con `GET` y solo `Accept`; 404 con `detail`, fallo de red y plazo de 5 s producen el `ErrorDeApi` y el texto esperados (CA-03, primera mitad; CA-04, parte unitaria).
  2. Rojo, `frontend/src/lint.test.ts`: un fixture que usa `fetch`, `XMLHttpRequest`, `WebSocket` o `EventSource` fuera de `src/shared/api/` da error (CA-03, segunda mitad).
  3. Rojo, `frontend/src/shared/sondeo.test.ts`: con seis recursos a 10 s, en 30 s cada uno se pide 4 veces; una petición que tarda 15 s impide la de t = 10 s; con la pestaña oculta 60 s no hay peticiones y al volver hay una ronda antes de 100 ms; al desmontar, las señales quedan abortadas y en 30 s no hay más peticiones; recuento ≤ 60 por minuto en Progreso; una ronda con un recurso fallido no es correcta y la siguiente en la que todos responden bien sí, y un 404 de `…/escaleta` o un 416 del log no la hacen incorrecta (CA-05, CA-06, CA-07, RNF-05; CA-04, parte del aviso que desaparece).
  4. Verde.
- Archivos: `frontend/src/shared/api/cliente.ts` (modificar) · `frontend/src/shared/api/errores.ts` (nuevo) · `frontend/src/shared/sondeo.ts` (nuevo) · `frontend/src/shared/ui/aviso.ts` (modificar si hace falta, de T-20) · `frontend/eslint.config.js` (modificar) · `frontend/src/shared/api/cliente.test.ts` (modificar) · `frontend/src/shared/sondeo.test.ts` (nuevo) · `frontend/src/lint.test.ts` (modificar) · `frontend/test/fixtures/lint/*` (nuevos)
- Cubre: RF-03, RF-04, RF-05, RF-06, RF-07, RNF-05 (parte unitaria)
- Criterios: CA-03, CA-05, CA-06; CA-04 y CA-07 en su parte unitaria
- Documentación: ninguna asignada.
- Depende de: T-05
- Hecho cuando: los tres tests se han visto en rojo y pasan; `npm run verificar` en verde.
- Complejidad: M

#### T-07 Rutas, layout de marca e Inicio

- Descripción:
  - `frontend/src/app/rutas.ts`: rutas por hash de la spec §8.4; slug contra `^[a-z0-9-]+$` y capítulo contra `^[1-9][0-9]{0,2}$`, sin normalizar, antes de cualquier petición (D41); «ruta no válida»; al cambiar de vista, desmonta la anterior (RF-07) y refleja vista, novela y capítulo en el hash (RF-10).
  - `frontend/src/app/layout.ts`: barra lateral de 270 px con el logo de `logo.ts`, «Navegación» con «Novelas» y «Lanzar», el bloque de la novela de la ruta con «Progreso» y «Lectura», `aria-current="page"` en el ítem activo y la zona inferior con «API conectada»/«API sin respuesta» y la URL, derivada de las rondas de la vista, o «sin datos» en una ruta inválida (D50); barra superior con el botón de plegar (`aria-expanded`, `aria-controls`), el título de la vista y «Actualizado a las <hora>» de la última ronda correcta; plegado a 72 px sin guardar nada en el navegador.
  - `frontend/src/app/inicio.ts`: una subtarjeta por novela de `GET /novelas` con slug, `capitulo`, `fase` y `ultimo_paso`, enlaces a Progreso, Lectura y Lanzar, botón primario «Lanzar una novela», esqueleto, vacío («todavía no hay novelas: lanza la primera») y error.
  - Sin avatar, notificaciones, bienvenida, conmutador de modo oscuro ni selector de idioma (RF-59).
- Orden TDD:
  1. Rojo, `frontend/src/app/rutas.test.ts`: `#/novelas/..%2Fetc/progreso`, `#/novelas/Demo/progreso`, `#/novelas/demo-24/lectura/0`, `…/lectura/07`, `…/lectura/+3` y `…/lectura/1000` muestran «ruta no válida» sin peticiones, sin normalizar la ruta y con «sin datos» en la zona de estado; cambiar de vista desmonta la anterior; el hash refleja el capítulo abierto (CA-09; CA-07 y CA-10, parte unitaria).
  2. Rojo, `frontend/src/app/inicio.test.ts`: dos novelas dan dos entradas con los tres enlaces; `[]` da el texto de vacío; un fallo da el aviso (CA-08 y CA-58, parte unitaria).
  3. Rojo, `frontend/src/app/layout.test.ts`: estructura y `aria-current` de CA-48; «Actualizado a las 10:00:00» que no cambia tras una ronda fallida (CA-49); plegado con 72 px, nombres accesibles, «Desplegar barra lateral» y `aria-expanded="false"`, y nada en `localStorage`, `sessionStorage` ni cookies (CA-50, parte unitaria); ningún elemento de RF-59 (CA-59, parte unitaria).
  4. Verde.
- Archivos: `frontend/src/app/rutas.ts` (nuevo) · `frontend/src/app/layout.ts` (nuevo) · `frontend/src/app/inicio.ts` (nuevo) · `frontend/src/main.ts` (modificar) · `frontend/src/app/{rutas,inicio,layout}.test.ts` (nuevos)
- Cubre: RF-07, RF-08, RF-09, RF-10, RF-48, RF-49, RF-50, RF-58, RF-59
- Criterios: CA-09, CA-49; CA-07, CA-08, CA-10, CA-48, CA-50, CA-58 y CA-59 en su parte unitaria
- Documentación: ninguna asignada.
- Depende de: T-06, T-20
- Hecho cuando: los tres tests se han visto en rojo y pasan; `tokens.test.ts` sigue en verde; `npm run verificar` en verde; con la API y `npm run dev` arrancados, `http://localhost:5173/#/` lista las novelas de `NOVELAS_DIR` (comprobación a mano, no criterio de cierre).
- Complejidad: L

#### T-08 Job `frontend` en CI y presupuestos

- Descripción:
  - `frontend/scripts/presupuesto.mjs`: mide en gzip los chunks de `dist/assets/` que carga `index.html` (≤ 100 KB, RNF-01) y el de Lectura (≤ 300 KB, RNF-02; 0 KB mientras no exista, PD5), los WOFF2 (≤ 60 KB), el CSS gzip (≤ 20 KB) y `logo.png` más `favicon.png` en `dist/` (≤ 80 KB) (RNF-20), siempre con 1 KB = 1 000 bytes (D52). Sale con distinto de 0 si algo excede.
  - `build` y `presupuesto` entran al final de `verificar` (D40).
  - Job `frontend` en `.github/workflows/ci.yml`, con `working-directory: frontend`: `actions/setup-node` con `node-version: 24` (D35), `npm ci`, `npm run tipos:comprobar`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npm run presupuesto` y `npm audit --omit=dev --audit-level=high`. El job `backend` (`ci.yml:8-25`) no cambia.
- Orden TDD:
  1. Rojo, `frontend/scripts/presupuesto.test.ts` (o equivalente en Vitest): sobre un `dist/` de fixture, un chunk inicial de más de 100 000 bytes gzip, uno de Lectura de más de 300 000 y un WOFF2 de más de 60 000 hacen salir con distinto de 0, y unas imágenes de marca de 80 001 bytes también, mientras que 80 000 pasan (D52); el `dist/` real sale con 0 (CA-40, parte del presupuesto).
  2. Verde: script.
  3. Job de CI. En una rama de prueba, un chunk inflado a propósito hace fallar el job; se anota en el PR y la rama no se fusiona.
- Archivos: `frontend/scripts/presupuesto.mjs` (nuevo) · `frontend/scripts/presupuesto.test.ts` (nuevo) · `frontend/package.json` (modificar: script `presupuesto`, y `build` y `presupuesto` en `verificar`) · `.github/workflows/ci.yml` (modificar) · `docs/validators.md` §6 y §2 (modificar)
- Cubre: RF-39, RF-40, RF-45, RNF-01, RNF-02 (sin chunk de Lectura hasta T-14), RNF-11, RNF-20
- Criterios: CA-40 en su parte `frontend`; CA-39 en CI
- Documentación: `docs/validators.md` §6, fila «CI del harness» con el job `frontend`; y el párrafo de estado de §2, con `tsc` y `eslint` en CI (D33).
- Depende de: T-05, T-19
- Hecho cuando: el test del presupuesto se ha visto en rojo y pasa; el job `frontend` sale verde en el push de la rama y rojo en la rama de prueba con el chunk inflado; `npm run verificar`, que ya incluye `build` y `presupuesto`, en verde en local.
- Complejidad: M
