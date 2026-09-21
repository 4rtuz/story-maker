---
spec: 0002
titulo: "Índice recuperable híbrido: exacto, léxico y semántico"
estado: borrador
autor: "arturo.soto"
fecha: 2026-09-21
version: 0.2
afecta: [backend, agentes, docs]
depende_de: [0001]
sustituye: []
adr: []
commit: null
---

# 0002 — Índice recuperable híbrido: exacto, léxico y semántico

## 1. Propósito y alcance

Materializar `indice_recuperable` (rama 5 de `docs/definitions.md`) sobre la base SQLite de la spec 0001, con tres vías de búsqueda —exacta por id, léxica por palabra y semántica por embeddings locales— fusionadas en un único resultado, expuesto como subcomando acotado del CLI.

Revierte la decisión de `architecture.md` §12.4, que posponía el índice hasta unas 40 capítulos.

**Dentro del alcance**

- **Exacta**: tabla `menciones(entidad_id, escena_id, capitulo)`, escrita por el `cronista` como parte del delta.
- **Léxica**: tabla virtual FTS5 sobre los resúmenes por escena de `memoria/resumenes/NN.md`.
- **Semántica**: tabla `escenas_vec` con el embedding de cada resumen de escena, calculado por un modelo **local**, y búsqueda por producto escalar en numpy.
- **Fusión**: los aciertos exactos van primero sin fusionar; el resto se combina con Reciprocal Rank Fusion.
- Subcomando `novela recuperar` con tope de resultados y de tokens, y `novela reindexar` para reconstruir las dos capas derivadas.
- Registro de cada recuperación en `runs/<run_id>/briefings/NN-<agente>-recuperado.md`.

**Fuera del alcance**

- Sustituir capas del briefing. El `escritor` sigue recibiendo el capítulo anterior completo y los resúmenes por receta; la recuperación **añade** una vía de consulta, no reemplaza el ensamblado.
- Cualquier cambio en el techo de 100.000 tokens de `architecture.md` §6.5.
- Índices vectoriales aproximados (`sqlite-vec`, HNSW, IVF). Ver §15.
- Reranking con un modelo de cross-encoder. La fusión es aritmética.

## 2. Problema

Hay una clase de pregunta que el sistema hoy no puede responder de forma barata: la consulta puntual y retrospectiva sobre un detalle concreto. «¿En qué escena se vio por última vez `obj-011`?», «¿en qué capítulos aparece la casa del faro?», «¿dónde se habló de una llave oxidada?». `docs/definitions.md` ya la nombra al definir `indice_recuperable`.

Hoy solo hay tres caminos y los tres son malos: cargar los capítulos afectados en el briefing (rompe el presupuesto de la receta), pedir al agente que los lea por su cuenta (rompe el invariante 7 y el principio 7 de `architecture.md`), o conformarse con los resúmenes, que por construcción han perdido el detalle que la pregunta busca.

Las tres preguntas del párrafo anterior no son la misma pregunta, y es la razón de que la solución sea híbrida: la primera trae un id y se responde exactamente; la segunda trae un nombre propio y se responde por palabra; la tercera trae una descripción que probablemente no aparece literalmente en ningún resumen, y solo se responde por semejanza.

**Sobre el ahorro de tokens, que es la motivación declarada de este cambio, conviene ser exacto:** el reparto de `architecture.md` §6.5 da unos 24.000 tokens sobre un presupuesto de 60.000 para el briefing del `escritor` en el capítulo 12, y la única capa que crece con la novela lo hace a unos 25 tokens por capítulo. A 24 capítulos no hay presión de contexto que resolver. El índice se justifica por **capacidad de consulta**, no por ahorro; y si se usa mal —agentes consultando libremente— **aumenta** el consumo, porque cada resultado entra en la ventana del agente además del briefing, y el agente no tiene forma de saber cuándo parar. De ahí que la propuesta acote la recuperación en el CLI en lugar de dar a los agentes una herramienta de búsqueda abierta (§5, y la pregunta abierta de §16).

Evidencia: ninguna de ejecución. `backend/` está vacío y no hay novelas escritas. Esto es una decisión de diseño previa, no la respuesta a un fallo observado, y por tanto se acepta o se descarta por argumento.

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Orquestador | Añade un paso opcional al bucle; no cambia el orden ni los gates |
| Agente `cronista` | Su delta incluye ahora las menciones por escena. Es trabajo de extracción, que es lo que ya hace |
| Agente `continuista` | Consumidor principal: verificar contra hechos es exactamente consultar detalle retrospectivo |
| Agente `escritor` | Consumidor secundario y el más delicado: toda recuperación suya debe seguir excluyendo `canon/misterio.md` (invariante 3) |
| Operador humano | `novela recuperar` sirve también para auditar a mano |

