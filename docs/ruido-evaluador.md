# Ruido del Evaluador: informe

Pre-registro: `docs/pre-registro-automejora.md`. Datos crudos: `docs/ruido-evaluador.jsonl`
(42 líneas). Estadísticas: `docs/ruido-evaluador-resumen.json` (este informe cita ese
fichero, no recalcula nada). 42/42 llamadas `ok`, 0 fallidas, coste total ≈ $2.44
(3 pasadas × 14 borradores, `--split all`).

Dev y holdout se reportan siempre por separado; nunca se agregan en una sola cifra.

## σ y rango intra-borrador, seis criterios + media_calculada

**DEV** — `runs/el-buzon-de-la-planta-baja-2`

| borrador | tension | escaleta | voz | caracterizacion | ritmo | prosa | media_calculada |
|---|---|---|---|---|---|---|---|
| 01-i0 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.00 / 0 | 0.00 / 0 | 0.25 / 0.50 |
| 01-i1 | 1.00 / 2 | 1.00 / 2 | 0.00 / 0 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.60 / 1.17 |
| 01-i2 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 1.00 / 2 | 0.00 / 0 | 0.17 / 0.34 |
| 02-i0 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.00 / 0 | 0.58 / 1 | 0.58 / 1 | 0.42 / 0.83 |
| 03-i0 | 0.00 / 0 | 0.58 / 1 | 0.00 / 0 | 0.58 / 1 | 0.00 / 0 | 0.58 / 1 | 0.19 / 0.33 |
| 03-i1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 1.00 / 2 | 0.58 / 1 | 1.00 / 2 | 0.63 / 1.17 |
| 03-i2 | 0.58 / 1 | 1.00 / 2 | 0.58 / 1 | 0.58 / 1 | 1.00 / 2 | 0.58 / 1 | 0.44 / 0.83 |
| **σ promedio** | **0.56** | **0.70** | **0.41** | **0.56** | **0.53** | **0.47** | **0.39** |

**HOLDOUT** — `runs/los-ruidos-del-bosque`

| borrador | tension | escaleta | voz | caracterizacion | ritmo | prosa | media_calculada |
|---|---|---|---|---|---|---|---|
| 01-i0 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 1.00 / 2 | 0.58 / 1 | 0.58 / 1.00 |
| 01-i1 | 0.00 / 0 | 0.00 / 0 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.00 / 0 | 0.17 / 0.33 |
| 02-i0 | 0.58 / 1 | 1.15 / 2 | 1.00 / 2 | 1.00 / 2 | 1.00 / 2 | 0.58 / 1 | 0.79 / 1.50 |
| 02-i1 | 0.00 / 0 | 0.00 / 0 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.25 / 0.50 |
| 02-i2 | 0.00 / 0 | 0.00 / 0 | 0.00 / 0 | 0.58 / 1 | 0.58 / 1 | 0.00 / 0 | 0.19 / 0.33 |
| 03-i0 | 1.15 / 2 | 1.15 / 2 | 0.58 / 1 | 1.00 / 2 | 0.00 / 0 | 0.58 / 1 | 0.51 / 1.00 |
| 03-i1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.58 / 1 | 0.44 / 0.83 |
| **σ promedio** | **0.41** | **0.49** | **0.56** | **0.70** | **0.62** | **0.41** | **0.42** |

(σ = desviación estándar muestral sobre 3 pasadas; rango = máx − mín. Fuente:
`docs/ruido-evaluador-resumen.json`, campos `criterios.*` y `media_calculada` por borrador.)

## Restringido a los criterios bloqueantes (tension, escaleta)

Estos dos vetan la aceptación (§9.2); su ruido es el que más importa.

**DEV**

| borrador | tension σ/rango | escaleta σ/rango | ¿gate estable entre pasadas? |
|---|---|---|---|
| 01-i0 | 0.58 / 1 | 0.58 / 1 | no |
| 01-i1 | 1.00 / 2 | 1.00 / 2 | no |
| 01-i2 | 0.58 / 1 | 0.58 / 1 | **sí** |
| 02-i0 | 0.58 / 1 | 0.58 / 1 | no |
| 03-i0 | 0.00 / 0 | 0.58 / 1 | no |
| 03-i1 | 0.58 / 1 | 0.58 / 1 | no |
| 03-i2 | 0.58 / 1 | 1.00 / 2 | no |

