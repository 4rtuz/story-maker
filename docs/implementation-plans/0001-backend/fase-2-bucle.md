# Fase 2 — El bucle por capítulo

**Objetivo.** Que el bucle de `.claude/commands/novela-continuar.md` sea ejecutable de principio
a fin.

**Al terminar existe**: `briefing`, `validar`, `aplicar-delta` y `checkpoint`. Con eso, un
capítulo se puede escribir, revisar, registrar y cerrar sin intervención manual.

**Cierra**: RF-08 a RF-21, RF-27, RF-29. CA-08 a CA-22, CA-27, CA-33.

Es la fase larga y la que más superficie tiene. Requiere la fase 1 terminada —los modelos, el
lock, la escritura atómica y los fixtures—, pero no requiere leer su documento.

Antes de empezar, lee las convenciones de ciclo del [README](README.md). Dos aplican aquí con
especial fuerza: **property-based obligatorio** en `assemble.py`, `gates.py`, `apply.py` y
`violaciones.py`, y **la frontera pura/impura** — si un fichero del núcleo importa `pathlib`,
`open` o `datetime.now`, el property-based deja de ser posible y la fase se vuelve intestable.

---

## Orden y por qué

`briefing` primero porque es el subcomando con más superficie y el que más decisiones arrastra.
`aplicar-delta` después, porque todo lo demás depende de que el estado avance. `checkpoint` al
final, porque confirma lo que los otros tres hicieron.

`run.py` va antes que todos: los cuatro escriben en `harness.log`.

---

## 2.1 — Run y manifiesto

**Construye**: `backend/novela/plataforma/run.py`.

Este fichero no aparece en el árbol de `architecture.md` §3.1 ni en el de la spec §5.1, pero la
tabla de trazabilidad de la spec §12 sí nombra su test
(`novela/plataforma/test_run.py::test_manifiesto_y_log`). Va en `plataforma/` porque es I/O
compartida por cuatro slices.

**Rojo**: `novela/plataforma/test_run.py::test_manifiesto_y_log`. El primer subcomando de un
capítulo sin run abierto crea `runs/<run_id>/` y `manifest.json` con sha de commit y versión de
recetas; y `harness.log` **contiene ya su línea antes de que el proceso termine** — no al
cerrarse. Lo segundo se comprueba leyendo el log desde otro descriptor mientras el proceso vive.

**Verde**: generación de `run_id`, `manifest.json` y un logger con volcado línea a línea.

**El `run_id` viene de dos sitios**, y ahora es **RF-29**: si `NOVELA_RUN_ID` está definida se
usa; si no, el CLI genera `r-AAAAMMDD-HHMM`. El valor de entorno **se valida contra
`^r-\d{8}-\d{4}$`**: una variable con basura aborta en vez de crear `runs/<lo-que-sea>/`. Es una
cadena de fuera del proceso que se convierte en ruta, con la misma precaución que el slug.

Segundo test, entonces: `test_run.py::test_run_id_de_entorno` — con la variable definida el
briefing se escribe bajo ese run; con un valor que no casa el formato, el comando aborta sin crear
directorio (CA-33).

Compra dos cosas: alinear el run con el `session_id` de Langfuse —lo que cierra
`architecture.md` §12.2— y hacer deterministas las rutas de `runs/` en los tests, que es lo que el
golden de la tarea 2.6 necesita para comparar byte a byte.

`manifest.json` lleva sha del commit, versión de recetas, y versiones de canon y plan vigentes.
Sin él, comparar dos ejecuciones es comparar dos anécdotas (`validators.md` §4.7).

**El volcado línea a línea no es un detalle de implementación.** `architecture.md` §12.6 quiere
servir el log en vivo por la API y lo dice explícitamente: antes de escribir nada de eso hay que
comprobar que el harness vacía el buffer línea a línea, porque si volcara al final, no sirve de
nada. Esta tarea es esa comprobación, hecha por adelantado.

**Cierra**: CA-13, CA-33, RF-13, RF-27, RF-29.

**Commit**: `feat(plataforma): run, manifiesto y log con volcado línea a línea`

---

## 2.2 — Recetas

**Construye**: `backend/novela/slices/briefing/recipes.py`, `backend/config/recipes.yaml`.

**Rojo**: `novela/slices/briefing/test_recipes.py::test_receta_valida`. Una receta con una capa
desconocida se rechaza; las siete recetas del fichero cargan.

