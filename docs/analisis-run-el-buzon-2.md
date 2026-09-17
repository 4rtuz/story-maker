# Diagnóstico del run `el-buzon-de-la-planta-baja-2` — bucles y consumo

**Fuente:** sesión Langfuse `el-buzon-de-la-planta-baja-2`, 6 trazas, 2026-09-16 16:15 → 17:53 UTC.
Obtenido con `langfuse-cli api observations list --trace-id <id> --fields core,basic,io,usage,metadata`.
**Perfil:** `poc` (3 capítulos, 60 palabras objetivo, umbral 3,0, 2 reescrituras).
**Resultado:** 3 capítulos aceptados (cap. 3 *con deuda*) + auditoría final.

Complementa a [analisis-traza-2026-09-16.md](analisis-traza-2026-09-16.md), que diseccionó
**una** traza (cap. 1). Este mira **las seis** y encuentra cosas que sólo se ven a escala de
run. Los arreglos H1-H3, H5-H7 y H9 de aquel documento **no estaban aplicados cuando corrió
esto** (commit `71af732`, 18:32 UTC; el run terminó a las 17:53), así que no se repiten aquí.

---

## 1. Las cifras del run

| Invocación | Cap. | Estado inicial | Turnos | Subag. | Reloj | Coste |
|---|---|---|---:|---:|---:|---:|
| `791be39d` | 1 | INIT | 10 | 1 | 91 s | 0,56 $ |
| `8d8a04c8` | 1 | INIT | 33 | 4 | 326 s | 2,69 $ |
| `edce12e7` | 1 | ESCRIBIENDO | 52 | 10 | 1.035 s | 4,75 $ |
| `f2b1b61f` | 2 | ESCRIBIENDO | 25 | 4 | 410 s | 2,22 $ |
| `0d834e01` | 3 | ESCRIBIENDO | 73 | 10 | 1.405 s | **7,19 $** |
| `146425e5` | — | AUDITORIA_FINAL | 14 | 0 | 80 s | 0,72 $ |
| | | | **207** | **29** | **55,8 min** | **18,13 $** |

**4,72 $ y 16 minutos por capítulo aceptado de ≤ 90 palabras.**

### Dónde se van los tokens

| Cubo | Tokens | % de la entrada |
|---|---:|---:|
| Orquestador · `cache_read` | 16.630.617 | **97,5 %** |
| Orquestador · `cache_creation` | 423.727 | 2,5 % |
| Orquestador · `input` | 406 | 0,0 % |
| Orquestador · `output` | 154.907 | — |
| **Los cinco roles, juntos** | **515.105** | — |

**Ratio orquestador : subagentes = 33 : 1.** La palanca de cuota de CLAUDE.md (`tools: []`)
está aplicada sobre el 3 % del gasto. Confirma y agrava H4 del documento anterior: allí el
ratio medido en una sola traza era 25 : 1.

### Coste por rol

| Rol | Llamadas | Tokens | Reloj | Tok/llamada |
|---|---:|---:|---:|---:|
| **continuista** | 7 | **184.863** | **911 s** | 26.409 |
| escritor | 9 | 140.117 | 134 s | 15.568 |
| evaluador | 7 | 98.050 | 417 s | 14.007 |
| arquitecto | 5 | 58.433 | 80 s | 11.686 |
| editor-acto | 3 | 33.642 | 88 s | 11.214 |

Los subagentes son el 49 % del reloj del run. **El Continuista solo es el 27 %.**

---

## 2. El hallazgo central: el bucle de reescritura cuesta 3,2×

Comparando la traza que **no** entró en bucle con la que lo agotó:

| | cap. 2 (`f2b1b61f`) | cap. 3 (`0d834e01`) |
|---|---|---|
| Iteraciones | 1 | 3 |
| Turnos | 25 | 73 |
| Subagentes | 4 | 10 |
| `cache_read` | 1,62 M | 7,62 M |
| Reloj | 410 s | 1.405 s |
| Coste | 2,22 $ | **7,19 $** |
| Media final | 3,00 → aceptado | 2,67 → **aceptado con deuda** |

**El camino largo cuesta 3,2× y termina peor.** No es casualidad de un capítulo: la
trayectoria de calidad es prácticamente la misma función en los tres.

