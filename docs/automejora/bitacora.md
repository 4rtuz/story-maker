# Bitácora: calibración del Evaluador

Memoria del bucle. Se lee **entera** al empezar cada iteración y se le añade una entrada al
terminarla. Contrato: `pre-registro-calibracion-evaluador.md` (no se edita).
Datos crudos: `candidatos.jsonl` (una línea por tanda, la escribe el script) y
`resultados/*.jsonl` (una línea por llamada).

Aquí van las **lecciones**, no las cifras: las cifras ya están en el ledger. Una entrada
vale si la siguiente iteración la puede usar para no repetir trabajo.

## Palancas ya probadas — no repetir

| # | Palanca | Veredicto | Por qué |
|---|---|---|---|
| — | (vacío: aún no se ha medido ningún candidato) | | |

## Iteraciones

### 0 · baseline — 2026-09-20

- **Candidato:** `.claude/agents/evaluador.md` sin tocar (sha256 `73b37263…`, el mismo que
  midió `docs/ruido-evaluador.md` el 2026-09-18). Modelo: Haiku 4.5.
- **Qué se midió:** dev, 21 prompts × 3 pasadas = 63 llamadas, 0 fallidas, 0 inválidas.
  61 min de reloj, 3,50 $.

| métrica | valor | meta |
|---|---|---|
| σ(media) promedio | **0,317** | ≤ 0,17 |
| gates bloqueantes estables | **4/7** | ≥ 6/7 |
| AUC `barajado` (suelo) | 0,976 | no bajar |
| AUC `singancho` (sensibilidad) | **0,730** | no bajar |
| σ entre borradores | 0,407 | no bajar |

σ por criterio: `ritmo` 0,59 · `voz` 0,56 · `escaleta` 0,49 · `caracterizacion` 0,45 ·
`prosa` 0,33 · `tension` 0,25. Gate inestable en `01-c01`, `05-c03`, `07-c03`.

- **Lecciones:**
  1. **La señal apenas supera al ruido.** σ entre borradores (0,407) es del mismo orden que
     la σ *dentro* de un mismo borrador (0,317). Distinguir dos capítulos distintos es casi
     tan difícil como distinguir un capítulo de sí mismo.
  2. **`tension` es el criterio MENOS ruidoso** (0,25), no el más. La intuición de que el
     cuello de botella es ruido en `tension` era falsa: lo que pasa es que es bloqueante, así
     que su ruido, aunque pequeño, mueve el gate. Los ruidosos son `ritmo` y `voz`, que no
     bloquean nada.
  3. **El juez casi no nota que falta el gancho.** AUC `singancho` = 0,730 cuando el suelo
     (`barajado`) da 0,976. La rúbrica pregunta explícitamente «¿cierra en gancho?» dentro de
     `tension`, y aun así ordena mal 1 de cada 4 comparaciones.
  4. El formato no es el problema: 0 respuestas inválidas en 63 llamadas.
- **Hipótesis para la iteración 1** (no medida todavía, no es un resultado): la lección 3
  sugiere atacar la *sensibilidad* antes que la varianza — obligar al Evaluador a localizar y
  citar la frase de cierre antes de puntuar `tension`. Si sube el AUC de `singancho` sin tocar
  σ, sigue siendo una victoria: el guardarraíl no se rompe y el instrumento discrimina mejor.

<!-- PLANTILLA DE ENTRADA — copiar y rellenar

### N · <etiqueta del candidato>

- **Hipótesis:** qué se esperaba y por qué.
- **Cambio:** qué se tocó del system prompt, en una frase.
- **Veredicto del script:** META_ALCANZADA | MEJOR | SIN_MEJORA | DESCARTADO | INVALIDO,
  con σ y gates, copiados del ledger.
- **Lección:** qué sabe ahora el bucle que no sabía antes. Si fue DESCARTADO, qué
  guardarraíl rompió y qué dice eso de la palanca.
- **Siguiente:** qué probar después, y qué NO volver a probar.

-->