**Verde**: el formato de `architecture.md` §6.2 como modelo Pydantic, y las **siete** recetas.

El formato, literal de §6.2:

```yaml
escritor:
  presupuesto_tokens: 60000
  capas:
    - permanente: [canon/premisa, canon/mundo, canon/estilo]
    - personajes: presentes_en_escena
    - estado: [personajes, conocimiento, hilos_abiertos, objetos]
    - inmediata: capitulo_anterior_completo
    - reciente: {n: 3, granularidad: parrafo}
    - remota: {granularidad: una_linea, desde: 1}
    - plan: capitulo_actual
    - variacion: restriccion_de_apertura
  excluir: [canon/misterio]
```

Detalle de forma que cuesta ver: `capas` es una **lista de mapas de un solo par**, no un mapa. El
orden importa —es el orden de ensamblado— y un mapa no lo conserva de forma explícita. El valor
de cada capa es heterogéneo: lista de rutas, cadena enum, lista de colecciones de estado, o mapa
de parámetros. Soporta glob (`canon/*`).

**`architecture.md` solo trae dos de las siete recetas.** Faltan cinco, y escribirlas es trabajo
de esta tarea. Lo que se sabe de cada una sale de §7.5 (entradas por agente) y §6.5
(presupuestos):

| Agente | Presupuesto | Entradas, de §7.5 | ¿Ve el misterio? |
|---|---|---|---|
| `arquitecto` | 50.000 | `config.yaml` | Lo escribe |
| `trazador` | 55.000 | `config.yaml`, `canon/*` incluido `misterio.md` | **Sí** |
| `escritor` | 60.000 | ya en §6.2 | No |
| `continuista` | 65.000 | ya en §6.2 | **Sí** |
| `editor-estilo` | 68.000 | `capitulos/NN.md`, `canon/estilo.md` con párrafos canónicos y prohibiciones | No |
| `lector-suspense` | 67.000 | `capitulos/NN.md`, `canon/misterio.md`, `plan/escaleta.md`, estado (`pistas`, `conocimiento_lector`, `tension_real`) | **Sí** |
| `cronista` | 70.000 | `capitulos/NN.md` aprobado, estado vigente | No |

Los presupuestos que faltan, derivados de la aritmética de §6.5 —`100.000 − 10.000 fijo −
salida_esperada − 15.000 margen`—: `arquitecto` 50.000, `trazador` 55.000, `editor-estilo` 68.000,
`lector-suspense` 67.000. El `cronista` lleva 70.000, que ya viene de §6.5.

**Techo conocido, y conviene que quede escrito en el YAML**: la salida de `arquitecto` y
`trazador` **escala con `num_capitulos`**, porque el segundo emite una ficha por capítulo. A 24
capítulos estos números sobran; a 99 el `trazador` no cabe. Estos presupuestos suponen
`num_capitulos ≤ 30`; más allá, o se re-derivan o el `trazador` escribe por actos en varias
invocaciones. No lo generalices ahora: es un problema que nadie tiene.

La receta se versiona, y su identificador se escribe en `manifest.json` (tarea 2.1). Es lo que
convierte un cambio de prompt en un despliegue comparable (`validators.md` §4.8).

**Commit**: `feat(briefing): recetas de los siete agentes`

---

## 2.3 — Ensamblado

**Construye**: `backend/novela/slices/briefing/assemble.py`.

**Rojo**: `novela/slices/briefing/test_assemble.py::test_incrusta_contenido_no_rutas`. Para una
receta con una capa `permanente`, el resultado contiene el **texto** de los ficheros, no sus
rutas.

**Verde**: función pura. Recibe receta y datos, devuelve el briefing ensamblado. **No abre
ficheros**: los recibe. Esa es la frontera que hace posible todo el property-based de las tareas
2.4 y 2.5.

**Incrusta contenido, nunca rutas.** Un briefing es el contexto exacto de una invocación. Si
llevara rutas, el agente tendría que abrirlas — y los agentes no tienen `Glob` ni `Grep`
precisamente para que solo alcancen lo que su briefing les nombra.

Las nueve capas vistas en §6.2: `permanente`, `personajes`, `estado`, `inmediata`, `reciente`,
`remota`, `plan`, `variacion`, `objetivo`.

