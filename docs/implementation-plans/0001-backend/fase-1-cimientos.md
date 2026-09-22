# Fase 1 — Cimientos

**Objetivo.** Que exista un workspace creable e inspeccionable, y que todo lo demás tenga dónde
apoyarse.

**Al terminar existe**: la ontología como código, `estado.db` con sus triggers, escritura
atómica, lock de workspace, y tres subcomandos — `nueva`, `estado`, `pendiente`.

**Cierra**: RF-01 a RF-07, RF-26. CA-01 a CA-07, CA-28.

Antes de empezar, lee las convenciones de ciclo del [README](README.md): rojo visto fallar,
un commit por ciclo, property-based donde toca.

---

## 1.1 — Arranque

**Construye**: `backend/pyproject.toml`, `backend/uv.lock`, `.gitignore`.

Andamiaje. No lleva test: no hay lógica que probar.

```bash
cd backend && uv init --bare --python 3.12
```

`pyproject.toml` necesita:

```toml
[project.scripts]
novela = "novela.cli:app"
```

Dependencias de ejecución: `typer`, `pydantic>=2`, `pyyaml`, `filelock`. De desarrollo: `pytest`,
`hypothesis`, `jsonschema`, `mypy`, `ruff`, `mutmut`. `ebooklib` y `fastapi` entran en sus fases
(3 y 4), no aquí: una dependencia que no se usa todavía es una dependencia que nadie sabe si
funciona.

`mypy` en `--strict` sobre `backend/`. `ruff` con las reglas `S` (flake8-bandit) activadas —
`validators.md` §3.2 las quiere desde el principio, no al final, porque su trabajo es que nadie
escriba un `open(..., "w")` suelto sobre el workspace.

**Y arregla `.gitignore`, que hoy tiene una sola línea.** Faltan cuatro entradas que la
documentación da por hechas:

```gitignore
.local.env
novelas/
.claude/settings.local.json
__pycache__/
*.py[cod]
.venv/
```

`novelas/` es la que importa: `AGENTS.md` lo declara ignorado y no lo está. Un `git add -A` antes
de esta línea versiona un workspace entero, y con él el misterio de una novela en curso.

**Commit**: `chore(backend): arranque con uv, mypy estricto y ruff con reglas S`

---

## 1.2 — Identificadores y tipos base

**Construye**: `backend/novela/dominio/ids.py`.

Este fichero **no está en el árbol de `architecture.md` §3.1**, que lista `config.py`, `canon.py`,
`plan.py`, `estado.py` y `qa.py`. Lo añade este plan porque la spec §5.2 exige que los
identificadores sean tipos con validador y los usan las cuatro ramas: ponerlos en cualquiera de
ellas crearía un import entre modelos de ramas distintas.

**Rojo**: `novela/dominio/test_ids.py::test_formato_de_cada_prefijo`. Property-based con
Hypothesis: para cada tipo de id, las cadenas que casan su regex se aceptan y las que no, no.
Falla porque no hay módulo.

**Verde**: un tipo por prefijo, con validador de formato. No `str`.

```
per-elena-vidal      ^per-[a-z0-9-]+$        personaje
esc-casa-del-faro    ^esc-[a-z][a-z0-9-]*$   escenario
esc-07-2             ^esc-\d{2,3}-\d+$       escena
pis-007              ^pis-\d{3}$             pista
pfa-003              ^pfa-\d{3}$             pista falsa
rev-002              ^rev-\d{3}$             revelación
hil-004              ^hil-\d{3}$             hilo
obj-011              ^obj-\d{3}$             objeto o prueba
hec-014              ^hec-\d{3}$             hecho
cap-01               ^cap-\d{2,3}$           capítulo
```

Tres cosas que la tabla de `AGENTS.md` no resuelve y esta tarea sí:

**`esc-` está colisionado.** Escenario es `esc-casa-del-faro`, escena es `esc-07-2`. Las dos
regex de arriba son disjuntas por construcción: la de escenario exige que el primer carácter tras
el guion sea una letra. Sin eso, el validador de escenario traga ids de escena y el error aparece
tres fases después, en una consulta de `linea_temporal` que devuelve vacío sin fallar.

