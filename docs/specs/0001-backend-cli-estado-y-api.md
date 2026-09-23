---
spec: 0001
titulo: "El backend: CLI `novela`, dominio, estado en SQLite y API de lectura"
estado: aceptada
autor: "arturo.soto"
fecha: 2026-09-22
version: 0.3
afecta: [backend, esquemas, docs]
depende_de: []
sustituye: []
adr: [0001]
commit: null
---

# 0001 — El backend: CLI `novela`, dominio, estado en SQLite y API de lectura

## 1. Propósito y alcance

Construir `backend/` desde cero: el CLI determinista `novela` que el orquestador invoca entre delegaciones, la ontología como código, el soporte de estado en SQLite y la API de solo lectura que consume el panel. Es la primera línea de código del sistema; hoy `backend/` es un directorio vacío.

**Dentro del alcance**

- Los ocho subcomandos que `AGENTS.md` declara: `estado`, `briefing`, `validar`, `aplicar-delta`, `checkpoint`, `pendiente`, `auditar`, `exportar`.
- Un noveno, `novela nueva`, que crea el workspace y la base de estado. Hoy no existe forma de que `novelas/<slug>/` y `estado.db` lleguen a existir (§2).
- `dominio/`: los modelos Pydantic de las ramas 1 a 4 de `docs/definitions.md`, y los JSON Schema generados a `backend/schemas/`.
- `plataforma/`: `esquema.sql` con los triggers append-only, conexión y transacciones, escritura atómica, lock de workspace y el `ScoreSink` de Langfuse.
- `config/default.yaml` y `config/recipes.yaml`.
- La API FastAPI de `architecture.md` §11.1: cinco `GET`, ningún verbo de escritura.
- La suite de tests con workspaces sintéticos, sin una sola llamada a modelo.
- Desde la v0.3, la **forma** que necesitan las verificaciones de `validators.md` §3.9.7, §3.9.8 y §4.9 y que sale cara de añadir más tarde: custodia del capítulo por hash, sello de los capítulos cerrados, `cita` opcional en las colecciones append-only y fichas de personaje estructuradas (§5.6).

**Fuera del alcance**

- La **política** que usa esos campos —qué es obligatorio, qué se filtra, qué para el bucle— y el resto de verificaciones de `validators.md` §3.9 a §4.16: spec 0002, en `borrador`. La v0.3 añade solo lo que no abre ninguna pregunta.
- `.claude/`: agentes, hooks, permisos y slash commands. La contención de agentes es `architecture.md` §12.7 y merece su propia spec; aquí solo se construye la mitad que vive en Python.
- Los prompts de los agentes y qué capas concretas maximizan la calidad de la prosa. Esta spec fija el **mecanismo** de ensamblado y el formato de las recetas, no su contenido.
- Las cuatro decisiones abiertas de `architecture.md` §12: `indice_recuperable` (§12.4), los dos `GET` del log en vivo (§12.6), la cola en disco y `run.sh` (§12.8) y la regla `deny` sobre el misterio (§12.7). Cada una es una spec posterior; ninguna es precondición de esta.

  De `indice_recuperable` sí hay una consecuencia para esta spec, aunque el índice no se construya: **no cerrarle la puerta a las dos capas baratas.** §12.4 fija que la exacta y la léxica no añaden dependencias y van primero, y que la semántica —`multilingual-e5-small` vía `fastembed`, descartado PyTorch por peso— solo entra si una medición la justifica. Las dos primeras dependen de decisiones que esta spec sí toma hoy: la capa exacta necesita que el delta del `cronista` traiga el identificador de escena, y la léxica necesita que `memoria/resumenes/NN.md` conserve granularidad por escena. Si la fase 1 fija esos dos formatos sin ese grano, añadirlas después deja de ser aditivo y pasa a ser una migración con reproceso. Ver §16.
- El slice `presupuesto/` y el subcomando `novela budget` de `architecture.md` §9. No está en la lista de CLI de `AGENTS.md`, la política de degradación la decide hoy el orquestador, y sin una ejecución real no hay con qué calibrar los umbrales. Ver §16.
- El frontend. Consume el OpenAPI que produce la fase 4, y nada más.

## 2. Problema

No hay backend. `find backend -type f` no devuelve nada, y sin él ninguno de los siete agentes puede ejecutarse: el bucle de `.claude/commands/novela-continuar.md` empieza por `novela briefing` y no hay `novela`.

Debajo de esa obviedad hay tres huecos que la documentación de referencia no cierra, y que hay que resolver aquí porque el código los va a encontrar el primer día.

**Nadie crea el workspace.** `architecture.md` §4 describe el árbol de `novelas/<slug>/` y §7.1 describe `estado.db` con su DDL y su `schema_version`, pero ningún subcomando lo construye. El `arquitecto` tiene `Read, Write` y no puede ejecutar DDL; el slash command `/novela-nueva` es un procedimiento, no un ejecutable. §12.8 ya apunta la dirección —«el `config.yaml` lo escribe siempre el backend»— pero el subcomando que lo escribiría no está en ninguna lista.

**Dos documentos dicen cosas distintas sobre quién escribe `memoria/`.** `architecture.md` §6.4 dice que `novela aplicar-delta` escribe `memoria/resumenes/NN.md` a partir de la salida del `cronista`; la tabla de §7.5 se lo atribuye al `cronista` directamente. No es un matiz: decide si `memoria/` es un artefacto validado contra esquema o texto libre de un agente, y si reconstruirlo cuesta cuota.

**La ontología se contradice a sí misma en cuatro sitios.** `definitions.md` §4 y `architecture.md` §7.1 nombran distinto ocho campos del estado —`estado_personajes` frente a `personajes`, `curva_tension_real` frente a `tension_real`, y seis más— y dan a `cursor` tres campos en un documento y cuatro en el otro. `revelaciones[]` no declara ni un campo pese a que RF-22 tiene que cruzarla con las pistas. El prefijo `esc-` sirve a escenario (`esc-casa-del-faro`) y a escena (`esc-07-2`) sin regla que los separe, y `hec-` se usa en §7.1 y §7.3 sin figurar en la tabla de identificadores. Nada de esto se puede dejar para después: el primer modelo Pydantic lo encuentra.

**Seis colecciones append-only no tienen quien las sostenga.** `definitions.md` §2 declara append-only `misterio.verdad_oculta`, `misterio.pistas`, `pistas_falsas`, `revelaciones`, `giros` y `estilo.prohibiciones`. Todas viven en markdown, no en SQLite, así que el trigger del invariante 2 no las alcanza. O lo impone el modelo o no lo impone nadie.

**El árbol y las convenciones no coinciden en la ruta de los modelos.** `architecture.md` §3.1 los pone en `backend/novela/dominio/`; `AGENTS.md` y `docs/validators.md` §3.1 los llaman `backend/novela/models/`. Cualquiera de las dos vale, pero no las dos: la regla dura de `validators.md` —«ningún dato cruza de disco o de agente al código sin pasar por un modelo de …»— necesita una única ruta a la que apuntar.

