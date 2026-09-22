# Decisiones de la spec 0001 — el porqué

Catorce cosas que estaban sin resolver: las cinco preguntas de §16, tres huecos de ontología que
la spec no recogía y seis hallazgos de un barrido posterior.

**Todas están decididas y aplicadas.** La spec pasó a `aceptada` en la versión 0.2 con §16 vacía,
y los docs de referencia quedaron corregidos. Este fichero conserva el razonamiento —incluidas las
alternativas descartadas y lo que costaría revertir cada una—, que es lo que el documento de
llegada no guarda y lo que evita que alguien las reproponga dentro de tres meses.

Dónde quedó cada cosa: §2, §5.0, §6, §8, §11, §12, §14 y §16 de la spec; `definitions.md` §2.4,
§4 y §6; `architecture.md` §5 y §8; `AGENTS.md`; `validators.md` §3.1; y
`docs/adr/0001-orquestador-en-claude-code.md`.

Las urgencias de abajo eran las de antes de decidir. Se conservan porque explican el orden en que
se atacaron.

Marcado por urgencia:

- 🔴 **Bloquea** una tarea concreta del plan.
- 🟡 Decide antes de tocar código; después cuesta.
- 🟢 Barato en cualquier momento.

---

## A — Las cinco preguntas de §16

### A1 🟢 ¿`novela nueva` o `novela init`?

**Propuesta: `nueva`.**

La premisa de la pregunta —«el resto del CLI usa verbos»— no se sostiene. De los ocho
subcomandos de `AGENTS.md`: `validar`, `aplicar-delta`, `auditar` y `exportar` son verbos;
`estado`, `briefing` y `checkpoint` son sustantivos; `pendiente` es un adjetivo. Cuatro y cuatro.
No hay convención que romper.

A favor de `nueva`: `/novela-nueva` ya aparece en `architecture.md` §8, en `AGENTS.md` y en
`CLAUDE.md`. Renombrar toca tres documentos y un slash command para ganar una coherencia
gramatical que el CLI no tiene.

A favor de `init`: es la convención de la industria y lo reconoce cualquiera sin leer la ayuda.
En contra: sería la única palabra inglesa en un CLI íntegramente en español.

**Reversión**: gratis mientras no exista ningún workspace. Después, un alias y una nota.

### A2 🟢 ¿`presupuesto/` y `novela budget` entran como fase 5?

**Propuesta: no. Spec 0003, cuando haya datos.**

Tres razones:

1. No está en la lista de CLI de `AGENTS.md`, así que añadirlo cambia el documento de
   convenciones, no solo el código.
2. La política de degradación de `architecture.md` §9 tiene cinco niveles y ningún umbral. Sin
   una ejecución real, fijarlos es inventar números y después defenderlos.
3. Depende de `runs/quota.json`, que se alimenta de invocaciones reales.

**Qué hacer ahora para que siga siendo barato después**: nada más que RF-27 —una línea por
subcomando en `harness.log`, con marca de tiempo—. Esa es exactamente la materia prima que
`novela budget` agregaría, y ya está en el plan (tarea 2.1).

**Cuándo abrir la 0003**: después de la novela de humo de tres capítulos, cuando existan
invocaciones por capítulo y tokens por llamada medidos.

Mientras tanto la degradación la decide el orquestador a mano, que es lo que pasa hoy.

### A3 🟡 ¿`run_id` lo genera el CLI o lo fija el orquestador?

**Propuesta: los dos, con precedencia. `NOVELA_RUN_ID` si está definida y es válida; si no, el
CLI genera `r-AAAAMMDD-HHMM`.**

El formato se valida contra `^r-\d{8}-\d{4}$`. Una variable con basura **falla ruidosamente**; no
se crea `runs/<lo-que-sea>/`. Es una cadena de fuera del proceso que se convierte en ruta: la
misma precaución que el slug.

Tres cosas que compra, por tres líneas de código:

1. **Cierra `architecture.md` §12.2.** El orquestador puede pasar un valor derivado del
   `session_id` de Claude Code, y entonces las trazas de Langfuse y los directorios de `runs/` se
   correlacionan sin trabajo extra. §12.2 pide literalmente comprobar si se puede fijar desde
   fuera; esto lo hace posible sin depender de la respuesta.
2. **Hace deterministas las rutas en los tests**, que es lo que el golden byte a byte de CA-08
   necesita. Sin esto, el fichero de briefing cambia de ruta en cada ejecución.
3. **Reanudación limpia.** Repetir un capítulo dentro del mismo run escribe en el mismo
   directorio en vez de dejar un `runs/` huérfano por intento.

