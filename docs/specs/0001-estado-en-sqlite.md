---
spec: 0001
titulo: "Estado narrativo en SQLite en lugar de state.json"
estado: borrador
autor: "arturo.soto"
fecha: 2026-09-21
version: 0.1
afecta: [backend, esquemas, agentes, docs]
depende_de: []
sustituye: []
adr: []
commit: null
---

# 0001 — Estado narrativo en SQLite en lugar de `state.json`

## 1. Propósito y alcance

Sustituir `estado/state.json` por `estado/estado.db` (SQLite, `sqlite3` de la stdlib) como soporte de la rama 4, para que el largo plazo se consulte por índice en vez de parsearse entero y para que el append-only del invariante 2 lo imponga el esquema en vez del código.

**Dentro del alcance**

- Esquema SQL de la rama 4: `cursor`, `linea_temporal`, `personajes`, `conocimiento`, `relaciones`, `objetos`, `libro_de_hechos`, `hilos`, `pistas`, `conocimiento_lector`, `tension_real`, `metricas`, `meta`.
- Append-only mediante triggers `BEFORE UPDATE` / `BEFORE DELETE` con `RAISE(ABORT)` en las cinco colecciones que `docs/definitions.md` declara append-only.
- `novela aplicar-delta` escribe en una única transacción `BEGIN IMMEDIATE` … `COMMIT`.
- `novela estado --json` para recuperar la vista legible que hoy da abrir el fichero.
- Los modelos Pydantic de `backend/novela/dominio/estado.py` y `backend/schemas/state.schema.json` **no cambian**: siguen siendo el contrato de la API (§11.1 de `architecture.md`).
- Sustituir el guardrail `PostToolUse` sobre `state.json` por un `PreToolUse` que deniega cualquier escritura bajo `estado/`.

**Fuera del alcance**

- El índice recuperable y la consulta de contexto por parte de los agentes: es la spec 0002.
- `canon/`, `plan/`, `memoria/`, `capitulos/`, `qa/`, `checkpoints/` y `runs/`: siguen siendo ficheros Markdown y JSON con escritura atómica. Este cambio **no** mete el workspace entero en una base de datos.
- El lock de workspace: `filelock` sobre `estado/state.lock` se mantiene tal cual (ver §4).
- Embeddings. No aparecen en esta spec.

## 2. Problema

`state.json` es un documento monolítico que crece con cada capítulo, y cada operación lo paga entero: `aplicar-delta` reescribe el fichero completo para añadir tres hechos, y `novela briefing` parsea el documento entero para seleccionar las entradas de `libro_de_hechos` que tocan a los personajes presentes en una escena. `architecture.md` §6.4 ya declara la intención correcta —«el largo plazo no se carga, se consulta»— pero sobre un fichero JSON esa consulta es un escaneo lineal en Python, no una consulta.

El append-only de `libro_de_hechos` y `conocimiento` (invariante 2) no está impuesto por la estructura: lo comprueba `aplicar-delta` con una postcondición en tiempo de ejecución (`docs/validators.md` §3.4, `assert nuevo_libro[:len(viejo)] == viejo`) y lo vigila un hook después de escribir. Nada impide estructuralmente que una escritura sustituya el documento; solo se detecta.

Evidencia disponible hoy: ninguna de ejecución, porque `backend/` está vacío y no existe ningún workspace. Esto no es una migración, es la elección del soporte **antes** de escribir el código. Su coste es cero ahora y crece con cada capítulo escrito, y eso es lo que la hace oportuna hoy y no dentro de diez.

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Orquestador | `novela estado --breve` y `aplicar-delta` dejan de depender del tamaño acumulado del estado |
| Agente `cronista` | Sin cambios: sigue escribiendo `estado/deltas/NN.json`, no toca el estado |
| Agente `continuista` | Su briefing recibe las entradas del libro de hechos que le tocan, seleccionadas por consulta indexada |
| Operador humano | Pierde el `cat estado/state.json`; lo recupera con `novela estado --json` |
| Frontend / API | Sin cambios de contrato: `GET /novelas/{slug}/estado` devuelve el mismo modelo Pydantic |

## 4. Contexto y restricciones

**Invariantes que aplican** (de los 8 de `AGENTS.md`):