La capa `estado` es la que justifica los índices de la tarea 1.9: trae **solo** las entradas que
tocan a las entidades del capítulo, por consulta con índice, no por recorrido en Python
(`architecture.md` §6.4).

**Commit**: `feat(briefing): ensamblado por capas, función pura`

---

## 2.4 — El guardarraíl del secreto

La tarea más importante de la fase. Es el invariante 3, y hoy es lo único que lo sostiene.

**Construye**: la comprobación de exclusión en `assemble.py`.

**Rojo**: dos tests.

- `novela/slices/briefing/test_briefing.py::test_misterio_nunca_en_briefing` —
  **property-based** sobre canons generados por Hypothesis: `misterio.md ⊄ briefing(escritor |
  editor-estilo, *)` para cualquier canon. Y el comando sale != 0 **sin dejar fichero**.
- `novela/slices/briefing/test_briefing.py::test_misterio_incrustado` — el briefing del
  `continuista` contiene literalmente el texto de `canon/misterio.md`.

**Verde**: si el briefing ensamblado de un agente cuya receta excluye `canon/misterio` contiene
texto procedente de ese fichero, **aborta y no escribe nada**.

Los dos tests parecen contradictorios y no lo son: tres agentes ven el misterio y dos no.
`trazador`, `continuista` y `lector-suspense` lo reciben **incrustado**; `escritor` y
`editor-estilo` no lo reciben en ninguna forma.

La incrustación no es una comodidad, es lo que hace viable la contención futura: los permisos de
Claude Code valen para la sesión entera y no por subagente, así que un `deny` sobre
`canon/misterio.md` rompería a los tres que sí lo necesitan. Si el contenido va incrustado,
ningún agente necesita abrir el fichero y la regla `deny` pasa a ser una línea igual para los
siete (`architecture.md` §12.7). Esta tarea deja esa puerta abierta sin tener que volver al CLI.

**Por qué property-based y no un ejemplo.** Un test de ejemplo comprueba que *ese* misterio no se
filtra. La propiedad comprueba que ninguno lo hace (`validators.md` §3.6). Es la cuarta propiedad
de esa tabla y la que su autor llama la más valiosa.

**Lo que este guardarraíl no cubre, y conviene saberlo**: compara texto. Nada impide que una
ficha de `plan/capitulos/NN.md` parafrasee la solución sin citarla. Eso es contenido, no ruta, y
ningún test lo coge — lo cubre la sonda adversaria de `validators.md` §4.9, que corre por release
del harness y no por capítulo. No intentes resolverlo aquí.

**Cierra**: CA-09, CA-10, RF-09, RF-10.

**Commit**: `feat(briefing): guardarraíl del secreto con property-based`

---

## 2.5 — Presupuesto y degradación

**Construye**: el conteo y la degradación, en `assemble.py`.

**Rojo**: dos tests.

- `test_briefing.py::test_presupuesto_excedido_falla` — un fixture cuyo ensamblado excede el
  presupuesto hace salir a `briefing` != 0, y `runs/…/briefings/` queda **sin el fichero**.
- `test_assemble.py::test_orden_de_degradacion` — con presupuesto ajustado, degrada en el orden
  de §6.5 y **conserva íntegras** las capas de `canon/` y de estado filtrado.

**Verde**: cuenta lo ensamblado a **3,5 caracteres por token** y compara contra
`presupuesto_tokens`. Si no cabe, degrada en este orden fijo, de menos a más doloroso:

1. Se recortan los resúmenes a una línea más antiguos.
2. Los resúmenes a párrafo bajan a una línea.
3. La lista de personajes se reduce a los que tienen diálogo en el capítulo.
4. Se para y se pide intervención.

**`canon/` y el estado filtrado no se degradan nunca**: son las dos capas cuya ausencia produce
contradicción en vez de imprecisión.

**Nunca trunca en silencio.** Un briefing truncado es un agente que no sabe lo que no sabe:
produce un capítulo plausible y contradictorio, que es el fallo más caro de detectar de todo el
sistema. Es también la alternativa que la spec §15 descarta explícitamente.

La ratio de 3,5 es una heurística de caracteres, tratada como **cota superior**. El error medido
ronda el 10% y siempre por exceso, que es el lado correcto. Es un riesgo aceptado de la spec
§13: si un día un briefing que el CLI dio por bueno falla por contexto, esa es la señal para
revisarlo — y la palanca entonces es subir el presupuesto de la receta, no el techo.