**HOLDOUT**

| borrador | tension σ/rango | escaleta σ/rango | ¿gate estable entre pasadas? |
|---|---|---|---|
| 01-i0 | 0.58 / 1 | 0.58 / 1 | no |
| 01-i1 | 0.00 / 0 | 0.00 / 0 | sí |
| 02-i0 | 0.58 / 1 | 1.15 / 2 | sí* |
| 02-i1 | 0.00 / 0 | 0.00 / 0 | sí |
| 02-i2 | 0.00 / 0 | 0.00 / 0 | sí |
| 03-i0 | 1.15 / 2 | 1.15 / 2 | no |
| 03-i1 | 0.58 / 1 | 0.58 / 1 | sí |

`*` en `02-i0` las puntuaciones sí varían (tension 3/4/3, escaleta 3/5/3) pero las tres
pasadas quedan por encima del umbral bloqueante (3): el booleano de paso/no-paso es
estable aunque el número no lo es. Es la distinción que separa "ruido en la puntuación"
de "ruido en la decisión" — la segunda es la que de verdad mueve una aceptación.

## ¿Discrimina?

`01-i0` del buzón (histórico: media 2,50) contra `01-i2` (histórico: media 3,00), 3
pasadas nuevas cada uno:

- `01-i0`: medias {2.33, 2.83, 2.50} → rango [2.33, 2.83]
- `01-i2`: medias {3.67, 3.33, 3.50} → rango [3.33, 3.67]

Los rangos no se solapan (hueco de 0.50 entre 2.83 y 3.33), así que en esta tanda el
Evaluador sí separa el borrador peor del mejor. Pero el hueco es del mismo tamaño que la
diferencia histórica completa (0.50): el margen de discriminación es del mismo orden que
el ruido de una sola pasada en otros borradores de la tabla anterior (p. ej. `03-i1` dev,
rango 1.17). La señal existe, pero no sobra.

## Cuántos borradores dan una media distinta / un bloqueante distinto entre pasadas

| | dev (de 7) | holdout (de 7) |
|---|---|---|
| media_calculada distinta en las 3 pasadas | 7 | 7 |
| criterio bloqueante (paso/no-paso) distinto entre pasadas | 6 | 2 |

Los 14 borradores del fixture dieron una `media_calculada` distinta cada una de las 3
veces que se relanzó la misma llamada sobre el mismo texto: cero repeticiones exactas.
El gate de aceptación (lo segundo) es más estable — el ruido en la puntuación no siempre
cruza el umbral — pero aun así cambia de veredicto en 8 de los 14 borradores (6 dev + 2
holdout) solo por volver a preguntar.

## Contraste con el histórico (`*-eval.json`), indicativo, no medida

| borrador | media histórica | veredicto histórico | medias nuevas (3 pasadas) |
|---|---|---|---|
| dev/01-i0 | 2.50 | CORREGIR | 2.33, 2.83, 2.50 |
| dev/01-i1 | 2.67 | CORREGIR | 3.17, 2.83, 4.00 |
| dev/01-i2 | 3.00 | CORREGIR | 3.67, 3.33, 3.50 |
| dev/02-i0 | 3.00 | APROBADO | 3.50, 2.67, 3.17 |
| dev/03-i0 | 2.50 | CORREGIR | 2.17, 2.50, 2.17 |
| dev/03-i1 | 2.67 | CORREGIR | 2.33, 2.50, 3.50 |
| dev/03-i2 | 2.67 | CORREGIR | 3.50, 2.67, 3.33 |
| holdout/01-i0 | 2.33 | CORREGIR | 3.17, 3.17, 2.17 |
| holdout/01-i1 | 3.00 | APROBADO | 3.67, 3.83, 3.50 |
| holdout/02-i0 | 3.67 | APROBADO | 2.67, 4.17, 3.00 |
| holdout/02-i1 | 4.00 | APROBADO | 2.50, 2.67, 2.17 |
| holdout/02-i2 | 2.67 | CORREGIR | 3.33, 3.00, 3.00 |
| holdout/03-i0 | 2.50 | CORREGIR | 2.17, 2.50, 3.17 |
| holdout/03-i1 | 3.67 | APROBADO | 4.00, 3.17, 3.33 |