**`hec-` no está en la tabla de prefijos** de `AGENTS.md` ni de `architecture.md` §5, pero §7.1 y
§7.3 lo usan en sus ejemplos. Es una omisión de la tabla, no del dominio.

**El número de capítulo es un tipo**, no un `int`: rango `1..num_capitulos`, y formato de dos o
tres dígitos según `num_capitulos`. `architecture.md` §5 lo dice y es una regla de todo el
workspace: no se mezclan formatos. Conviene que el formateo viva aquí y no disperso en seis
`f"{n:02d}"`.

**En el mismo commit**: corrige `AGENTS.md` y `validators.md` §3.1, que dicen
`backend/novela/models/`. La ruta es `dominio/` (spec §5.0.3). Este es el primer commit que la
crea, así que es el suyo.

**Cierra**: nada de la spec directamente; es base de todo lo demás.

**Commit**: `feat(dominio): identificadores como tipos con validador de formato`

---

## 1.3 — Rama 1: configuración

**Construye**: `backend/novela/dominio/config.py`, `backend/config/default.yaml`.

**Rojo**: `novela/dominio/test_config.py::test_deriva_palabras_por_capitulo`. Un `config.yaml`
con `longitud_total_palabras` y `num_capitulos` pero sin `palabras_por_capitulo` debe derivar la
terna; uno sin ninguno de los tres debe fallar explícitamente.

**Verde**: el modelo de `definitions.md` §1. Dos bloques, `parametros_obra` y
`parametros_sistema`, todo INMUTABLE (`model_config = ConfigDict(frozen=True)`).

Cuatro detalles que la prosa de `definitions.md` esconde y el código necesita:

- **`palabras_por_capitulo` es una terna `{objetivo, min, max}`**, y el gate de longitud compara
  contra `min` y `max`, nunca contra `objetivo`. `definitions.md` §1 es explícito: exigir un
  número exacto degrada la prosa. Quien escriba `gates.py` en la fase 2 va a tener la tentación.
- **La derivación es bidireccional.** Si el usuario fija longitud y número, la terna se deriva;
  si fija solo uno, lo propone el `trazador`. El validador de modelo cubre el primer caso y falla
  explícitamente en el segundo, que es lo que `AGENTS.md` pide ante ambigüedad.
- **`presupuesto` es `{requests_dia, tokens_por_llamada, tokens_contexto_por_agente}`.**
- **`temperatura_por_agente` se modela y no hace nada.** `definitions.md` §1 lo avisa: requiere
  acceso directo a API y no está disponible por suscripción. Se modela porque el campo existe en
  la ontología; queda documentado como inerte para que nadie lo cablee creyendo que mueve algo.

`subgenero`, `punto_de_vista` y `tiempo_verbal` son enums. `definitions.md` enumera valores y
cierra con «etc.» en el primero: ciérralo con lo que hay y añade el enum, no un `str` libre.

**Commit**: `feat(dominio): rama 1, configuración de ejecución`

---

## 1.4 — Rama 2: canon

**Construye**: `backend/novela/dominio/canon.py`.

**Rojo**: `novela/dominio/test_canon.py::test_colecciones_append_only_sin_trigger`. Para cada una
de las seis colecciones append-only del canon, intentar modificar o borrar una entrada existente
debe ser imposible — no «debe fallar en runtime»: el modelo no expone el método.

**Verde**: los cinco subárboles de `definitions.md` §2 — premisa, mundo, personajes, misterio,
estilo.

**Lo que la spec no vio y esta tarea resuelve.** La spec §5.2 habla de `LibroDeHechos` como el
caso de «mutabilidad en el tipo». Pero `definitions.md` declara **seis colecciones más como
append-only, todas en el canon**:

| Colección | `definitions.md` |
|---|---|
| `misterio.verdad_oculta` | §2.4 |
| `misterio.pistas[]` | §2.4 |
| `misterio.pistas_falsas[]` | §2.4 |
| `misterio.revelaciones[]` | §2.4 |
| `misterio.giros[]` | §2.4 |
| `estilo.prohibiciones` | §2.5 |

El canon vive en markdown, no en SQLite: **no hay trigger que las proteja**. Para la rama 4 el
append-only lo impone el motor; para estas seis, o lo impone el modelo o no lo impone nadie. El
patrón de `LibroDeHechos` —expone `añadir()`, no expone forma de modificar ni de borrar— se
aplica a las seis.

`estilo.prohibiciones` tiene además dos escritores, `arquitecto` y `editor-estilo`: es la única
colección del canon que crece durante la ejecución, cuando el editor detecta un patrón repetido.

Campos que la prosa enumera en línea y el modelo necesita separados:

- `personaje.identidad`: `{id, nombre, alias, edad, rol_narrativo}`
- `personaje.psicologia`: `{deseo, necesidad, miedo, herida}`
- `personaje.secreto`: `{que_oculta, a_quien}` — dos campos, no uno
- `personaje.voz`: el fragmento de diálogo canónico es obligatorio (`min_length=1`). El escritor
  imita mejor de lo que obedece
- `escenario`: `{id, nombre, descripcion, detalle_sensorial, quien_tiene_acceso}`, y el último es
  `list[PersonajeId]` — es material de trama, no metadato
- `pista`: `{id, contenido, capitulo_plantado, capitulo_pagado, quien_la_percibe, es_fair_play}`.
  `capitulo_pagado` admite `None`: una pista plantada y no pagada existe, y es precisamente el
  hallazgo que busca `novela auditar`
- `pista_falsa`: `{a_quien_apunta, cuando_se_desmonta}`
- `giro`: es una revelación con `que_creia_el_lector_antes` obligatorio. Sin ese campo el giro no
  es evaluable, y `definitions.md` §2.4 lo dice así
- `estilo.ritmo`: longitud media de frase y proporción diálogo/acción/interioridad. **Campos
  numéricos**, no texto: es lo que hace verificable al `editor-estilo`

**Commit**: `feat(dominio): rama 2, canon con append-only en el tipo`

---

## 1.5 — Rama 3: plan

**Construye**: `backend/novela/dominio/plan.py`.

**Rojo**: `novela/dominio/test_plan.py::test_curva_tension_cuadra_con_num_capitulos`. Una
`curva_tension_objetivo` de longitud distinta a `num_capitulos` se rechaza; un valor fuera de
`1..10` se rechaza.

**Verde**: `definitions.md` §3.

- `puntos_de_giro` es un objeto de **claves fijas** —detonante, punto medio, crisis, clímax,
  resolución—, cada una anclada a un número de capítulo. No es una lista.
- `curva_tension_objetivo`: `list[int]` con `ge=1, le=10`, longitud exactamente `num_capitulos`.
- `gancho_final` es **enum, no texto**: se especifica el tipo para no encorsetar al escritor.
- `capitulos[].escenas[]`: `{id, lugar, tiempo_diegetico, personajes, beat, conflicto}`. Es la
  unidad mínima de planificación — el escritor recibe escenas, no resúmenes de capítulo.
- `pistas_a_plantar` / `pistas_a_pagar` son referencias a `canon.misterio.pistas`, y son **el
  mecanismo de aislamiento**: el escritor recibe el contenido de esas pistas concretas y nada más
  del misterio. Quien implemente `assemble.py` en la fase 2 va a volver aquí.

Ojo con un falso amigo: el plan dice `pistas_a_plantar` y el frontmatter del capítulo escrito
dice `pistas_plantadas`. Son modelos distintos —contrato de entrada y de salida—, no el mismo
campo con dos nombres.

**Commit**: `feat(dominio): rama 3, plan y ficha de capítulo`

---

## 1.6 — Rama 4: estado narrativo

La tarea más cargada de la fase. Léela entera antes de escribir nada.