**Cierra**: CA-11, CA-12, RF-11, RF-12.

**Commit**: `feat(briefing): techo de contexto y degradación en orden fijo`

---

## 2.6 — `novela briefing`

**Construye**: `backend/novela/slices/briefing/cmd.py`.

**Rojo**: `novela/slices/briefing/test_briefing.py::test_golden_escritor`. El briefing del
`escritor` sobre el fixture coincide **byte a byte** con el esperado. Es el golden dataset de
`validators.md` §4.2, y el único sitio del sistema donde cabe uno: la prosa no tiene golden, el
ensamblado sí.

**Verde**: la cáscara. Argumentos, lock, lectura de disco, llamada a `assemble.py`, escritura de
`runs/<run_id>/briefings/NN-<agente>.md`, código de salida.

```
novela briefing <slug> <cap> <agente>
```

El golden es frágil por diseño: cualquier cambio en el ensamblado lo rompe, y eso es lo que se
quiere. Si se rompe por un cambio deliberado, se regenera y el diff del fichero golden es la
revisión del cambio.

Aquí es donde el `run_id` determinista de la tarea 2.1 paga: sin él, la ruta del briefing cambia
en cada ejecución y el golden no se puede comparar.

**Nota para quien mantenga esto**: los ficheros de `runs/<run_id>/briefings/` son el único
registro de qué vio cada agente — el trazado de Langfuse no captura el contexto ensamblado
(`validators.md` §4.1). No los borres al limpiar.

**Cierra**: CA-08, RF-08.

**Commit**: `feat(cli): novela briefing`

---

## 2.7 — Los gates

**Construye**: `backend/novela/slices/validacion/gates.py`.

**Rojo**: `novela/slices/validacion/test_gates.py::test_gates_property`. **Property-based**: un
capítulo con una pista del plan ausente, con un hilo cerrado sin abrir, o con palabras fuera de
rango, **nunca** pasa `validar`. Es la quinta propiedad de `validators.md` §3.6.

**Verde**: funciones puras. Cinco comprobaciones, **en este orden**:

1. Frontmatter del capítulo contra su JSON Schema.
2. Palabras dentro de `palabras_por_capitulo.{min, max}`.
3. Presencia en el frontmatter de todas las pistas que `plan/capitulos/NN.md` manda plantar y
   pagar.
4. Que ningún hilo se cierre sin haberse abierto.
5. Que todo id citado exista.

El orden es de más barato a más caro y de más común a más raro.

**Cuidado con el gate 2**: compara contra `min` y `max`, **nunca contra `objetivo`**. La terna
viene de la tarea 1.3 y la tentación de exigir el objetivo es real; exigir un número exacto
degrada la prosa, y `definitions.md` §1 lo dice.

El frontmatter que se valida, de `architecture.md` §7.2:

```yaml
capitulo: 7
titulo: "…"
pov: per-elena-vidal
palabras: 3180
escenas: [esc-07-1, esc-07-2, esc-07-3]
pistas_plantadas: [pis-009]
pistas_pagadas: [pis-004]
hilos_abiertos: [hil-007]
hilos_cerrados: [hil-002]
version_canon: 3
version_plan: 2
run_id: r-20260921-0942
```

Este gate es lo que decide si se gastan tres llamadas a modelo. Ejecutarlo antes de cualquier
agente de revisión no es una optimización: es el diseño (`validators.md` §6).

**Cierra**: parte de CA-14, RF-14.

**Commit**: `feat(validacion): los cinco gates como funciones puras`

---

## 2.8 — Mutación sobre los gates

**Construye**: configuración de `mutmut` y su entrada en CI.

**Rojo**: no aplica — es una medición, no un ciclo.

**Verde**: `mutmut` sobre `gates.py` **no deja mutantes vivos en las comparaciones de rango**.

El caso concreto que esto busca, de `validators.md` §3.7: si al mutar `>=` por `>` en la
comprobación de longitud mínima ningún test falla, ese gate es decorativo y lleva siéndolo desde
que se escribió. **Un gate no probado es peor que no tenerlo, porque da confianza falsa.**

`mutmut` corre **solo** sobre `gates.py` y `apply.py`. En el resto del backend es caro y poco
informativo; no lo extiendas.

