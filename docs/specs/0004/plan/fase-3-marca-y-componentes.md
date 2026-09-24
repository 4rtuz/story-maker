# Fase 3: Marca y componentes

Plan: `README.md` · Spec: §5 (RF-46, RF-47, RF-51, RF-52, RF-56, RF-57, RF-60, RF-61), §8.4 «Marca» · Decisiones: D21 a D28, D31, D32, D33, D51, D52

Los recursos de terceros ya están en el repositorio, sin versionar (D31): `frontend/src/shared/marca/fuentes/outfit-800.woff2` (14 048 bytes, subconjunto latino de `@fontsource/outfit` 5.3.0, fichero `files/outfit-latin-800-normal.woff2`) con su `OFL.txt`, y `frontend/src/shared/iconos/LICENSE` (ISC) con `iconos/lucide/*.svg`, los doce iconos de la spec §8.4 de `lucide-static` 1.48.0. T-19 no descarga nada. El favicon se deriva con la orden de la spec §8.4 (D32). Los valores de color y medida son los aproximados de la spec §8.4 (S6): si llega el manual de marca, solo cambia `tokens.css` y los pares se recalculan.

Ninguna imagen, fixture ni texto de esta fase contiene nombres, fotos ni cargos de personas reales. La captura de la plataforma de referencia no entra en el repositorio (RF-60).

---

#### T-19 Tokens, pares, fuente, iconos, logo y favicon

- Descripción:
  - `frontend/src/shared/marca/tokens.css`: primitivos, roles semánticos y medidas de la spec §8.4, el `@font-face` de Outfit 800 con `font-display: swap` y `color-scheme: light` en `:root`. Es el único fichero con colores literales y `font-family`.
  - `frontend/src/shared/marca/pares.ts`: los 21 pares de la spec §8.4 con su tipo (`texto`, `texto-grande`, `no-textual`).
  - Lector de tokens con dos implementaciones: el navegador lee las propiedades CSS computadas; los tests leen `tokens.css`. Lo usan T-11 y T-14 (CA-55).
  - `frontend/src/shared/marca/fuentes/outfit-800.woff2` y `OFL.txt`, versionados tal cual (D31).
  - `frontend/src/shared/iconos/trazados.ts`, con los trazados de los doce iconos copiados de `iconos/lucide/*.svg` y una cabecera con el origen y la versión (`lucide-static` 1.48.0, y `@fontsource/outfit` 5.3.0 para la fuente); `iconos/LICENSE` versionado tal cual; una función que los dibuja con `createElementNS` y `aria-hidden="true"`. En este mismo commit se borra `iconos/lucide/`, que nunca se versiona, porque RF-60 solo admite `logo.png` y `favicon.png` como imágenes (D31).
  - `frontend/src/shared/marca/logo.png` versionado tal cual, sin recomprimir; `logo.ts`, el único módulo que lo importa, con `<img alt="Qaracter">` de `--q-tamano-logo` dentro de un contenedor con `border-radius: var(--q-radio-logo)` y `overflow: hidden`, y la comprobación del PNG y del favicon, con 80 KB = 80 000 bytes (D52).
  - `frontend/public/favicon.png`, derivado una vez del logo desde `backend/`, sin añadir dependencias, con esta orden (D32), y enlazado en `index.html` con `<link rel="icon" type="image/png" href="/favicon.png">`:

    ```bash
    uv run --with pillow python -c "from PIL import Image, ImageDraw; s=64; r=round(s*0.22); im=Image.open('../frontend/src/shared/marca/logo.png').convert('RGBA').resize((s, s), Image.LANCZOS); m=Image.new('L', (s, s), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, s - 1, s - 1), radius=r, fill=255); im.putalpha(m); im.save('../frontend/public/favicon.png')"
    ```

  - Regla de eslint que reserva a `logo.ts` la importación de `logo.png` (PD2, D33).
  - Mensaje del commit: el origen y la versión de la fuente y de los iconos, y la orden exacta del favicon.
- Orden TDD:
  1. Rojo, `frontend/src/shared/marca/tokens.test.ts`: ningún `.ts` ni `.css` de `src/` que no sea test ni `tokens.css` contiene los literales de CA-46, ningún color con nombre de CSS ni `font-family`, con `transparent`, `currentColor` e `inherit` como únicas palabras clave permitidas (D51); toda `var(--q-…)` usada está definida en `tokens.css`; ningún componente usa un primitivo (CA-46). Para ver el rojo, fixtures con un hexadecimal, con `color: orange; border-color: gray;` en CSS y con `el.style.fill = 'red'` en TS.
  2. Rojo, `frontend/src/shared/marca/pares.test.ts`: contraste recalculado desde `tokens.css`, con las transparencias compuestas sobre su fondo (p. ej. `--q-chip-fondo` al 15 %); `--q-naranja-500` y `--q-cian-500` solo en `--q-deco-*` y `--q-nav-indicador`; ningún par de texto con un `--q-deco-*` como primer plano; cada par ≥ su umbral (CA-47, RNF-19).
  3. Rojo, `frontend/src/shared/marca/logo.test.ts`: la comprobación rechaza, con su motivo, cuatro fixtures generados por el propio test —no PNG, 200 × 200 px, 90 KB y fichero ausente— y acepta el `logo.png` real (firma PNG, 400 × 400 px, ≤ 80 KB); el favicon es PNG de 64 × 64 px con alfa, esquinas transparentes y centro opaco; `index.html` lo enlaza (CA-52; CA-61 parte unitaria). El `logo.png` real solo se lee.
  4. Rojo, `frontend/src/shared/marca/recursos.test.ts`: las fuentes son `.woff2` con `OFL.txt` al lado y `font-display: swap`; los iconos salen de `trazados.ts` con `createElementNS`; `trazados.ts` lleva en su cabecera el origen y la versión; `iconos/LICENSE` existe; `package.json` sigue cumpliendo RF-44 (CA-56, parte unitaria).
  5. Rojo, `frontend/src/configuracion.test.ts` (existe desde T-04): las únicas imágenes versionadas bajo `frontend/` (`git ls-files`) son `logo.png`, `favicon.png` y las referencias de `frontend/e2e/visual.spec.ts`, así que ningún `iconos/lucide/*.svg` (CA-60).
  6. Rojo, `frontend/src/lint.test.ts`: un fixture que importa `logo.png` fuera de `logo.ts` da error (CA-51, parte estática).
  7. Verde: ficheros de marca, regla de eslint y enlace del favicon.