| Inv. | Hoy | Tras el cambio |
|---|---|---|
| 1 — fuente única de verdad | `estado/state.json` | `estado/estado.db`. El invariante se mantiene; cambia el nombre del soporte |
| 2 — append-only | postcondición en `delta.py` + hook | trigger `RAISE(ABORT)` en la tabla. **Se refuerza**: pasa de comprobado a imposible |
| 6 — escritura atómica (`.tmp` + rename) | aplica a todo fichero, estado incluido | aplica a todo fichero **salvo** el estado, que usa transacción. El invariante se reformula, no se relaja |
| 8 — un proceso por workspace | `filelock` sobre `state.lock` | idéntico. El WAL de SQLite no cubre `capitulos/` ni `qa/`, así que el lock de workspace sigue haciendo falta |

Los invariantes 3, 4, 5 y 7 no se tocan.

**Restricciones técnicas**

- `sqlite3` es stdlib en Python 3.12: **cero dependencias nuevas**.
- Sin SDK de proveedores de modelos. Esta spec no añade ninguna llamada a modelo.
- La API sigue siendo de solo lectura.
- WAL requiere sistema de ficheros local. Los workspaces viven en `novelas/<slug>/` en la máquina que ejecuta el harness; no se soporta workspace en red.

**Supuestos**

- El estado de una novela de 24 capítulos cabe holgadamente en memoria; el motivo del cambio es el coste de selección y la imposición de invariantes, no el volumen.
- Nadie depende hoy de que el estado sea diffable con git: `novelas/` está en `.gitignore`.

**Dependencias**: ninguna. Es la primera spec y no hay código previo que migrar.

## 5. Propuesta

`estado/estado.db`, un único fichero SQLite por workspace, en lugar de `estado/state.json`.

```
novelas/<slug>/estado/
├── estado.db                 # rama 4 — fuente única de verdad
├── estado.db-wal             # WAL de SQLite; efímero
├── state.lock                # filelock, sin cambios
└── deltas/
    └── 01.json               # salida del cronista, sin cambios
```

**Esquema.** Una tabla por colección de la rama 4, con los ids de §5 de `architecture.md` como claves primarias. Abreviado:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
-- ('schema_version', '1.0.0')