**Nada ata un veredicto al texto que juzgó** (añadido en la v0.3). Los tres revisores leen una versión del capítulo, el `editor-estilo` escribe otra y el `cronista` extrae el delta de la que haya en disco. Ningún fichero registra qué versión leyó cada uno, así que un `aplicar-delta` sobre un capítulo que cambió después de validarse no se distingue de uno correcto. Lo mismo vale entre capítulos: el invariante 7 prohíbe reescribir un capítulo cerrado, y la política de cuota de `architecture.md` §9 lo hace en sus niveles 2 y 4 sin que nada lo detecte (`validators.md` §3.9.7). Y tres formatos que esta spec fija en la fase 1 no tienen hueco para lo que exigirá la verificación: las entradas de `conocimiento`, `linea_temporal` y `conocimiento_lector` no llevan cita, y la ficha de personaje no separa `secreto` ni `coartada_y_cronologia_privada` del resto (`validators.md` §3.9.8, §4.9). Añadir cualquiera de las tres cosas con novelas ya escritas exige volver a pasar el `cronista` o el `arquitecto` sobre ellas.

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Orquestador | Es el usuario del CLI. Todo lo que ejecuta entre delegaciones sale de esta spec, y `--breve` es lo que protege su contexto |
| Agente `escritor` | Su briefing y el gate mecánico que lo evalúa. Un reintento suyo es el más caro del bucle |
| Agentes `continuista`, `lector-suspense` | Consumen briefing y producen JSON contra `backend/schemas/`; el CLI valida su salida |
| Agente `cronista` | Su delta es la única entrada de `aplicar-delta`, y la única vía de escritura del estado |
| Operador humano | `novela nueva` para arrancar, `novela auditar` para cerrar |
| Frontend / API | Los cinco `GET` de la fase 4 y el OpenAPI del que genera sus tipos |

## 4. Contexto y restricciones

- **Invariantes que aplican**: los ocho. Los cuatro que el código tiene que hacer mecánicamente son el **1** (`estado.db` solo por `aplicar-delta`), el **2** (append-only por triggers), el **6** (escritura atómica) y el **8** (un proceso por workspace). El **3** (el secreto) lo sostiene el aborto de `novela briefing`. El **4** (fair play) lo verifican los gates de `validar` y `auditar`. El **5** es del orquestador, no del CLI. El **7** también, pero desde la v0.3 el CLI **detecta** su violación con el sello de RF-35: no la impide, y basta con que no pase inadvertida.
- **Restricciones técnicas**: Python 3.12, `uv`, sin SDK de proveedores de modelos, cero llamadas a modelo desde el CLI y desde los tests. La API no escribe. La única salida de red del CLI es la emisión de scores a Langfuse.
- **Supuestos**: (a) la ratio de 3,5 caracteres por token de §6.5 es cota superior suficiente para español; (b) el workspace vive en un solo disco local, de modo que `os.replace` es atómico y `filelock` basta; (c) no hay ninguna novela empezada, así que no hay nada que migrar.
- **Dependencias**: ninguna spec previa. Las cuatro decisiones de §12 dependen de esta, no al revés.

## 5. Propuesta

### 5.0 Los huecos de §2, resueltos

1. **Se añade `novela nueva <slug>`**, que crea el árbol de `architecture.md` §4, escribe `config.yaml` a partir de `config/default.yaml` más los flags, y crea `estado.db` ejecutando `plataforma/esquema.sql`. El slash command `/novela-nueva` pasa a ser lo que ya pretendía ser: `novela nueva` y después la delegación al `arquitecto`.
2. **`memoria/resumenes/NN.md` lo escribe `novela aplicar-delta`**, como dice §6.4. El delta del `cronista` transporta las tres granularidades en `resumen: {linea, parrafo, escena}`, validadas contra `delta.schema.json`; el CLI las renderiza al fichero dentro de la misma operación. Así `memoria/` es derivado de verdad: se reconstruye recorriendo `estado/deltas/*.json`, sin volver a invocar al `cronista` y sin gastar cuota. La tabla de §7.5 queda desfasada y se corrige en el mismo commit.
3. **La ruta es `backend/novela/dominio/`**, la de §3.1, porque es la que nombra la metodología de §3.0. `AGENTS.md` y `validators.md` §3.1 se corrigen.
4. **Los nombres canónicos del estado son los de §7.1**, sin alias. Es el documento que valida `state.schema.json`, el que responde la API y el que nombra las tablas; `definitions.md` es un diccionario y cede ante el contrato. `cursor` tiene cuatro campos, `{capitulo, fase, ultimo_paso, intento}`: el `intento` se persiste porque la parada al tercero y el model checking de §13 dependen de él. Un alias dejaría los dos nombres vivos, que es exactamente cómo se llegó a la divergencia.
5. **`revelaciones[]` gana campos**: `{id, contenido, pistas_que_la_pagan, capitulo_previsto, quien_la_recibe, impacto}`, y `giros[]` añade `que_creia_el_lector_antes`. `pistas_que_la_pagan` lleva **mínimo una** referencia, y eso es lo que convierte el fair play en guardarraíl: una revelación sin pista no se puede escribir en el canon, en vez de detectarse en la auditoría con la novela terminada. Sin el campo, RF-22 tendría que inferir qué pista paga qué revelación, y `pista.capitulo_pagado` no lo dice: dice cuándo se pagó, no qué pagó.
6. **`esc-` se desambigua por expresión regular**: escenario es `^esc-[a-z][a-z0-9-]*$` y escena es `^esc-\d{2,3}-\d+$`, disjuntas por construcción. Se descarta renombrar escena a otro prefijo: los ids son claves estables y ya aparecen en §5, §7.1 y el frontmatter. `hec-` se añade a la tabla de identificadores.
7. **Las seis colecciones append-only del canon las sostiene el tipo** (RF-28). Un único `ColeccionAppendOnly[T]` en `dominio/` sirve a las seis y a `LibroDeHechos`: expone `añadir()`, devuelve tupla en vez de la lista interna, y no expone forma de modificar ni de borrar. En la rama 4 el tipo evita escribir el bug y el trigger lo caza igual; en el canon el tipo es la única línea.

### 5.1 Forma del backend

El árbol es el de `architecture.md` §3.1. Lo que esta spec crea, fase a fase:

```
backend/
├── pyproject.toml            # [project.scripts] novela = "novela.cli:app"
├── uv.lock
├── api/                      # fase 4
│   ├── main.py
│   └── routers/{novelas.py,capitulos.py}
├── novela/
│   ├── cli.py                # Typer; solo registra el cmd.py de cada slice
│   ├── slices/
│   │   ├── nueva/            # fase 1
│   │   ├── estado/           # fase 1
│   │   ├── briefing/         # fase 2 — cmd.py · assemble.py · recipes.py
│   │   ├── validacion/       # fase 2 — cmd.py · gates.py
│   │   ├── delta/            # fase 2 — cmd.py · apply.py · violaciones.py
│   │   ├── checkpoint/       # fase 2
│   │   ├── auditoria/        # fase 3
│   │   └── export/           # fase 3 — cmd.py · markdown.py · epub.py
│   ├── dominio/              # fase 1 — config.py · canon.py · plan.py · estado.py · qa.py
│   └── plataforma/           # fase 1 — workspace.py · esquema.sql · estado_db.py
│                             #          atomic.py · lock.py · langfuse.py
├── config/{default.yaml,recipes.yaml}
├── schemas/                  # generados desde Pydantic
└── tests/{test_api.py,test_contratos.py,fixtures/}
```

Reglas de estructura, de `architecture.md` §3.0: el `cmd.py` de cada slice es la única cáscara imperativa —argumentos, lock, disco, código de salida—; `gates.py`, `assemble.py` y `apply.py` son funciones puras. Un fichero del núcleo que importe `pathlib`, `open`, `datetime.now` o red está mal colocado, y esa frontera es lo que hace posible el property-based testing de `validators.md` §3.6.

**Invocación.** El CLI se instala como script del proyecto. El orquestador lo llama con `uv run --project backend novela …`; la forma corta `novela …` de la documentación supone el venv activo. El workspace se resuelve a `./novelas/<slug>` desde el directorio de trabajo, o a `$NOVELAS_DIR/<slug>` si la variable está definida — que es también como los tests apuntan a los fixtures.