## 4. Contexto y restricciones

**Invariantes que aplican**

| Inv. | Cómo lo condiciona |
|---|---|
| 3 — el misterio es secreto | La recuperación es una vía nueva por la que el secreto puede llegar al `escritor`. Ninguna de las tres capas indexa `canon/misterio.md`, y `novela recuperar` aplica el mismo aborto que `novela briefing` (§6.3 de `architecture.md`) |
| 5 — el contexto vive en disco | Se cumple: el índice está en `estado.db` y cada recuperación se escribe en `runs/` |
| 7 — no se reescriben capítulos anteriores | Sin cambio. El índice es de lectura |
| 1, 2 | Sin cambio: `menciones` es append-only y la escribe `aplicar-delta` |

También condiciona, sin ser invariante, el **principio 7** de `architecture.md` («contexto mínimo suficiente por invocación») y la regla de `AGENTS.md`: «lee solo el briefing y las rutas listadas dentro de él. No explores el workspace por tu cuenta». Una herramienta de búsqueda libre en manos de un agente contradice las dos; un subcomando con tope, no.

**Restricciones técnicas**

- **La regla «nunca añadir un proveedor de modelos, un gateway o un SDK de API de modelos» de `AGENTS.md` se respeta.** El modelo de embeddings corre en local, sin red y sin clave: no es un proveedor ni un gateway. Merece decirlo explícitamente porque es el punto donde esta spec se acerca más a esa regla. La vía prohibida —Voyage, OpenAI, Cohere— queda descartada en §15, y además no existe alternativa dentro de la suscripción: Anthropic no ofrece endpoint de embeddings.
- **Añade una dependencia**, que es lo que distingue esta spec de la 0001. Es el coste principal a aceptar o rechazar. Ver §16.
- FTS5 debe estar compilado en el binario de SQLite de Python. Se comprueba con `SELECT 1 FROM pragma_compile_options WHERE compile_options = 'ENABLE_FTS5'` y se falla con mensaje explícito si no está.
- La API sigue siendo de solo lectura; si expusiera la recuperación, sería con `GET`.

**Supuestos**

- Los ids de `architecture.md` §5 son canónicos y estables, y el `cronista` los usa de forma consistente al extraer el delta. Si este supuesto cae, la capa exacta es inútil y la spec se revisa entera.
- Una novela de 24 capítulos tiene del orden de 200 escenas. Es el dato que decide §15: sobre 200 vectores no hace falta índice vectorial ninguno.
- El texto está en español. Descarta cualquier modelo de embeddings monolingüe en inglés, que es la mayoría de los pequeños.

**Dependencias**: spec 0001 implementada.

## 5. Propuesta

Tres capas, de la exacta a la aproximada, un solo punto de entrada, y una regla de fusión.

### 5.1 Capa exacta — `menciones`

El `cronista` ya recorre el capítulo aprobado para extraer el delta. Emite además, por cada entidad citada, la escena en que aparece:

```sql
CREATE TABLE menciones (                     -- APPEND-ONLY
  entidad_id TEXT NOT NULL,                  -- per-…, obj-…, esc-…, pis-…, hil-…
  escena_id  TEXT NOT NULL,                  -- esc-07-2
  capitulo   INTEGER NOT NULL,
  PRIMARY KEY (entidad_id, escena_id)
);
CREATE INDEX idx_menciones_entidad ON menciones(entidad_id);
```

«¿Dónde se mencionó `obj-011`?» es un `SELECT` por índice que devuelve ids de escena, no prosa: una línea por resultado. Es la consulta que `definitions.md` nombra, resuelta sin aproximación y sin modelo.

### 5.2 Capa léxica — FTS5

Para la pregunta con nombre propio pero sin id, una tabla virtual poblada desde los resúmenes por escena de `memoria/resumenes/NN.md`:

```sql
CREATE VIRTUAL TABLE resumenes_fts USING fts5(
  escena_id UNINDEXED, capitulo UNINDEXED, texto,
  tokenize = "unicode61 remove_diacritics 2"
);
```