CREATE TABLE cursor (
  id INTEGER PRIMARY KEY CHECK (id = 1),   -- fila única
  capitulo INTEGER NOT NULL, fase TEXT NOT NULL,
  ultimo_paso TEXT, intento INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE libro_de_hechos (               -- APPEND-ONLY
  id TEXT PRIMARY KEY, texto TEXT NOT NULL,
  capitulo INTEGER NOT NULL, cita TEXT
);

CREATE TABLE conocimiento (                  -- APPEND-ONLY
  personaje TEXT NOT NULL,
  hecho TEXT NOT NULL REFERENCES libro_de_hechos(id),
  desde_capitulo INTEGER NOT NULL,
  PRIMARY KEY (personaje, hecho)
);
CREATE INDEX idx_conocimiento_hecho ON conocimiento(hecho);

CREATE TABLE personajes (                    -- MUTABLE
  id TEXT PRIMARY KEY, ubicacion TEXT, estado_fisico TEXT,
  estado_emocional TEXT, condicion TEXT NOT NULL,
  objetivo_activo TEXT, ultima_aparicion INTEGER
);
-- linea_temporal, relaciones, objetos, hilos, pistas,
-- conocimiento_lector, tension_real, metricas: analogas
```

**Append-only por trigger**, una pareja por tabla append-only (`libro_de_hechos`, `conocimiento`, `linea_temporal`, `conocimiento_lector`, `tension_real`):

```sql
CREATE TRIGGER libro_de_hechos_no_update BEFORE UPDATE ON libro_de_hechos
BEGIN SELECT RAISE(ABORT, 'libro_de_hechos es append-only'); END;

CREATE TRIGGER libro_de_hechos_no_delete BEFORE DELETE ON libro_de_hechos
BEGIN SELECT RAISE(ABORT, 'libro_de_hechos es append-only'); END;
```

**Atomicidad.** `novela aplicar-delta` abre `BEGIN IMMEDIATE`, aplica el delta entero y hace `COMMIT`. Un fallo a mitad deja el estado en el punto anterior, sin `.tmp` huérfano y sin paso manual de limpieza. Un delta que viole el append-only aborta la transacción completa; la diferencia respecto a hoy no es el rechazo, que ya ocurre, sino que deja de poder violarse por una ruta que no sea `aplicar-delta`.

**Guardrail.** El hook `PostToolUse` sobre `state.json` de `architecture.md` §7.1 pierde sentido —un `.db` no es un documento que se valide contra JSON Schema tras escribirlo— y se sustituye por un `PreToolUse` que **deniega** cualquier `Write` o `Edit` cuya ruta caiga bajo `estado/`. Es un guardrail preventivo en lugar de detectivo, que es el orden que `docs/validators.md` §4.4 pide explícitamente.

**Validación de esquema.** `backend/schemas/state.schema.json` sigue existiendo y sigue generándose desde Pydantic: es el contrato de la respuesta de la API y del test de contratos. Lo que cambia es dónde se valida: antes, el documento completo en cada escritura; ahora, el modelo Pydantic en la frontera (al leer el delta y al serializar para la API) más las restricciones `CHECK`, `NOT NULL` y `REFERENCES` del esquema SQL en cada fila.

**Fases.** Una sola. No hay código previo, así que no hay estado intermedio utilizable que proteger.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `novela aplicar-delta <slug> <cap>` aplica el delta sobre `estado/estado.db` en una única transacción y no deja nada escrito si alguna precondición falla | debe |
| RF-02 | Un `UPDATE` o `DELETE` sobre cualquiera de las cinco tablas append-only aborta con error, venga de donde venga | debe |
| RF-03 | `novela estado <slug> --breve` imprime cursor, hilos abiertos y capítulos hechos sin cargar el libro de hechos | debe |
| RF-04 | `novela estado <slug> --json` imprime el estado completo serializado con el mismo modelo Pydantic que devuelve la API | debe |
| RF-05 | `novela briefing <slug> <cap> continuista` selecciona las entradas de `libro_de_hechos` que referencian a los ids presentes en el capítulo, mediante consulta SQL indexada | debe |
| RF-06 | `novela checkpoint <slug> <cap>` deja en `checkpoints/NN.json` un volcado suficiente para restaurar `estado.db` desde cero | debe |
| RF-07 | `GET /novelas/{slug}/estado` devuelve el mismo modelo de respuesta que antes del cambio | debe |
| RF-08 | El hook `PreToolUse` deniega cualquier escritura de un agente bajo `estado/` | debe |
| RF-09 | `novela auditar <slug>` detecta pistas huérfanas e hilos sin cerrar con una consulta, no con un recorrido en Python | debería |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | `novela estado --breve` termina en < 200 ms con 24 capítulos aplicados |
| RNF-02 | Consumo de contexto | Sin cambio en los techos de §6.5 de `architecture.md`. Esta spec no reduce tokens: reduce coste de selección y refuerza invariantes |
| RNF-03 | Coste / cuota | Cero llamadas a modelo añadidas. Cero dependencias añadidas (`sqlite3` es stdlib) |
| RNF-04 | Fiabilidad | Un corte a mitad de `aplicar-delta` deja `estado.db` en el estado anterior al delta; el checkpoint anterior sigue siendo válido |
| RNF-05 | Observabilidad | Sin scores nuevos. El `manifest.json` del run registra el `schema_version` de la tabla `meta` |
| RNF-06 | Compatibilidad | No aplica: no hay novelas en curso (ver §10) |
| RNF-07 | Seguridad | `estado.db` vive dentro del workspace; ninguna ruta sale de `novelas/<slug>/`. La API sigue sin verbo de escritura |

## 8. Interfaces y contratos

- **CLI** — **nuevo**: `novela estado <slug> --json` (código 0; 2 si el workspace no tiene `estado.db`). **Compatible**: `estado --breve`, `briefing`, `validar`, `aplicar-delta`, `checkpoint`, `pendiente`, `auditar` y `exportar` conservan firma y códigos de salida.
- **API** — **compatible**: `GET /novelas/{slug}/estado` mantiene ruta, modelo de respuesta y status codes. Cambia solo de dónde se leen los datos.
- **Esquemas** — **compatible**: `backend/schemas/state.schema.json` se sigue generando desde Pydantic y sigue siendo el contrato de la API. **Nuevo**: `backend/novela/plataforma/esquema.sql` con el DDL, versionado.
- **Contrato de agente** — **compatible**: ningún agente leía ni escribía `state.json`. El `cronista` sigue escribiendo `estado/deltas/NN.json`. Lo que cambia es el guardrail que lo impide (`PreToolUse` en vez de `PostToolUse`).
- **Ficheros del workspace** — **ruptura**: `estado/state.json` deja de existir; aparece `estado/estado.db`. Ver §10.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Sin cambios. Markdown versionado |
| `plan/` | Sin cambios. Markdown versionado |
| `estado/state.json` | **Sustituido** por `estado/estado.db`. Mismos campos, misma ontología, mismos ids. Sigue siendo la única escritura de `aplicar-delta` |
| `memoria/` | Sin cambios. Sigue en `memoria/resumenes/NN.md`, derivada y reconstruible |

`libro_de_hechos`, `conocimiento`, `linea_temporal`, `conocimiento_lector` y `tension_real` siguen siendo append-only, ahora por trigger.

## 10. Migración y compatibilidad

No aplica en el sentido habitual: `backend/` está vacío y no existe ningún workspace, así que no hay datos que migrar. Es una elección de soporte previa a la implementación.

Si esta spec se acepta después de que exista alguna novela, hace falta `novela migrar <slug>`: lee `state.json`, crea `estado.db` y conserva el JSON como `estado/state.json.bak` sin borrarlo. La reversión es el mismo subcomando al revés, y es barata mientras el esquema SQL siga siendo un reflejo uno a uno de los modelos Pydantic.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01) Aplicar un delta válido sobre un workspace de fixture deja las filas nuevas y el cursor avanzado; aplicar un delta cuya última operación viola una `CHECK` deja `estado.db` byte a byte como antes
- [ ] **CA-02** (RF-02) `UPDATE libro_de_hechos SET texto=...` y `DELETE FROM libro_de_hechos` lanzan `sqlite3.IntegrityError`; property-based sobre secuencias de deltas generadas: ninguna reduce el número de filas de una tabla append-only
- [ ] **CA-03** (RF-03, RNF-01) `novela estado --breve` sobre el fixture de 24 capítulos termina en < 200 ms y su consulta no menciona `libro_de_hechos`
- [ ] **CA-04** (RF-04, RF-07) El JSON de `novela estado --json` y el cuerpo de `GET /novelas/{slug}/estado` validan contra `backend/schemas/state.schema.json` y son iguales campo a campo
- [ ] **CA-05** (RF-05) El briefing del `continuista` para un capítulo con 3 personajes y 2 objetos contiene exactamente las entradas del libro de hechos que referencian esos 5 ids, y ninguna más
- [ ] **CA-06** (RF-06, RNF-04) Borrar `estado.db` y restaurar desde `checkpoints/NN.json` reproduce un estado igual campo a campo al del checkpoint
- [ ] **CA-07** (RF-08) El hook rechaza un `Write` simulado sobre `estado/estado.db` y sobre `estado/deltas/../estado.db`
- [ ] **CA-08** (RNF-03) El lockfile tras el cambio no contiene ninguna dependencia que no estuviera antes
- [ ] **CA-09** El arranque comprueba `PRAGMA journal_mode` y falla con mensaje explícito si WAL no queda activo

## 12. Trazabilidad

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01 | `backend/novela/slices/delta/test_delta.py::test_transaccion_atomica` | pendiente |
| RF-02 | CA-02 | `backend/novela/slices/delta/test_delta.py::test_append_only_property` | pendiente |
| RF-03 | CA-03 | `backend/novela/slices/estado/test_estado.py::test_breve_no_carga_hechos` | pendiente |
| RF-04, RF-07 | CA-04 | `backend/tests/test_contratos.py::test_estado_json_igual_api` | pendiente |
| RF-05 | CA-05 | `backend/novela/slices/briefing/test_briefing.py::test_seleccion_hechos` | pendiente |
| RF-06 | CA-06 | `backend/novela/slices/checkpoint/test_checkpoint.py::test_restaurar` | pendiente |
| RF-08 | CA-07 | `backend/tests/test_hooks.py::test_deniega_escritura_estado` | pendiente |

## 13. Verificación

Cubre, de `docs/validators.md`:

- **§3.6 property-based** — obligatorio aquí: el cambio toca las ramas de `delta.py`. CA-02 es property-based sobre secuencias de deltas generadas, no de ejemplo.
- **§3.4 invariantes append-only** — mejora de clase. Hoy es una obligación de prueba descargada en tiempo de ejecución (`assert nuevo[:n] == viejo`); con el trigger pasa a ser una restricción del esquema, que se cumple para toda entrada por construcción y no solo en el momento en que se ejecuta el assert.
- **§3.3 symbolic execution** — sigue diferida y sigue necesitando el mismo refactor previo: extraer `aplicar(estado, delta) -> estado` como función pura. Este cambio no lo hace más fácil ni más difícil.
- **§4.4 guardrails** — la fila «Hook `PostToolUse` sobre `state.json`» de esa tabla se sustituye por «Hook `PreToolUse` sobre `estado/**`».
- **§4.3 sandboxed execution** — la línea «`state.json` solo lo escribe `novela aplicar-delta`» se mantiene con el nombre nuevo.

**Riesgos aceptados**

1. **El estado deja de ser legible con `cat`.** Mitigado con `novela estado --json`, no eliminado: depurar un workspace roto pasa por el CLI o por `sqlite3`.
2. **Las opciones de compilación de SQLite dependen del binario de Python.** No afecta a esta spec, que solo usa SQL básico, pero sí a la 0002 si usa FTS5; el arranque consulta `pragma_compile_options` y lo reporta.
3. **La validación de esquema deja de ser un solo punto.** Antes un JSON Schema cubría el documento entero en cada escritura; ahora se reparte entre las restricciones SQL y Pydantic en la frontera. Un campo que se añada a Pydantic y no al DDL no se detecta hasta el test de contratos, que por eso pasa a ser obligatorio en CI.
4. **WAL no funciona en sistemas de ficheros en red.** Aceptado: el harness corre en local.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | **Sí**: el 1 cambia de soporte, el 2 se refuerza, el 6 se reformula para excluir el estado, el 8 no se toca. Requiere decisión explícita antes de implementar |
| Esquemas | `state.schema.json` sigue generándose desde Pydantic; se añade `plataforma/esquema.sql`. `docs/definitions.md` §4 y §6 quedan desfasados |
| Contratos de agente | Ninguno cambia de `tools`. Cambia el hook que los vigila |
| Docs de referencia | `architecture.md`: §1, §2 (stack), §3.1 (árbol), §4 (workspace), §5 (escritura atómica), §6.4, §7.1, §11.1. `definitions.md`: rama 4, §6 y §10 `esquema_validado`. `domain-knowledge.md`: diagramas de líneas 58, 252 y 332-333. `validators.md`: fila 12 de la tabla de proceso, §4.3 y §4.4. `AGENTS.md`: tabla de ramas e invariantes 1, 2 y 6. `CLAUDE.md`: menciones a `state.json` y al hook |
| Frontend | Ninguno: consume la API, y la API no cambia de contrato |

## 15. Alternativas descartadas

- **Dejar `state.json` y optimizar la selección en Python.** Es lo que hay hoy. Funciona a 24 capítulos y no impone el append-only. Descartada porque el coste de cambiar de soporte es cero ahora y creciente después.
- **Un fichero JSON por colección** (`estado/libro_de_hechos.json`, …). Reduce la reescritura pero no da índice, ni transacción entre colecciones, ni append-only estructural. Media solución con la misma complejidad.
- **JSONB en SQLite, una fila por documento.** Conserva la forma actual pero vuelve a escanear para seleccionar. Si el destino es SQLite, el esquema relacional no cuesta más.
- **Postgres.** Un servicio que arrancar y mantener para un fichero por novela en una máquina de desarrollo. Contradice «un proceso por workspace» sin dar nada a cambio.
- **Un ADR en lugar de esta spec.** El ADR procede cuando revertir sea caro, es decir cuando existan novelas. Hoy basta el §15 de esta spec; al pasar a `aceptada` se abre `docs/adr/0002-estado-en-sqlite.md`.

## 16. Preguntas abiertas

- [ ] ¿Se acepta reformular el invariante 6 para que la escritura atómica del estado sea una transacción y no `.tmp` + rename? — arturo.soto
- [ ] ¿`checkpoints/NN.json` sigue siendo JSON, o pasa a ser una copia de `estado.db` con `VACUUM INTO`? JSON es inspeccionable y reconstruible; la copia binaria es exacta y de una línea. — arturo.soto
- [ ] ¿Se mantiene `state.lock` con `filelock`, o se delega el bloqueo a `BEGIN IMMEDIATE`? Recomendado mantenerlo: el lock protege el workspace entero, no solo el estado. — arturo.soto
