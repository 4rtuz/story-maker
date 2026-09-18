# Repetición de la prueba de discriminación (01-i0 vs 01-i2)

Sigue a `docs/ruido-evaluador.md` ("informe de hoy"). No modifica `novela/config.json`,
`harness/` ni `.claude/agents/`. No genera commits. Datos crudos de esta repetición:
`docs/repeticion-01-i0-vs-01-i2.json`.

## Punto de partida

`docs/ruido-evaluador.md` §"¿Discrimina?" comparó `dev/01-i0` (histórico: el capítulo peor,
media 2,50) contra `dev/01-i2` (histórico: el mejor, media 3,00) con 3 pasadas nuevas cada
uno:

- `01-i0`: {2.33, 2.83, 2.50} → rango [2.33, 2.83]
- `01-i2`: {3.67, 3.33, 3.50} → rango [3.33, 3.67]
- Hueco entre rangos: **+0.50** (no solapan)

Ese mismo informe ya advertía que el margen "no sobra": es del mismo orden que el σ de un
solo borrador en la tabla de ruido (p. ej. rango 1.17 en `03-i1` dev).

## Verificación previa

- `scripts/fixture.json verificado: coincide con el estado actual.` — los 14 borradores,
  `.claude/agents/evaluador.md` y el bloque `evaluacion` de `novela/config.json` no han
  cambiado desde que se fijó el fixture.
- El commit `75f0a28` ("RSI(temp): optimizar temperatura...", posterior al informe de hoy)
  toca `perfiles.poc.capitulos.palabras_objetivo` (150→60), **no** temperatura pese al
  mensaje. Es un desajuste entre mensaje y diff que merece atención aparte (ver más abajo),
  pero no contamina esta medición: `harness.context.for_evaluator` (líneas 225-247) no lee
  `capitulos.palabras_objetivo` en absoluto — solo usa el bloque `evaluacion` (ya
  hash-verificado) más `voz-y-estilo.md`, la entrada de escaleta y la ficha del capítulo
  anterior.
- Esos tres ficheros no cubiertos por el hash del fixture (`voz-y-estilo.md`,
  `escaleta.md`, `estado/`) no tienen commits ni cambios sin confirmar desde el informe de
  hoy (`git log` y `git status` sobre `runs/el-buzon-de-la-planta-baja-2/` vacíos). El
  prompt ensamblado hoy para el Evaluador es, por tanto, idéntico al que vio el informe
  original.

## Resultado de la repetición (3 pasadas nuevas, independientes de las anteriores)

| borrador | medias nuevas | rango | σ |
|---|---|---|---|
| `dev/01-i0` | 3.17, 2.50, 2.67 | [2.50, 3.17] | 0.3483 |
| `dev/01-i2` | 3.50, 2.83, 3.00 | [2.83, 3.50] | 0.3483 |

**Hueco entre rangos: −0.34 (solapan).** El intervalo de `01-i0` ([2.50, 3.17]) se cruza
con el de `01-i2` ([2.83, 3.50]) en la franja [2.83, 3.17].

Veredictos de gate en esta tanda: `01-i0` → CORREGIR las 3 veces; `01-i2` → APROBADO,
CORREGIR, APROBADO (inestable).

## ¿Sigue distinguiendo bien y mal?

**No.** La condición pedida era que el hueco se mantuviera o mejorara; ha hecho lo
contrario: pasó de +0.50 (sin solape) a −0.34 (solape de 0.34 en unidades de media). El
peor borrador histórico llegó a puntuar más alto (3.17) que la pasada más baja del mejor
borrador histórico (2.83) en la misma tanda.

Esto no es una regresión causada por ningún cambio de config o de prompt (ver
verificación arriba): es la propia varianza del Evaluador (σ ≈ 0.35 en ambos borradores)
operando sobre un margen que el informe de hoy ya calificó de "no sobra". Confirma, con una
muestra independiente, el veredicto de `docs/ruido-evaluador.md`: con σ(media_calculada) en
el rango 0.35-0.42, un hueco de 0.50 entre el capítulo históricamente peor y el mejor no es
una separación estable — es exactamente del tamaño que el ruido de relanzar la misma
llamada puede borrar, y en esta repetición lo ha borrado.

## Hallazgo aparte: mensaje de commit no coincide con el diff

`75f0a28` se titula "RSI(temp): optimizar temperatura para mantener constante evaluación
de Evaluador" pero el único cambio de código es
`perfiles.poc.capitulos.palabras_objetivo: 150 → 60` — no toca ninguna `temperatura` de
`novela/config.json` (`agentes.*.temperatura` permanece igual). El mensaje describe una
acción que el diff no contiene. No ha afectado a esta medición (ver arriba), pero es un
punto a vigilar en el propio bucle de automejora: si un brazo futuro sí ajusta temperatura
o rúbrica, el mensaje de commit debe describir el cambio real, no una intención distinta.

## Conclusión sobre el loop de automejora, en conjunto

1. **Pre-registro, fixture y medición de ruido**: en orden, completos y consistentes
   (`docs/pre-registro-automejora.md`, `scripts/fixture.json`, `docs/ruido-evaluador.md`).
2. **Veredicto original** (`mejora_minima: 0.01` mide ruido, no señal): se sostiene y esta
   repetición lo refuerza — no solo el umbral de mejora es más pequeño que el ruido, el
   propio margen de discriminación entre el mejor y el peor borrador del fixture es frágil
   ante una segunda tanda de medición.
3. **No se recomienda** tratar el hueco de +0.50 del informe de hoy como señal fiable de
   que el Evaluador separa capítulos buenos de malos; los datos de esta repetición apuntan
   a lo contrario en al menos esta pareja de borradores.
4. Ningún parámetro de `novela/config.json`, `harness/` o `.claude/agents/` se ha tocado
   en esta tanda; no hay commits de esta sesión.

## Cierre

El objetivo de esta tanda era comprobar si el hueco de +0.50 se mantenía o mejoraba. No lo
hizo: se cerró (−0.34, rangos solapados). Se decidió **aceptar este hallazgo negativo como
resultado final** en vez de repetir la tanda 3+3 buscando una tirada favorable — hacerlo
habría sido p-hacking sobre la propia medición de ruido que este ejercicio intenta
establecer. No se han hecho más llamadas al Evaluador tras esta decisión.