**Códigos de salida**, iguales para todos los subcomandos:

| Código | Significado |
|---|---|
| 0 | Correcto. En `pendiente`, además: quedan capítulos |
| 1 | Gate fallido, hallazgos de auditoría, o en `pendiente`: no quedan capítulos |
| 2 | Uso incorrecto (lo emite Typer) |
| 3 | Lock ocupado: otro proceso trabaja sobre el workspace |
| 4 | Workspace inválido o estado ilegible |

### 5.2 Fase 1 — dominio, plataforma y lectura de estado

Al final de la fase existe un workspace creable e inspeccionable, y todo lo demás tiene dónde apoyarse.

**`dominio/`.** Las ramas 1 a 4 de `docs/definitions.md` como modelos Pydantic v2, con la mutabilidad en el tipo y no en un comentario: `LibroDeHechos` expone `añadir()` y no expone forma de modificar ni de borrar. Los identificadores de `AGENTS.md` son tipos con validador de formato (`^per-[a-z0-9-]+$`, `^pis-\d{3}$`, …), no `str`. El número de capítulo es un tipo con su rango y su formato de dos o tres dígitos según `num_capitulos`.

**`plataforma/esquema.sql`.** Una tabla por colección de la rama 4, `meta` con `schema_version`, y triggers `BEFORE UPDATE` y `BEFORE DELETE` con `RAISE(ABORT)` en las cinco colecciones que `definitions.md` declara append-only: `libro_de_hechos`, `conocimiento`, `linea_temporal`, `conocimiento_lector` y `tension_real`. Índices por `capitulo` y por id de entidad, que es lo que hace que el largo plazo se consulte en vez de cargarse (§6.4).

**`plataforma/estado_db.py`.** Conexión con `journal_mode=WAL`, `foreign_keys=ON` y `busy_timeout`; toda escritura dentro de `BEGIN IMMEDIATE … COMMIT`. La API abre la misma base con `file:…?mode=ro`, así que no hay ruta de escritura ni por descuido.

**`plataforma/atomic.py`, `lock.py`, `workspace.py`.** Escritura `.tmp` + `os.replace` para todo fichero; `filelock` sobre `estado/state.lock` en todo subcomando que escribe; `WorkspaceRepository` como puerto, con la implementación real y la de fixtures.

**`novela nueva <slug> --idea "…" --capitulos 24 --palabras 80000`.** Crea el árbol, escribe `config.yaml` —`default.yaml` más los flags, validado contra el modelo de la rama 1— y crea `estado.db`. Si el slug ya existe, sale con 1 sin tocar nada. El slug se valida contra `^[a-z0-9-]+$` antes de tocar el disco, la misma regla que la API.

**`novela estado <slug> [--breve|--json]`.** `--breve` imprime cursor, capítulos hechos, hilos abiertos, pistas pendientes de pagar y palabras acumuladas, en un máximo de doce líneas: es lo que el orquestador paga en contexto muchas veces por novela. `--json` serializa el contrato de §7.1 desde los modelos del dominio. **`novela pendiente <slug>`** no imprime nada y comunica por código de salida.

### 5.3 Fase 2 — el bucle por capítulo

Al final de la fase el bucle de `.claude/commands/novela-continuar.md` es ejecutable de principio a fin.

**`novela briefing <slug> <cap> <agente>`.** Lee la receta del agente en `config/recipes.yaml` (formato de §6.2), ensambla las capas **incrustando su contenido** —un briefing es el contexto exacto de una invocación, no una lista de rutas— y lo escribe en `runs/<run_id>/briefings/NN-<agente>.md`. Tres comportamientos que no son opcionales:

1. **Guardarraíl del secreto.** Si el briefing ensamblado de un agente cuya receta excluye `canon/misterio` contiene texto procedente de ese fichero, aborta y no escribe nada. Para el `trazador`, el `continuista` y el `lector-suspense` el contenido se incrusta, que es además lo que hace viable la regla `deny` de §12.7 sin volver a tocar el CLI.
2. **Techo de contexto.** Cuenta lo ensamblado con la ratio de 3,5 caracteres por token y lo compara contra `presupuesto_tokens`. Si no cabe, degrada en el orden fijo de §6.5 —resúmenes a una línea más antiguos, resúmenes a párrafo bajados a una línea, personajes reducidos a los que tienen diálogo— y si sigue sin caber **falla**. Nunca trunca en silencio.
3. **Run y manifiesto.** Si no hay run abierto, crea `runs/r-AAAAMMDD-HHMM/` y escribe `manifest.json` con el sha del commit, la versión de recetas y las versiones de canon y plan vigentes. Todo subcomando añade una línea a `runs/<run_id>/harness.log` con volcado línea a línea: es la condición previa que §12.6 necesita comprobar antes de servirlo.

**`novela validar <slug> <cap>`.** El gate barato, y el que decide si se gastan tres llamadas a modelo. Comprueba, en este orden: frontmatter del capítulo contra su JSON Schema; palabras dentro de `palabras_por_capitulo.{min,max}`; presencia en el frontmatter de todas las pistas que `plan/capitulos/NN.md` manda plantar y pagar; que ningún hilo se cierre sin haberse abierto; que todo id citado exista. Escribe los hallazgos en `qa/NN-validacion.json` con el formato de informe de §7.3 y sale con 1. El reintento del escritor recibe ese fichero y nada más.

**`novela aplicar-delta <slug> <cap>`.** Valida `estado/deltas/NN.json` contra `delta.schema.json` y aplica el delta entero dentro de una transacción: si una fila viola una restricción o un trigger, no queda nada escrito. Comprueba además lo que el esquema no expresa —ids únicos entre colecciones y monotonía del cursor— y renderiza `memoria/resumenes/NN.md`. Es idempotente: `aplicar(aplicar(e, d), d) == aplicar(e, d)`, porque reanudar repite el paso.

**`novela checkpoint <slug> <cap>`.** Escribe `checkpoints/NN.json` y `checkpoints/latest.json` atómicamente, con cursor, versiones y `run_id`. Es también el punto donde se emiten los scores del capítulo por `ScoreSink`, tomándolos de `qa/NN-suspense.json` y del resultado de los gates: `coherencia`, `continuidad`, `tension`, `longitud`, `fair_play`, `estilo`. Con `TRACE_TO_LANGFUSE` distinto de la cadena `"true"`, el sink es un no-op y el checkpoint se escribe igual.

### 5.4 Fase 3 — cierre de novela

**`novela auditar <slug>`** cruza plan, canon y estado y saca las tres cosas que `definitions.md` §10 llama auditoría final: pistas plantadas y nunca pagadas, hilos abiertos y nunca cerrados, pistas falsas nunca desmontadas. Añade la comprobación de fair play del invariante 4 —ninguna revelación sin pista plantada antes— y sale con 1 si hay hallazgos.

**`novela exportar <slug> --formato md|epub`** concatena los capítulos en orden a `export/novela.md`, y con `ebooklib` produce `export/novela.epub`. No reescribe prosa: es transporte, no edición.

### 5.5 Fase 4 — API de lectura

Los cinco `GET` de §11.1, con los modelos del dominio como modelos de respuesta. La app no importa nada de `slices/`: no hay ruta de código desde un `GET` a una escritura, y el test lo comprueba montando el workspace en solo lectura durante toda la suite.

El slug se valida contra `^[a-z0-9-]+$` **antes** de construir ninguna ruta. Es la única superficie de inyección real del sistema (`validators.md` §3.2) y tiene test propio con `../`.

El OpenAPI se commitea; CI falla si el fichero commiteado no coincide con el que genera el código. De ahí saldrán los tipos del frontend.

### 5.6 Enmienda 0.3 — custodia, sello, citas y fichas