**Construye**: `backend/novela/dominio/estado.py`.

**Rojo**: dos tests.

- `novela/dominio/test_estado.py::test_libro_de_hechos_solo_crece` — property-based:
  `len(nuevo.libro_de_hechos) >= len(viejo.libro_de_hechos)` para cualquier secuencia de
  operaciones expuestas por el tipo. Es la segunda propiedad de `validators.md` §3.6.
- `novela/dominio/test_estado.py::test_roundtrip_exacto` — `Estado.model_validate(e.model_dump())
  == e` para estados generados. Ver 1.6b.

**Verde**: el contrato serializado de `architecture.md` §7.1, que es lo que devuelven
`novela estado --json` y `GET /novelas/{slug}/estado`.

### Decisión: mandan los nombres de §7.1

`definitions.md` §4 y `architecture.md` §7.1 **no coinciden en ocho campos**. Esta es la tabla de
traducción, y la dirección es una sola:

| `definitions.md` §4 | `architecture.md` §7.1 — **este** |
|---|---|
| `estado_personajes` | `personajes` |
| `grafo_relaciones` | `relaciones` |
| `inventario_objetos_pruebas` | `objetos` |
| `hilos_abiertos` + `hilos_cerrados` | `hilos` (fusionados, con `estado` como discriminante) |
| `pistas_estado` | `pistas` |
| `conocimiento_del_lector` | `conocimiento_lector` |
| `curva_tension_real` | `tension_real` |
| `metricas_acumuladas` | `metricas` |

Ganan los de §7.1 porque son los que salen por la API, los que valida `state.schema.json` y los
que tendrán tabla en `esquema.sql`. Si quieres conservar el nombre largo, que sea un `alias`.

`cursor` tiene además dos formas: `definitions.md` declara `{capitulo_actual, fase,
ultimo_paso_completado}` y §7.1 declara `{capitulo, fase, ultimo_paso, intento}`. **Cuatro campos,
los de §7.1.** `intento` no es opcional: el model checking de la tarea 2.18 enumera
`fase × ultimo_paso × intento`, y sin el tercero no hay máquina de estados que enumerar.

### Enums que hay que cerrar aquí

`architecture.md` los deja abiertos y tres tareas distintas los van a necesitar. Se deciden una
vez, aquí:

| Enum | Valores | Fuente |
|---|---|---|
| `cursor.fase` | `escritura`, `revision`, `registro`, `cerrado` | derivado del bucle de §2.1 |
| `cursor.ultimo_paso` | `briefing`, `escritor`, `validar`, `continuista`, `editor-estilo`, `lector-suspense`, `cronista`, `aplicar-delta`, `checkpoint` | los pasos del bucle de §2.1 |
| `pista.estado` | `plantada`, `pagada`, `pendiente`, `huerfana` | `definitions.md` §4 — **son cuatro**; el diagrama 3 de `domain-knowledge.md` solo enseña tres, y se queda corto |
| `hilo.estado` | `abierto`, `cerrado` | §7.1 |
| `personaje.condicion` | `viva`, `muerta`, `desaparecida` | §7.1 muestra `"viva"` |
| `objeto.relevancia` | `alta`, `media`, `baja` | §7.1 muestra `"alta"` |

Si añades un valor a alguno de estos, es cambio de esquema: regenera `schemas/` y actualiza
`definitions.md` en el mismo commit.

### Formas que solo se ven en el JSON

- `schema_version` es **campo raíz del documento**, no solo de la tabla `meta`.
- `conocimiento` es `dict[PersonajeId, list[Entrada]]`; `conocimiento_lector` es `list[Entrada]`
  plana. **Misma entrada `{hecho, desde_capitulo}`, contenedor distinto.** Reutiliza el tipo de
  entrada, no el contenedor.
- `relaciones` es lista de aristas `{de, a, tipo, intensidad, desde}` con `intensidad` float
  `0..1`. El canon declara una `tension` cualitativa para lo mismo: **son campos distintos**, el
  del canon es el punto de partida y el del estado la evolución.
