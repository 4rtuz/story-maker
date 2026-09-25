# Presentación y demo

Deck: [enlace a la presentación]

## Vídeo: `demo.webm`

3 min 26 s, 1280 × 720, WebM (VP8), 12,5 MB, sin audio. Lo grabó Playwright (`recordVideo`) sobre
el panel real (API en `127.0.0.1:8000`, Vite en `localhost:5173`) y sobre páginas HTML locales para
los rótulos y las salidas de terminal. La novela es `ejemplo-carmen`, con datos ficticios. Las
salidas del CLI son reales: se ejecutaron el 2026-09-25 sobre el workspace terminado.

| Tramo | Qué se ve |
|---|---|
| 0:00–0:07 | Rótulo de apertura. |
| 0:07–0:39 | **Brief**: las respuestas y la carta del README (texto libre no confiable) y el informe de `novela brief validar` (`valido: true`, sin hallazgos). |
| 0:39–1:47 | **Panel**: el inicio con las novelas; `#/lanzar` con el formulario relleno (no se pulsa «Lanzar novela»); Progreso de `ejemplo-carmen` (10 de 10 capítulos, 13 419 palabras, tensión por acto); Lectura: portada con la dedicatoria, índice, ficha de personajes y lugares; el capítulo 7 abierto desde el índice, y un capítulo abierto desde la ficha. |
| 1:47–2:13 | **Cambio del lector**: `novela cambio … --hecho hec-004 … --simular` (el hecho ya se sustituyó en `cam-001`, así que sale 2), la simulación de un cambio más sobre `hec-058` (regenera 01 y 09 y reaplica el resto, versión 3) y `novela versiones` (v1 original, v2 con 3 capítulos cambiados). |
| 2:13–2:32 | **PDF v2**: páginas 1 (portada y dedicatoria), 2 (novedades de la versión 2, enlazadas a los capítulos 1, 7 y 9) y 3 (índice) de `ejemplos/novela-ejemplo-v2.pdf`. |
| 2:32–2:51 | **Langfuse**: la tabla de coste por paso de `docs/evaluacion/costes-ejemplo-carmen.md` y el total, **24,52 USD por novela**. |
| 2:51–3:14 | **Lean y TLC**: `novela verificar-lean ejemplo-carmen` (39 eventos, los cuatro invariantes demostrados) y el resumen de TLC de `docs/formal/tla.md` (`Harness.cfg` pasa con 281 824 estados; cada mutante da su contraejemplo). |
| 3:14–3:26 | Rótulo de cierre. |

## Cómo reproducirlo

Cualquier navegador moderno abre `demo.webm` (arrástralo a una pestaña), y también VLC o mpv. El
reproductor de Windows necesita la extensión de vídeo VP8/WebM.

## PDFs de ejemplo

- [`../ejemplos/novela-ejemplo.pdf`](../ejemplos/novela-ejemplo.pdf): versión 1.
- [`../ejemplos/novela-ejemplo-v2.pdf`](../ejemplos/novela-ejemplo-v2.pdf): versión 2, tras el cambio
  del lector (la carta estaba en el cajón del mostrador de préstamos). La página 2 recoge las
  novedades, con enlaces a los capítulos 1, 7 y 9, que son los regenerados.