Cuatro cambios de forma sobre subcomandos que ya existen en esta spec, repartidos en las fases 1 y 2. Ninguno añade subcomando ni cambia qué entra en un briefing. La política que los usa es de la spec 0002.

**Custodia del capítulo (RF-30 a RF-32, fase 2).** Ningún agente puede calcular un hash, así que lo registra el CLI en los dos puntos por donde pasa el texto. `novela briefing` escribe `capitulo_sha256` en el frontmatter del briefing cada vez que incrusta `capitulos/NN.md`: es la versión exacta que vio ese agente. `novela validar` escribe `qa/NN-validacion.json` también cuando pasa, con `veredicto: aprobado`, `hallazgos: []` y el `capitulo_sha256` del fichero validado. El hash es el de los bytes en disco, sin normalizar. `aplicar-delta` solo aplica si la cadena cierra:

1. el sha256 de `capitulos/NN.md` en disco es igual al del briefing del `cronista` y al del último `qa/NN-validacion.json`, y ese informe no tiene hallazgos;
2. los briefings de revisión del capítulo presentes en el mismo run que el del `cronista` —`continuista`, `lector-suspense`, `editor-estilo`— llevan todos el mismo hash. El del editor incluido: partió de la versión que revisaron los otros dos.

Si no cierra, sale con 1 sin escribir nada y deja la causa en `harness.log`. Es una precondición sobre datos, no un juicio sobre veredictos de modelo: el orquestador sigue decidiendo los gates (§15). De paso hace mecánicas dos reglas que hoy solo están escritas en prosa. El invariante de orden 1 de la tarea 2.18: no se aplica un delta sin que `validar` haya pasado sobre esa misma versión. Y la regla de que un reintento repite todos los gates: un briefing de revisión que queda del intento anterior lleva otro hash.

**Sello de capítulos cerrados (RF-35, fase 2).** `checkpoint` guarda en `checkpoints/NN.json` el sha256 de cada `capitulos/*.md` cerrado hasta N. Cada `briefing` compara los capítulos cerrados con `checkpoints/latest.json` y, si alguno ha cambiado o ha desaparecido, sale con 4 sin escribir el briefing: el workspace viola el invariante 7. El coste son veinticuatro hashes de unos veinte kilobytes por invocación.

**Citas opcionales (RF-33, fases 1 y 2).** Las entradas de `conocimiento`, `linea_temporal` y `conocimiento_lector` ganan `cita: str | None`, con columna nula en `esquema.sql`. `aplicar-delta` rechaza el delta entero si alguna `cita` presente —de esas tres colecciones o de `libro_de_hechos`— no es subcadena del cuerpo del capítulo, sin el frontmatter. Antes de comparar, los dos lados se normalizan a NFC y cada secuencia de espacios en blanco se colapsa en un espacio. Nada más: ni comillas tipográficas ni mayúsculas, porque una cita que solo casa aflojando la comparación ya no es una cita. Que sea obligatoria es una política, y es de la 0002; que exista desde el capítulo 1 es lo que evita tener que rellenarla hacia atrás.

**Hilos: delta contra frontmatter (RF-34, fase 2).** Las pistas no entran en el delta: son derivadas del frontmatter (tarea 2.11 del plan). Los hilos sí, así que hay dos descripciones del mismo texto que pueden divergir. `aplicar-delta` exige que los hilos abiertos y cerrados del delta sean exactamente `hilos_abiertos` e `hilos_cerrados` del frontmatter. Si difieren, uno de los dos productores se equivoca, y no hace falta saber cuál para no aplicar. Lo que el plan admita fuera de lo planificado es de la 0002.

**Fichas de personaje estructuradas (RF-36, fase 1).** `canon/personajes/<id>.md` lleva los campos de `definitions.md` §2.3 en frontmatter YAML y el cuerpo es prosa libre. El modelo `Personaje` prohíbe campos desconocidos. `secreto: {que_oculta, a_quien}` y `coartada_y_cronologia_privada: list[{momento, ubicacion: EscenarioId, detalle}]` son campos propios; `momento` es texto, como `linea_temporal.inicio`. El briefing sigue incrustando la ficha entera: qué campos se filtran y a quién es la 0002.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `novela nueva <slug>` crea el árbol de `architecture.md` §4, escribe `config.yaml` validado y crea `estado.db` con el DDL y `meta.schema_version`. Sobre un slug existente sale con 1 sin escribir | debe |
| RF-02 | `estado.db` aborta por trigger cualquier `UPDATE` o `DELETE` sobre `libro_de_hechos`, `conocimiento`, `linea_temporal`, `conocimiento_lector` y `tension_real` | debe |
| RF-03 | Todo subcomando que escribe toma `filelock` sobre `estado/state.lock` y sale con 3 si está ocupado | debe |
| RF-04 | Todo fichero del workspace se escribe con `.tmp` + `os.replace`; `estado.db` se escribe dentro de `BEGIN IMMEDIATE … COMMIT` | debe |
| RF-05 | `novela estado <slug> --breve` imprime cursor, capítulos hechos, hilos abiertos, pistas pendientes y palabras acumuladas en ≤ 12 líneas | debe |
| RF-06 | `novela estado <slug> --json` emite el documento de §7.1 y valida contra `schemas/state.schema.json` | debe |
| RF-07 | `novela pendiente <slug>` sale con 0 si quedan capítulos y con 1 si no, sin imprimir nada | debe |
| RF-08 | `novela briefing <slug> <cap> <agente>` ensambla las capas de la receta y escribe `runs/<run_id>/briefings/NN-<agente>.md` con su contenido incrustado | debe |
| RF-09 | `novela briefing` aborta sin escribir si el briefing de un agente que excluye `canon/misterio` contiene texto de ese fichero | debe |
| RF-10 | La receta de `trazador`, `continuista` y `lector-suspense` incrusta el contenido de `canon/misterio.md` en el briefing | debe |
| RF-11 | `novela briefing` estima tokens a 3,5 caracteres por token y falla si supera `presupuesto_tokens`; no trunca nunca | debe |
| RF-12 | Antes de fallar por presupuesto, `novela briefing` degrada en el orden fijo de §6.5, sin tocar `canon/` ni el estado filtrado | debe |
| RF-13 | El primer subcomando de un capítulo sin run abierto crea `runs/<run_id>/` y `manifest.json` con sha de commit y versión de recetas | debe |
| RF-14 | `novela validar <slug> <cap>` comprueba frontmatter, rango de palabras, pistas del plan presentes, balance de hilos e ids existentes | debe |
| RF-15 | `novela validar` escribe sus hallazgos en `qa/NN-validacion.json` con el formato de §7.3 y sale con 1 | debe |
| RF-16 | `novela aplicar-delta` valida el delta contra `delta.schema.json` y lo aplica entero en una transacción; ante cualquier violación no queda nada escrito | debe |
| RF-17 | `novela aplicar-delta` rechaza ids duplicados entre colecciones y cursor no monótono | debe |
| RF-18 | `novela aplicar-delta` renderiza `memoria/resumenes/NN.md` con las tres granularidades del delta | debe |
| RF-19 | `novela aplicar-delta` es idempotente sobre el mismo delta | debe |
| RF-20 | `novela checkpoint` escribe `checkpoints/NN.json` y `latest.json` atómicamente, con cursor, versiones y `run_id` | debe |
| RF-21 | `novela checkpoint` emite los seis scores del capítulo por `ScoreSink`, que es no-op salvo con `TRACE_TO_LANGFUSE == "true"` | debe |
| RF-22 | `novela auditar` reporta pistas huérfanas, hilos sin cerrar, pistas falsas sin desmontar y revelaciones sin pista previa; sale con 1 si hay hallazgos | debe |
| RF-23 | `novela exportar --formato md\|epub` produce `export/novela.md` y `export/novela.epub` | debería |
| RF-24 | La API sirve los cinco `GET` de §11.1 con los modelos del dominio y abre `estado.db` en modo lectura | debe |
| RF-25 | La API valida el slug contra `^[a-z0-9-]+$` antes de construir ninguna ruta | debe |
| RF-26 | `backend/schemas/*.json` se generan desde los modelos Pydantic y se versionan; cada documento lleva su `schema_version` | debe |
| RF-27 | Todo subcomando añade una línea a `runs/<run_id>/harness.log`, con volcado línea a línea | debería |
| RF-28 | Los modelos de `canon.py` no exponen forma de modificar ni de borrar una entrada de las seis colecciones que `definitions.md` §2 declara append-only | debe |
| RF-29 | `run_id` se toma de `NOVELA_RUN_ID` si está definida y casa `^r-\d{8}-\d{4}$`; si no, lo genera el CLI. Una variable con formato inválido aborta | debe |
| RF-30 | `novela briefing` escribe `capitulo_sha256` —sha256 de los bytes en disco— en el frontmatter del briefing cuando incrusta `capitulos/NN.md` | debe |
| RF-31 | `novela validar` escribe `qa/NN-validacion.json` también cuando pasa, con `veredicto: aprobado`, `hallazgos: []` y el `capitulo_sha256` del fichero validado | debe |
| RF-32 | `novela aplicar-delta` sale con 1 sin escribir si el sha256 del capítulo en disco difiere del del briefing del `cronista` o del último `qa/NN-validacion.json`, si ese informe tiene hallazgos, o si los briefings de revisión del capítulo en el run del `cronista` no llevan todos el mismo hash | debe |
| RF-33 | Las entradas de `conocimiento`, `linea_temporal` y `conocimiento_lector` admiten `cita` opcional; `aplicar-delta` rechaza el delta si alguna cita presente, incluidas las de `libro_de_hechos`, no es subcadena del cuerpo del capítulo tras normalizar a NFC y colapsar espacios en blanco | debe |
| RF-34 | `novela aplicar-delta` rechaza el delta si sus hilos abiertos y cerrados no son exactamente `hilos_abiertos` e `hilos_cerrados` del frontmatter del capítulo | debe |
| RF-35 | `novela checkpoint` registra el sha256 de cada capítulo cerrado; `novela briefing` sale con 4 sin escribir si alguno ha cambiado o falta respecto a `checkpoints/latest.json` | debe |
| RF-36 | Las fichas `canon/personajes/<id>.md` llevan los campos de `definitions.md` §2.3 en frontmatter YAML, con `secreto` y `coartada_y_cronologia_privada` como campos propios; el modelo rechaza campos desconocidos | debe |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | `novela validar` termina en < 2 s para un capítulo de 4.000 palabras; `novela estado --breve`, en < 500 ms sobre un workspace de 24 capítulos |
| RNF-02 | Consumo de contexto | `--breve` no pasa de 12 líneas; `novela briefing` nunca emite un fichero por encima del `presupuesto_tokens` de su receta |
| RNF-03 | Coste / cuota | Cero llamadas a modelo desde el CLI, la API y la suite de tests. La única salida de red del CLI es el `ScoreSink` |
| RNF-04 | Fiabilidad | Un corte a mitad de `aplicar-delta` deja `estado.db` en el punto anterior al delta; un corte a mitad de cualquier otra escritura deja el fichero anterior intacto |
| RNF-05 | Observabilidad | `manifest.json` de cada run lleva sha de commit, versión de recetas y versiones de canon y plan; los seis scores por capítulo llegan a Langfuse al cerrar |
| RNF-06 | Compatibilidad | No aplica: no hay ninguna novela empezada |
| RNF-07 | Seguridad | El slug se valida antes de tocar disco en CLI y API; ninguna clave en fichero versionado; `ruff` con reglas `S` en pre-commit |