- `tension_real` es `list[int]` desnuda: **el índice es el capítulo**. No lleva número de
  capítulo dentro.
- `metricas.desviacion_vs_plan` es float con signo, fracción (`-0.04`), no porcentaje.
- `objetos` usa nombres abreviados frente al canon: `objeto`→`id`,
  `capitulo_introduccion`→`capitulo_intro`. Y `ubicacion` admite `None`: un objeto en manos de
  alguien no tiene lugar fijo.
- `hilos` no trae `cerrado_en` en el ejemplo de §7.1, pero `novela auditar` lo necesita para
  reportar hilos cerrados fuera de plan. Añádelo opcional.

### `LibroDeHechos` y las demás append-only

Cinco colecciones —`libro_de_hechos`, `conocimiento`, `linea_temporal`, `conocimiento_lector`,
`tension_real`— expuestas con `añadir()` y sin forma de modificar ni de borrar. En la rama 4 el
trigger es la garantía real (tarea 1.9); el tipo es lo que evita escribir el bug, no lo que lo
detecta.

Dato que conviene no perder: `tension_real` es la única colección de la rama 4 que **no escribe
el `cronista`** — la escribe el `lector-suspense`. Importa en la tarea 2.11, al derivar la forma
del delta.

Y dos derivadas, que **no se escriben desde el delta, se computan**: `pistas` (cruce de plan con
texto escrito) y `metricas`.

**Commit**: `feat(dominio): rama 4, estado narrativo con append-only en el tipo`

---

## 1.6b — Round-trip exacto

**Rojo**: `novela/dominio/test_estado.py::test_roundtrip_exacto`, property-based sobre estados
generados por Hypothesis.

CA-21 exige `restore(checkpoint(e)) == e`. Eso es un requisito **de serialización**, y la
decisión que lo rompe se toma aquí, no tres tareas más tarde: si `model_dump` usa
`exclude_none=True`, `ubicacion: null` y `ubicacion` ausente dejan de distinguirse, y un objeto
que estaba explícitamente en manos de alguien vuelve como objeto sin ubicación conocida.

No es una tarea con commit propio: es una propiedad que se añade al commit de 1.6. Está separada
en el plan porque es lo que más se olvida.

---

## 1.7 — Informe de QA

**Construye**: `backend/novela/dominio/qa.py`.

**Rojo**: `novela/dominio/test_qa.py::test_informe_valida`. Un informe con un `tipo` de hallazgo
desconocido se rechaza; uno completo hace round-trip.

**Verde**: el formato de `architecture.md` §7.3. Cabecera `{capitulo, agente, veredicto,
hallazgos}`; cada hallazgo, `{tipo, gravedad, referencia, ubicacion, descripcion,
correccion_sugerida}`.

Enums a cerrar: `veredicto` (`aprobado`, `rechazado`, `aprobado_con_reservas`) y `gravedad`
(`alta`, `media`, `baja`). `tipo` es el vocabulario de hallazgos y conviene que sea enum también
—`contradiccion_hecho` es el único que la documentación nombra—: un hallazgo con tipo libre es un
hallazgo que el reintento del escritor no sabe interpretar.

Lo usan cuatro productores: `continuista`, `editor-estilo`, `lector-suspense` y el propio
`novela validar` (tarea 2.9). Un solo modelo para los cuatro.

**En el mismo commit**: corrige `definitions.md` §6, que dice `qa/NN-informe.md` — markdown y un
fichero único. Lo vigente es `qa/NN-<agente>.json`, JSON y un fichero por agente
(`architecture.md` §4 y §7.5).

**Commit**: `feat(dominio): informe de QA, contrato de los cuatro productores`

---

## 1.8 — Generación de `backend/schemas/`

**Construye**: `backend/schemas/*.json`, `backend/tests/test_contratos.py`.

**Rojo**: `tests/test_contratos.py::test_state_schema_al_dia`. Compara el JSON Schema commiteado
con el que genera Pydantic ahora mismo; falla porque el fichero no existe.