**Riesgo**: dos procesos con la misma variable colisionarían. Lo impide el lock de workspace
(invariante 8), que ya prohíbe dos procesos.

**Dónde se documenta**: §8 de la spec, como contrato de variable de entorno. Hoy §8 no declara
ninguna.

### A4 🟡 ¿La fase 4 ahora o cuando exista la primera novela terminada?

**Propuesta: ahora, y la última de las cuatro.**

Posponerla no ahorra el trabajo, lo mueve. Los modelos de respuesta ya existen desde la fase 1
—son los mismos Pydantic, una sola ontología—, así que lo que queda es enrutado, validación de
slug y OpenAPI: cinco tareas.

El argumento real para hacerla ahora no es el coste, es **CA-25**: montar el workspace en solo
lectura durante toda la suite es mucho más barato de establecer antes de que exista código que
asuma acceso de escritura. Establecer esa garantía a posteriori significa auditar todo lo escrito.

Contraargumento reconocido: YAGNI, no hay frontend. Se resuelve así: se implementan **los cinco
`GET` y ninguno más**. En particular **no** entran los dos de `architecture.md` §12.6 —listado de
runs y tramo del log en vivo—, que son los que de verdad no tienen consumidor hasta que el panel
exista.

**Regla para quien implemente**: si algo tiene que caerse por tiempo o por cuota, es esta fase
entera. Ninguna otra depende de ella.

### A5 🟡 ¿Identificador de escena en el delta desde la fase 2?

**Propuesta: sí.**

Forma concreta: `resumen.escena` es `dict[EscenaId, str]`, no un bloque de prosa. Y cada entrada
de `linea_temporal` del delta ya lleva `escena` — está en el JSON de §7.1, así que el
identificador **ya existe en la ontología**; no se está inventando una entidad.

**Qué cuesta hoy**: un campo en `delta.schema.json` y una sección en el renderizador de
`memoria/`.

**Qué compra**: la capa exacta de `architecture.md` §12.4 —`menciones(entidad_id, escena_id,
capitulo)`— pasa a ser una lectura sobre deltas ya escritos, y la capa léxica (FTS5 sobre
`memoria/resumenes/`) gana grano de escena. Las dos capas baratas, sin dependencias nuevas.

**Qué cuesta añadirlo después**: reprocesar cada capítulo escrito volviendo a invocar al
`cronista`. Eso es cuota, y además **no determinista**: los resúmenes reprocesados no coincidirán
con los originales, así que `memoria/` dejaría de ser reconstruible de forma estable.

Esa asimetría es todo el argumento: el coste de hoy es fijo y minúsculo; el de después crece con
cada capítulo y cambia de naturaleza.

---

## B — Huecos de ontología que la spec no recoge

### B1 🟡 Ocho nombres de rama 4 y la forma de `cursor`

`definitions.md` §4 y `architecture.md` §7.1 nombran distinto los mismos campos.

**Propuesta: manda §7.1, sin alias.**

| `definitions.md` §4 | Canónico (§7.1) |
|---|---|
| `estado_personajes` | `personajes` |
| `grafo_relaciones` | `relaciones` |
| `inventario_objetos_pruebas` | `objetos` |
| `hilos_abiertos` + `hilos_cerrados` | `hilos`, fusionados con `estado` como discriminante |
| `pistas_estado` | `pistas` |
| `conocimiento_del_lector` | `conocimiento_lector` |
| `curva_tension_real` | `tension_real` |
| `metricas_acumuladas` | `metricas` |

**Por qué gana §7.1**: es el contrato de la API, es lo que valida `state.schema.json` y es lo que
nombrará las tablas de `esquema.sql`. `definitions.md` es un diccionario, y un diccionario cede
ante el contrato.

**Sin alias, deliberadamente.** Un alias deja los dos nombres vivos y funcionando, que es
exactamente cómo se llegó a esta divergencia. Un nombre.

**`cursor`**: cuatro campos, `{capitulo, fase, ultimo_paso, intento}`. La versión de tres de
`definitions.md` se retira. `intento` no es decorativo: el model checking de la tarea 2.18 enumera
`fase × ultimo_paso × intento`, y la parada al tercer intento (`validators.md` §4.5) necesita que
se persista.

**Acción**: corregir `definitions.md` §4 en el commit de la tarea 1.6, y añadirlo a la fila de
docs de §14 de la spec, donde hoy no está.

### B2 🟡 Seis colecciones append-only del canon sin trigger