No es una comparación limpia — el estado (`estado/`, fichas, escaleta) de estos runs ha
avanzado desde que se generó la puntuación original, así que el contexto que ensambla hoy
`harness prompt evaluador` no es el mismo que vio el Evaluador entonces (algunos casos,
como `holdout/02-i1`, se mueven más de una unidad entera). La σ entre las 3 pasadas nuevas
de esta tanda, en cambio, sí es una medición limpia porque las 3 comparten el mismo
contexto ensamblado una sola vez.

## Hashes (punto 0 del encargo)

```json
{
  "borradores": {
    "dev/01-i0": "38b0be8ddab5585a85a206388ffb81dc072e08f761ae4499f3778dc25908b555",
    "dev/01-i1": "f7cbebc36de57885461a88656e4e3d62a10c01903156cb10193bccc0feb535fc",
    "dev/01-i2": "a355af8e502421fbb6940a67a3eaa370547ade4d0db3ffabe74ebe0798b29a34",
    "dev/02-i0": "903a77cd91988662848b242d5cf4350da088ef32d1f012ff0223b19223d83b85",
    "dev/03-i0": "8896bb890ad59bd1fd672b02c29fb866bb085c3b6047e6d8a2114427300d5eb1",
    "dev/03-i1": "d1c87c056e868dab30e72807b08a236b598df276548e691dacf90bbec9219bd9",
    "dev/03-i2": "94c7c0e453febef5ba4733bbc2b52875684f99e3c69cf2860d93253422559b2d",
    "holdout/01-i0": "bcc5943514ed0311712f5ce60c3f6cd3e7cb1a07910aa9d6b3dec1eec4165ebc",
    "holdout/01-i1": "e469e69017406d083eb4bce916da2ca602adfde46054df531606e2afab6b399c",
    "holdout/02-i0": "c95db248774b0c54b3d93047da22b1765cb154c6e1f1a2caa63d33182e985866",
    "holdout/02-i1": "79ae1d1bdfedf8dd74d9c4abfe8d306c4e71eef535f414675c5363745ff91da5",
    "holdout/02-i2": "a9dda01647a462d69a8238c86c1c0c85dbd9d72bc51607b757d7cc82757888c5",
    "holdout/03-i0": "315cfa0b5e8fb8ad72208a9d8c2c3b59828f74ddc5cc34a7e71762fefe2ea3e6",
    "holdout/03-i1": "e5c389b5eaa9b84312904ad8fb76f70c49e13668c297c6d4c9a17eba20b79fe2"
  },
  "evaluador_md": "73b37263c0c3d44580a901ae67e0d26150a5dcc608793dde563827546850992e",
  "evaluacion_config": "5abd3351466e64067cf9c0a963e019cb8fd05b22b6e0a419d95b5f6c40934102"
}
```

`scripts/repuntuar.py` (informativo, no verificado — no puede verificarse a sí mismo):
`a5e5640d5ab8171c876bc90c08f913c2975998bc810b6b15e71e1bf0615f7e1e`

## Verificación independiente

```
python -c "import json,statistics,collections; d=collections.defaultdict(list)
for l in open('docs/ruido-evaluador.jsonl',encoding='utf-8'):
    r=json.loads(l); d[(r['split'],r['iteracion'])].append(r['media_calculada'])
for k in sorted(d): print(k, round(statistics.stdev(d[k]),4))"
```

Recorre `docs/ruido-evaluador.jsonl` línea a línea y recalcula σ(media_calculada) por
borrador sin volver a llamar al Evaluador; los valores reproducen exactamente la columna
`media_calculada` de las tablas de arriba y `sigma_media_calculada_promedio` de
`docs/ruido-evaluador-resumen.json`.

## Veredicto

σ(media_calculada) promedio por partición es 0.39 (dev) y 0.42 (holdout), y 13 de los 14
borradores individuales ya superan 0.17 por sí solos (el único al borde es
`holdout/01-i1`, con 0.165) — **`mejora_minima: 0.01` está midiendo ruido**, tal como
predecía la regla del pre-registro (`σ(media) >= 0.17 => "mejora_minima: 0.01" está
midiendo ruido`).