**Verde**: un pequeño generador, y los seis esquemas de la spec §8 — `config.schema.json`,
`state.schema.json`, `canon.schema.json`, `plan-capitulo.schema.json`, `delta.schema.json`,
`qa-informe.schema.json`. `delta.schema.json` se completa en la tarea 2.11; aquí basta con que
el mecanismo exista.

Cada documento lleva su `schema_version` (RF-26). El test es lo que hace verdad la regla de
`AGENTS.md`: si cambias un modelo, regeneras los esquemas en el mismo commit — porque si no, la
suite se pone roja.

**Cierra**: CA-06 (la mitad de esquema; la otra mitad la cierra 1.15), RF-26.

**Commit**: `feat(schemas): generación desde Pydantic y test de contrato`

---

## 1.9 — El DDL

**Construye**: `backend/novela/plataforma/esquema.sql`.

**Rojo**: `novela/plataforma/test_esquema.py::test_append_only_por_trigger`. Para cada una de las
cinco tablas append-only, un `UPDATE` y un `DELETE` deben abortar con el mensaje del trigger.
Diez casos, no cinco.

**Verde**: el DDL. **Y aquí hay trabajo de verdad: `architecture.md` no lo trae.** §7.1 dice «una
tabla por colección de la rama 4» y enseña un único trigger de ejemplo. Todo lo demás se deriva
del JSON de §7.1 y de la tarea 1.6.

Una tabla por colección: `cursor`, `linea_temporal`, `personajes`, `conocimiento`, `relaciones`,
`objetos`, `libro_de_hechos`, `hilos`, `pistas`, `conocimiento_lector`, `tension_real`,
`metricas`. Más `meta`, con `schema_version`.

**Los diez triggers**, `BEFORE UPDATE` y `BEFORE DELETE` sobre las cinco append-only. El patrón,
de §7.1:

```sql
CREATE TRIGGER libro_de_hechos_no_update BEFORE UPDATE ON libro_de_hechos
BEGIN SELECT RAISE(ABORT, 'libro_de_hechos es append-only'); END;
```

Convención de nombre: `<tabla>_no_update` y `<tabla>_no_delete`. Mensaje: `'<tabla> es
append-only'`.

**Índices** por `capitulo` y por id de entidad. No son optimización prematura: `architecture.md`
§6.4 apoya en ellos una decisión de diseño —«el largo plazo no se carga, se consulta»— y el
briefing del `continuista` trae solo las entradas que tocan a las entidades de su capítulo. Sin
índice, eso es un recorrido en Python y la regla se incumple en silencio.

**Cierra**: CA-02, RF-02.

**Commit**: `feat(plataforma): DDL de estado.db con triggers append-only`

---

## 1.10 — Conexión y transacciones

**Construye**: `backend/novela/plataforma/estado_db.py`.

**Rojo**: `novela/plataforma/test_estado_db.py::test_conexion_ro_no_escribe`. Una conexión
abierta con `file:…?mode=ro` debe rechazar cualquier `INSERT`.

**Verde**: conexión con `journal_mode=WAL`, `foreign_keys=ON` y `busy_timeout`. Toda escritura
dentro de `BEGIN IMMEDIATE … COMMIT`.

La apertura en solo lectura no es un detalle de la fase 4: es lo que hace que **no exista ruta de
escritura desde la API, ni por descuido**. Se escribe aquí porque aquí vive la conexión.

`estado.db-wal` es efímero y no se respalda.

**Cierra**: parte de RF-04 (la mitad de transacción).

**Commit**: `feat(plataforma): conexión a estado.db, PRAGMAs y transacciones`

---

## 1.11 — Escritura atómica

**Construye**: `backend/novela/plataforma/atomic.py`.

**Rojo**: `novela/plataforma/test_atomic.py::test_corte_deja_fichero_anterior`. Inyecta una
excepción entre la escritura del `.tmp` y el `os.replace`, y comprueba que el fichero anterior
queda íntegro byte a byte.