## 8. Interfaces y contratos

**CLI** — todo **nuevo**. Códigos de salida en §5.1.

```
novela nueva <slug> --idea "…" [--capitulos N] [--palabras N] [--subgenero S] [--idioma es]
novela estado <slug> [--breve | --json]
novela briefing <slug> <cap> <agente>
novela validar <slug> <cap>
novela aplicar-delta <slug> <cap>
novela checkpoint <slug> <cap>
novela pendiente <slug>
novela auditar <slug>
novela exportar <slug> --formato md|epub
```

**API** — toda **nueva**, solo lectura. Modelos de respuesta en `backend/novela/dominio/`.

| Método y ruta | Respuesta | Status |
|---|---|---|
| `GET /novelas` | lista de `{slug, cursor}` | 200 |
| `GET /novelas/{slug}/estado` | documento de §7.1 | 200 · 404 · 422 (slug inválido) |
| `GET /novelas/{slug}/capitulos` | índice con frontmatter | 200 · 404 |
| `GET /novelas/{slug}/capitulos/{n}` | markdown del capítulo | 200 · 404 |
| `GET /novelas/{slug}/runs/{run_id}` | `manifest.json` | 200 · 404 |

**Variables de entorno** — **nuevas**. `NOVELA_RUN_ID` fija el run del capítulo (RF-29); `NOVELAS_DIR` reubica la raíz de workspaces, y es como los tests apuntan a los fixtures. `TRACE_TO_LANGFUSE` ya existía y solo activa el sink con el valor exacto `"true"`.

**Esquemas** — todos **nuevos**, en `backend/schemas/`: `config.schema.json`, `state.schema.json`, `canon.schema.json`, `plan-capitulo.schema.json`, `delta.schema.json`, `qa-informe.schema.json`. `delta.schema.json` incluye `resumen: {linea, parrafo, escena}` (§5.0), con `resumen.escena` indexado por id de escena. `canon.schema.json` incluye los campos de `revelaciones[]` y `giros[]` de §5.0.5. Desde la v0.3 (§5.6): `qa-informe.schema.json` gana `capitulo_sha256` opcional; `delta.schema.json` y `state.schema.json` ganan `cita` opcional en las entradas de `conocimiento`, `linea_temporal` y `conocimiento_lector`; `canon.schema.json` define la ficha de personaje con `secreto` y `coartada_y_cronologia_privada`. `checkpoints/NN.json` gana `capitulos_sha256`, un mapa de capítulo a hash.

**Briefing** — **nuevo** frontmatter: `capitulo_sha256` cuando el briefing incrusta el capítulo (RF-30). El agente lo ve y no tiene que hacer nada con él.

**Contrato de agente** — **compatible** con §7.5, con una corrección: el `cronista` escribe solo `estado/deltas/NN.json`; `memoria/resumenes/NN.md` pasa a escribirlo `aplicar-delta`.

**Ficheros del workspace** — el árbol de §4, creado por `novela nueva`. Orden de escritura dentro de un capítulo: briefing → capítulo (agente) → `qa/` → delta (agente) → `estado.db` + `memoria/` → `checkpoints/`.

**Códigos de salida** — **compatible**. Dos usos nuevos de códigos que ya existen: 1 en `aplicar-delta` cuando la custodia no cierra (RF-32), y 4 en `briefing` cuando el sello de capítulos cerrados no coincide (RF-35).

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Las fichas de `personajes/` llevan sus campos en frontmatter (RF-36). El CLI lo lee para ensamblar briefings y no lo escribe nunca |
| `plan/` | Sin cambios de forma. `validar` lo lee para saber qué pistas exigir |
| `estado/estado.db` | Se crea aquí, con el DDL y los triggers de §5.2. Solo lo escribe `aplicar-delta`, en transacción. `conocimiento`, `linea_temporal` y `conocimiento_lector` llevan columna `cita` nula (RF-33) |
| `memoria/` | Lo escribe `aplicar-delta` a partir del delta (§5.0). Reconstruible recorriendo `estado/deltas/*.json` |