`remove_diacritics 2` es lo que hace que «faro» encuentre «Faró» y que la búsqueda no dependa de cómo acentuó el resumen el `cronista`. El ranking es `bm25()`.

### 5.3 Capa semántica — embeddings locales

Un vector por escena, sobre el mismo texto que indexa FTS5:

```sql
CREATE TABLE escenas_vec (
  escena_id TEXT PRIMARY KEY,
  capitulo  INTEGER NOT NULL,
  modelo    TEXT NOT NULL,                   -- nombre y revisión, ver abajo
  dim       INTEGER NOT NULL,
  vector    BLOB NOT NULL                    -- float32 little-endian, dim valores
);
```

**Modelo.** Local, multilingüe y pequeño. Propuesta: `intfloat/multilingual-e5-small` vía `fastembed` — ONNX Runtime, sin torch, 384 dimensiones, unos 120 MB. Tiene un detalle que hay que respetar o los resultados salen mudos: e5 espera el prefijo `query: ` en la consulta y `passage: ` en lo indexado. La alternativa más ligera es `model2vec` con `potion-multilingual-128M`: embeddings estáticos, inferencia en numpy puro, sin ONNX, más rápido y de menor calidad. Queda como pregunta abierta en §16.

**Búsqueda.** Producto escalar sobre la matriz de vectores normalizados. Con ~200 escenas de 384 dimensiones son 200×384 floats, unos 300 KB: `np.load` del BLOB completo y un `matmul` resuelven la consulta en microsegundos. No hay índice vectorial y no hace falta (§15).

**Reproducibilidad.** La inferencia de embeddings es determinista: mismos pesos y mismo texto dan el mismo vector, no hay muestreo. Lo que rompe la comparabilidad es **cambiar de modelo**, y sobre todo mezclar vectores de dos modelos en la misma tabla, que no falla: devuelve un ranking sin sentido. Por eso `modelo` está en cada fila, la versión vigente está en la tabla `meta` y en `runs/<run_id>/manifest.json`, y `novela recuperar` **falla** si encuentra en `escenas_vec` un modelo distinto del instalado, en vez de buscar con lo que haya.

### 5.4 Fusión

Los aciertos exactos de `menciones` **no se fusionan**: son exactos, van primero y en orden de capítulo. La fusión solo ordena lo aproximado, con Reciprocal Rank Fusion sobre las dos listas restantes:

```python
# rrf: una escena que sale 3ª en léxico y 7ª en semántico puntúa 1/63 + 1/67
puntuacion = sum(1 / (60 + rango) for rango in rangos_por_capa)
```

Es una suma sobre rangos, no sobre puntuaciones: no hay que normalizar `bm25()` contra un coseno, que es donde suelen torcerse estas fusiones, y no hay pesos que ajustar. `k = 60` es el valor habitual y se deja fijo hasta que haya una medición que justifique otro.

### 5.5 Punto de entrada

```
novela recuperar <slug> --entidad obj-011 [--max-resultados 20]
novela recuperar <slug> --texto "llave oxidada" [--capas lexica,semantica]
                        [--max-resultados 10] [--max-tokens 2000]
novela reindexar <slug> [--solo lexica|semantica]
```

Devuelve Markdown: una línea por resultado con `escena_id`, capítulo, capa de procedencia y el fragmento. **Falla —no trunca en silencio—** si el resultado supera `--max-tokens`, igual que `novela briefing` (§6.5 de `architecture.md`). El valor por defecto sale del margen sin asignar de la receta del agente, no del techo total.

Cada invocación escribe `runs/<run_id>/briefings/NN-<agente>-recuperado.md` con la consulta, las capas usadas, el modelo vigente y el resultado exacto. Sin eso el contexto de una invocación deja de ser auditable, y se pierde la razón por la que los briefings existen como fichero (§6.1 y §10.3 de `architecture.md`).

**Quién consulta.** El orquestador, no el agente. El agente declara en su informe de QA qué no pudo verificar; el orquestador recupera y lo reinyecta en el briefing del reintento. Los agentes no reciben una herramienta de búsqueda: `tools` sigue restringido en su frontmatter y `novela recuperar` no está entre las suyas. Es lo que mantiene verificable el techo de §6.5 antes de la invocación. La alternativa queda abierta en §16.

### 5.6 Fases

