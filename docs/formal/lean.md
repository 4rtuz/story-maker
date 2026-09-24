# Verificación formal de la cronología en Lean 4

`novela verificar-lean <slug>` convierte la cronología guardada en la base de estado de una
novela en un fichero Lean, `novelas/<slug>/formal/Cronologia.lean`, y lo compila contra el
proyecto versionado en `formal/lean/`. Cada invariante es un teorema `… = true := by decide
+kernel`: si la historia lo viola, **la compilación falla**, y el gate con ella.

## 1. Qué se modela

| Lean (`StoryMaker.Invariantes`) | Origen en el workspace |
|---|---|
| `Evento.momento : Nat` | minutos desde el día 1 a las 00:00 |
| `Evento.duracion` | `duracion_min` (0 si es un instante) |
| `Evento.lugar` | escenario (`esc-…`) |
| `Evento.presentes` | personajes presentes |
| `Evento.excluidos` | quien sale de la historia en el evento: muerte o partida definitiva |
| `Evento.edades` | edades que el texto declara en ese evento |
| `Evento.tras` | eventos que el texto sitúa antes |
| `Cronologia.edadAlInicio` | `identidad.edad` de `canon/personajes/*.md`: la edad en el momento 0 |

Lean trabaja con ids `Nat` (comparar `Nat` en el kernel es barato; `String`, no). El generador
numera eventos por orden de inserción y personajes y lugares por orden alfabético, y deja la
correspondencia en comentarios del fichero; `lean.Tabla` la usa para traducir el informe.

**Memoria.** Dos tablas nuevas, append-only con triggers como el resto (`esquema.sql`, bloque
`-- cronologia:`): `cronologia` (evento, capítulo, momento, duración, lugar, `tras` en JSON, cita)
y `cronologia_personajes` (evento, personaje, papel `presente|excluido`, edad declarada). Las
escribe `aplicar-delta` desde el campo opcional `Delta.cronologia` (`EventoCronologia`, ids
`evt-NN-k`) que emite el cronista; sobre una base anterior las crea al vuelo. Un delta sin
`cronologia` sigue siendo válido.

**Nacimientos: del canon, no del delta.** `identidad.edad` ya existe, la escribe el arquitecto
y no cambia; el nacimiento es «`edad` años antes del momento 0». Pedírselo al cronista en cada
capítulo duplicaría un dato fijo y le daría ocasión de contradecirse. Lo que sí varía —la edad
que el texto *declara* en una escena— va en el evento.

**Novela antigua.** Si `cronologia` está vacía, se deriva un evento por escena de
`linea_temporal` (momento de `inicio` con formato `dia N, HH:MM`, y duración), con el lugar y los
personajes de la escena en `plan/capitulos/NN.md`. Sin exclusiones, edades ni `tras`: la base
antigua no los tiene, así que en ese modo solo muerde el invariante (c). Las escenas no datables
se listan en `escenas_omitidas`. Si no queda ningún evento, el veredicto es `sin_datos`, se dice
explícitamente y no bloquea: no hay nada que demostrar.

## 2. Invariantes

Cada uno es un checker `Bool` decidible, una `Prop` y un lema general
`checker c = true → Prop c` demostrado para **cualquier** cronología (sin Mathlib). El fichero
generado liga los tres: `theorem ubicuidad : sinUbicuidad cronologia = true := by decide +kernel`
y `example : SinUbicuidad cronologia := sinUbicuidad_correcto _ ubicuidad`.

| | Nombre | Proposición |
|---|---|---|
| (a) | `orden` | todo evento de `tras` existe y termina antes de que empiece el que lo cita |
| (b) | `edad` | una edad declarada en `m` es `edadAlInicio + m / año` o uno más (el cumpleaños cae dentro) |
| (c) | `ubicuidad` | si dos eventos se pisan en el tiempo y comparten un personaje, son en el mismo lugar |
| (d) | `exclusion` | nadie está presente en un evento posterior a aquel que lo excluye |

«Se pisan»: empiezan a la vez o sus intervalos `[momento, momento + duración)` se cortan.

**Por qué estas.** Son las cuatro que exigen razonar sobre *toda* la cronología a la vez, que es
justo lo que ningún gate existente hace: `validar` mira un capítulo, `aplicar-delta` compara el
delta con el estado vigente campo a campo y el continuista es un modelo con una ventana de
contexto. (c) y (d) cubren los errores de continuidad más caros en suspense —la coartada
imposible y el muerto que vuelve— y (c) funciona incluso en novelas antiguas. Trade-off: no se
modela duración de trayectos (ir del faro al puerto a la misma hora + 5 minutos pasa), ni el
orden relativo sin `tras` explícito, ni personajes nacidos durante la historia. Añadir cualquiera
es otro checker y otro lema en `Invariantes.lean`.

**`decide +kernel` y no `native_decide`.** El kernel comprueba la reducción: no hay que fiarse
del compilador. Con `decide` a secas, 144 eventos agotan `maxRecDepth`; con `+kernel`, compilan
en unos 25 s en esta máquina.

## 3. Cómo se ejecuta

```bash
novela verificar-lean <slug>        # 0 aprobado o sin_datos · 1 violación, Lean ausente o error
```