`misterio.verdad_oculta`, `misterio.pistas`, `pistas_falsas`, `revelaciones`, `giros` y
`estilo.prohibiciones` están declaradas append-only en `definitions.md` §2. Viven en markdown, no
en SQLite: **no hay trigger que las sostenga**.

**Propuesta: un tipo genérico, y un requisito que lo obligue.**

`ColeccionAppendOnly[T]` en `dominio/`: entradas congeladas, expone `añadir()`, `__iter__` y
`__len__`, y devuelve una tupla en vez de la lista interna para que no se escape una referencia
mutable. No expone `__setitem__`, ni `remove`, ni `clear`.

Una sola implementación sirve para `LibroDeHechos` y para las seis del canon. Siete usos, un tipo.

**La asimetría, dicha en voz alta**: en la rama 4 el tipo evita escribir el bug y el trigger lo
caza igualmente. En el canon **el tipo es la única línea de defensa**. Si alguien edita
`canon/misterio.md` a mano, nada lo impide — pero `AGENTS.md` ya prohíbe editar el workspace a
mano y el `arquitecto` es su único escritor.

`estilo.prohibiciones` es la única que crece durante la ejecución: el `editor-estilo` le añade
patrones. Crece, no cambia.

**Falta un requisito**, porque hoy nada lo obliga:

> **RF-28** — Los modelos de `canon.py` no exponen forma de modificar ni de borrar una entrada de
> las seis colecciones que `definitions.md` §2 declara append-only.
>
> **CA-30** (RF-28) Property-based sobre canons generados: ningún método público de esas seis
> colecciones reduce su longitud ni altera una entrada existente.

### B3 🟢 `esc-` colisionado y `hec-` ausente

**Propuesta: dos regex disjuntas, y añadir la fila que falta.**

```
escenario   ^esc-[a-z][a-z0-9-]*$      esc-casa-del-faro
escena      ^esc-\d{2,3}-\d+$          esc-07-2
hecho       ^hec-\d{3}$                hec-014
```

Disjuntas por construcción: escenario exige letra tras el guion, escena exige dígito. El `\d{2,3}`
de escena sigue la misma regla de dos o tres dígitos que los capítulos.

**Alternativa descartada**: renombrar escena a `sce-` o `esn-`. Más limpio, pero cambia un prefijo
de id que ya aparece en `architecture.md` §5, en §7.1 y en el ejemplo de frontmatter — y los ids
son claves estables por definición. No compensa para una colisión que una regex resuelve.

**`hec-`** es una omisión de la tabla, no del dominio: `hec-014` ya aparece en §7.1 y §7.3. Se
añade la fila a `AGENTS.md` y a `architecture.md` §5.

**Acción**: las dos correcciones, a la fila de docs de §14.

---

## C — Hallazgos del barrido

### C1 🔴 `revelaciones[]` no declara ni un campo

**Bloquea la tarea 1.4.** Es lo único de esta lista que impide escribir código.

Lo que se sabe: append-only, la escribe el `arquitecto`, la leen `trazador` y `lector-suspense`;
prefijo `rev-`; «momentos en que una parte de la verdad oculta pasa al conocimiento del lector»;
y `giros[]` son revelaciones que además invalidan una creencia previa, con
`que_creia_el_lector_antes`. Ningún documento dice qué campos tiene.

**Propuesta:**

```
revelacion:
  id                    RevelacionId          rev-002
  contenido             str                   qué parte de la verdad oculta se revela
  pistas_que_la_pagan   list[PistaId]         mínimo 1
  capitulo_previsto     CapituloNum           es plan; el real se deriva del texto
  quien_la_recibe       "lector" | "personaje" | "ambos"
  impacto               "alta" | "media" | "baja"

giro(revelacion):
  que_creia_el_lector_antes   str             obligatorio
```

Justificación de los dos campos que no son obvios:

**`pistas_que_la_pagan`, mínimo 1.** Es el campo que sostiene todo. RF-22 exige que `auditar`
reporte «revelaciones sin pista plantada antes»; sin este campo esa comprobación tiene que
*inferir* qué pista paga qué revelación, y no hay de dónde inferirlo. Con él, la comprobación es
aritmética: para cada revelación, toda pista listada tiene `plantada_en` anterior a su capítulo.

Y la cardinalidad mínima de 1 convierte el fair play en **guardarraíl en vez de gate**: una
revelación sin pista no se puede ni escribir en el canon, en lugar de detectarse en la auditoría
final cuando ya hay 24 capítulos escritos. `validators.md` §4.4 dice que se prefiera siempre lo
primero.