1. **Exacta.** `menciones` y `--entidad`. Utilizable por sí sola, cero dependencias, cubre la consulta que `definitions.md` nombra.
2. **Léxica.** FTS5 y `--texto`. Sigue sin dependencias.
3. **Semántica.** `escenas_vec`, el modelo local y la fusión. Es la única fase que añade dependencia, y la única que conviene medir antes de dar por buena: si sobre las consultas reales no aporta resultados que la fase 2 no diera, se retira.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `novela aplicar-delta` inserta en `menciones` una fila por pareja (entidad, escena) declarada en el delta del `cronista` | debe |
| RF-02 | `novela recuperar --entidad <id>` devuelve las escenas que mencionan ese id, ordenadas por capítulo, sin abrir ningún fichero de `capitulos/` | debe |
| RF-03 | `novela recuperar` falla con código distinto de 0 si el resultado supera `--max-tokens`, sin truncar ni emitir resultados parciales | debe |
| RF-04 | Cada invocación de `novela recuperar` escribe consulta, capas, modelo y resultado en `runs/<run_id>/briefings/` | debe |
| RF-05 | `novela recuperar` aborta si el material recuperado procede de `canon/misterio.md`, con el mismo mecanismo que `novela briefing` | debe |
| RF-06 | `novela recuperar --texto` consulta las capas léxica y semántica y las fusiona con RRF; los aciertos exactos de `menciones`, si los hay, van antes y sin fusionar | debe |
| RF-07 | `novela reindexar` reconstruye `resumenes_fts` y `escenas_vec` desde `memoria/resumenes/` sin tocar el resto del estado | debe |
| RF-08 | `novela recuperar` falla si el `modelo` de alguna fila de `escenas_vec` no coincide con el modelo instalado, indicando que hay que reindexar | debe |
| RF-09 | Ningún agente tiene `novela recuperar` entre sus `tools`; la recuperación la ejecuta el orquestador | debe |
| RF-10 | El arranque comprueba que FTS5 está disponible y falla con mensaje explícito si no | debe |
| RF-11 | `--capas` permite pedir un subconjunto de capas, para poder medir el aporte de la semántica por separado | debería |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | `novela recuperar --entidad` en < 100 ms y `--texto` con las tres capas en < 1 s sobre un fixture de 24 capítulos, incluida la carga del modelo |
| RNF-02 | Consumo de contexto | Una recuperación por reintento y capítulo no añade más de 2.000 tokens al briefing, y se cuenta contra el mismo `presupuesto_tokens` de la receta |
| RNF-03 | Coste / cuota | Cero llamadas a la API de ningún modelo. El cálculo de embeddings es local y no consume cuota. **Una dependencia nueva** (`fastembed` o `model2vec`) más su fichero de modelo |
| RNF-04 | Fiabilidad | Las capas léxica y semántica son derivadas: si se corrompen, `novela reindexar` las reconstruye sin gastar cuota. `menciones` no es derivada y se restaura del checkpoint |
| RNF-05 | Observabilidad | El `manifest.json` del run registra el modelo de embeddings vigente y cuántas recuperaciones hubo por capítulo. Una cifra que crece capítulo a capítulo es la señal de que el briefing está mal dimensionado |
| RNF-06 | Compatibilidad | Una novela indexada con un modelo y consultada con otro **falla**, no degrada |
| RNF-07 | Seguridad | Ninguna de las tres capas contiene texto procedente de `canon/misterio.md`. El modelo corre en local: no sale texto de la máquina |

## 8. Interfaces y contratos