**Verde**: escribir en `.tmp` y renombrar. Todo fichero del workspace pasa por aquí — es el
invariante 6 de `AGENTS.md`, y `estado.db` es la única excepción porque su atomicidad la da la
transacción de 1.10.

Supuesto que conviene que esté escrito: `os.replace` es atómico **porque el workspace vive en un
solo disco local** (spec §4). Si algún día vive en red, esta garantía se cae y el plan de
entonces tendrá que decirlo.

**Cierra**: CA-04, RF-04.

**Commit**: `feat(plataforma): escritura atómica tmp + replace`

---

## 1.12 — Lock de workspace

**Construye**: `backend/novela/plataforma/lock.py`.

**Rojo**: `novela/plataforma/test_lock.py::test_lock_ocupado_sale_3`. Con el lock tomado por otro
proceso, un subcomando que escribe sale con 3 y no toca nada.

**Verde**: `filelock` sobre `estado/state.lock`, tomado por **todo subcomando que escribe**.

El WAL serializa escritores de la base, pero no protege `capitulos/`, `qa/` ni `runs/`: el lock
es del workspace, no del estado. Es el invariante 8.

**Cierra**: CA-03, RF-03.

**Commit**: `feat(plataforma): un proceso por workspace`

---

## 1.13 — El puerto del workspace

**Construye**: `backend/novela/plataforma/workspace.py`.

**Rojo**: `novela/plataforma/test_workspace.py::test_resolucion_de_ruta`. El workspace se resuelve
a `./novelas/<slug>`, o a `$NOVELAS_DIR/<slug>` si la variable está definida.

**Verde**: `WorkspaceRepository` con dos implementaciones — la real y la de fixtures. Es uno de
los **dos únicos puertos** del sistema (`architecture.md` §3.0); no añadas un tercero, y no hagas
un repositorio por entidad.

`NOVELAS_DIR` es además cómo los tests apuntan a `backend/tests/fixtures/` sin tocar el
directorio de trabajo.

**Commit**: `feat(plataforma): WorkspaceRepository y su doble de fixtures`

---

## 1.13b — Fixtures

**Construye**: `backend/tests/fixtures/`.

Sin test propio: es infraestructura de test. Pero es lo que más se apoya después — media docena
de criterios de aceptación dependen de estos workspaces, empezando por el de la tarea siguiente.

Va aquí y no al final de la fase: necesita los modelos (1.2–1.7), el DDL (1.9) y el puerto de
workspace (1.13), y a partir de 1.15 **todo lo demás lo necesita a él**.

Hacen falta al menos tres:

| Fixture | Para qué |
|---|---|
| `demo-24/` | novela de 24 capítulos con 7 escritos, cursor en revisión. Base de CA-05, CA-08, CA-12 |
| `demo-terminado/` | los 24 capítulos cerrados. Base de CA-07 y CA-24 |
| `demo-huerfana/` | con una pista plantada y nunca pagada. Base de CA-23 |

Los alcanza `NOVELAS_DIR`, de la tarea 1.13: los tests apuntan ahí sin tocar el directorio de
trabajo.

Ningún fixture se genera llamando a un modelo. Los capítulos son prosa prefabricada, y da igual
que sea mala: lo que se prueba es el mecanismo, no el texto.

**Commit**: `test(fixtures): workspaces sintéticos de 24 capítulos`

---

## 1.14 — `novela nueva`

**Construye**: `backend/novela/cli.py`, `backend/novela/slices/nueva/cmd.py`.

**Rojo**: `novela/slices/nueva/test_nueva.py::test_crea_arbol_y_base`. Dos partes:
`novela nueva demo --idea "x" --capitulos 3 --palabras 9000` crea el árbol de `architecture.md`
§4 y un `estado.db` con `meta.schema_version`; repetido sobre `demo`, sale con 1 **y no modifica
ningún fichero** — comprueba mtimes, no solo el código de salida.