**`quien_la_recibe`.** Una revelación a un personaje no es una revelación al lector. El estado
tiene `conocimiento` y `conocimiento_lector` como colecciones separadas precisamente por esto; sin
la distinción, el `lector-suspense` no puede calcular qué sabe el lector.

**Alternativa descartada**: dejar `revelaciones[]` como lista de texto libre y derivar el fair
play de `pista.capitulo_pagado`. No sirve: ese campo dice *cuándo* se pagó una pista, no *qué
revelación* pagó. Dos revelaciones en el mismo capítulo que una pista pagada son indistinguibles,
y RF-22 necesita atribución.

**Acción**: es contrato nuevo. Entra en §8 de la spec (`canon.schema.json` lo gana) y en §14.

**Esta es la que más conviene que revises tú**: es diseño narrativo, no de sistema, y me he guiado
por lo que la auditoría necesita calcular. Si el género pide otra cosa, mándame los campos y
ajusto.

### C2 🟢 RNF-01 tiene dos umbrales y un solo criterio

RNF-01 exige `validar` < 2 s **y** `novela estado --breve` < 500 ms sobre 24 capítulos. CA-27 solo
cubre el primero.

**Propuesta**: añadir

> **CA-31** (RNF-01) `novela estado --breve` sobre el fixture de 24 capítulos termina en < 500 ms

El test ya está colocado en la tarea 1.15 del plan (`test_estado.py::test_breve_rendimiento`), con
el aviso de que hoy no cierra ningún CA. Una línea en §11 y una fila en §12.

### C3 🟢 Cuatro RNF sin fila de trazabilidad

§12 dice «sin esta tabla no se pasa a `implementada`», y le faltan RNF-02, RNF-04, RNF-06 y
RNF-07.

**Propuesta**: tres se cierran con criterios que ya existen, y el cuarto destapa un hueco real.

| RNF | Propuesta |
|---|---|
| RNF-02 (contexto) | Filas apuntando a CA-05 y CA-11, que ya lo cubren |
| RNF-04 (fiabilidad) | Filas apuntando a CA-04 y CA-17 |
| RNF-06 (compatibilidad) | Fila explícita «no aplica», en vez de omitirla. Una tabla completa se ve completa |
| RNF-07 (seguridad) | CA-26 cubre el path traversal. **La otra mitad no la cubre nadie** |

RNF-07 dice además «ninguna clave en fichero versionado; `ruff` con reglas `S` en pre-commit», y no
hay ni criterio ni tarea. `validators.md` §3.2 lo pide explícitamente y remata: «la regla la hace
cumplir el linter, no la disciplina».

> **CA-32** (RNF-07) Un fichero versionado que contenga `LANGFUSE_SECRET_KEY` o equivalente hace
> fallar el pre-commit

**Acción en el plan**: la configuración de pre-commit se añade a la tarea 1.1, que ya monta `ruff`.

### C4 🟢 `novela auditar` no está en §8 de `architecture.md`

La lista de §8 tiene ocho entradas y `auditar` no es una, pese a existir en `AGENTS.md`, como
slash command y como slice.

**Propuesta**: añadir `novela auditar <slug>` junto a `novela nueva`, en el mismo commit (tarea
1.14). `novela budget` se queda fuera mientras A2 siga diferida.

### C5 🟢 `docs/adr/` no existe y hay tres referencias a él

`architecture.md` §3.1 nombra un fichero concreto —`docs/adr/0001-orquestador-en-claude-code.md`—
que no existe. `AGENTS.md` y `_plantilla.md` también lo referencian. `AGENTS.md` tiene una regla
dura: la documentación de referencia describe lo que hay.

**Propuesta: escribir el ADR, no borrar la referencia.**

La decisión cumple el criterio que el propio `AGENTS.md` fija —«cuando revertirla sería caro»— y de
largo: todo el harness asume que el orquestador es una sesión de Claude Code, y revertirlo
significa un orquestador en Python con un SDK de modelos, que la sección «Nunca» prohíbe.

Contenido propuesto:

- **Decisión**: el orquestador es una sesión de Claude Code, no un proceso.
- **Alternativas descartadas**: orquestador Python con SDK de proveedor (prohibido por
  `AGENTS.md`); un framework de agentes tipo LangGraph o CrewAI (añade framework y gateway, y no
  aporta aislamiento por subagente); un bucle de shell con prompts (sin subagentes no hay `tools`
  restringido, que es la contención del invariante 3).
- **Consecuencias**: sin control de temperatura (§12.1); techo de contexto por sesión (§6.5); un
  capítulo por sesión en modo desatendido.