**Cierra**: CA-15.

**Commit**: `test(validacion): mutación sobre gates, sin mutantes vivos en los rangos`

---

## 2.9 — `novela validar`

**Construye**: `backend/novela/slices/validacion/cmd.py`.

**Rojo**: `novela/slices/validacion/test_validacion.py::test_informe_valida`. Tras un fallo,
`qa/NN-validacion.json` valida contra `qa-informe.schema.json`.

**Verde**: la cáscara. Escribe los hallazgos con el modelo de la tarea 1.7 y **sale con 1**.

```
novela validar <slug> <cap>
```

`qa/NN-validacion.json` es el único fichero que recibe el escritor en un reintento. Ni el
capítulo de vuelta, ni un «está mal» genérico: el informe y nada más. De ahí que el formato sea
estructurado y no prosa.

**Cierra**: CA-16, RF-15.

**Commit**: `feat(cli): novela validar y su informe de QA`

---

## 2.10 — Rendimiento de `validar`

**Construye**: `novela/slices/validacion/test_validacion.py::test_rendimiento`.

**Verde**: `validar` sobre un capítulo de 4.000 palabras termina en **< 2 s**.

Es RNF-01, y no es una métrica decorativa: `validar` corre al menos una vez por capítulo y hasta
tres con reintentos. Si tarda, el bucle desatendido se nota.

Si falla, el sospechoso número uno es la comprobación 5 (todo id citado existe) hecha por
recorrido en vez de por consulta indexada.

**Cierra**: CA-27, RNF-01.

**Commit**: `test(validacion): cota de 2 s sobre un capítulo de 4.000 palabras`

---

## 2.11 — El esquema del delta

**El hueco de modelado más grande de la spec.** Léelo entero antes de escribir.

**Construye**: `backend/schemas/delta.schema.json`, y el modelo Pydantic del que se genera.

**Rojo**: `novela/slices/delta/test_delta.py::test_delta_valida`. Un delta de ejemplo valida; uno
al que le falta `resumen` no.

**Verde**: el modelo.

**No existe ni un ejemplo del delta del `cronista` en ninguno de los cuatro documentos de
referencia**, y es la única entrada de `aplicar-delta`. Su forma hay que derivarla. La derivación
propuesta:

- **Una sección por colección mutable o append-only de la rama 4**: `linea_temporal`,
  `personajes`, `conocimiento`, `relaciones`, `objetos`, `libro_de_hechos`, `hilos`. Las
  append-only traen solo altas; las mutables traen el estado nuevo de las entidades tocadas.
- **`pistas` y `metricas` no entran**: son derivadas (`definitions.md` §4). Se computan al
  aplicar, no vienen en el delta.
- **`tension_real` tampoco**: la escribe el `lector-suspense`, no el `cronista`. Es la única
  colección de la rama 4 con otro autor, y meterla en el delta del cronista sería darle un dato
  que no tiene.
- **`cursor`**: el delta lo avanza, y `aplicar-delta` comprueba que la monotonía se respeta.
- **`resumen: {linea, parrafo, escena}`** — las tres granularidades, obligatorias. Es lo que
  `aplicar-delta` renderiza a `memoria/resumenes/NN.md` en la tarea 2.15.

**El identificador de escena va desde ahora** (decisión 5 del README). `resumen.escena` es un
mapa de `EscenaId` a texto, no un bloque de prosa. Cuesta un campo hoy; no ponerlo convierte las
dos capas baratas del índice recuperable (`architecture.md` §12.4) en una migración con
reproceso el día que se aborden. `linea_temporal` ya trae `escena` en §7.1, así que el id ya
existe: no se está inventando una entidad.

`schema_version` en el propio documento, como todos los contratos de agente
(`validators.md` §3.8).

**En el mismo commit**: lleva el ejemplo trabajado a `architecture.md` §7.x, junto a los otros dos
contratos de agente —§7.2 el frontmatter, §7.3 el informe de QA—. El delta es el tercero y es el
único sin ejemplo, siendo el que tiene el consumidor más estricto. Es donde alguien lo buscará.

**Cierra**: parte de RF-16, RF-18.

**Commit**: `feat(schemas): delta del cronista con las tres granularidades`

---

## 2.12 — Violaciones

**Construye**: `backend/novela/slices/delta/violaciones.py`.