**Verde**: crea el árbol, escribe `config.yaml` (`default.yaml` más los flags, validado contra el
modelo de 1.3) y crea `estado.db` ejecutando `esquema.sql`.

```
novela nueva <slug> --idea "…" [--capitulos N] [--palabras N] [--subgenero S] [--idioma es]
```

El slug se valida contra `^[a-z0-9-]+$` **antes de tocar el disco**, la misma regla que usará la
API en la tarea 4.2. Es la primera vez que el sistema convierte una cadena de fuera en una ruta.

Este subcomando no existía en la documentación: lo añade la spec §5.0.1, porque nadie creaba el
workspace. El `arquitecto` tiene `Read, Write` y no puede ejecutar DDL; el slash command
`/novela-nueva` es un procedimiento, no un ejecutable.

`cli.py` es Typer y **solo registra el `cmd.py` de cada slice**. Nada de lógica.

**En el mismo commit**: añade `novela nueva` a la lista de subcomandos de `architecture.md` §8 y
de `AGENTS.md`.

**Cierra**: CA-01, RF-01.

**Commit**: `feat(cli): novela nueva crea workspace y base de estado`

---

## 1.15 — `novela estado`

**Construye**: `backend/novela/slices/estado/cmd.py`.

**Rojo**: dos tests.

- `novela/slices/estado/test_estado.py::test_breve_acotado` — sobre el fixture de 24 capítulos,
  `--breve` imprime **≤ 12 líneas** e incluye cursor, hilos abiertos y palabras.
- `tests/test_contratos.py::test_state_schema_al_dia` extendido — `--json` valida contra
  `state.schema.json`.

**Verde**: `--breve` imprime cursor, capítulos hechos, hilos abiertos, pistas pendientes de pagar
y palabras acumuladas. `--json` serializa el contrato de §7.1 desde los modelos.

El límite de doce líneas es un requisito, no una guía de estilo: `--breve` es lo que el
orquestador paga en contexto muchas veces por novela, y es el único subcomando cuyo coste se
multiplica por el número de capítulos.

**Cierra**: CA-05, CA-06, RF-05, RF-06.

**Commit**: `feat(cli): novela estado, breve y json`

---

## 1.16 — `novela pendiente`

**Construye**: `backend/novela/slices/estado/cmd.py` (mismo slice).

**Rojo**: `novela/slices/estado/test_estado.py::test_pendiente_codigos`. Sale 0 con capítulos
restantes, 1 sobre el fixture terminado, **y stdout vacío en ambos casos**.

**Verde**: no imprime nada. Comunica por código de salida, porque quien lo consume es el
`while` del modo desatendido.

**Cierra**: CA-07, RF-07.

**Commit**: `feat(cli): novela pendiente comunica por código de salida`

---

## 1.17 — Ningún cliente de modelo

**Construye**: `backend/tests/test_contratos.py::test_sin_clientes_de_modelo`.

**Rojo**: recorre el árbol de imports del CLI y falla si aparece cualquier cliente de modelo.
Falla al escribirlo solo si algo se coló; si pasa a la primera, añádele temporalmente un import
de `anthropic` a un módulo y compruébalo — **un test que nunca has visto en rojo no prueba nada**.

**Verde**: la lista de módulos prohibidos.

Es barato y va temprano a propósito: `AGENTS.md` prohíbe añadir un SDK de proveedor de modelos, y
RNF-03 exige cero llamadas desde el CLI, la API y la suite. Cuanto antes exista el test, menos
probable es que alguien lo descubra tarde.

**Cierra**: CA-28, RNF-03.

**Commit**: `test(contratos): el backend no importa ningún cliente de modelo`

---

## Al cerrar la fase

```bash
cd backend && uv run pytest && uv run mypy --strict . && uv run ruff check .
novela nueva humo --idea "prueba" --capitulos 3 --palabras 9000
novela estado humo --breve
novela pendiente humo; echo $?     # 0
```

Si esas cuatro líneas funcionan, la fase 1 está. Sigue por [fase-2-bucle.md](fase-2-bucle.md).
