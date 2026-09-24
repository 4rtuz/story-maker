# Fase 6: Lectura

Plan: `README.md` · Spec: §5 (RF-10, RF-24 a RF-31, RF-55, RF-58), §6 (RNF-02, RNF-03, RNF-07), §8.4 (escena, lector) · Decisiones: D8, D9, D11, D12, D14, D16, D33, D41, D47, D56

Independiente de la fase 5. Three.js, `markdown-it`, la escena y el lector se cargan con `import()` al entrar en Lectura, en su propio chunk (RNF-02). Desde T-14 ese chunk existe y `npm run presupuesto` (PD5) lo mide de verdad. Recursos a 10 s: `config`, `escaleta`, `checkpoint` y `capitulos`; `capitulos/{n}` solo a demanda y solo si el capítulo está cerrado (spec §8.4).

Los fixtures de esta fase viven en `frontend/test/fixtures/`: RF-43 prohíbe importar desde `frontend/src/` ficheros de `backend/`, incluidos los de `backend/tests/fixtures/`.

---

#### T-13 Lectura: disposición, estados, lista y teclado

- Descripción:
  - `features/lectura/estados.ts`: `EstadoDeVolumen` —`cerrado` si `n ≤ checkpoint.capitulo`, `en_curso` si está en el índice y es mayor, `pendiente` en otro caso; con `checkpoint` `null`, ninguno cerrado (D8)—.
  - `features/lectura/disposicion.ts`: `x = (n − 1) × 1,2 + a × 2,0`, con `a` los actos anteriores; sin escaleta o fuera de acto, sin hueco.
  - `features/lectura/navegacion.ts`: ← y → mueven la selección sin dar la vuelta —← en el primero y → en el último no hacen nada (D47)—, Enter abre y Esc cierra y devuelve el foco a la lista.
  - `features/lectura/vista.ts`: banner, lista HTML con el estado también como texto, «capítulo no disponible todavía» sin petición, ruta `#/novelas/<slug>/lectura/<n>`, esqueleto, «ningún capítulo cerrado todavía» y error.
- Orden TDD:
  1. Rojo, `frontend/src/features/lectura/estados.test.ts` y `disposicion.test.ts`: el caso de CA-24 (7 cerrados, el 8 en curso, del 9 al 24 pendientes; x estrictamente creciente; el hueco entre actos mayor que entre volúmenes del mismo acto) y un capítulo fuera de acto (CA-24, parte unitaria).
  2. Rojo, `frontend/src/features/lectura/navegacion.test.ts`: del 3, → pasa al 4 con `aria-current` en el 4, Enter abre el 4 y Esc cierra y deja el foco en el 4 de la lista; ← en el 1 lo deja en el 1 y → en el 24 lo deja en el 24 (CA-28, parte unitaria).
  3. Rojo, `frontend/src/features/lectura/vista.test.ts`: `#/novelas/demo-24/lectura/8` con `checkpoint.capitulo` 7 muestra el texto y el espía no registra `GET …/capitulos/8` (CA-27); recarga con `/lectura/3` reabre el 3 (CA-10, parte unitaria); estados de carga, vacío y error (CA-58, parte unitaria).
  4. Verde.
- Archivos: `frontend/src/features/lectura/{vista,estados,disposicion,navegacion}.ts` (nuevos) · `frontend/src/features/lectura/{vista,estados,disposicion,navegacion}.test.ts` (nuevos) · `frontend/src/app/rutas.ts` (modificar)
- Cubre: RF-10, RF-24 (estados y disposición), RF-27, RF-28, RF-58
- Criterios: CA-27, CA-28; CA-24, CA-10 y CA-58 en su parte unitaria
- Documentación: ninguna asignada.
- Depende de: T-07
- Hecho cuando: los cuatro tests se han visto en rojo y pasan; `npm run verificar` en verde.
- Complejidad: M

#### T-14 Lectura: escena Three.js

- Descripción: `features/lectura/escena.ts`, cargada con `import()` desde `vista.ts`:
  - un `InstancedMesh` con un volumen por capítulo coloreado con `setColorAt` según su estado (`--q-primario`, `--q-icono-cian`, `--q-pendiente`), una malla de contorno para la selección en `--q-deco-seleccion` y un plano de suelo sobre `--q-fondo-pagina`: como mucho 5 objetos dibujables;
  - cámara en perspectiva hacia el seleccionado, con transición de 400 ms, o de 0 ms con `prefers-reduced-motion: reduce`;
  - selección por raycasting sobre el `InstancedMesh`, por teclado y desde la lista;
  - `data-volumenes`, `data-seleccion` y `data-draw-calls` en el contenedor;
  - renderer creado con una fábrica inyectable; ante falta de WebGL o `webglcontextlost`, retira la escena y deja la lista con «vista 3D no disponible»;
  - al salir de Lectura, `dispose()` de geometrías, materiales, texturas y renderer, y retirada del `<canvas>`;
  - colores del lector de tokens de T-19.