**Rojo**: `novela/slices/delta/test_violaciones.py::test_ids_y_cursor_property`.
**Property-based**: ids duplicados entre colecciones y cursor decreciente se rechazan, para
cualquier delta generado.

**Verde**: función pura. Comprueba lo que el JSON Schema **no puede expresar**: unicidad de ids
entre colecciones distintas y monotonía del cursor.

Son las dos postcondiciones que `validators.md` §3.4 nombra al explicar por qué la verificación
formal se descarta y qué subconjunto barato sí se hace.

**Cierra**: CA-18, RF-17.

**Commit**: `feat(delta): violaciones que el esquema no expresa`

---

## 2.13 — Aplicar

**Construye**: `backend/novela/slices/delta/apply.py`.

**Rojo**: `novela/slices/delta/test_apply.py::test_idempotencia_property`. **Property-based**:
`aplicar(aplicar(e, d), d) == aplicar(e, d)` para cualquier estado y delta generados. Es la
primera propiedad de `validators.md` §3.6.

**Verde**: función pura. Recibe estado y delta, devuelve estado. No toca disco.

**Por qué la idempotencia no es negociable**: reanudar tras un fallo repite el paso, siempre
entero. `/novela-continuar` lee `checkpoints/latest.json` y repite el último paso no confirmado.
Si `aplicar` no es idempotente, la primera reanudación corrompe el estado — y la reanudación es
el caso normal en modo desatendido, no el excepcional.

`mutmut` corre también sobre este fichero (tarea 2.8).

Riesgo aceptado que conviene tener presente: la idempotencia se prueba sobre deltas generados por
Hypothesis, no sobre deltas reales de un `cronista`. El primer acto de la novela de humo es lo
que la valida de verdad.

**Cierra**: CA-20, RF-19.

**Commit**: `feat(delta): aplicar idempotente, función pura`

---

## 2.14 — `novela aplicar-delta`

**Construye**: `backend/novela/slices/delta/cmd.py`.

**Rojo**: `novela/slices/delta/test_delta.py::test_transaccion_todo_o_nada`. Un delta que intenta
un `UPDATE` sobre `libro_de_hechos` deja `estado.db` **byte a byte idéntico**.

**Verde**: la cáscara. Valida el delta contra `delta.schema.json`, llama a `violaciones.py` y a
`apply.py`, y escribe **dentro de una única transacción**.

```
novela aplicar-delta <slug> <cap>
```

Si una fila viola una restricción o un trigger, no queda nada escrito y el capítulo se reintenta
sobre el estado anterior. Es el invariante 1 y la única vía de escritura de `estado.db`.

El test de byte a byte es deliberadamente estricto: comprobar que el `INSERT` falló no basta:
hay que comprobar que **nada** de la transacción quedó.

**Cierra**: CA-17, RF-16.

**Commit**: `feat(cli): novela aplicar-delta, única vía de escritura del estado`

---

## 2.15 — Render de `memoria/`

**Construye**: el render de `memoria/resumenes/NN.md`, en el mismo slice.

**Rojo**: `novela/slices/delta/test_delta.py::test_renderiza_memoria`.
`memoria/resumenes/NN.md` contiene las **tres** granularidades del delta aplicado.

**Verde**: renderiza, dentro de la misma operación que aplica el delta.

**Este es el único cambio de contrato de agente de la spec.** `architecture.md` §7.5 atribuía
`memoria/resumenes/NN.md` al `cronista` y §6.4 a `novela aplicar-delta`; ganó §6.4 (spec §5.0.2) y
los documentos ya están corregidos. La razón no es de gusto: si lo escribe el agente, `memoria/`
es texto libre no validado y reconstruirlo cuesta cuota. Si lo escribe el CLI desde el delta,
`memoria/` es derivado de verdad — se reconstruye recorriendo `estado/deltas/*.json`, sin volver
a invocar a nadie.

Conserva **granularidad por escena** en el fichero, no solo párrafo y línea. Misma razón que la
tarea 2.11: es lo que deja abierta la capa léxica del índice recuperable.

**Cierra**: CA-19, RF-18.

**Commit**: `feat(delta): render de memoria desde el delta, no desde el cronista`

---

## 2.16 — `ScoreSink`

**Construye**: `backend/novela/plataforma/langfuse.py`.