`libro_de_hechos` y `conocimiento` son append-only, y aquí dejan de serlo por acuerdo para serlo por trigger.

## 10. Migración y compatibilidad

No aplica: no existe ninguna novela empezada ni ningún `estado.db` previo. Es la única ventana en la que el DDL puede fijarse sin coste de migración, y por eso `meta.schema_version` entra desde la primera versión.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01) `novela nueva demo --idea "x" --capitulos 3 --palabras 9000` crea el árbol de §4 y un `estado.db` con `meta.schema_version`; repetido sobre `demo`, sale con 1 y no modifica ningún fichero
- [ ] **CA-02** (RF-02) `UPDATE` y `DELETE` sobre cada una de las cinco tablas append-only abortan con el mensaje del trigger
- [ ] **CA-03** (RF-03) con el lock tomado por otro proceso, `novela aplicar-delta` sale con 3 y `estado.db` no cambia
- [ ] **CA-04** (RF-04) una excepción inyectada entre escritura y `replace` deja el fichero anterior íntegro; una excepción dentro de la transacción del delta deja `estado.db` en el punto anterior
- [ ] **CA-05** (RF-05) sobre el fixture de 24 capítulos, `--breve` imprime ≤ 12 líneas e incluye cursor, hilos abiertos y palabras
- [ ] **CA-06** (RF-06, RF-26) `--json` valida contra `state.schema.json`, y el esquema commiteado coincide con el generado desde Pydantic
- [ ] **CA-07** (RF-07) `pendiente` sale 0 con capítulos restantes y 1 sobre el fixture terminado, sin stdout
- [ ] **CA-08** (RF-08) el briefing del `escritor` sobre el fixture coincide byte a byte con el esperado (golden dataset, `validators.md` §4.2)
- [ ] **CA-09** (RF-09) property-based sobre canons generados: `misterio.md ⊄ briefing(escritor|editor-estilo, *)`, y el comando sale != 0 sin dejar fichero
- [ ] **CA-10** (RF-10) el briefing del `continuista` contiene literalmente el texto de `canon/misterio.md`
- [ ] **CA-11** (RF-11) un fixture cuyo ensamblado excede el presupuesto hace salir a `briefing` != 0, y `runs/…/briefings/` queda sin el fichero
- [ ] **CA-12** (RF-12) con presupuesto ajustado, el briefing degrada en el orden de §6.5 y conserva íntegras las capas de `canon/` y de estado filtrado
- [ ] **CA-13** (RF-13, RF-27) el primer subcomando de un capítulo crea `manifest.json` con sha y versión de recetas, y `harness.log` contiene ya su línea antes de que el proceso termine
- [ ] **CA-14** (RF-14) property-based: un capítulo con una pista del plan ausente, con un hilo cerrado sin abrir, o con palabras fuera de rango, nunca pasa `validar`
- [ ] **CA-15** (RF-14) `mutmut` sobre `gates.py` no deja mutantes vivos en las comparaciones de rango
- [ ] **CA-16** (RF-15) tras un fallo, `qa/NN-validacion.json` valida contra `qa-informe.schema.json`
- [ ] **CA-17** (RF-16) un delta que intenta un `UPDATE` sobre `libro_de_hechos` deja `estado.db` byte a byte idéntico
- [ ] **CA-18** (RF-17) property-based: ids duplicados entre colecciones y cursor decreciente se rechazan
- [ ] **CA-19** (RF-18) `memoria/resumenes/NN.md` contiene las tres granularidades del delta aplicado
- [ ] **CA-20** (RF-19) property-based: `aplicar(aplicar(e, d), d) == aplicar(e, d)`
- [ ] **CA-21** (RF-20) property-based: `restore(checkpoint(e)) == e`
- [ ] **CA-22** (RF-21) sin `TRACE_TO_LANGFUSE`, `checkpoint` no abre ninguna conexión de red y escribe igual; con `"true"`, el sink recibe los seis scores
- [ ] **CA-23** (RF-22) sobre un fixture con una pista plantada y no pagada, `auditar` la reporta y sale con 1
- [ ] **CA-24** (RF-23) `exportar --formato epub` produce un `.epub` que `ebooklib` reabre con el número de capítulos del fixture
- [ ] **CA-25** (RF-24) `TestClient` recorre los cinco `GET` sobre el fixture con el workspace montado en solo lectura y la suite entera pasa
- [ ] **CA-26** (RF-25) `GET /novelas/..%2F..%2Fetc/estado` devuelve 422 y no toca el disco
- [ ] **CA-27** (RNF-01) `validar` sobre un capítulo de 4.000 palabras termina en < 2 s
- [ ] **CA-28** (RNF-03) un test recorre el árbol de imports del CLI y de la API y falla si aparece cualquier cliente de modelo
- [ ] **CA-29** (RNF-05) el OpenAPI commiteado coincide con el generado; CI falla si no
- [ ] **CA-30** (RF-28) property-based sobre canons generados: ningún método público de las seis colecciones append-only del canon reduce su longitud ni altera una entrada existente
- [ ] **CA-31** (RNF-01) `novela estado --breve` sobre el fixture de 24 capítulos termina en < 500 ms
- [ ] **CA-32** (RNF-07) un fichero versionado que contenga `LANGFUSE_SECRET_KEY` o equivalente hace fallar el pre-commit
- [ ] **CA-33** (RF-29) con `NOVELA_RUN_ID` definida, el briefing se escribe bajo ese run; con un valor que no casa el formato, el comando aborta sin crear directorio
- [ ] **CA-34** (RF-30) el briefing del `continuista` sobre el fixture lleva en su frontmatter el sha256 de `capitulos/NN.md`; el del `escritor`, que no incrusta el capítulo, no lo lleva
- [ ] **CA-35** (RF-31) `validar` sobre un capítulo válido sale con 0 y deja un `qa/NN-validacion.json` que valida contra `qa-informe.schema.json`, con `veredicto: aprobado`, `hallazgos: []` y el hash del fichero
- [ ] **CA-36** (RF-32) property-based: con la cadena íntegra el delta aplica. Cambiar cualquier byte de `capitulos/NN.md` después del briefing del `cronista`, o dejar un briefing de revisión con otro hash, hace salir a `aplicar-delta` con 1 y deja `estado.db` byte a byte idéntico
- [ ] **CA-37** (RF-33) property-based: una cita presente que no es subcadena del cuerpo se rechaza; una que solo difiere en espacios en blanco o en forma de normalización Unicode se acepta; un delta sin citas opcionales aplica
- [ ] **CA-38** (RF-34) un delta que cierra un hilo que el frontmatter no cierra, o al revés, se rechaza sin escribir nada
- [ ] **CA-39** (RF-35) tras el `checkpoint` del capítulo N, cambiar un byte de un capítulo M ≤ N hace salir al `briefing` de N+1 con 4 sin escribir el fichero; sin cambios, el briefing se escribe
- [ ] **CA-40** (RF-36) una ficha fixture se parsea con `secreto` y `coartada_y_cronologia_privada` como campos, y hace round-trip; una ficha con un campo desconocido en el frontmatter se rechaza