- Orden TDD:
  1. Rojo, `frontend/src/features/lectura/escena.test.ts`, con una fábrica de renderer falsa que registra cada `dispose()` y sin WebGL real:
     - al navegar fuera, todos los recursos liberados y ningún `<canvas>` (CA-31);
     - con `webglcontextlost`, la escena se retira y aparece el aviso (CA-29, parte unitaria);
     - objetos dibujables ≤ 5 con 24 y con 999 volúmenes (RNF-03, parte unitaria);
     - colores de cada estado, del contorno y del fondo iguales a sus roles, y un cambio de `--q-primario` en el test que llega a los volúmenes cerrados (CA-55, parte de la escena).
  2. Rojo, en `disposicion.test.ts` o `escena.test.ts`: con `prefers-reduced-motion: reduce`, duración de la transición 0 ms y cámara en el 4 en el fotograma siguiente (CA-30, parte unitaria).
  3. Verde.
  4. `npm run build` y `npm run presupuesto`: el chunk de Lectura existe y cumple ≤ 300 KB gzip, y el inicial sigue ≤ 100 KB (RNF-01, RNF-02).
- Archivos: `frontend/src/features/lectura/escena.ts` (nuevo) · `frontend/src/features/lectura/escena.test.ts` (nuevo) · `frontend/src/features/lectura/vista.ts` (modificar) · `frontend/scripts/presupuesto.mjs` (modificar solo si el nombre del chunk no casa con el que espera PD5)
- Cubre: RF-24 (escena), RF-29, RF-30, RF-31, RF-55, RNF-02, RNF-03 (parte unitaria)
- Criterios: CA-31; CA-29, CA-30 y CA-55 en su parte unitaria; CA-24 y CA-29 se cierran en T-16
- Documentación: ninguna asignada.
- Depende de: T-13
- Hecho cuando: los tests se han visto en rojo y pasan; `npm run verificar`, `npm run build` y `npm run presupuesto` en verde, con el chunk de Lectura medido.
- Complejidad: L

#### T-15 Lectura: lector

- Descripción: `features/lectura/lector.ts`, el único módulo que inserta HTML en todo el panel:
  - si el texto empieza por una línea `---`, quita hasta la siguiente `---` inclusive (D16);
  - `markdown-it` con `html: false`, `linkify: false` y las reglas `link`, `image`, `autolink` y `reference` desactivadas (D14, D56);
  - encabezado con el `titulo` del índice, escrito con `textContent` (D56);
  - diálogo modal en `--q-fuente-cuerpo` y `--q-texto-cuerpo`, con líneas de `--q-ancho-lectura` como máximo, y botón de cerrar con sus estados de T-20.

  Se pide `GET …/capitulos/{n}` solo para capítulos cerrados. La regla `no-unsanitized` de T-04 no lleva excepción por fichero: la única inserción de HTML del panel, en este módulo, va en una sola sentencia alimentada por la salida de `markdown-it` y marcada con un único `eslint-disable-next-line` (D56).
- Orden TDD:
  1. Rojo, `frontend/src/features/lectura/lector.test.ts`:
     - un capítulo de fixture de `frontend/test/fixtures/` con frontmatter (incluido `run_id:`) se muestra sin `run_id:` ni la línea `---` inicial y con el `titulo` del índice; y con un `titulo` `<img src=x onerror=alert(1)>`, el `textContent` del encabezado es el literal y no hay ningún `img` (CA-25, parte unitaria);
     - el capítulo con `\r\n` de VAL-16 pierde el frontmatter y conserva su `<hr>` del cuerpo;
     - el capítulo hostil de CA-26 —`<script>`, `<img onerror>`, `<iframe>`, enlace `javascript:`, imagen de `ejemplo.invalid`, `<http://ejemplo.invalid>`, enlace e imagen por referencia, URL suelta, `<svg onload>` y enlace `data:`— no crea `script`, `iframe`, `img`, `a`, `object`, `embed` ni `svg`, ni ningún atributo `on*`, y los once fragmentos aparecen como texto (CA-26, parte unitaria; RNF-07).
  2. Rojo, `frontend/src/lint.test.ts`: un fixture que inserta HTML fuera de `lector.ts` sigue dando error; `lector.ts` pasa; `eslint.config.js` no tiene excepciones por fichero de `no-unsanitized`, y `lector.ts` contiene exactamente una inserción de HTML y un único `eslint-disable-next-line` de `no-unsanitized` (CA-26, parte estática).
  3. Verde.
- Archivos: `frontend/src/features/lectura/lector.ts` (nuevo) · `frontend/src/features/lectura/lector.test.ts` (nuevo) · `frontend/test/fixtures/capitulos/*.md` (nuevos) · `frontend/src/features/lectura/vista.ts` (modificar) · `frontend/src/lint.test.ts` (modificar) · `docs/architecture.md` §11.2 (modificar)
- Cubre: RF-25, RF-26, RF-45, RNF-07
- Criterios: CA-25 y CA-26 en su parte unitaria y estática (se cierran en T-16)
- Documentación: `docs/architecture.md` §11.2 (`:860`), donde la frase de Lectura pasa a «capítulos cerrados» y describe la estantería 3D con lista HTML equivalente (D8, D9, D33).
- Depende de: T-13
- Hecho cuando: los dos tests se han visto en rojo y pasan; `npm run verificar` en verde.
- Complejidad: S