- Archivos: `frontend/src/shared/marca/tokens.css` (nuevo) · `frontend/src/shared/marca/pares.ts` (nuevo) · `frontend/src/shared/marca/lector-de-tokens.ts` (nuevo; nombre provisional, la spec no lo fija) · `frontend/src/shared/marca/logo.ts` (nuevo) · `frontend/src/shared/marca/logo.png` (existente, sin versionar: se añade tal cual) · `frontend/src/shared/marca/fuentes/outfit-800.woff2` (existente, sin versionar: se añade tal cual) · `frontend/src/shared/marca/fuentes/OFL.txt` (existente, sin versionar: se añade tal cual) · `frontend/src/shared/iconos/trazados.ts` (nuevo) · `frontend/src/shared/iconos/LICENSE` (existente, sin versionar: se añade tal cual) · `frontend/src/shared/iconos/lucide/` (existente, sin versionar: se borra) · `frontend/public/favicon.png` (nuevo) · `frontend/index.html` (modificar) · `frontend/eslint.config.js` (modificar) · `frontend/src/shared/marca/{tokens,pares,logo,recursos}.test.ts` (nuevos) · `frontend/src/configuracion.test.ts` (modificar) · `frontend/src/lint.test.ts` (modificar) · `docs/architecture.md` §3.1 y §11.2 (modificar)
- Cubre: RF-45, RF-46, RF-47, RF-51 (parte estática), RF-52, RF-56 (parte unitaria), RF-60, RF-61 (parte unitaria), RNF-19, RNF-20 (los ficheros que mide T-08)
- Criterios: CA-46, CA-47, CA-52, CA-60; CA-51, CA-56 y CA-61 en su parte unitaria
- Documentación: `docs/architecture.md` §3.1, con `shared/marca/` y `shared/iconos/` en el árbol, y §11.2, con la identidad visual y el logo siempre redondeado (D21, D23).
- Depende de: T-04
- Hecho cuando: los seis tests se han visto en rojo y pasan; `npm run verificar` en verde; `git diff --stat` del `logo.png` muestra el fichero binario sin cambios respecto al aportado (mismo sha256 que antes del commit); `frontend/src/shared/iconos/lucide/` ya no existe; y el mensaje del commit lleva el origen, la versión y la orden del favicon.
- Complejidad: L

#### T-20 Componentes de `shared/ui/` con sus estados

- Descripción: botón primario, botón secundario («… →» con `--q-sombra-boton`), campo, tarjeta, tarjeta de métrica, subtarjeta, chip, etiqueta, banner, esqueleto, texto de vacío, aviso y tabla (spec §8.2 y §8.4). Cada interactivo tiene reposo, hover, `focus-visible` con `outline` de `--q-contorno-foco` en `--q-foco` o `--q-foco-sobre-oscuro` y, donde aplica, deshabilitado. Transiciones de `--q-transicion` (≤ 150 ms), a 0 con `prefers-reduced-motion: reduce`, y foco con `outline`, no `box-shadow`, para que siga visible con `forced-colors: active`. Construidos con `createElement` y `textContent`; ningún `innerHTML`. El banner acepta titular, subtítulo y chips, y parte el titular en líneas dentro de la mitad izquierda.
- Orden TDD:
  1. Rojo, `frontend/src/shared/ui/estados.test.ts` (jsdom): cada componente interactivo expone sus estados (clases o atributos distintos para hover, foco y deshabilitado); `--q-transicion` pasa a 0 bajo `prefers-reduced-motion: reduce`; el foco se declara con `outline` (CA-57, parte unitaria; RNF-24, parte estática).
  2. Rojo, `frontend/src/shared/ui/banner.test.ts`: estructura del banner (titular, subtítulo, chips) sin datos de novela, que los pone T-10.
  3. Verde: componentes.
- Archivos: `frontend/src/shared/ui/*.ts` (nuevos) · `frontend/src/shared/ui/estilos.css` o CSS por componente (nuevo; solo `var(--q-…)` de roles) · `frontend/src/shared/ui/estados.test.ts` (nuevo) · `frontend/src/shared/ui/banner.test.ts` (nuevo)
- Cubre: RF-57, RF-53 (estructura del banner), RNF-24 (parte estática)
- Criterios: CA-57 en su parte unitaria
- Documentación: ninguna asignada por la spec. Todo cambio posterior en `shared/ui/` o `shared/marca/` obliga a repetir T-22 (D55).
- Depende de: T-19
- Hecho cuando: los dos tests se han visto en rojo y pasan; `tokens.test.ts` de T-19 sigue en verde, sin literales nuevos; `npm run verificar` en verde.
- Complejidad: M