## 12. Trazabilidad

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01 | `novela/slices/nueva/test_nueva.py::test_crea_arbol_y_base` | pendiente |
| RF-02 | CA-02 | `novela/plataforma/test_esquema.py::test_append_only_por_trigger` | pendiente |
| RF-03 | CA-03 | `novela/plataforma/test_lock.py::test_lock_ocupado_sale_3` | pendiente |
| RF-04 | CA-04 | `novela/plataforma/test_atomic.py::test_corte_deja_fichero_anterior` | pendiente |
| RF-05 | CA-05 | `novela/slices/estado/test_estado.py::test_breve_acotado` | pendiente |
| RF-06, RF-26 | CA-06 | `tests/test_contratos.py::test_state_schema_al_dia` | pendiente |
| RF-07 | CA-07 | `novela/slices/estado/test_estado.py::test_pendiente_codigos` | pendiente |
| RF-08 | CA-08 | `novela/slices/briefing/test_briefing.py::test_golden_escritor` | pendiente |
| RF-09 | CA-09 | `novela/slices/briefing/test_briefing.py::test_misterio_nunca_en_briefing` | pendiente |
| RF-10 | CA-10 | `novela/slices/briefing/test_briefing.py::test_misterio_incrustado` | pendiente |
| RF-11 | CA-11 | `novela/slices/briefing/test_briefing.py::test_presupuesto_excedido_falla` | pendiente |
| RF-12 | CA-12 | `novela/slices/briefing/test_assemble.py::test_orden_de_degradacion` | pendiente |
| RF-13, RF-27 | CA-13 | `novela/plataforma/test_run.py::test_manifiesto_y_log` | pendiente |
| RF-14 | CA-14, CA-15 | `novela/slices/validacion/test_gates.py::test_gates_property` | pendiente |
| RF-15 | CA-16 | `novela/slices/validacion/test_validacion.py::test_informe_valida` | pendiente |
| RF-16 | CA-17 | `novela/slices/delta/test_delta.py::test_transaccion_todo_o_nada` | pendiente |
| RF-17 | CA-18 | `novela/slices/delta/test_violaciones.py::test_ids_y_cursor_property` | pendiente |
| RF-18 | CA-19 | `novela/slices/delta/test_delta.py::test_renderiza_memoria` | pendiente |
| RF-19 | CA-20 | `novela/slices/delta/test_apply.py::test_idempotencia_property` | pendiente |
| RF-20 | CA-21 | `novela/slices/checkpoint/test_checkpoint.py::test_roundtrip_property` | pendiente |
| RF-21 | CA-22 | `novela/plataforma/test_langfuse.py::test_sink_noop_y_scores` | pendiente |
| RF-22 | CA-23 | `novela/slices/auditoria/test_auditoria.py::test_pista_huerfana` | pendiente |
| RF-23 | CA-24 | `novela/slices/export/test_export.py::test_epub_reabrible` | pendiente |
| RF-24 | CA-25 | `tests/test_api.py::test_cinco_get_en_solo_lectura` | pendiente |
| RF-25 | CA-26 | `tests/test_api.py::test_path_traversal` | pendiente |
| RNF-01 | CA-27 | `novela/slices/validacion/test_validacion.py::test_rendimiento` | pendiente |
| RNF-03 | CA-28 | `tests/test_contratos.py::test_sin_clientes_de_modelo` | pendiente |
| RNF-05 | CA-29 | `tests/test_contratos.py::test_openapi_al_dia` | pendiente |
| RF-28 | CA-30 | `novela/dominio/test_canon.py::test_append_only_sin_trigger` | pendiente |
| RF-29 | CA-33 | `novela/plataforma/test_run.py::test_run_id_de_entorno` | pendiente |
| RF-30 | CA-34 | `novela/slices/briefing/test_briefing.py::test_hash_del_capitulo_incrustado` | pendiente |
| RF-31 | CA-35 | `novela/slices/validacion/test_validacion.py::test_informe_al_pasar` | pendiente |
| RF-32 | CA-36 | `novela/slices/delta/test_custodia.py::test_cadena_property` | pendiente |
| RF-33 | CA-37 | `novela/slices/delta/test_violaciones.py::test_citas_property` | pendiente |
| RF-34 | CA-38 | `novela/slices/delta/test_violaciones.py::test_hilos_contra_frontmatter` | pendiente |
| RF-35 | CA-39 | `novela/slices/briefing/test_briefing.py::test_sello_capitulos_cerrados` | pendiente |
| RF-36 | CA-40 | `novela/dominio/test_canon.py::test_ficha_personaje_estructurada` | pendiente |
| RNF-01 | CA-31 | `novela/slices/estado/test_estado.py::test_breve_rendimiento` | pendiente |
| RNF-02 | CA-05, CA-11 | `novela/slices/estado/test_estado.py::test_breve_acotado`, `briefing/test_briefing.py::test_presupuesto_excedido_falla` | pendiente |
| RNF-04 | CA-04, CA-17 | `novela/plataforma/test_atomic.py::test_corte_deja_fichero_anterior`, `slices/delta/test_delta.py::test_transaccion_todo_o_nada` | pendiente |
| RNF-06 | — | No aplica: no hay ninguna novela empezada | cerrado |
| RNF-07 | CA-26, CA-32 | `tests/test_api.py::test_path_traversal`, `tests/test_contratos.py::test_sin_claves_versionadas` | pendiente |

## 13. Verificación

Métodos de `docs/validators.md` que cubren este cambio:

- **A — tipos y análisis estático** (§3.1, §3.2): `mypy --strict` sobre `backend/`, `ruff` con reglas `S`. La regla dura del borde se hace cumplir desde el principio: ningún `json.load()` suelto, todo dato de disco o de agente entra por un modelo de `dominio/`.
- **T — property-based** (§3.6): obligatorio en `gates.py`, `apply.py`, `violaciones.py` y `assemble.py`, que son exactamente las funciones puras de esta spec. Las cinco propiedades de la tabla de §3.6 son CA-09, CA-14, CA-18, CA-20 y CA-21. La v0.3 añade dos: la cadena de custodia (CA-36) y las citas (CA-37), que son ramas de `delta.py` y por tanto entran en la regla.
- **T — mutación** (§3.7): `mutmut` solo sobre `gates.py` y `apply.py`.
- **T — contrato** (§3.8): `schemas/` contra Pydantic y OpenAPI contra el código, los dos en CI.
- **T — integración** (§3.5): el bucle completo con un agente falso que escribe un capítulo prefabricado desde `tests/fixtures/`. Es lo que hace testable el bucle sin escribir una novela.
- **A — model checking** (§4.10): el test que enumera las transiciones de `cursor.fase × ultimo_paso × intento` y verifica los cinco invariantes de orden. Entra al cerrar la fase 2, cuando los cuatro subcomandos del bucle existen.

**Riesgos aceptados**, además de los de `validators.md` §5:

- La estimación de tokens es una heurística de caracteres. Si se desviara por defecto en algún caso, un briefing podría pasar el presupuesto sin que el CLI lo note. Se acepta porque el error medido ronda el 10% y siempre por exceso; la señal para revisarlo es un fallo de contexto en una invocación que el CLI dio por buena.
- El guardarraíl del secreto compara texto. El `escritor` no recibe el misterio, pero nada impide que una ficha de `plan/capitulos/NN.md` parafrasee la solución, ni que la ficha de personaje del culpable la contenga en su `secreto`: eso es contenido, no ruta, y ningún test lo coge. La v0.3 deja el `secreto` en un campo propio (RF-36) para que se pueda filtrar; filtrarlo, y las sondas de `validators.md` §4.15, son de la spec 0002.
- La custodia (RF-32) prueba que el delta se extrajo de la versión validada, no que esa versión sea la que revisaron el `continuista` y el `lector-suspense`: el `editor-estilo` reescribe entre medias por diseño (`validators.md` §3.9.3). La cadena garantiza que el editor partió de la versión revisada y que la final pasó `validar`; lo que cambió el editor solo lo ven los gates mecánicos.
- Con el sello (RF-35), los niveles 2 y 4 de la política de cuota de `architecture.md` §9 paran el bucle, porque el `editor-estilo` diferido reescribe capítulos cerrados. Se acepta: es el invariante 7 funcionando, y esta spec no construye la degradación. Cómo degradar sin violarlo es una pregunta de la 0002.
- La idempotencia de `aplicar-delta` se prueba sobre deltas generados por Hypothesis, no sobre deltas reales de un `cronista`. El primer acto de la novela de humo es lo que la valida de verdad.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno se toca. Cuatro pasan de estar descritos a estar impuestos por código: 1, 2, 6 y 8. Desde la v0.3, la violación del 7 se detecta (RF-35), aunque no se impide |
| Esquemas | Se crean los seis de `backend/schemas/` y el test de contrato que los mantiene al día. `canon.schema.json` estrena los campos de `revelaciones[]` (§5.0.5). La v0.3 añade los campos de §8: todos opcionales salvo la estructura de la ficha de personaje |
| Contratos de agente | Uno: el `cronista` deja de escribir `memoria/resumenes/NN.md`. Su frontmatter no cambia. La v0.3 añade dos contratos de salida, sin cambiar ningún frontmatter de agente: el `cronista` **puede** traer `cita` en tres colecciones más, y el `arquitecto` **debe** escribir las fichas de personaje en frontmatter (RF-36). El prompt del `arquitecto` está fuera de alcance (§1) y tendrá que reflejarlo cuando exista |
| Docs de referencia (v0.3) | A diferencia de lo corregido en la v0.2, los campos de la v0.3 describen código futuro. Por la regla de `AGENTS.md` se documentan **en el commit que los implementa**, no antes: `architecture.md` §7.1 (`cita` en tres colecciones), §7.3 (`capitulo_sha256`), §4 (`capitulos_sha256` en los checkpoints) y `definitions.md` §2.3 y §4. `validators.md` §3.9.7 y §3.9.8 ya remiten a esta spec |
| Docs de referencia | **Ya corregidos** al aceptar esta spec: todos eran incoherencias entre documentos vigentes, no descripciones de código futuro, así que dejarlos habría sido dejar la referencia contradiciéndose durante toda la implementación. `definitions.md` §2.4 (campos de `revelaciones` y `giros`), §4 (ocho nombres alineados con §7.1, `cursor` a cuatro campos) y §6 (`qa/NN-informe.md` → `qa/NN-<agente>.json`); `architecture.md` §5 y `AGENTS.md` (identificadores, con `hec-` y `esc-` desambiguado), §8 y `AGENTS.md` (aparecen `novela nueva` y `novela auditar`), §7.5 (el `cronista` deja de escribir `memoria/`, que ya contradecía a §6.4 del mismo documento); `domain-knowledge.md` (nodos de estado, ficheros de `qa/` y salidas del `cronista` en los diagramas 3, 4 y 5); `AGENTS.md` y `validators.md` §3.1 (`backend/novela/models/` → `dominio/`); `_plantilla.md` (misma ruta). Nada queda pendiente |
| ADR | Se escribe `docs/adr/0001-orquestador-en-claude-code.md`, que `architecture.md` §3.1 ya nombraba y no existía |
| Frontend | Nada que romper: no existe. La fase 4 le entrega el OpenAPI del que generará sus tipos |

## 15. Alternativas descartadas

- **Un solo subcomando `novela paso`** que hiciera el capítulo entero. Borraría la frontera entre lo determinista y lo que necesita juicio, que es justo lo que `architecture.md` §2.1 protege: el orquestador decide, el CLI ejecuta.
- **Estado en JSON** en vez de SQLite. Ya decidido antes de esta spec y absorbido en §7.1: sin triggers, el append-only depende de que todas las rutas de escritura se acuerden de comprobarlo.
- **Un ORM (SQLModel, SQLAlchemy).** Cuatro subcomandos escriben la base y las consultas son selecciones por id. `sqlite3` de la stdlib no añade dependencia y deja el DDL —que es donde vive el invariante 2— a la vista en un `.sql`.
- **Repositorio por entidad y capa de casos de uso.** `architecture.md` §3.0 fija dos puertos y solo dos; el resto se llama directo.
- **Truncar el briefing al llegar al presupuesto.** Un briefing truncado es un agente que no sabe lo que no sabe: produce un capítulo plausible y contradictorio, que es el fallo más caro de detectar.
- **Que el `cronista` escriba `memoria/`**, como dice hoy §7.5. Ahorra código en el CLI y a cambio convierte un artefacto derivado en texto libre no validado, y hace que reconstruir `memoria/` cueste cuota.
- **Que cada agente registre el hash del capítulo que leyó** (v0.3). Un modelo no calcula un sha256: lo inventaría. Lo registra el CLI en el briefing, que es por donde el texto llega al agente.
- **Normalizar el capítulo antes de hashearlo** (v0.3). Obligaría a decidir qué cambios dejan «el mismo texto», que es justo la pregunta que un hash evita. Con los bytes tal cual, el error posible es parar de más, nunca aplicar de menos.
- **Comprobar la custodia en un subcomando `novela gate`** (v0.3). Ese subcomando decidiría también los gates desde los veredictos, y eso revierte la frontera de la primera alternativa de esta lista. Está planteado en la 0002 y necesita ADR. La cadena de RF-32 es una precondición sobre datos y cabe en `aplicar-delta` sin tocar esa frontera.
- **Cruzar también delta y plan** (v0.3). Decidir si el escritor puede abrir un hilo o plantar una pista fuera del plan es una pregunta de diseño abierta. Delta contra frontmatter no lo es: son dos descripciones del mismo texto.

## 16. Preguntas abiertas

Ninguna. Las cinco que esta spec tuvo en `borrador` se cerraron al pasar a `aceptada`; el
razonamiento de cada una está en `docs/implementation-plans/0001-backend/decisiones-abiertas.md`
hasta que la spec se implemente.

| Pregunta | Decisión |
|---|---|
| ¿`novela nueva` o `novela init`? | **`nueva`**. El CLI ya mezcla verbos, sustantivos y un adjetivo, así que no hay convención que romper, y `/novela-nueva` ya existe en tres documentos |
| ¿El slice `presupuesto/` y `novela budget` entran aquí? | **No**. Spec posterior: sin una ejecución real no hay con qué calibrar los umbrales de §9, y hoy la degradación la decide el orquestador. RF-27 deja la materia prima registrada |
| ¿`run_id` lo genera el CLI o el orquestador? | **Los dos, con precedencia** (RF-29). Cierra `architecture.md` §12.2 y hace deterministas las rutas de `runs/`, que es lo que el golden de CA-08 necesita |
| ¿La fase 4 ahora o al terminar la primera novela? | **Ahora, y la última**. Los modelos de respuesta ya existen desde la fase 1; lo que se gana es establecer CA-25 antes de que exista código que asuma escritura. Los dos `GET` de §12.6 siguen fuera |
| ¿Identificador de escena en el delta desde la fase 2? | **Sí**. Cuesta un campo hoy; añadirlo después exige reprocesar cada capítulo con el `cronista`, que es cuota y además no determinista |

La v0.3 añade §5.6 sin abrir ninguna pregunta: cada decisión que exigía está tomada en el propio texto (hash de bytes sin normalizar, normalización NFC más espacios para las citas, delta contra frontmatter y no contra plan, salida 4 para el sello, forma de la coartada). Lo que sí abría preguntas —obligatoriedad de las citas, filtrado del secreto, invariantes narrativas, `novela gate`— está en `docs/specs/0002-verificacion-a-escala-de-novela.md`, en `borrador`, y no bloquea esta.
