# Pre-registro: suelo de ruido del Evaluador

Escrito antes de la primera llamada de medición. No se edita tras ver resultados; un
cambio de opinión posterior va en el informe (`docs/ruido-evaluador.md`), no aquí.

## Pregunta

`novela/config.json` fija `evaluacion.mejora_minima: 0.01` (§9.4): la ganancia de media
que una reescritura debe aportar para justificar otra vuelta. Si el Evaluador varía más
que eso solo por relanzar la misma llamada sobre el mismo borrador, ese umbral no mide
mejora real: mide ruido del juez.

## Métrica

Por cada borrador del fixture, 3 pasadas independientes (3 procesos `claude -p` distintos,
mismo prompt ensamblado una sola vez por el núcleo). Para cada borrador se calcula:

- σ (desviación estándar muestral, `statistics.stdev`, n=3) de `media_calculada`
  (recalculada por `harness.deltas.computed_mean`, nunca la `media` que declara el modelo).
- σ de cada uno de los seis criterios de la rúbrica.
- Rango (máx − mín) de cada criterio y de `media_calculada`, como lectura intuitiva junto
  a σ con n tan pequeño.

Los informes agregan estas σ por partición (dev / holdout) como la media de las σ
intra-borrador; dev y holdout nunca se combinan en una sola cifra.

## Regla de veredicto

**Si σ(media_calculada) >= 0.17, `mejora_minima: 0.01` está midiendo ruido, no señal.**

0.17 no es arbitrario: un solo criterio de los seis vale 0.167 en la media (1/6), que es
exactamente el umbral que ya usa `_mejora_minima` en `config.json` para razonar sobre
cuánto vale un criterio suelto. Si el ruido de relanzar la misma llamada iguala o supera
lo que vale mover un criterio entero, ninguna ganancia de 0.01 es distinguible de repetir
la tirada.

## Partición dev / holdout

**DEV (7)** — `runs/el-buzon-de-la-planta-baja-2/novela/.intentos/`:
`01-i0, 01-i1, 01-i2, 02-i0, 03-i0, 03-i1, 03-i2`

**HOLDOUT (7)** — `runs/los-ruidos-del-bosque/novela/.intentos/`:
`01-i0, 01-i1, 02-i0, 02-i1, 02-i2, 03-i0, 03-i1`

Capítulo e iteración se leen del nombre del fichero. Los 14 borradores son de solo
lectura; `scripts/repuntuar.py --split all` mide las dos particiones en la misma tanda
porque medir ruido no ajusta nada — no hay fuga de información de dev a holdout al
no tocar ningún parámetro entre medias.

## Restricción de no-daño (para brazos futuros)

Esta tanda no optimiza nada. Pero si una tanda futura ajusta un criterio de la rúbrica o
del prompt del Evaluador para mejorar su señal, la restricción es: **ninguno de los otros
cinco criterios puede empeorar** (más σ intra-borrador, o discriminación holdout peor)
respecto a la línea base que fija este informe. Optimizar `tension` a costa de que
`prosa` se vuelva ruidosa no es una mejora neta.

## Tope

42 llamadas (`3 pasadas × 14 borradores`), verificadas con una llamada de humo previa que
no cuenta contra el tope. Tope duro: si la partición pedida más las pasadas superan 42, el
script aborta antes de gastar nada.