Está fuera del alcance de la 0001, pero cierra una referencia colgada y cuesta media hora.

### C6 🟡 Tres cosas que decidí yo y nadie ha validado

#### C6a — Presupuestos de cuatro recetas

Derivados de la aritmética de §6.5: `techo = 100.000 − 10.000 fijo − salida_esperada − 15.000
margen`.

| Agente | Salida estimada | Presupuesto propuesto |
|---|---|---|
| `arquitecto` | ~25.000 (canon entero: premisa, mundo, estilo, misterio, N fichas) | 50.000 |
| `trazador` | ~20.000 (escaleta + N fichas de capítulo) | 55.000 |
| `editor-estilo` | ~7.000 (capítulo reescrito + informe) | 68.000 |
| `lector-suspense` | ~8.000 (scores y hallazgos) | 67.000 |
| `cronista` | ~5.000 | 70.000, de §6.5 |

**Límite conocido, y conviene que esté escrito**: la salida de `arquitecto` y `trazador` **escala
con `num_capitulos`**. A 24 capítulos estos números sobran; a 99 el `trazador` no cabe, porque su
salida es una ficha por capítulo. No propongo generalizarlo ahora —sería resolver un problema que
nadie tiene—, sino dejar la nota: **estos presupuestos suponen `num_capitulos ≤ 30`**. Más allá, o
se re-derivan o el `trazador` escribe por actos en varias invocaciones.

#### C6b — Enums que cerré desde los ejemplos

Ninguno está documentado; los derivé del bucle de §2.1 y de los ejemplos de §7.1 y §7.3.

`cursor.fase` = `escritura | revision | registro | cerrado`, los cuatro tramos del bucle.
`cursor.ultimo_paso` = los nueve pasos. `veredicto` = `aprobado | rechazado |
aprobado_con_reservas`. `gravedad` = `alta | media | baja`. Más `condicion`, `relevancia` y el
`estado` de hilo y de pista, en las tareas 1.6 y 1.7 del plan.

**Propuesta**: que aterricen en `definitions.md`, que es el diccionario, y no solo en el código. Un
enum que vive únicamente en Python es un contrato que el `continuista` no puede consultar.

#### C6c — La forma del delta

Está derivada entera por mí en la tarea 2.11. Es la única entrada de `aplicar-delta` y el único
contrato de agente sin ejemplo: §7.2 tiene el frontmatter, §7.3 tiene el informe de QA, y el delta
no tiene nada.

**Propuesta**: que el ejemplo trabajado viva en `architecture.md` §7.x, junto a los otros dos
contratos de agente, y no solo en `delta.schema.json`. Es donde alguien lo buscará.

Y que lo revise quien sepa qué puede producir un `cronista` de verdad: mi derivación sale de qué
necesita el estado, no de qué es razonable pedirle a un agente en una invocación.

---

## Resumen para decidir

| # | Qué | Propuesta | Urgencia |
|---|---|---|---|
| A1 | `nueva` o `init` | `nueva` | 🟢 |
| A2 | `presupuesto/` | Spec 0003, tras la novela de humo | 🟢 |
| A3 | `run_id` | `NOVELA_RUN_ID` con fallback y formato validado | 🟡 |
| A4 | Fase 4 | Ahora, la última, sin los dos GET de §12.6 | 🟡 |
| A5 | Escena en el delta | Sí | 🟡 |
| B1 | Nombres rama 4 | Manda §7.1, sin alias | 🟡 |
| B2 | Append-only del canon | `ColeccionAppendOnly[T]` + RF-28 y CA-30 | 🟡 |
| B3 | `esc-` y `hec-` | Dos regex disjuntas, añadir fila `hec-` | 🟢 |
| C1 | Campos de `revelacion` | Seis campos; `pistas_que_la_pagan` mínimo 1 | 🔴 |
| C2 | Segundo umbral de RNF-01 | CA-31 | 🟢 |
| C3 | RNF sin trazabilidad | Cuatro filas, y CA-32 para las claves | 🟢 |
| C4 | `auditar` en §8 | Añadir la línea | 🟢 |
| C5 | `docs/adr/` | Escribir el ADR 0001 | 🟢 |
| C6 | Presupuestos, enums y delta | Documentarlos; techo de 30 capítulos | 🟡 |

Las catorce están cerradas. La spec está en 0.2 y `aceptada`; lo único que queda con fecha futura
es la corrección de `architecture.md` §7.5 —las salidas del `cronista`—, que espera al commit de
la tarea 2.15 porque describe un contrato que cambia cuando exista el código que lo sustituye.