- **CLI** — **nuevo**: `novela recuperar <slug>` (`--entidad` | `--texto`, `--capas`, `--max-resultados`, `--max-tokens`; código 0 con resultados, 1 sin resultados, 3 si excede el tope, 4 si el modelo no coincide) y `novela reindexar <slug> [--solo …]`.
- **API** — **sin cambios**. Si el panel llegara a necesitarlo, sería un `GET`.
- **Esquemas** — **nuevo**: `menciones`, `resumenes_fts` y `escenas_vec` en `plataforma/esquema.sql`; bloque `menciones[]` en `backend/schemas/delta.schema.json`. **Ruptura** del esquema de delta: se declara requerido y posiblemente vacío, que falla ruidosamente si el `cronista` lo ignora, en vez de opcional, que falla en silencio.
- **Dependencias** — **nuevo**: `fastembed` (ONNX Runtime) o `model2vec` (numpy), a decidir en §16, más el fichero de modelo. Es la primera dependencia de inferencia del proyecto y conviene que se vea en el `pyproject.toml` como tal.
- **Contrato de agente** — **ruptura** en el `cronista`: su contrato de salida gana un campo. Es un cambio de prompt, así que no lleva TDD (`AGENTS.md`) y se valida con la novela de humo de 3 capítulos.
- **Ficheros del workspace** — **nuevo**: `runs/<run_id>/briefings/NN-<agente>-recuperado.md`.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Sin cambios. `canon/misterio.md` explícitamente **no** se indexa en ninguna capa |
| `plan/` | Sin cambios |
| `estado/` (spec 0001) | **Nuevas tablas**: `menciones` (append-only, la escribe `aplicar-delta`), `resumenes_fts` y `escenas_vec` (derivadas, las escribe `reindexar`) |
| `memoria/` | Sin cambios de formato. Es la fuente de las dos capas derivadas, que por tanto son derivadas de una derivada y reconstruibles con `novela reindexar` |

Que dos tablas derivadas vivan en el mismo fichero que la fuente única de verdad es una tensión con la rama 5 de la ontología, donde `memoria/` es reconstruible y `estado/` no. Se acepta porque la alternativa —un segundo fichero SQLite— duplica conexiones y locks para no ganar nada: lo derivado se distingue por tabla y `novela reindexar` lo reconstruye sin tocar el resto.

## 10. Migración y compatibilidad

No aplica: no hay novelas en curso. Si las hubiera, `menciones` nacería vacía para los capítulos ya escritos y la recuperación exacta solo cubriría los nuevos; repoblarla exige pasar el `cronista` por los capítulos anteriores, que cuesta cuota y no corrompe nada. Las capas léxica y semántica sí se reconstruyen completas desde `memoria/`, gratis.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01) Aplicar un delta con 4 menciones deja 4 filas en `menciones`; reaplicar el mismo delta no duplica filas y no aborta
- [ ] **CA-02** (RF-02) `novela recuperar --entidad obj-011` sobre el fixture devuelve exactamente las escenas que lo mencionan, y el proceso no abre ningún fichero de `capitulos/`
- [ ] **CA-03** (RF-03) Con `--max-tokens 10` el comando sale con código 3 y no imprime resultados parciales
- [ ] **CA-04** (RF-04) Tras una recuperación existe `runs/<run_id>/briefings/NN-<agente>-recuperado.md` y su contenido es byte a byte lo que se imprimió, con el modelo vigente anotado
- [ ] **CA-05** (RF-05) Con un `canon/misterio.md` marcado con un centinela, ninguna capa devuelve el centinela, y el intento de indexarlo aborta
- [ ] **CA-06** (RF-06) `--texto "faro"` encuentra «Faró» por la capa léxica; `--texto "una llave que no abre nada"` encuentra la escena cuyo resumen habla de «el cerrojo forzado» sin compartir ninguna palabra, por la capa semántica
- [ ] **CA-07** (RF-06) La fusión es reproducible: dos ejecuciones sobre el mismo índice devuelven el mismo orden. Una escena con acierto exacto aparece antes que cualquier resultado fusionado
- [ ] **CA-08** (RF-07) Borrar `resumenes_fts` y `escenas_vec` y ejecutar `novela reindexar` reproduce los mismos resultados y el mismo orden que antes del borrado
- [ ] **CA-09** (RF-08, RNF-06) Con una fila de `escenas_vec` cuyo `modelo` no coincide con el instalado, `novela recuperar --texto` sale con código 4 y no devuelve resultados
- [ ] **CA-10** (RF-09) Ningún fichero de `.claude/agents/` declara `novela recuperar`; un test recorre los frontmatter y lo comprueba
- [ ] **CA-11** (RNF-02) El briefing de un reintento con una recuperación incluida sigue bajo el `presupuesto_tokens` de la receta
- [ ] **CA-12** (RNF-03) La suite completa sigue corriendo sin red: el modelo se resuelve desde caché local y un test lo ejecuta con la red cortada