### Trayectoria de calidad (`.intentos/*-eval.json`)

Los dos criterios bloqueantes del perfil (`tension`, `escaleta`, umbral 3) en negrita:

| Capítulo | i0 | i1 | i2 | Desenlace |
|---|---|---|---|---|
| 1 | **2**/**2** · 2,50 | **2**/**3** · 2,67 | **3**/**3** · 3,00 | aceptado, último intento disponible |
| 2 | **3**/**3** · 3,00 | — | — | aceptado a la primera |
| 3 | **2**/**2** · 2,50 | **2**/**3** · 2,67 | **2**/**3** · 2,67 | **aceptado con deuda desde i1** |

Tres observaciones, todas caras:

1. **El cuello de botella no es la media, es `tension`.** En los tres capítulos la media
   supera o roza el umbral antes que los criterios bloqueantes; lo que veta la aceptación
   es `tension: 2`, que en el cap. 3 **no se movió en ninguna de las tres pasadas**. Bajar
   `umbral_media` no habría cambiado una sola decisión de este run.
2. **La ganancia marginal por iteración es +0,17 y se agota.** +0,17 es exactamente un
   criterio de seis. En el cap. 3 la iteración 2 ganó **0,00** (2,67 → 2,67) y el capítulo se
   aceptó desde i1. Ese ciclo estéril costó 1 Escritor + 1 Evaluador + 1 Continuista
   (58.000 tokens de subagente) y los ~25 turnos más caros de la traza:
   **≈ 3,2 M de `cache_read`, ≈ 52 % del coste del capítulo.**
3. **El cap. 1 aceptó en el filo**: *exactamente* en 3,00 y *exactamente* en el último
   intento disponible. Cualquier regla de parada tiene que dejar pasar ese caso, que es
   progreso real, y cortar el del cap. 3, que no lo es. La frontera entre ambos es
   estrecha: 0,17 contra 0,00.

### Por qué el bucle es tan caro: el contexto crece 1.860 tok/turno

Deduplicando las generations por `request_id`:

| Traza | Turnos | `cache_read` 1.er turno | último turno | pendiente |
|---|---:|---:|---:|---:|
| `edce12e7` | 52 | 29.167 | 119.271 | 1.767 |
| `f2b1b61f` | 23 | 29.167 | 91.554 | 2.836 |
| `0d834e01` | **75** | 14.181 | **151.800** | 1.860 |

Cada turno paga la lectura íntegra del contexto acumulado, así que el coste de una
invocación crece con el **cuadrado** de sus turnos. Lo que lo engorda está medido en el
cap. 3:

| Qué entra en el contexto del orquestador | chars |
|---|---:|
| `Read` de los `ctx-*.md` que construye el núcleo | 39.462 |
| Los mismos textos otra vez, como `prompt` del `Task` | 87.785 |
| Salidas de los subagentes | ~21.000 |
| `Write` de esas mismas salidas a disco | ~25.000 |

**Cada artefacto pasa dos veces por el contexto y se queda allí el resto de la invocación.**
`SKILL.md:35` lo manda explícitamente ("luego lees ese archivo con `Read` y lo pasas entero").
Con `tools: []` es inevitable que el prompt viaje por valor en el `Task`; lo que sí es
evitable es que la invocación siga viva 75 turnos arrastrándolo.

---

## 3. Fricción operativa: turnos tirados

Todos verificados en el `input`/`output` de las observaciones `TOOL` con `level: ERROR`.

| # | Qué pasó | Dónde | Frecuencia |
|---|---|---|---|
| F1 | `python -m harness next --root <ruta>` → exit 2 | primer turno | **6 de 6 trazas** |
| F2 | `python … record cont …; if ($?) { python … decide }` → denegado por el validador de permisos | cap. 3 | 1 |
| F3 | `save-attempt` rechaza el borrador: **29 palabras**, el perfil exige 30-90 | cap. 3, i0 | 1 |
| F4 | `save-attempt` rechaza el parche: **3 escenas**, el perfil exige exactamente 2 | cap. 3, i2 | 1 |
| F5 | `shell` denegado ×2 en la auditoría final | cap. 4 | 2 |

- **F1 ya está arreglado** (H5, `harness/cli.py:build_parser`, commit `71af732`). Verificado:
  `python -m harness next --root runs/el-buzon-de-la-planta-baja-2` → exit 0.
- **F2 no es el `;`** —eso funciona y `panel/tracing.py:tool_names` ya lo contempla— sino el
  `if ($?) { … }` de PowerShell, que el validador no puede analizar estáticamente.
- **F3/F4 no son fallos de prompt**: `harness/context.py:170-176` ya le dice al Escritor el
  rango exacto y que fuera de él se rechaza automáticamente. El modelo lo incumple igual, y
  cada incumplimiento cuesta una reinvocación completa (~15.500 tokens).
- **F4 es el caso interesante**: el parche pasó la verificación por hash de §9.5 (las escenas
  no señaladas no cambiaron) y *aun así* fue rechazado, porque el Escritor **añadió** una
  escena 3. El modo PARCHE puede violar `escenas_max` por construcción.

---

## 4. Modificaciones propuestas

Ordenadas por ahorro dividido entre esfuerzo. Las tres primeras son las que importan.

### M1 · Parar cuando la reescritura deja de mejorar — `harness decide`

**Problema.** §9.4 sólo para al agotar `max_reescrituras`. La iteración 2 del cap. 3 ganó
0,00 y costó ≈ 3,2 M de `cache_read` y 58.000 tokens de subagente.

**Cambio.** Nueva clave `evaluacion.mejora_minima` en `base`. En `harness decide`, si
`media(i) − media(i−1) < mejora_minima`, la decisión es `aceptar_con_deuda` con el mejor
intento por media, en vez de `parchear`.

Es la regla que ya existe para "iteraciones agotadas", disparada por una condición distinta.
Determinista, en el núcleo, y no toca el reparto de capas.

**Valor: `0.01`, no 0,20.** Un criterio de seis vale 0,167, así que cualquier umbral por
encima de eso vetaría un progreso legítimo de un solo criterio — justo el +0,17 con el que el
cap. 1 empezó la escalada que terminó en 3,00. La regla útil es la mínima: *parar sólo cuando
la reescritura no mejora nada*.

**Ahorro medido sobre este run:** el cap. 3 habría parado en i1 con la misma media que acabó
aceptando (2,67) → **−52 % del coste de ese capítulo**. El cap. 1 no se habría acortado
(+0,17 y +0,33 superan 0,01), que es el comportamiento correcto.

---

### M2 · Cerrar la invocación por *iteración*, no por capítulo — §7.5

**Problema.** El coste de una invocación crece con el cuadrado de sus turnos (1.860 tok/turno).
El cap. 3 llegó a 151.800 tokens de contexto en un único proceso.

**Cambio.** §7.5 pasa de "una invocación escribe un capítulo y para" a "una invocación
**adelanta el estado y para**". El estado ya está íntegro en `estado.json` y en `.intentos/`
—`harness next` ya sabe devolver `ACCION: escribir` con `ITERACION: 2`—, así que **no hace
falta tocar el núcleo**: es un cambio en `SKILL.md` y en el bucle de `panel/server.py`, que
ya relanza el binding como subproceso.

**Ahorro proyectado** (modelo cuadrático `N·b + s·N(N−1)/2`, ajustado a las 6 trazas):
cap. 3, 75 turnos en una invocación → 3 invocaciones de ~25 → `cache_read` de 7,62 M a
≈ 3,3 M, **−56 %**. Combinado con M1 (2 invocaciones): **−71 %**.

**Coste.** Un `cache_creation` de baseline extra por invocación (≈ 14 k tokens, ≈ 2,5 % del
gasto actual) y una petición más de arranque. Se paga solo con creces.

**Contrapartida honesta.** Es un cambio de spec, no de código, y el documento anterior ya lo
apuntaba como pendiente (H4, palanca 2). Estas seis trazas son la evidencia para decidirlo.

---

### M3 · El Continuista, sólo en el momento de aceptar

**Problema.** 7 llamadas, 184.863 tokens (36 % del gasto de subagentes), 911 s (27 % del reloj
del run) y **veredicto `OK, 0 contradicciones` en las 7**. Se ejecuta en cada iteración,
incluso sobre parches de 2 escenas en capítulos de 60 palabras.

**Cambio.** En `SKILL.md`, la verificación de continuidad deja de correr tras cada
`save-attempt` y corre **una sola vez, sobre el intento que `harness decide` va a aceptar**.
`harness decide` necesita entonces poder decidir sin informe del Continuista en las
iteraciones intermedias (hoy §9.2 exige `continuidad OK`): en i>0 y sin informe, la decisión
se toma sólo por media, y la continuidad se comprueba antes del `accept`.

**La puerta no se pierde**: el capítulo que se acepta y se commitea sigue pasando por el
Continuista. Lo que se elimina es verificar intentos que se van a tirar.

**Ahorro sobre este run:** 7 llamadas → 3. **−110.000 tokens de subagente y −540 s (9 min)**,
más ~6 turnos de orquestador por capítulo en bucle.

**Riesgo.** Si el intento aceptado falla continuidad, hay que reescribir con una iteración ya
gastada. Mitigación: ese caso cae en `aceptar_con_deuda`, que es lo que ya hace el harness
cuando se agotan las iteraciones, y la contradicción queda anotada en `deuda-narrativa.md`.

---

### M4 · Calibrar el perfil `poc` — ~~sólo `config.json`~~ **retirada**

La propuesta era bajar `umbral_media` a 2,5 en el perfil `poc`. **Las puntuaciones por
criterio la desmienten**: lo que veta la aceptación no es la media sino `tension: 2` contra
un `umbral_criterio_bloqueante: 3`. Bajar la media no habría cambiado ni una decisión de
este run, y bajar el criterio bloqueante a 2 deja la puerta de §9.2 sin sentido.

La otra mitad, `max_reescrituras: 1`, tampoco se sostiene una vez aplicado M1: con la regla
de estancamiento el cap. 3 ya para en i1 por sí solo, mientras que el cap. 1 conserva la
iteración con la que llegó legítimamente a 3,00. Recortarla a 1 sólo costaría esa aceptación
limpia.

**M4 queda subsumida por M1.** Se deja escrita porque el razonamiento original —leer sólo
la media— es el error que hay que no repetir al calibrar el perfil `base`.

---

### M5 · Una orden por llamada, sin control de flujo de PowerShell

**Cambio.** Una línea en `SKILL.md`: encadenar con `;` está permitido; `if ($?) { … }`, `&&`
y demás control de flujo **no** —el validador de permisos no puede analizarlos y deniega la
llamada, que es exactamente lo que pasó en el cap. 3.

**Ahorro:** un turno denegado más su reintento por ocurrencia. Coste: una línea.

---

### M6 · En modo PARCHE, el Escritor devuelve sólo las escenas parcheadas

**Problema.** El cap. 3 i2 devolvió 3 escenas donde el perfil exige exactamente 2. El parche
pasó la verificación de hashes de §9.5 y fue rechazado después por `structural_problems`.
Añadir una escena en un parche no debería ser expresable.

**Cambio.** En modo PARCHE, el contrato pasa a ser "devuelve sólo los bloques
`<!-- ESCENA n -->` que se te han pedido" y el núcleo reensambla el capítulo sustituyendo
esas escenas. Toca `harness/context.py` (instrucción) y `harness/scenes.py` (reensamblado).

**Ahorro:** una reinvocación del Escritor (~15.500 tokens) por ocurrencia, y de paso baja el
tamaño de la respuesta del Escritor en cada parche. **Es el único de la lista que toca el
núcleo de verdad**; si hay que recortar la lista, es el primero que se cae.

---

### M7 · Deduplicar generations por `request_id` — observabilidad

**Problema.** Deduplicando por `request_id`, el número de generations reproduce `num_turns`
mucho mejor que el conteo bruto:

| Traza | generations brutas | únicas por `request_id` | `result.num_turns` |
|---|---:|---:|---:|
| `791be39d` | 17 | **10** | 10 |
| `8d8a04c8` | 41 | **33** | 33 |
| `edce12e7` | 62 | **52** | 52 |
| `0d834e01` | 89 | **75** | 73 |

**Cambio.** En `panel/tracing.py:_assistant`, la clave de deduplicación pasa de `message.id` a
`metadata.request_id` con `message.id` como respaldo. Dos líneas.

**Por qué importa.** Todas las decisiones de este documento se leen de estas cifras. No es
ahorro; es la condición para poder medir si M1-M4 funcionan.

---

## 5. Efecto conjunto estimado

Con lo aplicado (M1 + M3 + M5), sobre el cap. 3, que es el caso malo:

| | Hoy | M1+M3 | +M2 |
|---|---:|---:|---:|
| Iteraciones | 3 | 2 | 2 |
| Llamadas a subagentes | 10 | 5 | 5 |
| Turnos del orquestador | 73 | ≈ 50 | ≈ 50 (en 2 procesos) |
| `cache_read` | 7,62 M | ≈ 3,0 M | ≈ 1,8 M |

Y sobre el run entero: **7 llamadas al Continuista → 3**, ~15 min de reloj menos sólo por
ahí, y la fase de escritura de 14,16 $ a **≈ 6-7 $**.

Son proyecciones sobre el modelo de crecimiento ajustado a estas seis trazas, **no
mediciones**: hay que confirmarlas con el primer run posterior, y M7 es lo que permite
hacerlo.

## 6. Estado de aplicación

| | Estado | Dónde |
|---|---|---|
| M7 · dedup por `request_id` | ✅ aplicado | `panel/tracing.py:_assistant` |
| M5 · sin control de flujo en las órdenes | ✅ aplicado | `SKILL.md` §«Cómo llamar al núcleo» |
| M4 · calibrar `poc` | ⛔ retirada | subsumida por M1 |
| M1 · parada por estancamiento | ✅ aplicado | `harness/cli.py:_improvement`, `cmd_decide`; `config.json` |
| M3 · Continuista sólo al aceptar | ✅ aplicado | `harness/cli.py:_to_verify`, `cmd_next`, `cmd_decide`, `cmd_accept`; `SKILL.md` paso 3 |
| M2 · invocación por iteración | ⏸ pendiente de medir | cambio de §7.5 + relanzado del panel |
| M6 · PARCHE devuelve sólo sus escenas | ⏸ pendiente | `harness/context.py`, `harness/scenes.py` |

`python tests/dry_run.py` → 46/46 (antes 40/40; las seis nuevas cubren la regla de
estancamiento, el salto del Continuista y la iteración elegida). `python -m panel.tracing`
y `python -m panel.runs` → correctas.

**M3 abrió un hueco que hubo que cerrar en el mismo cambio:** `accept` promocionaba
`best_attempt()` mientras que `decide` verificaba la iteración en curso. Mientras se
verificaban todas daba igual; verificando sólo una, podían no ser la misma (una media más
alta que no aprobó por criterio bloqueante) y se habría promocionado un capítulo sin pasar
por el Continuista. `decide` fija ahora `estado.iteracion_aceptada` y `accept` la respeta.

### Lo que queda, y por qué está parado

- **M2** es el mayor ahorro que queda, pero M1 y M3 acaban de recortar el mismo bucle que
  M2 abarata: el cap. 3 pasaría de 3 iteraciones y 10 subagentes a 2 y 5. Medir un capítulo
  con lo ya aplicado antes de tocar §7.5 es lo que dice la sección 5 de este documento, y
  es además un cambio que afecta al operador (una invocación deja de ser un capítulo).
- **M6** toca el núcleo para arreglar una fricción que se dio una vez. Es el primero que
  se cae si hay que recortar.

## 7. Lo que este run dice del riesgo abierto de §2

El POC gastó **18,13 $ y 56 minutos en 3 capítulos de ≤ 90 palabras**, con el Opus de 1 M de
contexto y sin salir de `development`. El perfil `base` son 30 capítulos de 2.000 palabras
con umbral 4,0 y bloqueantes ≥ 4 — un listón que este run no alcanzó ni una vez con el
umbral en 3,0. Extrapolar linealmente no sirve (el coste crece con el cuadrado de los turnos
por invocación), pero el orden de magnitud basta para decir que **M2 no es una optimización
opcional sino la condición para que una novela de 30 capítulos quepa**.