**Rojo**: `novela/plataforma/test_langfuse.py::test_sink_noop_y_scores`. Sin
`TRACE_TO_LANGFUSE`, `checkpoint` **no abre ninguna conexión de red** y escribe igual; con
`"true"`, el sink recibe los seis scores.

**Verde**: el segundo de los dos puertos del sistema, con sus dos implementaciones.

Los seis scores, de `domain-knowledge.md` y RF-21: `coherencia`, `continuidad`, `tension`,
`longitud`, `fair_play`, `estilo`. Salen de `qa/NN-suspense.json` y del resultado de los gates.

La comparación es contra **la cadena `"true"`**, no contra la presencia de la variable. Cualquier
otro valor deja el sink como no-op, y el checkpoint se escribe igual: el trazado no puede ser
nunca la razón por la que un capítulo no cierra.

Es la única salida de red del CLI. El test de que no se abre ninguna sin la variable es lo que lo
mantiene cierto.

Las claves viven en `.claude/settings.local.json`, que está en `.gitignore`. Nunca en
`settings.json`, ni en el código, ni en un briefing.

**Cierra**: CA-22, RF-21.

**Commit**: `feat(plataforma): ScoreSink con no-op por defecto`

---

## 2.17 — `novela checkpoint`

**Construye**: `backend/novela/slices/checkpoint/cmd.py`.

**Rojo**: `novela/slices/checkpoint/test_checkpoint.py::test_roundtrip_property`.
**Property-based**: `restore(checkpoint(e)) == e`. Es la tercera propiedad de
`validators.md` §3.6, y su autor señala que la reanudación depende de ella y nada más la
comprueba.

**Verde**: escribe `checkpoints/NN.json` y `checkpoints/latest.json` **atómicamente**, con
cursor, versiones y `run_id`. Y emite los seis scores por `ScoreSink`.

```
novela checkpoint <slug> <cap>
```

`checkpoint` **confirma una sola vez**, al final del capítulo y con el delta ya aplicado
(`architecture.md` §2.1). Antes de eso, el paso está ejecutado pero no confirmado, y reanudar lo
repite entero.

Si el round-trip falla, el sospechoso es la serialización de 1.6b: `exclude_none` perdiendo la
diferencia entre `null` y ausente.

**Cierra**: CA-21, RF-20.

**Commit**: `feat(cli): novela checkpoint con scores y round-trip verificado`

---

## 2.18 — Model checking del bucle

Última tarea de la fase, y solo es posible ahora: necesita que los cuatro subcomandos existan.

**Construye**: `backend/tests/test_bucle.py`.

**Verde**: un test que **enumera exhaustivamente** las transiciones de
`cursor.fase × cursor.ultimo_paso × intento` y verifica los cinco invariantes de orden de
`validators.md` §4.10:

1. Nunca `aplicar-delta` sin que `validar` haya pasado.
2. Nunca `checkpoint` antes de `aplicar-delta`.
3. Nunca dos procesos sobre el mismo workspace.
4. `intento` nunca pasa de 2 sin producir `intervencion.md`.
5. Nunca un capítulo N+1 con el N sin checkpoint.

**Es un test, no TLA+.** El espacio de estados son decenas, no millones, y `validators.md` §4.10
es explícito: TLA+ aquí sería ceremonia. Empezaría a pagar si el bucle creciera a ramas
condicionales por acto o a paralelismo entre capítulos.

Los valores de los dos enums salen de la tarea 1.6. Si esta enumeración resulta incómoda de
escribir, suele ser señal de que los enums están mal cerrados.

**Commit**: `test(bucle): enumeración de transiciones y los cinco invariantes de orden`

---

## Al cerrar la fase

```bash
cd backend && uv run pytest && uv run mypy --strict . && uv run ruff check .
uv run mutmut run --paths-to-mutate novela/slices/validacion/gates.py,novela/slices/delta/apply.py
```

Y el bucle entero sobre un fixture, con el agente falso que escribe un capítulo prefabricado:
briefing → capítulo → validar → QA → delta → aplicar → checkpoint, sin una sola llamada a modelo.
Ese test de integración (`validators.md` §3.5) es lo que hace testable el bucle sin escribir una
novela, y si no pasa, la fase no está cerrada por mucho que los unitarios estén en verde.

Sigue por [fase-3-cierre.md](fase-3-cierre.md).