## 12. Trazabilidad

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01 | `backend/novela/slices/delta/test_delta.py::test_menciones_idempotente` | pendiente |
| RF-02 | CA-02 | `backend/novela/slices/recuperar/test_recuperar.py::test_por_entidad` | pendiente |
| RF-03 | CA-03 | `backend/novela/slices/recuperar/test_recuperar.py::test_tope_falla` | pendiente |
| RF-05 | CA-05 | `backend/tests/test_adversario.py::test_no_fuga_por_recuperacion` | pendiente |
| RF-06 | CA-06, CA-07 | `backend/novela/slices/recuperar/test_fusion.py::test_rrf` | pendiente |
| RF-07 | CA-08 | `backend/novela/slices/recuperar/test_recuperar.py::test_reindexar` | pendiente |
| RF-08 | CA-09 | `backend/novela/slices/recuperar/test_recuperar.py::test_modelo_distinto_falla` | pendiente |
| RF-09 | CA-10 | `backend/tests/test_contratos.py::test_tools_por_agente` | pendiente |

## 13. Verificación

De `docs/validators.md`:

- **§4.4 guardrails** — se añade una fila: «`novela recuperar` aborta si el material procede de `canon/misterio.md` → fuga del secreto (invariante 3)». Es el guardrail que ya existe para `novela briefing`, aplicado a una superficie nueva.
- **§5 modelo de amenaza, riesgo 1 (fuga del misterio)** — este cambio **amplía** esa superficie: crea una segunda vía por la que texto del canon puede llegar al `escritor`, y la capa semántica la amplía más que las otras dos, porque puede traer una escena que no comparte ninguna palabra con la consulta. La sonda de la suite adversaria (canon marcado con centinelas) pasa a cubrir `recuperar`, y CA-05 es obligatorio.
- **§5 riesgo 2 (inyección por contenido del workspace)** — también se amplía: lo recuperado son resúmenes escritos por el `cronista`, texto generado por un modelo que entra en el contexto de otro. No se mitiga aquí.
- **§3.6 property-based** — aplica a la rama nueva de `delta.py`: reaplicar un delta no cambia el número de filas de `menciones`. Y a la fusión, que es función pura: para cualquier par de listas de rangos, RRF devuelve un orden total y estable.
- **§3.5 ningún test llama a un modelo** — se mantiene, y conviene ser preciso sobre por qué: el modelo de embeddings **sí** se ejecuta en los tests, pero es local, determinista y no consume cuota. La regla es «sin cuota y sin no-determinismo», y ambas se respetan. Lo que sí cambia es que la suite pasa a depender de un fichero de modelo en caché, y CA-12 lo fija como requisito explícito.
- Cambio de prompt del `cronista`: sin TDD. Baseline de la novela de humo: los scores de `coherencia` y `continuidad` de la ejecución anterior al cambio, en las mismas tres semillas.

**Riesgos aceptados**

1. **Inyección indirecta por resumen recuperado.** Un resumen con texto imperativo entra en el briefing de otro agente. No mitigado.
2. **La calidad de `menciones` depende del `cronista`.** Si omite una mención, la consulta devuelve un falso negativo silencioso, que es el peor modo de fallo de esta spec: el `continuista` concluirá que un objeto no se mencionó nunca. Mitigación parcial no implementada aquí: contrastar `menciones` contra el frontmatter del capítulo (§7.2 de `architecture.md`), que ya declara escenas, pistas e hilos. Ver §16.
3. **La capa semántica recupera sobre resúmenes, no sobre el texto.** Un detalle que el `cronista` no resumió no es recuperable por ninguna capa, y la semántica da la falsa impresión de cubrirlo porque siempre devuelve *algo*. Es la razón de que la capa exacta vaya primero y sin fusionar.
4. **Una dependencia de inferencia y un fichero de modelo** en un proyecto que hasta ahora corría con stdlib y cuatro librerías. Es el coste que §16 pone a decisión.
5. **FTS5 puede no estar en el binario.** Falla al arrancar en vez de degradar; la fase 1 no lo necesita.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | El 3 gana una superficie de fuga nueva y necesita el guardrail equivalente. Los demás no se tocan |
| Esquemas | `delta.schema.json` gana `menciones[]` (ruptura); `esquema.sql` gana tres tablas. `docs/definitions.md`: `indice_recuperable` pasa de «índice vectorial, opcional» a las tres capas descritas |
| Contratos de agente | `cronista`: campo nuevo en su salida. Ningún agente gana `tools` |
| Docs de referencia | `architecture.md`: §2 (stack, dependencia nueva), §6.2 (recetas), §6.4 (el largo plazo se consulta), §7.5 (salidas del `cronista`), §8 (subcomandos), y **§12.4 deja de ser cierto**. `definitions.md`: `indice_recuperable`. `validators.md`: §3.5, §4.4 y §5 |
| Frontend | Ninguno |