Requiere `lean` en el PATH o en `~/.elan/bin` (Lean 4.34.1, `formal/lean/lean-toolchain`). No usa
`lake`: en esta máquina Device Guard bloquea `lake.exe`, y un proyecto sin dependencias se compila
con `lean -o` más `LEAN_PATH`. La primera vez compila `StoryMaker/Invariantes.lean` a
`formal/lean/.lake/build/` (ignorado por git); después solo el fichero generado. Con `lake`
disponible, `lake build` en `formal/lean/` hace lo mismo. **Sin Lean, el gate falla** con
`veredicto: "error"` y «lean no está instalado»: nunca se salta.

Salida: `qa/lean.json` con `veredicto`, `fuente` (`cronologia` o `derivada`), `eventos`,
`invariantes` (uno a uno), `violaciones` (invariante, evento, personaje, evento con que choca o
edad declarada, y descripción) y `salida_lean` si Lean falló sin decir qué invariante. Emite por
el `ScoreSink` `lean_cronologia` (1/0) y `lean_<invariante>` por cada uno.

## 4. Dónde corre en el harness

En `/novela-auditar`, entre `novela auditar` y `novela exportar`: si sale con 1, **no se exporta**
(`novela producir` lo ve como «no exportó» y termina `fallido`). Es **intervención humana**, no un
reintento del `editor-estilo`: la incoherencia vive en capítulos cerrados, que no se reescriben
(invariante 7), y el editor no puede ni debe leer el delta ni la cronología. La corrección es una
versión nueva con `novela cambio`, decidida por una persona que lee `qa/lean.json`.

No está dentro del bucle por capítulo: cuesta segundos de Lean por llamada y, a mitad de novela,
una violación de (d) puede ser un giro que todavía no se ha escrito.

## 5. Caso real: lo que solo ve Lean

Fixture `fabrica.PARTIDA` (3 capítulos, `backend/tests/fixtures/fabrica.py`):

- cap. 1, `evt-01-1`: día 1, 21:00–21:40, en el faro, Elena (40 años declarados) y Tomás.
- cap. 2, `evt-02-1`: día 2, 07:00, en el puerto: Tomás se va en el ferry (`excluye`).
- cap. 3, `evt-03-1`: día 3, 21:00, en el faro, Elena **y Tomás**.
- cap. 3, `evt-03-2`: Inés recuerda a Tomás en el puerto el día 1 a las 21:10.

Cada capítulo es coherente por sí solo; el error está en cruzar el 1 con el 3 y el 2 con el 3.
Salida real (capítulos 1 y 2 cerrados con el bucle de la fábrica, el 3 a mano):

```
$ novela validar demo-partida 3
validar 03: aprobado
[salida 0]
$ novela aplicar-delta demo-partida 3
aplicar-delta 03: 1 hechos, 1 hilos, 0 pistas plantadas y 1 pagadas
[salida 0]
$ novela checkpoint demo-partida 3
checkpoint 03: cerrado · 12 scores
[salida 0]
$ novela auditar demo-partida
auditar: sin hallazgos
[salida 0]
$ novela verificar-lean demo-partida
verificar-lean: 2 violaciones en qa/lean.json
- ubicuidad: per-tomas-reyes está en evt-03-2 y en evt-01-1 a la vez, en lugares distintos
- exclusion: per-tomas-reyes aparece en evt-03-1, después de salir de la historia en evt-02-1
[salida 1]
```

Y Lean, sobre `formal/Cronologia.lean`:

```
VIOLACION|ubicuidad|3|2|0
VIOLACION|exclusion|2|2|1
Cronologia.lean:38:57: error: Tactic `decide` proved that the proposition
  sinUbicuidad cronologia = true
is false
Cronologia.lean:40:63: error: Tactic `decide` proved that the proposition
  respetaExclusiones cronologia = true
is false
```

Lo reproduce `test_caso_real_solo_lo_ve_lean` en `backend/novela/slices/formal/test_integracion.py`.

## 6. Validadores y verificadores

- **Generador determinista**: `test_lean.py::test_generador_determinista` contra el golden
  `backend/tests/fixtures/golden/Cronologia.lean`.
- **Memoria**: `test_cronologia.py` — `aplicar-delta` escribe eventos, presencias, exclusiones,
  edades y `tras`; una base sin tablas lee vacío; una edad de un ausente se rechaza en el modelo.
- **Gate** (`test_cmd.py`, con Lean falso): rechazo con invariante, evento y personaje; aprobado;
  novela antigua derivada de `linea_temporal`; `sin_datos`; Lean ausente → sale con 1; scores.
- **Integración** (`test_integracion.py`, se salta sin Lean): compila la coherente, rompe la
  incoherente en (c) y (d) y no en (a), rompe (b) con una edad falsa, y el caso real de §5.
- **Lemas generales**: `formal/lean/StoryMaker/Invariantes.lean` compila; si una prueba se rompe,
  el gate falla con «Invariantes.lean no compila».
- **Riesgos aceptados**: la verificación es tan buena como la cronología que extrae el cronista
  (un modelo): un evento que no registra no se comprueba. Sin lock alrededor del olean
  compartido: dos verificaciones simultáneas con el olean caducado lo compilan dos veces.