## 15. Alternativas descartadas

- **No hacer nada** (mantener `architecture.md` §12.4). Sigue siendo defendible: a 24 capítulos los resúmenes jerárquicos bastan y no hay presión de contexto medida. Es la alternativa contra la que hay que argumentar; se descarta porque la fase 1 cuesta una tabla y un `SELECT`, y las otras dos se pueden medir por separado con `--capas`.
- **Solo semántica, sin capa exacta ni léxica.** Es la forma habitual de montar un RAG y aquí sería un error: casi todo en este sistema tiene id canónico, y responder «¿dónde se mencionó `obj-011`?» por semejanza de vectores es sustituir una respuesta exacta por una aproximada teniendo la exacta disponible.
- **Solo léxica.** Era la propuesta de la v0.1 de esta spec. Cubre las consultas con id o con nombre propio, que son la mayoría, y no cubre la descripción que no comparte palabras con el resumen. Descartada al aceptarse el enfoque híbrido.
- **Embeddings con proveedor externo** (Voyage, OpenAI, Cohere). **Descartada por regla**: `AGENTS.md`, «Nunca añadir un proveedor de modelos, un gateway o un SDK de API de modelos». Además Anthropic no ofrece endpoint de embeddings, así que no hay variante que se quede dentro de la suscripción.
- **`sentence-transformers`.** Arrastra torch, del orden de 2 GB, para calcular 200 vectores de 384 dimensiones una vez por novela. Descartada por peso.
- **`sqlite-vec` o cualquier índice vectorial aproximado.** Con ~200 escenas, un `matmul` de numpy sobre una matriz de 200×384 resuelve la búsqueda en microsegundos y es exacto. Un índice aproximado sobre 200 vectores es complejidad e imprecisión sin beneficio. Si la novela llegara a miles de escenas, se reconsidera: es un cambio local a la función de búsqueda.
- **Reranking con cross-encoder.** Un segundo modelo para reordenar diez resultados. RRF hace el trabajo con una suma; añadir inferencia para esto no se justifica hasta que haya una medición que lo pida.
- **Normalizar y sumar `bm25()` con el coseno en vez de RRF.** Exige elegir escala y pesos, y ambos dependen del corpus. RRF solo usa rangos y no tiene parámetros que ajustar más allá de `k`.
- **Dar `Grep` o `Bash` a los agentes de revisión.** Resuelve la consulta en una línea y destruye el techo de §6.5, la reproducibilidad del briefing y la regla de «no explores el workspace por tu cuenta». Descartada.
- **Indexar el texto completo de los capítulos en vez de los resúmenes.** Más recall y un índice mayor que la propia novela, con el texto del misterio filtrado por implicación en cualquier capítulo posterior a una revelación. Descartada por el invariante 3.

## 16. Preguntas abiertas

Ninguna se resuelve en conversación: se resuelve en este fichero.

- [ ] **¿`fastembed` con `multilingual-e5-small`, o `model2vec` con `potion-multilingual-128M`?** El primero da mejor calidad en español y añade ONNX Runtime; el segundo es numpy puro, arranca en milisegundos y pierde calidad en paráfrasis. Recomendado empezar por `model2vec`: si la fase 3 no aporta sobre la 2 ni con el modelo bueno, sobra entera, y eso se descubre más barato con el ligero. — arturo.soto
- [ ] **¿Consulta el orquestador o consultan los agentes?** La propuesta es que consulte el orquestador, porque es la única forma de que el techo de §6.5 siga siendo verificable antes de la invocación. Si se decide que consulten los agentes, esta spec necesita una sección nueva sobre cómo se acota el contexto de una invocación cuyo tamaño no se conoce de antemano. — arturo.soto
- [ ] **¿Se acepta la primera dependencia de inferencia del proyecto?** Es el coste real de la fase 3. Las fases 1 y 2 no lo tienen. — arturo.soto
- [ ] **¿`menciones` se contrasta contra el frontmatter del capítulo?** Convertiría el riesgo aceptado 2 en un gate de `novela validar`. — arturo.soto
- [ ] **¿Qué consultas reales justifican la fase 3?** Antes de implementarla conviene tener por escrito tres preguntas que la fase 2 no responda. Si no aparecen, la fase 3 se cierra como `descartada` y esta spec se queda en dos capas. — arturo.soto
