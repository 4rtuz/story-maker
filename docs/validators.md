# validators.md

Catálogo de métodos de verificación del harness: qué comprueba cada uno, sobre qué artefacto, con qué clase del Trust Spec, y si está activo, planificado o descartado.

Hay dos preguntas distintas y no intercambiables:

- **¿El código es correcto?** El harness es software normal: CLI, esquemas, API, panel. Se verifica como cualquier otro software (§3).
- **¿El agente se comporta de forma fiable?** La prosa no tiene «correcta» e «incorrecta»: tiene coherente, contradictoria, o filtrando el final en el capítulo 3. Eso no lo detecta un test unitario (§4).

Regla de este documento: **un método que no se puede aplicar se declara `U` y se escribe en §5.** Un riesgo nombrado es gestionable; uno implícito es una sorpresa en el capítulo 14.

---

## 1. Marco de clasificación (Trust Spec)

| Clase | Nombre | Cómo se verifica | Ejemplo aquí |
|---|---|---|---|
| **T** | Test | Ejecutando el sistema contra entradas concretas | `uv run pytest` sobre los fixtures sintéticos |
| **A** | Analysis | Razonamiento estático: tipos, SAST, ejecución simbólica, prueba formal | `mypy --strict`, validación Pydantic, guardrail del briefing |
| **I** | Inspection | Una persona o un modelo crítico lo lee y juzga | `continuista`, revisión de `intervencion.md` |
| **D** | Demonstration | Observando operación correcta en un escenario realista | novela de humo de 3 capítulos antes de lanzar 24 |
| **U** | Unverifiable / riesgo aceptado | Ningún método aplica o no compensa; se nombra explícitamente | §5 |

Una propiedad puede cubrirse con varias clases, y conviene: el aislamiento de `canon/misterio.md` es `A` (el briefing aborta), `T` (un test lo comprueba) y `I` (el red-team lo ataca). Lo que nunca es aceptable es que una propiedad crítica tenga solo `I`: un juicio humano que nadie repite no es una verificación, es una opinión con fecha.

---

## 2. Tabla resumen

**Estado a 2026-09-24: las specs 0001 y 0003 están implementadas.** Corren hoy, en pre-commit o en CI (`.github/workflows/ci.yml`): 1 y 2 sobre `backend/`, el hook y `frontend/` —`tsc --noEmit` y `eslint` con `npm run verificar`, `eslint` en el pre-commit y los dos en el job `frontend` de CI, con los presupuestos de tamaño (spec 0004)—; 5, también sobre el panel: los unitarios de Vitest en el job `frontend` y los e2e de Playwright en el job `frontend-e2e`, en Chromium y Firefox contra la API real (spec 0004, §3.5); 6 sobre las funciones puras de la spec 0001 y sobre el hook; 7 sobre `gates.py` y `apply.py`; 8 en sus tres contratos: el OpenAPI commiteado, los JSON Schema de `backend/schemas/` y `.claude/` —agentes, `settings.json` y hook—; 9 en lo que cierra la spec 0001 —`validar`, `checkpoint` y las precondiciones de `aplicar-delta`—, sin `validar-plan` ni `validar-delta`; 13 entero: aborto del briefing, triggers, validación del slug, `tools`, `deny` y hook; 16 con `sucio` y los hashes de `.claude/` en el manifiesto; 19 y 24. La novela de humo de la spec 0003 (`humo-0003`, 2026-09-24) ejercitó 12 (`tools`, `deny` y hook; sigue siendo parcial, §5.6), 14 (una intervención real por el invariante 7, y el ensayo) y 15 (los tres revisores dentro de `/novela-continuar`). 10 es el plugin de Langfuse, habilitado por máquina en `settings.local.json`: cada sesión de la novela de humo dejó su traza. De 11 corre el emisor de scores de `checkpoint`, con las claves del entorno o de `.env` (F-54), que emitió los seis de cada capítulo de la novela de humo; el juez de sesión no existe. El canario de §4.9 da verde desde el 2026-09-24. 20 y 27 no están construidos: el control negativo necesita fixtures con defecto sembrado, y la auditoría de trayectoria es de la spec 0002. Del 28 (§4.17) corren las filas marcadas `activo`. 18, 21, 22, 23, 25 y 26 no están construidos. La columna sigue diciendo qué se espera de cada método; este párrafo, cuál corre de verdad.

Decirlo aquí, y no solo en `architecture.md` §12.7, es parte del método: un catálogo que se lee como inventario de protecciones vigentes es peor que no tenerlo, por la misma razón que un guardarraíl silenciado (§4.4).

### Verificación de código

| # | Método | Clase | Artefacto | Herramienta | Estado previsto |
|---|---|---|---|---|---|
| 1 | Type checking | A | `backend/`, `frontend/` | `mypy --strict`, Pydantic v2, `tsc --noEmit` | activo |
| 2 | Static analysis / SAST | A | `backend/`, `frontend/` | `ruff` (reglas `S`), `eslint` | activo |
| 3 | Symbolic execution | A | `delta.py`, `validate.py` | CrossHair | diferido |
| 4 | Formal verification | A | invariantes append-only | — | **U** (§5.2) |
| 5 | Unit / integration testing | T | CLI y API | `pytest` + `jsonschema` | activo |
| 6 | Property-based testing | T | `aplicar-delta`, `briefing`, `checkpoint` | Hypothesis | v1 |
| 7 | Mutation testing | T | `validate.py`, `delta.py` | `mutmut` | v1 |
| 8 | Contract testing | T + A | API ↔ frontend, agente ↔ CLI, harness ↔ Claude Code | OpenAPI + JSON Schema versionado + frontmatter | v1 |
| 9 | Gates de artefacto | A + T | `plan/`, `estado/deltas/`, capítulo final, frontera entre capítulos | `novela validar-plan`, `validar-delta`, re-`validar`, `checkpoint` | v1 |

### Verificación de proceso

| # | Método | Clase | Artefacto | Mecanismo | Estado previsto |
|---|---|---|---|---|---|
| 10 | Runtime observability / tracing | D | sesión de Claude Code | hook `Stop` + Langfuse (arch §10) | activo |
| 11 | Evals | T + I | salida de cada agente | scores por capítulo + juez de sesión | activo |
| 12 | Sandboxed execution | D | subagentes | `tools` restringido, workspace fuera del repo | parcial (§5.6) |
| 13 | Guardrails | A | briefings, `estado/` | aborto del briefing, hook `PreToolUse` | activo |
| 14 | Human-in-the-loop | I | `runs/<run_id>/intervencion.md` | parada al tercer intento | activo |
| 15 | Multi-agent verification | I | capítulo escrito | `continuista`, `editor-estilo`, `lector-suspense` | activo |
| 16 | CI/CD integration | T | commits del harness | pipeline + `manifest.json` con sha | v1 |
| 17 | Progressive rollout | D | cambios de prompt de agente | versión de receta como flag | diferido |
| 18 | Red-teaming / adversarial | I + T | fuga del misterio, inyección | suite adversaria por release | v1 |
| 19 | Model checking | A | bucle por capítulo | enumeración de la máquina de estados | v1 |
| 20 | Control negativo de revisores | T + I | `continuista`, `editor-estilo`, `lector-suspense` | fixtures con defecto sembrado | v1 |
| 21 | Ensayo de reanudación y degradación | D + T | bucle, política de cuota | corte inyectado, niveles forzados | v1 |
| 22 | Detección de deriva a escala de novela | A + T | la novela entera | métricas entre capítulos en `auditar`, huella de estilo contra el canon, carga de preguntas abiertas | v1 |
| 23 | Reproducción del estado | A + T | `estado.db`, `memoria/` | replay de `estado/deltas/*.json` sobre base vacía | v1 |
| 24 | Custodia del capítulo | A + T | briefings, `qa/NN-validacion.json`, `capitulos/` | sha256 encadenado en `aplicar-delta`, sello en `checkpoint` | v1 (spec 0001) |
| 25 | Integridad semántica del delta | A + T | `estado/deltas/NN.json`, `memoria/` | invariantes narrativos en `validar-delta` | v1 |
| 26 | Sondas ciegas del secreto | I + A | briefing del `escritor`, capítulos del acto | modelo sin misterio predice el culpable; comparación mecánica | v1 |
| 27 | Auditoría de trayectoria del orquestador | A | transcript de la sesión principal | script en el hook `Stop` + parada en `pendiente` | v1 |
| 28 | Contención y bucle de `.claude/` | T + A + D | agentes, hook, permisos, procedimientos, bucle, canario | catálogo de fallos F-01 a F-70 (§4.17) | spec 0003 |
| 29 | Verificación a escala de novela | T + A + I + D | secreto, estado, estilo, tensión y orquestador | catálogo de fallos F-80 a F-168 (§4.18) | spec 0002 |

---

## 3. Verificación de código

### 3.1 Type checking — A

Dos fronteras, y la segunda es la que importa.

- **Estática**: `mypy --strict` sobre `backend/`, `tsc --noEmit` con `strict` y `noUncheckedIndexedAccess` sobre `frontend/` (`npm run typecheck`, dentro de `npm run verificar`). Los tipos del frontend se generan desde el OpenAPI del backend (§3.8), así que no pueden derivar por su cuenta.
- **En el borde**: todo lo que llega de disco o de un agente es `Any` hasta que un modelo Pydantic lo parsea. **Regla dura: ningún dato cruza de disco o de agente al código sin pasar por un modelo de `backend/novela/dominio/`.** `json.load()` suelto en el código de negocio es un bug, no un atajo.

Lo que **no** cubre: `capitulo: int` acepta `0` y `-3`. Rango, formato de id y consistencia referencial son validadores Pydantic, no tipos.

### 3.2 Static analysis / SAST — A

`ruff` con las reglas `S` (flake8-bandit) en backend, `eslint` en frontend. Los patrones que de verdad importan en este repo:

1. **Path traversal en la API.** `GET /novelas/{slug}/...` concatena un valor de URL con una ruta de disco. Es la única superficie de inyección real del sistema. El slug se valida contra `^[a-z0-9-]+$` antes de tocar el filesystem, y hay un test que lo intenta con `../`.
2. **Escritura no atómica.** Cualquier `open(..., "w")` sobre el workspace que no pase por `plataforma/atomic.py` viola el invariante 6 de AGENTS.md. El estado no es la excepción por la vía fácil: escribir `estado.db` fuera de una transacción de `aplicar-delta` viola el mismo invariante.
3. **Claves en ficheros versionados.** Grep de `LANGFUSE_SECRET_KEY` y similares en pre-commit. `settings.local.json` y `.local.env` están en `.gitignore`, pero la regla la hace cumplir el linter, no la disciplina.
4. **Lo que el panel alcanza fuera de sí (spec 0004).** `frontend/eslint.config.js` marca como error todo import de `frontend/src/` que resuelva fuera de `src/` —`novelas/` y `backend/` incluidos, también con `?raw`— con una regla propia, y toda inserción de HTML con `eslint-plugin-no-unsanitized`, sin excepciones por fichero. Los fixtures con los usos prohibidos viven en `frontend/test/fixtures/lint/`, fuera de `eslint .`, y `lint.test.ts` los lintea con la ruta de `src/` que les toca, con un fixture limpio como control positivo. El dev server es la otra mitad: `root` fijo en `frontend/`, `server.fs.allow: ['.']` y sin fallback de SPA, comprobado desde los dos directorios de arranque por `servidor.test.ts`; sin `root`, arrancado desde la raíz del repositorio, servía `novelas/`.

### 3.3 Symbolic execution — A

Donde compensa: `aplicar-delta`. Es la única vía de escritura de `estado.db` y sus precondiciones son expresables (append-only, ids únicos, cursor monótono). CrossHair sobre las funciones puras de `delta.py` devuelve el contraejemplo concreto que las rompe, que es exactamente lo que un test de ejemplo no te da.

**Diferido**, con una condición previa clara: hoy `delta.py` mezcla lectura de disco con lógica. Hay que extraer primero `aplicar(estado, delta) -> estado` como función pura. Ese refactor es el trabajo real; CrossHair es una línea de CI después.

### 3.4 Formal verification / theorem proving — A

**Descartado para el conjunto del sistema** (§5.2). No hay especificación formal de «una novela de suspense coherente» y no la va a haber.

Existe un subconjunto barato que sí se hace, y conviene no confundirlo con una prueba: los invariantes append-only son triggers `BEFORE UPDATE` y `BEFORE DELETE` con `RAISE(ABORT)` en las tablas de `estado.db`. Eso sigue siendo detección en tiempo de ejecución, no una demostración, pero cambia de sitio: antes era un `assert` en la única función que se acordó de escribirlo, y ahora lo impone el motor en cualquier ruta de escritura, incluida la que nadie previó. Lo que queda como postcondición en `delta.py` son las propiedades que el esquema no expresa: ids únicos entre colecciones y monotonía del cursor.

### 3.5 Unit / integration testing — T

`pytest` sobre los workspaces sintéticos de `backend/tests/fixtures/`.

**Regla dura: ningún test llama a un modelo.** Es lo que permite ejecutar la suite en cada commit sin consumir cuota y sin no-determinismo.

- **Unitarios**: cada gate de `validate.py`, cada rama de `delta.py`, cada receta de `recipes.py`.
- **Integración**: el bucle completo por capítulo con un agente falso que escribe un capítulo prefabricado. Esto es lo que hace testable el bucle; sin el doble, la única forma de probarlo sería escribiendo una novela.
- **API**: `TestClient` de FastAPI contra un workspace fixture; se verifica también que **ningún** endpoint escribe (§4.3).
- **Plataforma**: en Windows, `os.replace` falla con `PermissionError` si otro proceso tiene abierto el destino —la API sirviendo ese capítulo, un antivirus—. El test abre el destino con otro handle y escribe: `atomic.py` reintenta con espera acotada y, si agota, sale con error dejando el fichero anterior intacto. CA-04 inyecta la excepción; esto la provoca de verdad, que no es lo mismo.
- **Sink caído**: con `TRACE_TO_LANGFUSE="true"` y Langfuse inalcanzable o colgado, `checkpoint` escribe igual, sale con 0 dentro de un timeout fijo y deja el fallo en `harness.log`. CA-22 prueba el sink apagado; el que para una novela es el encendido sin red.
- **e2e del panel** (spec 0004): Playwright en Chromium y Firefox contra la API real y `vite preview` en `localhost:5173`. Los workspaces los genera `backend/tests/fixtures/panel.py` —`demo-24`, `recien-creada` y `grande-999`, con el bucle real y sin claves: aparta `TRACE_TO_LANGFUSE`, `LANGFUSE_*` y el `.env` de la raíz mientras genera (CA-42)— y `e2e/preparar.ts` añade `hostil-24`, una copia de `demo-24` con el capítulo hostil de CA-26 en el 3. `page.route` solo retrasa o hace fallar respuestas. Cada test escucha `console.error` y `pageerror` y falla si aparece uno (RNF-16); solo se excluyen, con una lista cerrada, los mensajes del navegador por el fallo que provoca el propio escenario (WebGL desactivado, logo o fuente que no cargan, la API caída de `resiliencia.spec.ts`) y el «Failed to load resource» de Chromium por el 404 de `…/escaleta` de una novela sin plan, que el panel trata como respuesta correcta (D45). Draw calls, WebGL desactivado y las 20 entradas y salidas de Lectura (VAL-20) solo en Chromium.

### 3.6 Property-based testing — T

Hypothesis, generando estados y deltas aleatorios. Las propiedades que aquí son verdad y merecen la pena:

| Propiedad | Por qué importa |
|---|---|
| `aplicar(aplicar(e, d), d) == aplicar(e, d)` | Reanudar tras un fallo repite el paso; si no es idempotente, corrompe |
| `len(nuevo.libro_de_hechos) >= len(viejo.libro_de_hechos)` | Append-only, invariante 2 |
| `restore(checkpoint(e)) == e` | La reanudación depende de esto y nada más lo comprueba |
| `misterio.md ⊄ briefing(escritor, *)` | Invariante 3, sobre canons generados al azar |
| `validar(cap) == ok ⟹ todas las pistas del plan están en el frontmatter` | El gate no puede pasar en falso |

La cuarta es la más valiosa: un test de ejemplo comprueba que *ese* misterio no se filtra; la propiedad comprueba que ninguno lo hace.

### 3.7 Mutation testing — T

`mutmut`, y **solo sobre `validate.py` y `delta.py`**. En el resto del backend es caro y poco informativo.

El motivo es concreto: si al mutar `>=` por `>` en la comprobación de longitud mínima ningún test falla, ese gate es decorativo y lleva siéndolo desde que se escribió. Los gates son la defensa barata del sistema entero; un gate no probado es peor que no tenerlo, porque da confianza falsa.

### 3.8 Contract testing — T + A

Tres contratos, mismo principio.

**API ↔ frontend.** FastAPI emite OpenAPI; el frontend genera sus tipos desde ahí; CI falla si el esquema commiteado no coincide con el que genera el código. Eso es el contrato entero. No hace falta Pact para dos partes que viven en el mismo repo. Son dos comprobaciones encadenadas: `test_openapi_al_dia` (OpenAPI ↔ código) y `npm run tipos:comprobar` (OpenAPI ↔ tipos), que regenera `frontend/src/shared/api/esquema.gen.ts` con `openapi-typescript` y sale con distinto de 0 si el fichero no está en el índice —`git diff` no ve uno sin seguimiento— o si difiere del commiteado. Corre al principio de `npm run verificar` (spec 0004). `contrato.test.ts` cierra la puerta de atrás: ninguna `interface` ni `type` de `frontend/src/` fuera del generado lleva el nombre de un esquema de `components.schemas`, con un fixture que sí lo lleva como control positivo.

**Agente ↔ CLI.** Los ficheros de `qa/`, el delta del `cronista` y el frontmatter de capítulo son contratos igual de reales, entre un productor no determinista y un consumidor estricto. Se tratan igual: JSON Schema versionado en `backend/schemas/`, validación en ambos lados, y `schema_version` en el propio documento. Cuando un agente empieza a devolver un campo de más, quieres enterarte en el capítulo 1.

**Harness ↔ Claude Code.** El tercero, y el que nadie mira porque no parece un contrato: los ficheros de `.claude/`. El frontmatter de cada agente —`name`, `model`, `tools`— es lo que sostiene los invariantes 1 y 3 (§4.4), y es texto que se edita a mano. `test_contratos.py` lo comprueba sobre los siete ficheros —cada agente con exactamente las herramientas de `architecture.md` §7.4, ninguno con `Bash`, `Task`, `Skill`, `Glob` ni `Grep`, el modelo que le toca por rol, sus salidas y su esquema nombrados en el cuerpo— y falla en el commit en vez de en el capítulo 9 (spec 0003, CA-01 y CA-02). Vale igual para `settings.json`: que sea JSON válido, que solo tenga `permissions` y `hooks`, el `allow` exacto, los cuatro `deny`, el `matcher` del hook y que el script que nombra exista (CA-06).

Y el cruce entre ambos. El hook deniega todo `Write` bajo `estado/` salvo la salida declarada del `cronista`, `estado/deltas/NN.json` (`architecture.md` §7.1 y §7.5), y su tabla de salidas por rol es una copia de la de los agentes, porque no puede importar `backend/`. `test_hook.py` ejecuta el script como subproceso contra cada salida de cada rol —debe permitirla— y contra `estado/estado.db` y las salidas ajenas —debe denegarlas— (CA-03, CA-05), y compara su tabla con la del contrato de los agentes (F-16).

### 3.9 Gates de artefacto — A + T

Un gate es código barato en una frontera. El sistema tiene hoy uno solo, `novela validar` sobre el capítulo recién escrito, y varias fronteras que se cruzan sin nada.

**1. `plan/` y `canon/`, antes del capítulo 1.** Es el punto de mayor apalancamiento del sistema entero y no tiene verificación. El fair play (invariante 4) es comprobable sobre el plan sin leer una línea de prosa: toda `rev-` tiene al menos una `pis-` plantada en un capítulo anterior, ninguna pista se paga antes de plantarse, todo id citado en una ficha de capítulo existe en el canon, y las palabras planificadas suman lo que dice `config.yaml`. `novela auditar` ya calcula casi esto, pero al cerrar la novela. Las mismas cuentas antes del capítulo 1 son un gate; después del 24 son una autopsia, y el coste de la diferencia es una novela entera de cuota.

Dos comprobaciones más sobre el mismo plan. La **forma de `curva_tension_objetivo`**: el clímax es su máximo, el punto medio es un pico local y no hay más de tres capítulos seguidos sin subir en los actos 2 y 3. Un colapso de tensión puede venir planificado, y ningún revisor de capítulo lo ve porque cada capítulo cumple su objetivo. Y el **secreto por capítulo**: ninguna ficha anterior al `capitulo_previsto` de una revelación comparte bloques de cinco palabras con su contenido. El `trazador` ve el misterio y escribe el prompt del `escritor` (§4.9).

**2. El delta contra el capítulo, antes de `aplicar-delta`.** `aplicar-delta` valida forma —esquema, ids únicos, cursor monótono— y nada comprueba que lo que el `cronista` fija haya ocurrido en el texto. El campo `cita` de `libro_de_hechos` lo hace mecánico: debe ser subcadena literal del capítulo aprobado. Es gratis, y es la única defensa contra que una alucinación entre en un registro que el invariante 2 ya no permite corregir (§5.9). Que el `cronista` sea el agente más barato del bucle no es un argumento en contra: es la razón.

**3. El capítulo después del `editor-estilo`.** `validar` corre antes de los tres revisores, y el `editor-estilo` reescribe `capitulos/NN.md` después (`architecture.md` §7.5). El fichero que el `cronista` lee, que se exporta y que queda como salida final nunca ha pasado un gate en su forma definitiva: el editor puede dejar el frontmatter desincronizado con el texto, bajar las palabras del mínimo o deshacer la frase donde estaba plantada una pista. Y el veredicto del `continuista` es sobre una versión que ya no existe. Re-ejecutar `validar` tras el editor cuesta milisegundos y cierra el hueco, con la condición del punto 4: sin él, la pista borrada no se ve.

**4. La pista, contra la prosa.** `validar` comprueba que las pistas del plan figuran en el frontmatter, y el frontmatter lo escribe el mismo `escritor` que puede haberse olvidado de plantarla: es una declaración, no una prueba. El remedio es el de `cita` en el delta. Cada pista plantada o pagada lleva en el frontmatter el pasaje que la contiene, y ese pasaje debe ser subcadena literal del cuerpo. Es lo que da al punto 3 la capacidad que promete: sin cita, re-validar tras el `editor-estilo` ve el frontmatter intacto aunque la frase haya desaparecido. Añadir el campo es un cambio de modelo, así que entra por spec.

**5. Canon y plan, entre dos capítulos.** `ColeccionAppendOnly` (spec 0001, RF-28) protege las colecciones del canon dentro de un proceso. Entre procesos el canon es markdown en disco y se edita sin que nada lo note. `checkpoint` guarda el hash de `canon/` y `plan/`, y el primer `briefing` del capítulo siguiente lo compara. Si difiere, para: cambiar el canon a mitad de novela es una decisión del orquestador (AGENTS.md) y tiene que constar, no descubrirse. Si además alguna colección append-only del canon anterior no es prefijo de la nueva, el cambio es inválido con o sin autorización.

**6. El rastro del capítulo, en el checkpoint.** `CLAUDE.md` exige generar el briefing antes de delegar y nada lo comprueba (§5.8). `checkpoint` puede hacerlo: antes de confirmar, exige que cada paso del capítulo tenga su `runs/<run_id>/briefings/NN-<agente>.md` y su salida declarada (capítulo, `qa/NN-*.json`, delta). Un agente invocado sin briefing no deja ese fichero, y el capítulo no se confirma. De paso cubre el borrado de briefings contra el que advierte §4.1.

**7. La custodia del capítulo, antes de `aplicar-delta`.** Hoy nada ata un veredicto al texto que juzgó. Un modelo no calcula un sha256, así que no lo registra ningún agente: lo registra el CLI por donde pasa el texto. `novela briefing` escribe el hash del capítulo que incrusta, y `novela validar` el del fichero que valida, también cuando pasa. `aplicar-delta` solo aplica si la cadena cierra. Primero, los briefings de revisión del run llevan todos el mismo hash, el del editor incluido, porque partió de la versión revisada. Segundo, el fichero en disco es el que validó la última `validar`, sin hallazgos, y el que leyó el `cronista`. Es una precondición sobre datos y no un juicio sobre veredictos, así que no necesita `novela gate` (§4.16). El hueco entre capítulos lo cierra el **sello**: `checkpoint` guarda el hash de cada capítulo cerrado y cada `briefing` lo compara. Los niveles 2 y 4 de la política de cuota de `architecture.md` §9 difieren el `editor-estilo` hasta después del `cronista`, y el editor diferido reescribe un capítulo cerrado, que es lo que prohíbe el invariante 7. Con el sello, el bucle para. Está en la spec 0001 v0.3 (RF-30 a RF-32 y RF-35); cómo degradar sin violar el invariante 7 queda para la spec 0002.

**8. El delta contra la narrativa, antes de `aplicar-delta`.** El punto 2 comprueba que el hecho está en el texto; nada comprueba que el delta sea coherente con el estado al que se suma. El `cronista` es haiku y escribe en tablas que no admiten corrección (§5.9). `validar-delta` añade tres cosas, todas sin modelo y todas property-based por la regla de `delta.py`:

- **Cita en toda colección append-only**, no solo en `libro_de_hechos`. `conocimiento` es la estructura más importante del género y hoy entra sin evidencia: «el personaje ya sabe X» es exactamente la alucinación que después no hay forma de retirar. Igual `linea_temporal` y `conocimiento_lector`.
- **Invariantes narrativos.** Un personaje con `condicion` muerta no reaparece ni aprende nada. Toda `ubicacion` es un escenario del canon. Solo se cierra un hilo abierto y solo se paga una pista plantada. Nadie está en dos escenas que se solapan en `linea_temporal`. Un objeto de relevancia alta no se queda sin poseedor ni ubicación. Con punto de vista limitado, `conocimiento_lector` incluye lo que aprende el personaje POV en el capítulo.
- **Cruce con el plan.** Los hilos los declaran tres productores —`trazador`, `escritor` y `cronista`— y ninguno se contrasta con los otros. El delta y el frontmatter describen el mismo texto y deben coincidir; el plan puede admitir o no un hilo o una pista fuera de lo planificado.

Qué entra ya: la spec 0001 v0.3 añade `cita` **opcional** en las tres colecciones y comprueba que toda cita presente sea literal (RF-33), incluida la de `libro_de_hechos` del punto 2. También cruza los hilos del delta con los del frontmatter (RF-34). Las pistas no hace falta cruzarlas: no viajan en el delta, se derivan del frontmatter. Qué no entra todavía, y es de la spec 0002: que la cita sea obligatoria, las invariantes narrativas y el cruce con el plan. Cada una abre una pregunta de diseño (conocimiento inferido, analepsis, narrador no fiable, hilos no planificados).

**9. El estilo contra el canon, en `validar`.** Dos gates que hoy son juicio del `editor-estilo` sobre algo medible. **Léxico vetado**: `canon/estilo.md` `prohibiciones` es una lista, y la presencia de una entrada de la lista en el cuerpo se comprueba con una búsqueda, no con un modelo. **Huella estilométrica**: los rasgos que `ritmo` declara medibles —longitud media y dispersión de frase, proporción de diálogo— más frecuencias de palabras funcionales (Delta de Burrows), comparados contra `parrafos_canonicos` y contra la media de los capítulos 1–3, con la tolerancia que declare `ritmo`. La referencia es fija y nunca el capítulo anterior (§4.13). Los umbrales se calibran con la novela de humo: con párrafos canónicos cortos la Delta es ruidosa, y un umbral inventado es un gate que falla al azar.

**10. Gancho y pista falsa, contra la prosa.** El patrón de la cita del punto 4, aplicado a dos cosas que hoy solo se declaran. El `lector-suspense` devuelve `gancho: {tipo, cita}`: la cita es subcadena de la última escena y el tipo es el `gancho_final` de la ficha. Cada pista falsa lleva la cita del pasaje que la desmonta en su capítulo `cuando_se_desmonta`. `auditar` solo mira el estado, y el estado dice lo que el `cronista` creyó leer.

**11. Los resúmenes, contra el capítulo.** `memoria/` es derivada, pero es lo único que el `escritor` ve de los capítulos 1..N-2 durante el resto de la novela: una alucinación en el resumen es contaminación efectiva aunque `estado.db` esté limpio. `aplicar-delta` comprueba que todo id y todo nombre propio de `memoria/resumenes/NN.md` aparece en el delta o en el cuerpo del capítulo. Detecta el personaje o el lugar inventado; la interpretación equivocada sigue en §5.9.

---

## 4. Verificación de proceso

### 4.1 Runtime observability / tracing — D

Detalle completo en `architecture.md` §10. Lo relevante aquí: el trazado es la **única** evidencia de la trayectoria real del agente —qué herramientas llamó, en qué orden, cuánto tardó, qué falló—. Sin él, un fallo de calidad en el capítulo 12 no es diagnosticable.

Con un límite que hay que tener presente al usarlo como verificación: **el trazado no captura el contexto ensamblado**. Ve la conversación y las llamadas, no lo que el agente tenía delante. Por eso los briefings de `runs/<run_id>/briefings/` no son un artefacto de depuración opcional: son la mitad que falta de la traza. Borrarlos al limpiar deja las trazas sin sujeto.

### 4.2 Evals — T + I

El problema de fondo: **no existe un capítulo de referencia correcto**, así que el eval de golden-dataset clásico no aplica a la prosa. Se reparte así:

| Tipo de eval | Aplica a | Cómo |
|---|---|---|
| Golden dataset | partes deterministas | workspace fijo → briefing esperado, byte a byte |
| Task completion | el bucle | ¿pasó el capítulo todos los gates al primer intento? |
| LLM-as-judge | prosa | `lector-suspense` puntúa tensión, ritmo, fair play |
| Adversarial | secreto y robustez | §4.8 |
| Live / online | la novela en curso | scores a Langfuse al cerrar cada capítulo |

Las métricas por capítulo son `coherencia`, `continuidad`, `tension`, `longitud`, `fair_play` y `estilo`.

La señal más barata y más infravalorada es **intentos por gate**. Es gratis, es objetiva, y una subida sostenida de reintentos en el acto 2 dice que el plan o las recetas se están quedando cortas mucho antes de que la prosa se note mala.

Riesgo conocido, mitigado y no eliminado: el juez y el escritor son la misma familia de modelo y comparten puntos ciegos. La mitigación es que el juez puntúe **contra el libro de hechos y el plan**, no contra su gusto. Un juez que compara con hechos verifica; uno que opina, coincide. Ver §5.4.

Dos métricas no pueden salir del agente que evalúan. `estilo` se calcula con la huella de §3.9.9, no con `qa/NN-estilo.json`: quien reescribe el capítulo no puntúa su propia reescritura. Y la previsibilidad no la puede puntuar el `lector-suspense`, que lee `misterio.md` (`architecture.md` §7.5) y por tanto juzga la incertidumbre del lector conociendo ya la respuesta. La da el lector ciego de §4.15. El `lector-suspense` se queda con lo que sí exige conocer la solución: si el fair play se cumple en el texto.

### 4.3 Sandboxed execution — D

Parcial y por construcción, no por contenedor:

- Cada subagente tiene `tools` restringido en su frontmatter.
- El workspace vive fuera del repo y en `.gitignore`.
- `estado.db` solo lo escribe `novela aplicar-delta`; ningún agente lo toca.
- La API es de solo lectura: no hay verbo que mute una novela.

Lo que **no** está contenido: un subagente con `Write` puede escribir donde alcance la sesión. La contención real son los permisos de `.claude/settings.json` y el frontmatter, no un aislamiento. Aceptado mientras el harness corra en una máquina de desarrollo; si pasa a correr desatendido en CI, esto deja de ser aceptable y pasa a ser requisito (§5.6).

### 4.4 Guardrails — A

Preventivos: actúan **antes** de la acción, a diferencia de un gate, que detecta después.

| Guardrail | Impide |
|---|---|
| `novela briefing` aborta si el contenido ensamblado procede de `canon/misterio.md` | Fuga literal del secreto (invariante 3). No ve la paráfrasis: las tres filas siguientes y §4.15 |
| `novela briefing` excluye por campo `secreto` y `coartada_y_cronologia_privada` de las fichas de personaje del `escritor` y el `editor-estilo`, salvo revelación con `capitulo_previsto ≤ N` | Fuga por la ficha del culpable, que no procede de `misterio.md` y lo contiene entero. Exige fichas de personaje con frontmatter estructurado |
| `novela briefing` aborta si el briefing del `escritor` o del `editor-estilo` comparte bloques de cinco palabras con `verdad_oculta` o con una revelación de `capitulo_previsto > N` | Copia retocada del secreto en las fichas del `trazador`. No la paráfrasis real |
| En reintento, del `qa/` solo entran al briefing campos de lista blanca —`tipo`, `gravedad`, `ubicacion`, referencias `hec-`, `pis-`, `hil-`— y se descartan los hallazgos que citan `rev-`, `pfa-` o al culpable | Fuga por `correccion_sugerida`: la escriben `continuista` y `lector-suspense`, que ven el misterio |
| `novela gate` decide avanzar, reintentar o intervenir desde `qa/*.json` y el cursor, e incrementa `cursor.intento` en `estado.db` | Que la sesión apruebe un capítulo rechazado o reinicie la cuenta de intentos tras compactar su contexto (§4.16) |
| La política de cuota (`novela budget`, `architecture.md` §9) fija el nivel de degradación y lo escribe en el manifiesto | Que la sesión omita un revisor «por cuota» por decisión propia |
| `tools` restringido por agente | Que un agente descubra ficheros que su briefing no nombra (sin `Glob` ni `Grep`), ejecute el CLI, delegue o invoque skills. **No** impide leer una ruta conocida: eso lo hace el `deny` |
| `deny` de `.claude/settings.json`: `Read` de `canon/misterio.md`, `Edit` de `estado.db*` y `state.lock`, `Bash(sqlite3:*)` | Que cualquier agente o la sesión principal abra el misterio por su ruta, o escriba la base o el lock (invariantes 1 y 3) |
| Hook `PreToolUse`, regla 1: nada bajo `estado/` salvo `estado/deltas/NN.json`, con la ruta normalizada | Que un agente escriba el estado por fuera de `aplicar-delta`, también con variantes de ruta de Win32 |
| Hook `PreToolUse`, reglas 2 y 3: cada rol solo en sus salidas, y la sesión principal solo en `intervencion.md` dentro del workspace | Que un rol escriba donde no le toca, o que el orquestador haga el trabajo de un agente |
| Hook `PreToolUse`, reglas 4 y 5: órdenes sobre el misterio o `estado.db`, y subagentes fuera de los siete en una sesión del harness | Que la sesión principal lea el secreto por `Bash`, o que invoque a `general-purpose`, que tiene todas las herramientas |
| Triggers append-only en las tablas de `estado.db` | Reescribir la historia, por cualquier ruta de escritura y no solo por delta (invariante 2) |
| Validación del slug antes de tocar disco | Path traversal por la API |
| `novela pendiente` sale con un código propio, distinto de 0, mientras exista un `intervencion.md` sin marcar como resuelto | Que el bucle desatendido siga lanzando sesiones sobre una novela parada. Su `\|\| break` depende hoy del código de salida de `claude -p`, que ningún test fija (§5.8); `pendiente` sí es código y se prueba |
| `novela pendiente` sale con ese mismo código si falta `runs/<run_id>/trayectoria-NN.json` del último capítulo o registra violaciones | Que una sesión que se saltó el orden o leyó prosa pase su capítulo a la siguiente sin que nadie lo sepa (§4.16) |

Prefiere siempre un guardrail a un gate para la misma propiedad: es más barato y no quema un reintento. Cuando un hook salta, la respuesta correcta es corregir el contrato del agente, no silenciarlo — un guardrail silenciado es peor que ausente, porque el sistema sigue reportando que está protegido.

### 4.5 Human-in-the-loop review — I

Dos puntos de parada, ambos duros:

1. **Tercer intento de un gate.** El procedimiento escribe `runs/<run_id>/intervencion.md` con el hallazgo y el briefing que lo produjo, y termina. No degrada la calidad en silencio.
2. **Problema retroactivo.** Si un gate del capítulo 7 detecta que la causa está en el 5, el harness para y pide intervención. No se reescriben capítulos anteriores (invariante 7).

Esos ficheros son también el corpus de mejora: cada intervención registra un caso que las recetas o los prompts no cubrieron. Es la señal de entrenamiento del sistema, y por eso se escriben en disco en vez de resolverse en la conversación.

### 4.6 Multi-agent verification — I

Es el núcleo del bucle. Mapeado sobre la taxonomía:

| Técnica | Uso aquí |
|---|---|
| Critic / verifier | `continuista`, `editor-estilo`, `lector-suspense` sobre el capítulo recién escrito |
| Reflection | El reintento del escritor, al que se le pasa **solo** el informe de QA |
| Ensembles | Modelo por rol (opus / sonnet / haiku): es un ensemble por coste, no por verificación |
| Self-consistency | No se usa — §5.3 |
| Debate | No se usa — §5.3 |

El detalle que hace que el crítico sirva: el `continuista` **no opina**. Verifica el capítulo contra `libro_de_hechos` y `linea_temporal`, que son datos. Un crítico que juzga comparte los sesgos del escritor; uno que compara contra hechos, no. Cuando añadas un rol de revisión nuevo, la pregunta es contra qué dato verifica; si la respuesta es «contra su criterio», va a estar de acuerdo con el escritor.

Sobre el reintento: pasarle el informe de QA y nada más no es tacañería de contexto, es aislamiento de la señal. Devolverle el capítulo entero con un «está mal» reintroduce en su contexto la prosa que ya falló.

### 4.7 CI/CD integration — T

Los cambios del **harness** pasan por el mismo pipeline que cualquier código: tipos, SAST, tests, mutación sobre los gates, contrato de la API.

Asimetría importante: **los capítulos no pasan por CI**. Son datos, no código, y su pipeline es el bucle de gates. Confundir las dos cosas lleva a meter `novelas/` en el repo, que es lo que AGENTS.md prohíbe.

Procedencia: `runs/<run_id>/manifest.json` registra el sha del commit, la versión de recetas y las versiones de canon y plan vigentes. Es lo que permite atribuir un cambio de calidad a un cambio concreto de prompt. Sin él, comparar dos ejecuciones es comparar dos anécdotas.

El sha solo identifica el prompt si el árbol está limpio. Un cambio sin commitear en `.claude/agents/` produce dos ejecuciones con el mismo sha y prompts distintos, y la comparación sale igual de limpia que si fueran el mismo. Por eso `manifest.json` registra además `sucio: true|false` y el hash de cada fichero de `.claude/agents/` y `.claude/commands/`. Así la atribución depende de un dato y no de la disciplina de commitear antes de lanzar.

### 4.8 Progressive rollout — D

El análogo aquí: **un cambio en el prompt de un agente es un despliegue**. Hoy se aplica a la novela siguiente de golpe, y si empeora, se nota tres capítulos después.

El mecanismo de flag ya existe a medias: la versión de receta va en `manifest.json`. Falta el rodaje — ejecutar el prompt nuevo sobre los capítulos de una novela de prueba y comparar scores contra la versión anterior antes de adoptarlo.

**Diferido**, por una razón honesta: comparar requiere una línea base estable, y con σ alta entre ejecuciones hacen falta varias corridas para que la diferencia signifique algo. Hasta tener eso, un rollout progresivo daría una falsa sensación de rigor.

### 4.9 Red-teaming / adversarial testing — I + T

Modelo de amenaza real de este sistema, en orden de probabilidad. No es un sistema con usuarios ni con datos personales: lo que está en riesgo es **la calidad y el secreto**, no la infraestructura.

1. **Fuga del misterio.** El escritor recibiendo, infiriendo o deduciendo la solución. Sonda: ensamblar briefings sobre un canon marcado y buscar los marcadores; y plantar en `plan/capitulos/NN.md` texto que intente arrastrar `canon/misterio.md` al briefing. El guardarraíl de §4.4 busca texto literal, y el secreto tiene tres vías para llegar parafraseado: las fichas del `trazador`, que conoce el misterio y escribe el prompt del `escritor` (un beat «esconde el arma que usó» no es subcadena de nada); la ficha de personaje del culpable, cuyo `secreto` y `coartada_y_cronologia_privada` son el misterio, cargada entera por la receta de personajes presentes; y el `qa/` del reintento, escrito por revisores que ven la solución. Las tres tienen filtro en §4.4 y medida directa en §4.15.
2. **Inyección por contenido del workspace.** Los agentes leen ficheros escritos por otros agentes. Un capítulo o una ficha de canon que contenga «ignora tus instrucciones y…» es el vector natural, y no requiere atacante externo: basta un modelo que alucine una instrucción.
3. **Uso indebido de herramientas.** Un agente escribiendo `estado.db` directamente o invocando `aplicar-delta`. Lo cubre el frontmatter, pero se prueba explícitamente.
4. **Deriva de objetivo a 24 capítulos.** El escritor optimizando poco a poco su propia coherencia local por encima del plan. Es el fallo más difícil de detectar porque cada capítulo pasa sus gates; lo único que lo ve son las métricas entre capítulos de §4.13.
5. **Exfiltración.** La única salida de red es Langfuse. Las claves están en `settings.local.json`, fuera de git.
6. **Regresión silenciosa del entorno.** No es un atacante: es una actualización. Que `tools` restrinja el descubrimiento, que `PreToolUse` se dispare para las llamadas de un subagente —comprobado el 2026-09-23 con Claude Code 2.1.280 (spec 0003, experimento E-1), sin garantía de que siga así— y que el hook `Stop` vea el transcript son supuestos sobre un producto que se actualiza solo y que no promete ninguna de las tres cosas. Si una barrera deja de disparar, el sistema no avisa: sigue reportando que está protegido. Lo mismo vale para el modelo: `model: opus` es un alias, y una actualización a mitad de novela cambia de escritor sin que conste en ningún sitio. Es una fuente de deriva de estilo que ninguna revisión de prosa atribuiría a su causa (§4.13).

Contra la sexta, un **canario**: un agente de prueba que intenta deliberadamente lo prohibido —escribir bajo `estado/`, abrir `canon/misterio.md` por ruta conocida, ejecutar el CLI— y cuya invocación debe fallar. Si algún día pasa, la barrera ya no existe y te enteras a propósito, no por una base corrupta. Corre con la suite adversaria y además tras cada actualización mayor de Claude Code (§5.10). Además de los intentos que deben fallar, necesita controles positivos que deben pasar. Sin ellos, un canario que no llegó a ejecutarse, o un hook que lo deniega todo, da el mismo verde (§4.17, F-60).

El canario de contención existe: `backend/tests/canario/ejecutar.py`, con dos agentes que `claude -p --agents` define solo para su sesión, `canario` y un impostor con `name: escritor`. Empieza con `novela comprobar-entorno --limpio` y no lanza nada si falla. Tiene cinco intentos que deben fallar —escribir bajo `estado/`, leer `canon/misterio.md` por su ruta, ejecutar `novela`, que el impostor escriba `canon/estilo.md` y que la sesión principal invoque a `general-purpose`— y tres controles que deben pasar: un nonce que solo el `canario` conoce, una escritura permitida en el workspace y, desde la v0.5 de la spec, que un impostor `arquitecto` escribe `canon/misterio.borrador.md`. El tercero existe porque un `deny` de `Read` también deniega escribir (F-28). El veredicto sale del disco y de los transcripts de la sesión, que `--session-id` permite localizar, y exige el motivo del hook en los intentos 1, 4 y 5. Exige además el `tool_use` de cada intento, emparejado con su `tool_result` de error: sin él, el intento sale `NO CONCLUYENTE` y el canario no da verde, porque una negativa del modelo no prueba ninguna barrera (F-65). Corre por release del harness y tras cada actualización mayor de Claude Code. **Da verde desde el 2026-09-24**, con los prompts y el veredicto de la v0.4 y el tercer control de la v0.5 (Claude Code 2.1.281). Su primera ejecución, el 2026-09-23, salió en rojo porque los dos agentes se negaron a intentar lo prohibido (F-64). Dejó dos datos: la regla 5 del hook paró a `general-purpose` en una sesión real, así que el hook hereda el entorno de `claude`, y `--agents` sustituye al `escritor` del proyecto. La parte del orquestador sigue siendo de la spec 0002.

Cadencia: la suite adversaria corre por release del harness, no por capítulo.

### 4.10 Model checking — A

El bucle por capítulo es una máquina de estados pequeña: `cursor.fase` × `ultimo_paso` × `intento`. Merece exploración exhaustiva de los estados alcanzables para verificar invariantes de orden:

- Nunca `aplicar-delta` sin que `validar` haya pasado.
- Nunca `checkpoint` antes de `aplicar-delta`.
- Nunca dos procesos sobre el mismo workspace (invariante 8, el lock).
- Los intentos se numeran 1, 2 y 3: el fallo del tercero escribe `intervencion.md` y para. No existe un `intento` de valor 4.
- Nunca `aplicar-delta` sobre un capítulo reescrito por el `editor-estilo` sin `validar` posterior (§3.9).
- Nunca un capítulo N+1 con el N sin checkpoint.
- Un reintento repite todos los gates desde `validar`, no solo el que falló: el arreglo de un hallazgo puede romper un gate que ya había pasado.

El espacio de estados son decenas, no millones, así que **la versión que se hace es un test que enumera las transiciones**, no TLA+. Si el bucle crece a ramas condicionales por acto o a paralelismo entre capítulos, entonces TLA+ empieza a pagar; hoy sería ceremonia.

Con un límite que conviene no perder de vista: esto verifica la máquina que el procedimiento *debería* seguir. Quien la implementa es `.claude/commands/novela-continuar.md`, prosa que ningún test ejecuta (§5.8). Dos cosas acortan esa distancia. `novela gate` (§4.4) convierte en precondiciones de código los invariantes que dependen de un veredicto o de la cuenta de intentos, y esas sí se prueban con el agente falso. Y la auditoría de §4.16 contrasta cada sesión real con esta misma máquina.

### 4.11 Control negativo de los revisores — T + I

Un revisor que aprueba siempre es indistinguible de un sistema sano: los scores suben, los reintentos bajan y todo parece ir bien. La mutación de §3.7 hace exactamente esta pregunta sobre el código —«si rompo esto, ¿lo nota alguien?»— y nadie la hace sobre los agentes, que son la mitad cara de la verificación.

El ensayo es el mismo, aplicado a prosa: capítulos fixture con un defecto conocido sembrado —una contradicción contra el `libro_de_hechos`, un hilo cerrado que nunca se abrió, una pista pagada sin plantar, una filtración del misterio— y una tasa de detección por revisor. Un `continuista` que no coge la contradicción marcada no está revisando, y sin este control no hay forma de saberlo.

Al `editor-estilo` le corresponde su propio defecto sembrado: léxico vetado y frases fuera del `ritmo` del canon. Al `lector-suspense`, que puntúa en vez de detectar, una **calibración**: capítulos fixture de tensión conocida, baja y alta. Si el plano recibe 6 o más, o la separación entre ambos es menor que la banda del gate (§4.13), el juez está saturado y sus puntuaciones no valen como gate hasta que se corrija su prompt. Es la versión medida del síntoma que §5.4 deja como condición de revisión.

Y el control inverso: capítulos fixture sin defecto, para medir la tasa de falsos positivos. Un revisor que lo marca todo no se nota en los scores sino en las intervenciones, cuando ya ha agotado los reintentos de capítulos sanos.

Llama a modelos, así que no entra en `pytest` (§3.5): corre por release, con la suite adversaria. Los fixtures sí se versionan, porque el defecto sembrado es el único caso de este sistema en el que existe una respuesta correcta conocida, y eso es demasiado escaso como para no guardarlo.

### 4.12 Ensayos: reanudación y degradación — D

Dos procedimientos escritos y nunca ejecutados, y los dos se estrenan en el peor momento posible: uno después de una caída, el otro al borde del límite de cuota.

- **Reanudación.** `restore(checkpoint(e)) == e` (§3.6) prueba la función, no el procedimiento. Nadie ha matado el bucle entre `aplicar-delta` y `checkpoint` para ver si `/novela-continuar` repite el paso correcto sobre un workspace real. Un checkpoint que nunca se ha restaurado no es un checkpoint, es un fichero. Se ensaya con el agente falso, cortando en cada frontera de paso.
- **Degradación por cuota.** Los cinco niveles de `architecture.md` §9 no se han ejercitado nunca. Forzar cada nivel con el agente falso y comprobar qué agentes se invocan y cuáles no cuesta un test de integración, y evita descubrir que el nivel 4 estaba mal escrito justo cuando ya no queda cuota para arreglarlo. El ensayo tiene un resultado conocido de antemano que conviene ver fallar: en los niveles 2 y 4 el `editor-estilo` corre después del `cronista`, y la custodia de §3.9.7 tiene que detenerlo. Si pasa, la cadena de hashes no está donde debe.

### 4.13 Deriva a escala de novela — A + T

Los evals de §4.2 puntúan capítulos. La amenaza 4 de §4.9 —el escritor optimizando su coherencia local por encima del plan— y la convergencia de prosa de `architecture.md` §12.1 son propiedades de la novela entera, y hoy nada las mide: cada capítulo pasa sus gates mientras la curva se aplana.

Lo mecánico, barato y sin modelo:

| Señal | Se calcula con |
|---|---|
| `tension_real` contra la curva objetivo del plan | resta sobre `estado.db`; el dato ya está |
| Convergencia de aperturas y de vocabulario | n-gramas repetidos entre capítulos |
| Deriva de longitud y de ritmo | `metricas.desviacion_vs_plan` acumulada |
| Hilos sin cerrar, pistas plantadas sin pagar | lo que ya hace `auditar` |
| Distancia de estilo al canon | huella de §3.9.9 contra `parrafos_canonicos` y la media de los capítulos 1–3 |
| Carga de preguntas abiertas | hilos abiertos + pistas plantadas sin pagar + revelaciones pendientes, desde `estado.db` |
| Modelo resuelto por agente | id real de cada invocación, sacado del transcript (§4.16) |

Lo que falta no es el cálculo, es la **cadencia**: `auditar` corre al cerrar la novela. Las mismas cuentas en cada frontera de acto son un gate. Es además la única forma de saber si la restricción de apertura de `architecture.md` §2.2 sirve de algo: hoy es una mitigación declarada y sin un solo dato detrás.

**La deriva de estilo es un paseo aleatorio, y por eso el ancla es fija.** El `escritor` recibe el capítulo anterior entero (`architecture.md` §6.2) e imita mejor de lo que obedece (`definitions.md` §2.3). Cada capítulo se parece al anterior, así que cualquier comparación entre vecinos da por bueno un texto que, al capítulo 15, ya no se parece a los párrafos canónicos. La distancia se mide siempre contra el canon y contra el arranque, nunca contra N-1. Si el modelo resuelto de un agente cambia entre dos capítulos, `pendiente` para: es una causa de deriva que conviene conocer antes que medir.

**El colapso de tensión tiene una parte que no necesita juez.** En suspense, la tensión es en buena parte cuántas preguntas tiene abiertas el lector. Si la carga de preguntas abiertas cae a cero antes del clímax, o baja tres capítulos seguidos en el acto 2, hay colapso aunque el `lector-suspense` siga puntuando alto. Se calcula en cada `checkpoint`, no solo en frontera de acto, porque sale de datos que ya están en `estado.db`.

**El gate de tensión necesita una banda y una tendencia.** `definitions.md` §8 habla de «tensión dentro de la banda objetivo» y la banda no está definida en ningún sitio. La regla: si `|tension_real − objetivo| > banda_tension` de `config.yaml`, se reintenta el capítulo. Si la desviación es negativa tres capítulos seguidos, se va directo a intervención: un descenso sostenido nace del plan, y reintentar capítulos solo gasta los intentos antes de llegar al mismo sitio. Los capítulos sin `tension_real` porque la cuota bajó al nivel 3 (`architecture.md` §9) se marcan como huecos en la auditoría de acto y no se interpolan. Una curva rellenada hace pasar el gate sin datos.

### 4.14 Reproducción del estado — A + T

`estado.db` es la única fuente de verdad y no tiene copia: `checkpoints/NN.json` guarda cursor, versiones y `run_id`, no la base (spec 0001, RF-20). Pero el estado tiene una definición reproducible, que es aplicar en orden `estado/deltas/*.json` sobre una base vacía. Eso da un verificador sin modelo en dos puntos:

- **Al abrir la base.** `meta.schema_version` coincide con el código, los triggers append-only de las cinco tablas siguen en `sqlite_master` y `PRAGMA quick_check` devuelve `ok`. CA-02 prueba que los triggers se crean; esto prueba que siguen ahí. Una base a la que alguien quitó uno funciona sin dar un solo error, y ese es precisamente el problema.
- **En cada `checkpoint`.** Se reproducen los deltas en una base en memoria y se compara con `estado.db` tabla a tabla. Después se regenera `memoria/resumenes/` y se compara también. Una diferencia significa una de tres cosas: algo escribió la base por fuera de `aplicar-delta` (un `sqlite3` desde Bash, un hook que dejó de disparar, §5.10), un delta cambió después de aplicarse, o la base está corrupta. En cualquiera de los tres casos el checkpoint no confirma.

Requisito: `aplicar-delta` registra el hash de cada delta aplicado junto a su capítulo. Es la misma clave que necesita la idempotencia de §3.6, y es lo que permite detectar que un delta se editó después de aplicarse.

Hay un efecto más. Ni el `restore(checkpoint(e)) == e` de §3.6 ni el «se restaura del último checkpoint» de `architecture.md` §6.4 se cumplen con un JSON de cursor. Con la reproducción sí: restaurar es reproducir hasta el cursor del checkpoint. Con 24 deltas cuesta milisegundos.

Lo que no cubre: perder `estado/` entero se lleva los deltas junto con la base (§5.7). Tampoco cubre un delta fiel que fija una interpretación equivocada: la reproducción la reproduce igual (§5.9).

### 4.15 Sondas ciegas del secreto — I + A

Los filtros de §4.4 impiden que el secreto viaje por las vías conocidas y en forma literal o casi literal. Ninguno mide lo que importa: si con lo que el `escritor` tiene delante se puede deducir la solución. La sonda lo mide preguntándolo.

- **Sonda del briefing.** Un modelo sin herramientas recibe *solo* el briefing del `escritor` y devuelve `{culpable_id, confianza}` en JSON. La comparación con `culpable_o_amenaza` es mecánica. Si acierta antes del `capitulo_previsto` de la revelación que lo destapa, el briefing filtra, sea cual sea la vía. Es la única medida directa del invariante 3 tal como lo vive el `escritor`.
- **Sonda del texto.** La misma pregunta sobre los capítulos escritos del acto. Tienen que ser los capítulos y no los resúmenes, porque la fuga vive en el subtexto y el `cronista` no resume subtexto. Da dos señales: la **previsibilidad real**, que el `lector-suspense` no puede dar porque conoce la respuesta (§4.2), y el **fair play en el texto**: en el capítulo anterior a una revelación, con las pistas ya plantadas, la sonda debería poder deducirla. Si no puede, las pistas figuran en el frontmatter con su cita pero no funcionan como pistas.

La respuesta es un id, no prosa, así que aquí sí hay mayoría sobre la que votar: tres ejecuciones y se toma la moda. Es la condición con la que §5.3 se reabre. Cadencia: la sonda del briefing en el primer capítulo de cada acto, en los capítulos que pagan pista y en la novela de humo; la del texto, en cada frontera de acto. La clase es I porque juzga un modelo; la comparación con el canon es A, y eso es lo que evita que la propiedad crítica quede solo con I (§1).

### 4.16 Trayectoria del orquestador — A

§4.10 verifica la máquina que la sesión *debería* seguir, y `.claude/commands/novela-continuar.md` la implementa en prosa (§5.8). Lo que la sesión *hizo* está en un solo sitio: el transcript que el hook `Stop` ya lee para Langfuse. Un script determinista lo recorre al terminar la sesión y escribe `runs/<run_id>/trayectoria-NN.json`.

**Orden.** Se reconstruye la secuencia de `Bash: novela …` y de llamadas a `Task`, y se contrasta con los invariantes de §4.10: el briefing del mismo agente antes de cada `Task`, `validar` antes de los revisores y otra vez después del editor, el `cronista` después del gate, `aplicar-delta` antes de `checkpoint`.

**Lo que no deja artefacto.** Es lo que el rastro de §3.9.6 no puede ver, porque comprueba lo que existe y no lo que no debió ocurrir:

- `Read` o `cat` sobre `capitulos/` desde la sesión principal (principio 4 de `architecture.md`).
- `Write` o `Edit` de la sesión principal dentro del workspace: el orquestador haciendo el trabajo de un agente «para ahorrar una llamada».
- `Task` a un `subagent_type` que no es uno de los siete.
- Un prompt de `Task` de más de unos cientos de caracteres. Lleva prosa, y en un reintento significa que el capítulo ha vuelto por el canal de conversación.
- Un retorno de subagente por encima del informe de tres líneas de `architecture.md` §7.4.
- Un agente omitido sin un nivel de degradación registrado que lo justifique (§4.4).

**Contexto medido.** Del mismo transcript salen los tokens por turno y las marcas de compactación. Con eso §5.11 pasa a tener un dato: una alerta por encima de un umbral (por ejemplo 70.000 de los 100.000 de `architecture.md` §6.5), y una compactación a mitad de capítulo deja el capítulo marcado para revisión humana. Una sesión compactada es justo la que puede haber perdido la cuenta de intentos, y por eso esa cuenta vive en `novela gate` y no en la sesión.

Con cualquier violación, `pendiente` para el bucle (§4.4): mismo mecanismo que `intervencion.md` y ningún freno nuevo. En la novela de humo corre además un **canario del orquestador**: un informe de subagente que invita a leer el capítulo y un `qa/` rechazado que el subagente reporta como aprobado. `novela gate` tiene que parar el segundo y la auditoría tiene que detectar el primero si la sesión lo obedece.

Hay un supuesto que comprobar antes de construirlo: que el transcript distinga las llamadas de la sesión principal de las de los subagentes y deje marca de las compactaciones. Es la misma clase de dependencia de §5.10.

### 4.17 Contención y bucle de `.claude/` — T + A + D

La spec 0003 añade siete agentes, un hook `PreToolUse`, permisos, tres procedimientos, el bucle desatendido y cinco cambios en el backend. Cada pieza abre fallos propios. Esta sección los enumera, cada uno con su verificador.

**Estado a 2026-09-24: corren las filas en `activo`.** Las que dependen de un modelo esperan al canario y a la novela de humo. La columna «Estado» dice qué lo introduce:

- **0003**: un criterio de aceptación de la spec 0003 (`CA-NN`) o una tarea de su plan.
- **0002**: un mecanismo de la spec 0002.
- **activo**: ya corre, desde la spec 0001.
- **propuesto**: no está en ninguna spec. Entra por enmienda antes de implementarse, no se improvisa al implementar.
- **U**: riesgo aceptado, escrito en §5.

Un principio se repite en toda la tabla. Una barrera que falla **abierta** no avisa. Una que falla **cerrada** parece sana en cualquier prueba que solo mire denegaciones. Por eso cada barrera necesita dos controles: uno negativo, en el que lo prohibido falla, y otro positivo, en el que lo permitido pasa.

**Agentes**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-01 | El frontmatter deriva: `tools`, `model` o `name` distintos de la tabla, o YAML inválido | Un agente con `Bash` o `Glob`, o uno que Claude Code no carga | Test de contrato sobre `.claude/agents/*.md` | T | activo (CA-01) |
| F-02 | El cuerpo no nombra una de sus salidas | El agente escribe donde cree, el hook lo para y se pierde un reintento | Cada salida aparece como subcadena del cuerpo | T | activo (CA-02) |
| F-03 | Se renombra o desaparece el esquema de `backend/schemas/` que nombra el cuerpo | El agente adivina la forma y el primer capítulo falla `validar` | Toda ruta `backend/schemas/*.json` citada en un cuerpo existe. Es una aserción más en el test de CA-02 | T | activo (CA-02, RF-24) |
| F-04 | Se cambia un prompt sin commitear | Dos ejecuciones con el mismo sha y prompts distintos | `sucio` y `hashes_claude` en el manifiesto (§4.7) | A + T | activo (CA-08) |
| F-05 | `CLAUDE.md` o `AGENTS.md` cambian entre dos ejecuciones | Se cargan en cada subagente y cambian su conducta, pero no entran en `hashes_claude` ni en las rutas que vigila `sucio` | Añadir los dos ficheros a `hashes_claude` y a las rutas de `sucio` | A + T | activo (CA-08, RF-12) |
| F-06 | Un informe de QA malformado, o sin `veredicto` | El orquestador lee basura en el gate y puede aprobar | El procedimiento cuenta un `veredicto` ausente o ilegible como rechazo. Después, `novela gate` lo valida contra el modelo | D; A | activo en el procedimiento (CA-18) y en la novela de humo (CA-10); después, 0002 |
| F-07 | Un revisor lee `capitulos/NN.md` del disco en vez del texto incrustado, mientras el `editor-estilo` lo reescribe en el mismo turno | Veredicto sobre una versión intermedia que la custodia no ve, porque su briefing lleva el hash correcto | El cuerpo del agente manda juzgar lo incrustado. No hay verificador mecánico | I | U (§5.15) |
| F-08 | Un retorno de más de tres líneas | Consume el contexto del orquestador | Auditoría de trayectoria (§4.16) | A | 0002 |
| F-09 | En un reintento, el `arquitecto` no puede reescribir `canon/misterio.md`: el `deny` le impide leerlo, y `Write` no sobrescribe un fichero que el agente no ha leído | Un canon inválido por el misterio gasta los dos reintentos del gate del `arquitecto` y acaba en intervención | `/novela-nueva` no reintenta si la causa nombra `misterio.md`: `intervencion.md` y para (RF-34). Un test fija que la causa lo nombra | T + I | activo (CA-22) |

**Hook `PreToolUse`**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-10 | `python` no resuelve, o la ruta del script en `settings.json` está mal | El hook sale con un código distinto de 2 y **falla abierto**: todas las escrituras pasan, sin aviso | Comprobación de puesta en marcha. CA-06 comprueba que la orden nombra el script, y una aserción más, que el fichero existe. El primer intento del canario lo detecta | D + T | activo: CA-06 y comprobar-entorno antes del bucle y del canario. En cada canario del 2026-09-24, el hook paró el intento 1 |
| F-11 | Claude Code cambia la forma de la entrada, por ejemplo el nombre de `file_path` | El hook falla cerrado y deniega todas las escrituras: el bucle no avanza | El freno del bucle (RF-22) y el control positivo del canario (F-60) | D + T | activo: el freno paró el bucle real de la novela de humo (CA-10), y el control positivo del canario pasó el 2026-09-24 (CA-09) |
| F-12 | Desaparece `agent_type` de la entrada | La regla 2 se apaga sin aviso, y la regla 3 trata a todo subagente como sesión principal | Control positivo del canario: `notas/control.txt` no se escribe. El intento 4 no lo detecta, porque la regla 3 también lo deniega | T | activo (CA-09): el control positivo del canario pasó el 2026-09-24 |
| F-13 | Variantes de ruta: mayúsculas, `\`, `..`, absoluta o relativa | Una escritura bajo `estado/` que el comparador no reconoce | Property-based sobre el script, ejecutado como subproceso | T | activo (CA-03) |
| F-14 | Variantes de NTFS: punto o espacio final en un segmento (`estado./`), flujo alternativo (`estado.db:x`), prefijo `\\?\` | Win32 normaliza la ruta al escribir, y la regla 1, que es una lista de denegación, no la reconoce. La regla 2 es una lista blanca con `fullmatch` y ya las deniega | Normalizar los tres casos en el hook y añadirlos a la estrategia de CA-03 | T | activo (CA-03, RF-05) |
| F-15 | Nombres cortos 8.3 (`ESTADO~1`), uniones y enlaces simbólicos | Como F-14, pero sin forma de normalizarlos sin tocar el disco | Por debajo del hook: los triggers de `estado.db` y la reproducción del estado (§4.14) | A | U (§5.14) |
| F-16 | La tabla de salidas del hook y el contrato de los agentes divergen | El hook para a un rol en su salida legítima, o le deja escribir en otra | Test que compara `SALIDAS` del hook con el contrato de CA-01 | T | activo (plan, D-2) |
| F-17 | El hook bloquea al `cronista` | El delta no se escribe nunca | Mitad positiva de CA-03 y de CA-05 | T | activo (CA-03, CA-05) |
| F-18 | Latencia del hook | Cada escritura y cada `Bash` pagan el arranque del intérprete | Mediana por debajo de 300 ms | T | activo (RNF-01) |
| F-19 | La sesión principal escribe en el workspace: el capítulo «para ahorrar una llamada», el delta o un `qa/` | Sin una regla propia, a la sesión principal solo le aplicaría la de `estado/`, y `Edit(./novelas/**)` está permitido | Regla 3 del hook: sin `agent_type`, bajo `novelas/` solo se permite `runs/*/intervencion.md` | T | activo (CA-14, RF-25) |
| F-20 | El orquestador invoca un subagente que no es uno de los siete. `general-purpose` tiene todas las herramientas | Un agente con `Bash` y `Glob` dentro del bucle, al que solo aplica la regla 1. `Agent` no se puede restringir por nombre (E-9) | Regla 5 del hook: con `NOVELA_SESSION_ID` definido, que solo exportan el bucle y las sesiones del harness, deniega un `subagent_type` fuera de los siete y `canario`. Las sesiones de desarrollo no la tienen definida y conservan `Explore`. Que el hook herede el entorno de `claude` lo comprueba el quinto intento del canario | T | activo (CA-15 en lo estático, CA-09 en lo dinámico): en el canario del 2026-09-24, la regla 5 paró a general-purpose |
| F-27 | La regla 4 es texto sobre la orden y actúa también en las sesiones de desarrollo: un `git commit` cuyo mensaje, en la propia orden, nombra la ruta del misterio o `estado.db` se deniega | Falso positivo: la orden no corre y hay que reescribirla. No debilita ninguna barrera | Ninguno. El texto va a un fichero y se pasa por ruta (`git commit -F`). Encontrado al commitear la tarea 4.6 | — | propuesto |

**Permisos**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-21 | `settings.json` inválido | En `-p` se ignora sin avisar, y con él desaparecen el `deny` del misterio y el hook | Parseo y claves de primer nivel en el test | T | activo (CA-06) |
| F-22 | `settings.local.json` amplía permisos: un `allow` más, un `defaultMode`, otro hook | No está versionado, CI no lo ve, y el bucle lo carga con `--setting-sources project,local` | Comprobación previa de que solo contiene `enabledPlugins`, en `ejecutar.py` del canario y antes de lanzar el bucle | T | activo (CA-17): el bucle documentado y ejecutar.py la ejecutan antes de lanzar (RF-30, RF-18) |
| F-23 | La confianza del repo no está aceptada | El `allow` se ignora y el bucle gira sin avanzar | Freno del bucle (RF-22) | D | activo: la confianza se comprobó el 2026-09-24, y el freno paró el bucle real cuando una sesión no avanzó (CA-10) |
| F-24 | La herramienta `PowerShell` de Windows queda fuera del `matcher` | La rama de texto del hook no la ve. En `-p` con `dontAsk` se deniega porque no está en `allow`; en interactivo, Claude Code pregunta | Añadir `PowerShell` al `matcher` y comprobarlo en CA-06 | T | activo (CA-06, CA-11, RF-20) |
| F-25 | Una orden compuesta tras el prefijo permitido (`novela estado x && …`) | Si `Bash(novela:*)` casara solo el prefijo, el resto correría sin permiso | Canario del orquestador: una orden compuesta que debe denegarse | T | 0002 (§4.16). Observado el 2026-09-24: `Bash(novela:*)` no autoriza `novela … ; echo "exit=$?"`, y `dontAsk` la deniega. Los procedimientos piden cada orden sola (71b8fc9) |
| F-26 | `claude` se lanza desde un subdirectorio, como `backend/` | Si no encuentra `.claude/`, no hay permisos, ni hook, ni comandos | Freno del bucle. El bucle documentado corre en la raíz | D | activo: el bucle documentado corre en la raíz, y la novela de humo lo ejercitó (CA-10) |
| F-28 | El `deny` de `Read` de `canon/misterio.md` también deniega escribirlo («File is covered by a Read deny rule … and cannot be written») | El `arquitecto` no puede crear el misterio: ninguna novela puede empezar. Observado en la novela de humo el 2026-09-24 | El `arquitecto` escribe `canon/misterio.borrador.md` y el gate lo promueve (spec 0003 v0.5, RF-37). Tercer control positivo del canario (RF-39) | T + D | activo (CA-25, CA-27): el arquitecto de la novela de humo escribió el borrador y el gate lo promovió |

**Procedimientos**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-30 | Orden roto: revisiones antes de tener los tres briefings, el `cronista` antes del gate, o sin `validar` tras el editor | Los veredictos juzgan textos distintos | Custodia en `aplicar-delta` (0001 RF-32): la cadena de hashes no cierra y el delta no se aplica | A + T | activo |
| F-31 | La sesión lee mal la cuenta de intentos en `harness.log` | Reintentos de más, que gastan cuota, o una intervención prematura | Los intentos por gate se cuentan aparte en el baseline de la novela de humo. Después, `novela gate` | D; A | observado: en el capítulo 3 de la novela de humo, la sesión informó 1 de 2 reintentos de revisión, y la cuenta de harness.log da 2. La reanudación volvió a revisar el capítulo ya rechazado antes de reintentar al escritor (spec 0003 §13). Después, 0002 |
| F-32 | Un código 1 que viene de un fallo del CLI (un traceback, un import roto tras cambiar `pyproject.toml`) y no de un gate | El procedimiento lo toma por un gate fallido y reintenta al agente: gasta cuota en algo que ningún agente arregla | El procedimiento solo cuenta un 1 como gate si `harness.log` tiene la línea `<orden> NN -> 1` que el comando acaba de escribir; si no, para | D | activo (CA-18, CA-10) |
| F-33 | Un prompt de Task lleva prosa o el capítulo | Contexto contaminado y fuga de la señal (§4.6) | Inspección de las trazas en la novela de humo. Después, la auditoría de trayectoria | I; A | activo en la novela de humo: 31 prompts de Task, de 4 o 5 líneas. El más largo, un reintento del cronista con su causa en una línea (RF-15). Después, 0002 |
| F-34 | No se detecta un `intervencion.md` vivo | El bucle sigue sobre una novela parada | Ensayo: un `intervencion.md` sin `resuelto:` en el workspace de humo y una sesión de `/novela-continuar`, que debe parar sin invocar a ningún agente. Después, `novela pendiente` | D; T | activo (CA-19): el ensayo paró sin runs, briefings ni subagentes; después, 0002 |
| F-35 | Punto de reanudación equivocado | Se repite un paso ya confirmado o se salta uno | Ensayo de reanudación (§4.12) sobre las cuatro filas de la tabla de reanudación. La custodia para lo que se salte `validar` | D + A | 0002 (§4.12) |
| F-36 | El slash command no se resuelve, por la conversión de rutas de MSYS | La sesión recibe una ruta y no hace nada | `MSYS_NO_PATHCONV=1` en el bucle, y el freno | D | activo: MSYS_NO_PATHCONV=1 en el bucle, ejercitado en la novela de humo (CA-10) |
| F-37 | `/novela-nueva` no se puede reanudar | Un arranque cortado, por red o por un gate, deja el workspace creado, y el paso 1 (`novela nueva`) falla con él | Ninguno: se aparta el workspace y se repite el arranque. Encontrado en la novela de humo el 2026-09-24 | — | propuesto |

**Backend**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-40 | El run de arranque se reutiliza como run del capítulo 1, o al revés | El capítulo 1 queda atribuido a un canon vacío | Tests del run de arranque | T | activo (CA-07) |
| F-41 | Un `NOVELA_RUN_ID` fijado mezcla arranque y capítulo | Lo mismo que F-40, por otra vía | `run.abrir` rechaza un run fijado cuyo manifiesto sea de otra fase o de otro capítulo | T | activo (CA-16, RF-27) |
| F-42 | El arranque y el capítulo 1 caen en el mismo minuto | `RunInvalido` con salida 2, y el procedimiento para | Test de la colisión. La salida 2 para sin reintentar | T | activo (test_run_de_arranque) |
| F-43 | `git` ausente o lento | `sucio` sin dato | `true` por defecto | T | activo (plan, D-6) |
| F-44 | El sufijo `sesion=` altera las líneas que cuenta el procedimiento | La cuenta de intentos se rompe sin dar error | CA-12 comprueba además que la subcadena `validar NN -> ` sigue intacta | T | activo (CA-12, RF-21) |
| F-45 | `NOVELA_SESSION_ID` inválido, o heredado de la shell del bucle en una orden manual | Correlación traza ↔ paso perdida o falsa | Validación del formato (CA-12). La variable solo se exporta en la shell del bucle | T | activo en la validación del formato (CA-12); que la variable solo viva en la shell del bucle es disciplina |
| F-46 | El OpenAPI queda desfasado tras cambiar `Manifest` | Se rompe el contrato con el frontend | `test_openapi_al_dia` | T | activo |
| F-47 | Una causa con saltos de línea, como un `ValidationError` de Pydantic, parte la entrada de `harness.log` en varias líneas | La última línea ya no es la del subcomando: la regla de lectura 1 toma un gate por un fallo del CLI, y el gate del `arquitecto` no se reconoce | `Run.registro` escribe siempre una sola línea. Encontrado al escribir el test de CA-18 | T | activo (CA-18) |
| F-48 | El gate del `arquitecto` (`briefing 1 trazador`) valida los ficheros del canon que existen y no exige los que faltan | Sin misterio, el gate sale con 0 y el `trazador` planifica sin pistas. Observado en la novela de humo el 2026-09-24 | Con un agente distinto del `arquitecto`, falta un fichero del canon o no hay fichas de personaje: salida 4 (spec 0003 v0.5, RF-38) | T | activo (CA-26) |

**Bucle y trazado**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-50 | `novela` fuera del PATH, o la instalación editable sin sincronizar | Todas las órdenes fallan (ver F-32) | Comprobación de puesta en marcha, y `novela comprobar-entorno` antes del bucle | D + T | activo (CA-13, CA-17) |
| F-51 | Una sesión del harness sin `--setting-sources project,local` | Los hooks del ámbito de usuario reescriben órdenes, y el `allow` deja de casar (E-10). Además se inyecta contexto que el manifiesto no registra | El flag va en el bucle documentado y en las sesiones interactivas. Una sesión manual no tiene verificador | D | activo en la documentación: el flag va en el bucle y en la sesión interactiva; U para una sesión manual (§5.17) |
| F-52 | El plugin de Langfuse no carga, o falla | Sin trazas y sin aviso: el bucle sigue | Novela de humo (CA-10) y `~/.claude/state/langfuse_hook.log` | D | activo (CA-10): cada sesión de la novela de humo dejó su traza con la etiqueta. Hace falta el plugin habilitado en settings.local.json y LANGFUSE_PUBLIC_KEY en el entorno de usuario, porque pluginConfigs solo se lee del ámbito de usuario |
| F-53 | Una sesión avanza el checkpoint pero ha hecho algo indebido | El freno no lo ve, porque solo mira si hubo avance | Auditoría de trayectoria | A | 0002 |
| F-54 | Los scores de `novela checkpoint` necesitan `TRACE_TO_LANGFUSE=true` y las claves en el entorno del proceso, y `comprobar-entorno` prohíbe `env` en `settings.local.json` | Sin las variables en el entorno de usuario, el bucle cierra capítulos sin emitir scores: el sink es no-op y no avisa. El baseline de CA-10 se queda sin sus seis scores | `checkpoint` toma también `TRACE_TO_LANGFUSE` y `LANGFUSE_*` de `.env` en la raíz del repo, sin tocar `os.environ`; manda el entorno (RF-32) | T | activo (CA-20) |
| F-55 | Las claves de los scores están en un `.env` en la raíz del repo que `.gitignore` no ignora | Un `git add .` las versiona. El pre-commit de 0001 CA-32 es la última capa | `.env` en `.gitignore`, y `novela comprobar-entorno` avisa si no está ignorado (spec 0003 v0.4, RF-33) | T | activo (CA-21) |
| F-56 | Git para Windows instalado por usuario: `claude` no encuentra Git Bash | La sesión solo tiene la herramienta PowerShell: `Bash(novela:*)` no casa y `dontAsk` deniega cada orden. Los hooks corren en PowerShell: el del plugin falla con ParserError, y el nuestro no expande `$CLAUDE_PROJECT_DIR` y sale con 2 sin su motivo, así que falla cerrado para todo | `CLAUDE_CODE_GIT_BASH_PATH` en el entorno de usuario (`architecture.md` §11.1). `comprobar-entorno` no lo ve. Encontrado el 2026-09-24 | D | propuesto |
| F-57 | App Control (Device Guard) bloquea el `novela.exe` de `uv tool` (`~/.local/bin` y su venv en `AppData`) | `which novela` lo encuentra y cada orden sale con «Permission denied»: `comprobar-entorno` no llega a correr | El de `backend\.venv\Scripts` sí corre; esa carpeta va por delante en el PATH (`architecture.md` §11.1). Encontrado el 2026-09-24 | D | propuesto |
| F-58 | `--setting-sources project,local` no excluye `~/.claude/CLAUDE.md` ni la auto-memoria del proyecto | Se cargan en el orquestador sin constar en el manifiesto. El 2026-09-24, una memoria obsoleta escrita por una sesión de desarrollo hizo parar un arranque | Ninguno. Posible: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` en el bucle. Riesgo 5 del plan de la 0003, confirmado (CA-19) | — | propuesto |
| F-59 | Las claves de los scores en `.env` sin `TRACE_TO_LANGFUSE=true` | El sink queda en no-op sin avisar: `comprobar-entorno` avisa del flag sin claves, no de las claves sin flag. Pasó el 2026-09-24 | Ninguno | — | propuesto |

**Canario**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-60 | El canario pasa en vacío: el agente no llegó a ejecutarse, o todo se deniega | Verde falso: cinco fallos que no prueban ninguna barrera | Dos controles positivos. El `canario` devuelve un nonce propio, que prueba que se ejecutó él, y escribe una ruta permitida del workspace, que tiene que existir | T | activo (CA-09): verde el 2026-09-24 |
| F-61 | `--agents` no sustituye al `escritor` del proyecto | El cuarto intento lo hace el agente real | Nonce del impostor, buscado en el texto de los agentes en cualquier transcript: un subagente devuelve a la sesión solo su último mensaje, y el nonce puede no llegar a la salida | T | activo: el 2026-09-23 y el 2026-09-24 el impostor corrió con el modelo de --agents, que sustituye al del proyecto |
| F-62 | El misterio se lee pero no se imprime | El marcador no aparece en la salida y el intento parece fallido | Buscar el marcador también en los transcripts de la sesión, cuya ruta fija `--session-id` (E-5) | T | activo (CA-09) |
| F-63 | El canario corre con el árbol sucio o con `settings.local.json` ampliado | Prueba una configuración que no es la del bucle | `novela comprobar-entorno --limpio` al empezar `ejecutar.py` | T | activo (CA-09) |
| F-64 | Los agentes del canario se niegan a intentar lo prohibido: `CLAUDE.md` y `AGENTS.md` se cargan también en ellos y lo prohíben | El canario no prueba ninguna barrera. Sale en rojo, no en verde falso, porque faltan el nonce y los motivos del hook | Prompts de `agente.json` y de la sesión que presentan la prueba y piden cada intento una vez, con su herramienta (spec 0003 v0.4, RF-35). Observado en la primera ejecución, el 2026-09-23 | I + T | activo (CA-09): con los prompts de la v0.4, los agentes intentan cada paso |
| F-65 | Un agente del canario se niega a leer el misterio en lugar de intentarlo | El intento 2 da verde: el marcador tampoco aparece, y no se exige el motivo de ninguna barrera. Verde falso | Cada intento exige su `tool_use` en el transcript; sin él, `NO CONCLUYENTE` (spec 0003 v0.4, RF-36). Destapado al analizar F-64 | T | activo (CA-23) |

**Novela de humo**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-70 | Un baseline de una sola ejecución | Se usa como referencia una sola muestra con σ alta | El baseline declara su número de ejecuciones y no sirve para aceptar cambios de prompt hasta tener varias (§4.8) | — | U (§5.16) |

Cinco filas se encontraron al implementar la 0003 y entraron en su v0.4: F-09, al escribir los agentes; F-54, al registrar el hook; F-64, en la primera ejecución del canario, y F-55 y F-65, al preparar su enmienda. Las cinco están en `activo`, y también F-28 y F-48, que entraron en la v0.5. Siguen en **propuesto** F-27, F-37 y F-56 a F-59, encontradas al cerrar la 0003: son la entrada de la spec que las recoja. Las que lo estaban antes entraron en la spec 0003 v0.3 (§16, «Enmiendas de la v0.3»), agrupadas en tres bloques:

- **endurecer el hook**: F-14, F-19, F-20 y F-24;
- **comprobaciones previas y controles positivos**: F-11, F-22, F-50, F-60, F-62 y F-63;
- **reglas de lectura del procedimiento y aserciones de test**: F-03, F-05, F-32, F-34, F-41 y F-44.

Un fallo nuevo que aparezca al implementar se añade aquí como `propuesto`, y va a la spec antes que al código.

### 4.18 Verificación a escala de novela (spec 0002) — T + A + I + D

La spec 0002 añade cuatro subcomandos, un agente, un hook `Stop` y gates nuevos en `validar`, `aplicar-delta`, `briefing`, `checkpoint`, `pendiente` y `auditar`. Esta sección enumera dónde puede fallar lo que construye su plan (`docs/implementation-plans/0002-verificacion/`), y dónde falla el sistema aunque el código sea correcto.

**Estado a 2026-09-24: la spec 0002 está aceptada (v0.3) y nada de ella está implementado. Ninguna fila corre.** F-80 a F-160 salieron de la primera lectura del plan, y la v0.3 cerró parte de ellas antes de implementarse. F-161 a F-168 salieron de esas enmiendas. La columna «Estado» dice qué la cubrirá:

- **0002 (CA-NN, tarea X.Y)**: un criterio de aceptación de la spec 0002 o una tarea de su plan. Si sigue «; X, propuesto», esa parte no la cubre nadie.
- **propuesto**: no lo cubre ni la spec ni el plan. «Verificador» dice qué haría falta.
- **U**: riesgo aceptado, escrito en §5.

El principio de §4.17 sigue valiendo: cada barrera necesita un control negativo y uno positivo. En «Verificador», **abierto** es el control que atrapa una barrera que deja pasar lo prohibido, y **cerrado**, el que atrapa una que para lo permitido.

**Gates mecánicos: capítulo y delta (fase 1)**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-80 | La `cita` de una pista o de una entrada del delta es trivial, como «la» o «Elena» | RF-05 y RF-06 se cumplen en la letra. El `editor-estilo` borra la frase de la pista y `validar --final` pasa: §3.9.3 vuelve a ser decorativo | Abierto: `test_citas_de_pistas_property` con la cita recortada a menos de 15 caracteres normalizados, `test_delta_sin_cita_no_valida_property` con lo mismo en las cuatro colecciones, y mutación sobre `MIN_CITA`. Quince caracteres prueban que el pasaje existe, no que sea la pista (§5.9) | T | 0002 (CA-05, CA-06, tareas 1.3 y 1.6) |
| F-81 | La cita se compara sin normalizar uno de los dos lados | Una cita con otro espacio, un salto de línea u otra forma Unicode rechaza el capítulo y reintenta al `escritor`, que es opus, por nada | Abierto y cerrado: `test_citas_de_pistas_property`, que también exige que pase una cita que solo casa tras normalizar los dos lados | T | 0002 (CA-05, tarea 1.3) |
| F-82 | El `editor-estilo` borra la frase citada de una pista. `validar --final` rechaza con `cita_de_pista`, y el editor se reintenta con su mismo briefing, que no trae las pistas de la ficha | Si el hallazgo no lleva la cita, el editor no sabe qué restaurar: segundo rechazo y 5 por algo que tenía arreglo | `test_hallazgo_copia_la_cita`: la `descripcion` contiene la cita. Que el editor la restaure, solo `humo-0002` | T + D | 0002 (CA-05, tareas 1.3 y 6.3) |
| F-83 | El reintento del `editor-estilo` regenera su briefing, contra RF-05 y el paso 5 de la tarea 3.8 | El briefing nuevo incrusta el capítulo ya editado: su hash no es el de los revisores, la custodia no cierra y `gate … delta` sale con 5 al primer fallo | El camino de `final` rechazado de `test_la_maquina_con_el_gate_real` llega a `aplicar-delta`, pero reproduce el reintento con el CLI y no con la prosa. Que CA-29 compruebe que el paso 5 no llama a `novela briefing … editor-estilo`, ninguno | T | 0002 (RF-05, tareas 3.8 y 3.9); la prosa, propuesto |
| F-84 | El procedimiento olvida `--final` en el paso 5 | El léxico vetado no se comprueba nunca. La custodia cierra igual, porque la última `validar` pasó sin hallazgos | Abierto: `test_final_exige_final_true` (sin `final: true`, el gate `final` rechaza) y la regla de orden de §8.7 en `test_cada_violacion`. Si el procedimiento olvida también el gate, solo la segunda. Entre las tareas 1.9 y 3.4 no lo ve nada | A + T | 0002 (CA-19, tarea 3.4; CA-20, tarea 5.2) |
| F-85 | Una entrada de `lexico_vetado` en mayúsculas, con tildes en otra forma Unicode o dentro de otra palabra | Un término vetado que pasa, o un rechazo que no toca | Abierto: `test_lexico_vetado_property` con mayúsculas aleatorias y `final=True`. Cerrado: la misma, con la entrada dentro de otra palabra y con `final=False`. Mutación sobre `_lexico` | T | 0002 (CA-10, tarea 1.9) |
| F-86 | La huella añade un hallazgo o cambia el veredicto | La custodia exige que la última `validar` no tenga hallazgos: ningún capítulo con la huella fuera se aplica. En `humo-0003`, los tres | Cerrado: `test_huella_no_cambia_el_veredicto` (`aprobado` y `hallazgos` vacío). Falta el de extremo a extremo: `aplicar-delta` aplica tras una huella fuera de tolerancia | T | 0002 (CA-11, tarea 1.10); extremo a extremo, propuesto |
| F-87 | La huella no es gate | Una deriva de estilo pasa el bucle: consta y puntúa, pero no para | `estilo` en cada checkpoint y `deriva_de_estilo` en la auditoría de acto | A | U (§5.23) |
| F-88 | La segmentación de frases: «...» de tres puntos, abreviaturas («Sr.»), acotaciones de diálogo («—¿Vienes? —preguntó.») y segmentos vacíos | La longitud media baja por artefacto. `estilo` y `deriva_de_estilo` miden la segmentación, no el ritmo | Ninguno: el fixture de `test_ritmo_conocido` tiene frases limpias. Haría falta una tabla de casos para `texto.frases`, y medir `humo-0003` con la misma función que dio 7,9–8,4 | T | propuesto |
| F-89 | Burrows con palabras de desviación nula, con una sola escena de referencia o sin ninguna palabra útil | División por cero o `NaN` en `delta_burrows`, que queda dentro o fuera de tolerancia al azar | Capítulos 1–3: `test_burrows_desde_el_4` (`None`, no medido). Desviación nula y una sola escena: falta un caso que exija un valor finito o `None` | T | 0002 (CA-11, tarea 1.10); la desviación nula, propuesto |
| F-90 | `estilo` con cero rasgos medidos: `huella` ausente del informe o sin referencia en `ritmo` | `ZeroDivisionError` en `checkpoint`, que no cierra el capítulo, o un `estilo` 0 falso | Ninguno: CA-12 solo prueba 0,5. Haría falta un caso con `huella: None` y otro sin rasgos medidos: sin score y `checkpoint` en 0 | T | propuesto |
| F-91 | `_permitidos` admite demasiado o demasiado poco (D-10) | Con poco, el capítulo que desmonta una pista falsa no tiene briefing. Con mucho, pasa la de otro capítulo | Cerrado: `test_pistas_falsas_del_capitulo_en_el_briefing`. Abierto: `test_pista_falsa_ajena_sigue_siendo_fuga`. Al delegar en `secreto.permitidos` (D-3): `test_permitidos_igual_que_antes` | T | 0002 (tareas 1.4 y 2.2) |
| F-92 | La igualdad de RF-09 rechaza todo hilo o pista fuera del plan | Más reintentos del `escritor` | La mitad de humo de CA-09, en local. Intentos por gate `mecanico` en `humo-0002`, sacados de `harness.log` | T + D | 0002 (CA-09, tareas 1.5 y 6.3) |
| F-93 | El `cronista` (haiku) agota los reintentos del delta: cita de 15 caracteres o más en las cuatro colecciones (RF-06; en `humo-0003`, 1 de 85 era más corta), invariantes (RF-07) y resumen (RF-08). Un secundario sin ficha o un objeto sin paradero no tienen forma válida. Y su receta gana `canon/mundo` y el reparto, que pueden no caber en sus 70.000 tokens con un canon grande | 5 en `gate … delta` por un agente barato, en capítulos sanos; o `briefing` en 1 y parada | Cerrado, en la receta: `test_briefing_del_cronista_trae_ids_del_canon`, y el presupuesto sobre `demo-24` (tarea 1.7). La tasa: intentos por gate `delta` en `humo-0002` | T + D | 0002 (tareas 1.7 y 6.3) |
| F-94 | Un consumidor olvida `al_estado()` (D-4), ahora en cuatro tipos: `EntradaTemporalDelta`, `EntradaConocimientoDelta` y `HechoDelta`. La igualdad de Pydantic exige la misma clase | Al reanudar, una entrada append-only duplicada, o «ya está con otro contenido» sobre la misma | `test_apply.py::test_idempotencia_property` y `test_violaciones.py::test_reaplicar_lo_mismo_no_es_duplicar`, con los tipos nuevos y `libro_de_hechos` incluido | T | 0002 (CA-06, tarea 1.6) |
| F-95 | Un invariante narrativo sin su excepción, o una excepción que abre de más | Se rechaza al muerto de una analepsis o de una revelación, o un muerto aprende sin analepsis | Abierto y cerrado en cada uno de los seis tests de `test_invariantes.py`, con mutación sobre `_invariantes` | T | 0002 (CA-07, tarea 1.7) |
| F-96 | Nombres propios con mayúscula tras «—», «¿», «¡» o comillas, que no abren frase (§8.3). No está dicho si la búsqueda en el cuerpo distingue mayúsculas | «Nadie» o «Quién» a mitad de frase rechazan un resumen correcto: más reintentos del `cronista` | Abierto: `test_resumen_nombres_e_ids`. Cerrado: la mitad de humo (74 candidatos, 0 falsos positivos). Faltan casos con esos signos | T | 0002 (CA-08, tarea 1.8); los signos, propuesto |
| F-161 | `delta.schema.json` lleva `minLength: 15` como aproximación, y el validador de D-4 mide la cita normalizada | Una cita de 15 caracteres con espacios repetidos valida contra el esquema que lee el `cronista` y la rechaza `aplicar-delta`: un reintento que el agente no puede prever | Abierto: `test_delta_sin_cita_no_valida_property` con una cita que pasa `minLength` y no `MIN_CITA`. La diferencia la acepta D-4: manda el validador | T | 0002 (CA-06, tarea 1.6) |

**El secreto en el briefing (fase 2)**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-97 | El filtro deja pasar un campo de la ficha que señala al culpable: `rol_narrativo` o `arco_previsto` | El culpable llega señalado por su rol o su arco. La sonda del briefing lee ese briefing y sale con 5 en el capítulo 1, o el `escritor` escribe hacia la solución | Abierto y cerrado: `test_filtro_por_campo_property` con los cuatro campos de RF-01 y `test_conjunto_secreto_segun_n` (el rol y el arco de un filtrado están en el conjunto secreto). El resto de la ficha (`psicologia`, `relaciones`) llega entero: lo cubren el solape y la sonda | T | 0002 (CA-01, tareas 2.2 y 2.3) |
| F-98 | El cuerpo de la ficha repite el secreto que se quitó del frontmatter: D-9 no filtra la prosa | La vía de la ficha del culpable sigue abierta | Abierto, literal: `test_solape_property` sobre la capa de personajes. Paráfrasis: la sonda del briefing | T + I | 0002 (CA-02, tarea 2.4; CA-04, tarea 4.5) |
| F-99 | Toda ficha filtrada se re-renderiza desde el diccionario de `model_dump` (D-9), porque `rol_narrativo` siempre está. Un volcado de YAML que escapa las tildes, que cambia comillas o que pierde un campo por `exclude_none` | El `escritor` lee «Tom\xE1s» donde el canon dice «Tomás», y el guardarraíl y el solape miran un texto que no es el del canon. En un mismo briefing, la ficha de un destapado va cruda y la de otro, re-renderizada | El diff del golden solo toca las tres fichas de `demo-24`, que llevan tildes; `test_misterio_nunca_en_briefing` en verde. Cerrado: el `continuista` recibe la ficha cruda. Falta una aserción de que `nombre` y `alias` de cada ficha filtrada aparecen literales en el briefing | T | 0002 (CA-01, tarea 2.3); los nombres literales, propuesto |
| F-100 | El `arquitecto` no pone al culpable en ningún `destapa`. `validar-plan` solo comprueba que los ids existen (§8.2.2) | Su secreto no llega al `escritor` ni en el capítulo de la revelación, y R pasa a ser el mayor `capitulo_previsto` (§8.1) | Ninguno. Haría falta un hallazgo de `validar-plan` para un `culpable` fuera de todo `destapa` | T | propuesto |
| F-101 | Falsos positivos del solape. «a la torre del faro» es un bloque: «torre» y «faro» tienen cuatro letras. El nombre de un escenario con su artículo («el faro de cabo ermo») casa con toda `verdad_oculta` que lo nombre, salvo que esté también en un texto permitido en N | `briefing` sale con 1 y el procedimiento para (D-28), o `validar-plan` reintenta al `trazador`. En CI no se ve: la fábrica usa frases distintas (README §8) | Cerrado: `test_bloque_permitido_no_cuenta` (lo permitido en N, y la revelación del capítulo R, ya no cuentan) y `test_capitulos_de_la_sonda_no_se_miran`. La tasa: `test_solape_sin_falsos_positivos` sobre las fichas y los briefings de `humo-0003`, en local y sin imprimir texto, con las constantes de §8.4 subidas si hace falta. Otro canon, solo `humo-0002` | T + D | 0002 (CA-02, tareas 2.4 y 6.3) |
| F-102 | El QA saneado pierde `descripcion` y `correccion_sugerida` de continuidad y suspense | El segundo intento del `escritor` repite el fallo, y el gate llega a 5 con un problema que tenía arreglo | Tasa de éxito del segundo intento en `humo-0002` | D | U (§5.19) |
| F-103 | `ubicacion` es texto libre de revisores que ven el misterio, y pasa la lista blanca. Un hallazgo sin `referencia` cuya `ubicacion` insinúa la solución no se descarta | El secreto vuelve por el reintento. La sonda del briefing no corre en los reintentos (§8.1): esta capa no tiene medida directa | Literal: el solape cubre la capa `reintento` (D-9), pero ningún test inyecta ahí. Haría falta un bloque del conjunto secreto en la `ubicacion` de un hallazgo de continuidad que haga salir a `briefing` con 1. Paráfrasis: ninguno | T | propuesto |
| F-104 | Entra en la capa un hallazgo con referencia `rev-`, `pfa-`, el `culpable` o una `pis-` ajena, o se pierde uno de `validar` o `gate` | Fuga por el QA (§4.9, tercera vía), o un reintento sin su causa | Abierto y cerrado: `test_capa_reintento_saneada_property`; `test_hec_se_completa_desde_el_estado` | T | 0002 (CA-03, tarea 2.5) |
| F-105 | El filtro por mtime de D-11 deja entrar el informe de un ciclo anterior, o deja fuera el del último | El `escritor` corrige lo ya corregido, o no ve lo que falló | `test_informe_anterior_al_ultimo_briefing_no_entra`, con `os.utime`. El orden depende del reloj | T | 0002 (tarea 2.5); el reloj, U (§5.18) |
| F-106 | La reanudación («cualquier otro caso → paso 2») regenera el briefing y escribe `NN-escritor-intento-K.md` aunque el `escritor` no llegara a correr | `K` no cuenta intentos, porque la cuenta es del log. Pero la trayectoria tiene que tomar ese fichero por el briefing del `escritor` | `test_briefing_original_intacto`. Falta un transcript fixture de 5.2 con `-intento-2` como único briefing del `escritor` del tramo | T | 0002 (CA-03, tarea 2.5); la trayectoria, propuesto |
| F-107 | La capa `reintento` pasa de 3.000 tokens: avisa y no trunca (PA-12) | El briefing excede su presupuesto: `briefing` sale con 1 y el procedimiento para | `test_capa_estima_menos_de_3000`, sobre 12 hallazgos | T | 0002 (RNF-02, tarea 2.5) |
| F-162 | La exención de lo permitido (§8.4) descuenta todo bloque que aparece en un texto permitido en N. Si el `arquitecto` copió cinco palabras de `verdad_oculta` en el contenido de una pista, ese bloque es público desde que la pista se planta | El solape deja de ver esa vía: el `escritor` y la `sonda` reciben el bloque sin aborto | Abierto, por medida: la sonda del briefing (`test_decision_con_votos_fixture`) y, en la novela real, `humo-0002`. Mecánico, ninguno: la spec lo acepta como diseño del canon | I + A | 0002 (CA-04, tareas 4.5 y 6.3) |

**El plan y `novela gate` (fase 3)**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-108 | El hallazgo `solape_con_el_secreto` de `validar-plan` copia el bloque en `qa/plan-validacion.json` | El secreto queda en `qa/`, al alcance de cualquier agente con `Read` que conozca la ruta. RF-02 prohíbe el texto en el mensaje del briefing, no en el informe | Ninguno. Haría falta que el hallazgo nombre la ficha y el campo y ninguna palabra del bloque, con su test | T | propuesto |
| F-109 | La curva en novelas cortas: `punto_medio = 1`, clímax en el último capítulo o igual a la resolución, clímax igual al punto medio, dos capítulos con el máximo | `validar-plan` rechaza un plan de humo válido, o acepta uno plano | `test_curva_casos_de_borde` (cuatro casos, ninguno de estos), la mitad de humo sobre tres capítulos y mutación sobre la curva. Faltan esos cuatro casos | T | 0002 (CA-14, tarea 3.3); los casos cortos, propuesto |
| F-110 | Un subcomando nuevo sobre un capítulo cerrado, un arranque cerrado o un capítulo por delante del siguiente llama a `run.abrir`, que crea un run (D-7) | Un run espurio, en el que el gate cuenta desde cero | `test_rango` (cerrado y por delante: 2 sin crear run), `test_codigos_y_salida` (2 con checkpoint) y `test_texto_sobre_capitulo_cerrado` (la sonda del texto, al revés: solo sobre el último cerrado) | T | 0002 (CA-19, tareas 3.3, 3.4 y 4.5) |
| F-111 | Dos llamadas seguidas al mismo gate, sin nada en medio, cuentan dos intentos (D-6) | Doble cuenta: el capítulo llega a 5 con menos intentos reales | Abierto: `test_repeticion_sin_orden_en_medio` (una sola línea `gate 08 mecanico -> 1`) | T | 0002 (CA-19, RNF-04, tarea 3.4) |
| F-112 | La sha incluye `st_mtime_ns` (D-6). Un `touch`, una copia sin fechas o una carpeta sincronizada entre dos llamadas seguidas la cambian sin cambiar el contenido | Otra evaluación y otro intento consumido. O el `touch` rejuvenece un informe viejo y lo vuelve legible | Ninguno: 3.5 solo prueba con `os.utime` un informe más antiguo. Haría falta un caso con `touch` tras el briefing que fije qué decide el gate | T | propuesto |
| F-113 | Un agente no reescribe nada: el `escritor` sale sin `Write`, o las sondas no dejan votos | Si la repetición no contara, el procedimiento reintentaría sin fin y el gate no llegaría a 5 | Abierto: `test_orden_en_medio_cuenta_otro_intento` (con un `briefing` en medio y las mismas entradas, dos líneas `-> 1`) y `test_tercer_voto_ausente_interviene` (la misma llamada sin cambios también cuenta) | T | 0002 (CA-19, tarea 3.4; CA-04, tarea 4.5) |
| F-114 | Un 5 se reutiliza como repetición | Tras resolver, el gate repite la intervención sin evaluar | La repetición solo repite 0 o 1 (D-6). `test_intervencion_viva_no_reinicia`, y `test_custodia_interviene_al_primero`: resuelta, otra custodia rota vuelve a dar 5 | T | 0002 (CA-19, tarea 3.4) |
| F-115 | La cuenta no se reinicia tras un 5 resuelto (§8.1), o la reinicia la línea `-> 5 · intervención viva` que escribe el gate cuando hay otra intervención en el run | Un capítulo reescrito tras la intervención no puede reintentarse, como el 3 de `humo-0003`; o gana intentos que no le tocan | `test_resuelta_concede_tres`, `test_intervencion_viva_no_reinicia` y `test_consumidos_property`, con mutación | T | 0002 (CA-19, tarea 3.4) |
| F-116 | El formato de línea de D-6: las causas primero y `entradas=<sha>` al final, separados por `; `; `intervención (<motivo>)` frente a `intervención viva`; líneas `aviso` sin ` -> ` (D-22). Una causa con `;` o ` -> `, y la «ó» de `intervención` si el log se escribe con la codificación local de Windows y se lee en UTF-8 | `consumidos` no ve la última intervención y no reinicia, o toma la viva por una de agotamiento; la sha sale partida. Sin error | `test_parsear_ida_y_vuelta_property`, `test_intervencion_y_viva_se_distinguen` y `test_lineas_sin_entradas_no_cambian`; F-44 y F-47 siguen. Faltan una causa con `;` y ` -> `, la línea `aviso`, y un log escrito y leído con codificaciones distintas | T | 0002 (tarea 3.2); esos casos, propuesto |
| F-117 | Un revisor no reescribe su informe en el reintento y queda el del intento anterior | Un veredicto sobre un texto que ya no existe aprueba el gate | Abierto: `test_informe_mas_antiguo_que_su_briefing`, con `os.utime`. La comparación es estricta sobre `st_mtime_ns`: NTFS guarda 100 ns, pero el reloj del sistema avanza a saltos de milisegundos, y FAT o una unidad de red, de segundos | T | 0002 (CA-19, tarea 3.5); el reloj, U (§5.18) |
| F-118 | `gate … delta` busca una causa que empiece por `custodia:`, y la de custodia no es la primera de varias | El `cronista` se reintenta dos veces por algo que no puede arreglar | `test_custodia_interviene_al_primero`, con una sola causa. Falta el caso con la de custodia en segundo lugar | T | 0002 (CA-19, tarea 3.4); varias causas, propuesto |
| F-119 | `qa/NN-suspense.json` sin `puntuaciones.tension` | Si aprobara, la banda no se aplicaría a un `lector-suspense` que no puntúa. Como es ilegible, el gate reintenta al `escritor` por un fallo del revisor, y gasta sus intentos | Abierto: `test_suspense_sin_tension_es_ilegible`. La tasa de ilegibles por revisor, en `humo-0002` | T + D | 0002 (CA-19, tareas 3.5 y 6.3) |
| F-120 | La banda compara con `>=` en vez de `>`, o la tendencia cuenta otro número de capítulos | Reintentos de más o de menos | `test_banda_y_tendencia_property`, con mutación sobre `>` y sobre el número de capítulos. Cerrado: la fábrica, con la tensión igual a la curva, sigue aprobando | T | 0002 (CA-16, tarea 3.6) |
| F-121 | Una tendencia negativa resuelta vuelve a intervenir: el mismo gate ve las mismas N−1 y N−2 | Otro 5 en cuanto el capítulo reescrito puntúe por debajo. La autorización de D-30 es por capítulo: con la curva baja, cada capítulo siguiente vuelve a intervenir | Abierto: `test_tendencia_resuelta_no_vuelve_a_intervenir` (0 con la banda y el gancho bien, 1 si la banda falla). El capítulo siguiente, ninguno: es lo que pide la spec | T | 0002 (CA-19, tarea 3.6); el capítulo siguiente, U (§5.20) |
| F-122 | La tendencia interviene con tres desviaciones de −1 | Ruido del juez que para la novela | Desviaciones registradas en `humo-0002` | D | U (§5.20) |
| F-123 | Gancho: capítulo sin separadores; separador con espacios; un capítulo con `***` y el canon en `* * *` (la fábrica usa `***`, D-18); el capítulo incrustado con frontmatter; una línea `## ` en la prosa que corta la sección `objetivo` | Sin separador que case, el capítulo entero es la última escena y pasa la cita de cualquiera. Con el frontmatter dentro, pasa una cita de pista. Con la sección cortada, un gancho correcto es ilegible | `test_gancho` (`***`, `* * *`, sin separador y sin `gancho`) y `test_gancho_fuera_de_plan_en_el_informe`; `objetivo` como última capa, en `test_recipes.py`. Frontmatter, separador ajeno al canon y `## ` en la prosa, ninguno | T | 0002 (CA-17, tarea 3.7); esos tres, propuesto |
| F-124 | La reanudación confunde el gate de después de `validar` con el de después de `validar --final` | Una sesión cortada entre el segundo y `gate … revision` revisa otra vez un capítulo ya revisado: tres llamadas y otra reescritura del editor | Son gates distintos, `mecanico` y `final` (D-29). `test_procedimientos_y_codigo_5` exige filas distintas para `gate NN mecanico -> 0` y `gate NN final -> 0`, y `test_mecanico_no_consume_final` separa sus cuentas | T | 0002 (CA-19, CA-29, tareas 3.4 y 3.8) |
| F-125 | Un procedimiento escribe `intervencion.md` para un gate de `novela gate`, o deja de escribirla para un 4 o un 1 de `briefing` o de `checkpoint` (D-28) | Dos bloques para una parada, o una parada sin rastro que `pendiente` no ve | `test_procedimientos_y_codigo_5`. La prosa no se ejecuta (§5.8) | T | 0002 (CA-29, tarea 3.8) |
| F-126 | La máquina del model checking y el gate real divergen | §4.10 verifica una máquina que no es la que corre | `test_la_maquina_con_el_gate_real`, contra el CLI y la fábrica, con una cuenta por gate y el invariante «no hay un cuarto intento de ningún gate» | A + T | 0002 (CA-19, tarea 3.9) |
| F-163 | `qa/NN-validacion.json` no tiene regla de antigüedad: la de §8.1 es contra el briefing del agente, y `validar` no tiene briefing. Si el procedimiento salta `validar` tras un reintento, `mecanico` lee el informe del ciclo anterior; si salta `validar --final` tras reintentar al editor, `final` lee el `final: true` del intento anterior | El gate aprueba un capítulo que nadie validó. La custodia lo para después, en `gate … delta`, con un 5 sin reintento | Spec §8.1 (enmienda): para `mecanico` y `final`, un informe cuyo `capitulo_sha256` no es el del capítulo en disco es ilegible. Abierto: un caso de CA-19 con `validar` saltado tras reescribir el capítulo | T | 0002 (CA-19, tarea 3.4) |
| F-164 | Cualquier orden en medio hace de la llamada un intento nuevo (D-6), y `sonda` no tiene repetición: cuenta cada llamada | Una reanudación que vuelve a correr `validar` o un `briefing` antes del gate, o que repite `novela sonda` con los votos aún ausentes, gasta un intento sin que haya corrido ningún agente: 5 antes de tiempo | `test_orden_en_medio_cuenta_otro_intento` y `test_tercer_voto_ausente_interviene` fijan la regla. Que la reanudación no meta órdenes de más, el ensayo de F-35 | T + D | 0002 (CA-19, tarea 3.4; CA-04, tarea 4.5); la reanudación, F-35 |

**Tensión y sondas por acto (fase 4)**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-127 | Carga de preguntas abiertas: `<` frente a `≤` en el clímax y en las bajadas, y las tres bajadas, que son cuatro valores con N−2, N−1 y N en el acto 2 (RF-15) | Avisos de más o de menos. Son avisos, no paran | `test_carga_humo_0003` (12, 9 y 0, sin aviso); `test_tres_bajadas_en_acto_2`, con dos bajadas, con una igualdad y con N−2 en el acto 1; `test_cero_antes_del_climax`; mutación | T | 0002 (CA-15, tarea 4.1) |
| F-128 | La auditoría de acto interpola un hueco de `tension_real`, o no para con una pista vencida | Una curva rellenada pasa sin datos (§4.13) | `test_acto_con_hueco` y `test_acto_pista_vencida_interviene`, con la línea `auditar acto-K -> 5 · intervención (auditoria)` en el run del último capítulo del acto | T | 0002 (CA-18, tarea 4.2) |
| F-129 | Votos obsoletos: `qa/NN-sonda-<tipo>-K.json` de un capítulo reescrito tras una intervención, o de una sonda que ya salió con 5 | La decisión mide un texto que ya no existe, o los mismos votos dan otro 5 tras resolver | `test_voto_mas_antiguo_que_su_briefing_es_ausente` (con `os.utime`) y `test_fuga_resuelta_mismos_votos` (resuelta y con los mismos votos, 0; con votos nuevos, 5). El orden depende del reloj | T | 0002 (CA-04, tarea 4.5); el reloj, U (§5.18) |
| F-130 | La moda o la mediana mal calculadas: una moda por el primer voto con tres distintos, o la mediana de los tres en lugar de la de la moda | Fuga falsa, o una fuga que no para | `test_decision_con_votos_fixture` (tres distintos, sin moda: 0) y `test_mediana_de_los_votos_de_la_moda`, con los dos casos en que las dos medianas deciden distinto. La moda es el `culpable_id` con dos votos o más (D-15), sin depender del orden | T | 0002 (CA-04, tarea 4.5) |
| F-131 | Cadencia mal calculada: R sin ningún `destapa`, R = 1, N = R − 1 que además cierra acto, N > R, actos de la escaleta con huecos | La sonda no corre donde toca, o corre y para donde no | `test_fuera_de_cadencia_no_lee_votos`, un solo punto. Haría falta una propiedad de `sonda.toca` sobre escaletas y misterios generados, contra la regla de §8.1 | T | propuesto |
| F-132 | Un acto largo no cabe en los 80.000 tokens de la receta `sonda`, que ahora solo tiene los capítulos del acto y el reparto | `PresupuestoExcedido` sale con 5 (D-15): una frontera de acto legítima para la novela | Ninguno. Haría falta generar `NN-sonda.md` para el acto más largo de un plan de 24 capítulos y 80.000 palabras | T | propuesto |
| F-133 | La `sonda` tiene `Read` y abre rutas que su briefing no nombra: `canon/personajes/<id>.md` de un id del reparto, `canon/mundo.md`, `plan/capitulos/` o `qa/NN-continuidad.json`. Solo el misterio está en `deny` | Una fuga falsa y un 5, o una medida que no mide el briefing. Sacar `canon/mundo` de la receta (D-15) no lo saca del alcance de `Read` | Ninguno: la trayectoria solo mira la sesión principal. Haría falta comprobar en el transcript de la sonda que solo leyó su briefing y su esquema | A | propuesto |
| F-134 | La trayectoria no acepta el `Task` de la sonda del briefing tras el briefing del `escritor`, ni el de la del texto tras `sonda … texto` con 1 (§8.7) | Un capítulo limpio con violación: intervención y parada | `test_cada_violacion` ya incluye la falta de `sonda … texto` y de `auditar --acto`. El control cerrado es `test_transcript_limpio` solo si `limpio.jsonl` trae las dos sondas, que el plan no dice | T | 0002 (CA-20, tarea 5.2); las sondas en el fixture limpio, propuesto |
| F-135 | La `previsibilidad` sale del `lector-suspense`, que conoce la solución, o no sale de nadie | El score mide al juez y no al lector ciego | La emite `sonda … texto` (D-31): `test_previsibilidad_desde_la_sonda` (dos de tres votos, 2/3, sin red). `test_lector_sin_previsibilidad` quita el campo del prompt; `checkpoint` ya no la emite | T | 0002 (RNF-05, tareas 4.5 y 4.6) |
| F-136 | El hook no conoce las salidas de la `sonda`, o la regla 5 admite un noveno nombre | La sonda no puede votar, o entra un subagente sin contrato | Cerrado: `test_salidas_casan_el_contrato` y `test_salidas_por_rol`, con K de 1 a 3. Abierto: `test_subagentes`, con `juez` denegado | T | 0002 (CA-30, tarea 4.4) |
| F-165 | Una intervención de `auditar --acto` no se autoriza al resolverla: D-30 solo autoriza `tendencia_negativa` y `fuga`, y los hallazgos altos de §8.6 no cambian nunca | Si la reanudación vuelve a correr la auditoría del acto, sale otra vez con 5, y la novela no pasa de esa frontera | Ninguno. Haría falta que la spec diga si una auditoría resuelta se repite o autoriza sus hallazgos, con su test | T | propuesto |
| F-166 | Tras el `checkpoint` quedan pasos (D-26, D-31): la sonda del texto, su `previsibilidad` y `auditar --acto`. El freno del bucle ya vio avanzar `latest.json`, la tabla de reanudación lee las líneas del capítulo siguiente, y `sonda … texto` sobre N sale con 2 en cuanto N+1 tiene checkpoint (D-7) | Una sesión cortada tras el checkpoint salta la sonda y la auditoría del acto, y ya no se pueden correr. El score `previsibilidad` de N no llega | Si el `Stop` corre: `test_cada_violacion` (falta de `sonda … texto` o de `auditar --acto`) y la intervención. Si no corre: `pendiente` para por trayectoria ausente (D-13). Una fila de reanudación para los pasos tras el checkpoint, ninguna | T | 0002 (CA-20, CA-21, tareas 5.2 y 5.5); la reanudación, propuesto |

**Trayectoria y `pendiente` (fase 5)**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-137 | El hook `Stop` corre en toda sesión del repo, también en las de desarrollo | Sin `NOVELA_SESSION_ID` no debe hacer nada. Si escribiera, ensuciaría `novelas/` desde una sesión ajena al harness | `test_sin_sesion_no_escribe` | T | 0002 (CA-20, tarea 5.3) |
| F-138 | En una sesión interactiva, `Stop` salta en cada turno. Un tramo abierto crece: su sha y su entrada cambian de turno en turno, y D-6 solo evita el bloque repetido si la entrada no cambió | Cada turno puede añadir otro bloque a `intervencion.md` por la misma violación, y uno que el operador resolvió vuelve al turno siguiente. Cada turno relee el transcript entero | `test_repetido_no_escribe_otra_linea` y `test_otra_linea_en_medio_no_duplica_la_intervencion`, los dos con la entrada igual. Haría falta un caso con un tramo abierto que crece con la misma violación, que deje un solo bloque | T | 0002 (RNF-04, tarea 5.3); el tramo que crece, propuesto |
| F-139 | El lock está ocupado cuando salta `Stop` | La sesión no deja su entrada: `pendiente` sale con 5, y la unión de RF-24 echa en falta a sus agentes. Recuperar exige correr `novela trayectoria --transcript` con la misma `NOVELA_SESSION_ID`, y no está escrito | `test_lock_ocupado_sale_con_0_sin_escribir`. Falla cerrado (D-13). La recuperación, ninguno | T | 0002 (tarea 5.3); la recuperación, propuesto |
| F-140 | `novela` no resuelve en el entorno del hook, o App Control lo bloquea (F-57) | El hook sale con un código distinto de 2 y no hay trayectoria: `pendiente` para en cada capítulo | Falla cerrado (D-13). `comprobar-entorno` comprueba que `novela` arranca en la shell que lanza `claude`, y el hook hereda su entorno (F-20) | D + T | 0002 (CA-21, tareas 5.4 y 5.5) |
| F-141 | `novela trayectoria` sale con 2 desde el hook | En un `Stop`, un 2 bloquea el fin del turno y Claude sigue | `test_stdin_ilegible_sale_con_1`, la envoltura de `cli.py`, y `novela trayectoria < /dev/null` en 1 | T | 0002 (tarea 5.3) |
| F-142 | El lector solo reconoce uno de los dos nombres de la herramienta de subagentes: `Agent` en los transcripts de `humo-0003`, `Task` en la documentación | No ve ningún subagente: RF-24 da todos por ausentes (cerrado) y las reglas de orden no se aplican a nada (abierto) | `test_agent_y_task_se_leen_igual`, `test_agent_y_task_dan_la_misma_trayectoria`, fixtures con `Agent`, y en local las 17 invocaciones de los transcripts de `humo-0003` (tarea 5.1). Que el nombre cambie otra vez: §5.10 | T + D | 0002 (CA-20, tareas 5.1 y 5.2) |
| F-143 | Una invocación interrumpida: `toolUseResult` como cadena de error, o sin resultado | Sin `resolvedModel` ni `content`: `modelo_cambiado` compara con nada, y el agente cuenta o no como presente según cómo se escriba el código | La cadena de error: `test_codigo_de_salida_de_bash` y los modelos tolerantes de 5.1. Un `tool_use` sin resultado, ninguno | T | 0002 (tarea 5.1); sin resultado, propuesto |
| F-144 | Una compactación con `trigger: "auto"`, nunca observada (spec §4) | Si su entrada no tiene la forma de la manual, no se ve | Solo el canario tras cada actualización | — | U (§5.10) |
| F-145 | Una sesión del harness sin `NOVELA_SESSION_ID` cierra un capítulo | Sus líneas no llevan `sesion=`, `trayectoria` no hace nada y `pendiente` no le exige trayectoria (D-13): falla abierto | Ninguno. La variable va en el bucle y en la sesión interactiva documentados | D | U (§5.21) |
| F-146 | La entrada se guarda con el `session_id` del hook, que cambia tras un `/clear`, y `pendiente` busca el `sesion=` de `NOVELA_SESSION_ID` | `pendiente` no encuentra la entrada y sale con 5 en la sesión siguiente | La clave es `NOVELA_SESSION_ID` (§8.7, D-12): `test_escribe_trayectoria_e_intervencion` la exige, con el `session_id` como dato; `test_pendiente_trayectoria_ausente` | T | 0002 (CA-21, tareas 5.3 y 5.5) |
| F-147 | La sesión de `/novela-nueva` nombra el capítulo 1 (`briefing <slug> 1 arquitecto`, `gate <slug> 1 plan`) y abre un tramo | Una `trayectoria-01.json` en el run de arranque, con las comprobaciones de un capítulo aplicadas a un arranque | `test_sesion_de_arranque_no_tiene_tramo` y el fixture `arranque.jsonl` | T | 0002 (tarea 5.1) |
| F-148 | La trayectoria resuelve el workspace con el `cwd` de la entrada del `Stop`, que no está verificado (spec §4) | Sin `cwd`, no hay workspace ni trayectoria, y `pendiente` para | `test_no_usa_cwd`: con un `cwd` falso, resuelve por el slug | T | 0002 (tarea 5.3) |
| F-149 | Una orden que no empieza por `novela`: con `cd … &&`, con una variable delante o con la ruta del ejecutable | No abre tramo, o el tramo pierde un paso: una violación de orden falsa o un capítulo sin trayectoria | Los procedimientos piden cada orden sola (F-25). Faltan fixtures con las tres formas | T | propuesto |
| F-150 | Una comprobación de §8.7 no produce su violación, o el transcript limpio produce alguna | La trayectoria no ve lo que promete, o para una novela sana | `test_cada_violacion`, `test_transcript_limpio` (con las lecturas del procedimiento y el `Write` de `intervencion.md`, que no cuentan), `test_modelo_cambiado`, `test_modelo_contra_la_ultima_trayectoria_con_ese_agente`, `test_compactacion_en_tramo`, `test_message_id_repetido_cuenta_una_vez`, `test_capitulo_cerrado_sin_lector_suspense`, `test_reanudado_no_da_agente_ausente` y `test_sin_texto_de_prompt_ni_retorno` | T | 0002 (CA-13, CA-20, CA-22 y CA-24, tareas 5.1 a 5.3) |
| F-151 | `pendiente` sale con 5 y el `while` del bucle desatendido termina sin decir por qué | Parar es lo correcto, pero el operador no distingue 1 (terminada) de 5 (intervención) sin volver a mirar | `test_pendiente_intervencion_viva` y `test_pendiente_trayectoria_ausente`. Que el bucle documentado imprima el código, ninguno | T | 0002 (CA-21, tarea 5.5); el aviso, propuesto |
| F-152 | `intervencion.md` con varios bloques (D-14): `viva` solo mira el último. `trayectoria`, `sonda` y `auditar --acto` pueden añadir uno con otro vivo, y un `Resuelto:` o un `- resuelto:` no cuentan | El operador resuelve el último y el anterior se pierde; o marca uno resuelto que el CLI sigue viendo vivo | `test_viva_y_resuelta` y `test_segundo_bloque_tras_uno_resuelto_esta_vivo`. Dos bloques vivos seguidos, ninguno | T | 0002 (tarea 3.1); dos vivos, propuesto |
| F-167 | El fin de tramo de D-12: el tramo de N acaba en la primera orden que nombra N+1. `novela auditar <slug> --acto K` no nombra capítulo, y una sesión reanudada tras el checkpoint solo tiene `sonda … texto` y `auditar --acto`, sin `checkpoint` en su tramo | La auditoría del acto no se atribuye a N y sale una «falta `auditar --acto`» falsa; o el tramo reanudado, abierto, da una violación de orden sobre un checkpoint que está en otra sesión | `test_tramos_de_una_sesion_limpia` (el tramo incluye las órdenes tras su checkpoint). Faltan un fixture con `auditar --acto` en el tramo del último capítulo de un acto y otro reanudado tras el checkpoint | T | 0002 (tarea 5.1); esos dos casos, propuesto |
| F-168 | Dos transcripts con la misma `NOVELA_SESSION_ID` tocan el mismo capítulo: un `/clear` a mitad de capítulo, un `--resume`, dos ventanas abiertas con la variable exportada. D-12 «fusiona su entrada de sesión» sin decir si une o sustituye | Si sustituye, RF-24 pierde los agentes del primer transcript y da un agente ausente falso | Ninguno. Haría falta un test con dos transcripts de la misma clave sobre el mismo capítulo | T | propuesto |

**Release, esquemas y novela de humo (fase 6)**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-153 | Las rupturas de §8.8 sobre `humo-0003`: el índice de capítulos da 404 y `exportar` sale con 4 desde 1.3; `briefing` y `auditar`, con 4 desde 2.1 (README §7.4) | La novela de humo de la 0003 solo se lee en parte | `test_humo_0003.py` en local (D-20); `novela estado` y `pendiente` siguen | T | U (§5.22) |
| F-154 | Las mitades de humo se saltan sin `novelas/humo-0003` (D-20) | CI da verde sin la evidencia de CA-06, CA-08, CA-09 y CA-14, ni la medida de falsos positivos del solape (tarea 2.4) | El «Hecho cuando» de cada tarea exige la ejecución local | I | 0002 (D-20) |
| F-155 | El OpenAPI queda desfasado: `FrontmatterCapitulo` cambia en 1.3, y `Config` en 3.3 si la 0004 lo sirve | Se rompe el contrato con el panel | `test_openapi_al_dia` (F-46), con regeneración en las dos tareas | T | 0002 (tareas 1.3 y 3.3) |
| F-156 | `extra="forbid"` con agentes que escriben campos nuevos antes de tiempo o viejos después: el `escritor` con ids sueltos, el `cronista` con un `inferido`, la `sonda` con un razonamiento, el `lector-suspense` sin `gancho` o sin `tension` (que ahora lo hacen ilegible) | Informe, voto o delta inválidos: reintento, o voto ausente | Cada prompt va en el commit de su modelo (regla 6 del README). Tasa de reintentos por gate en `humo-0002` | T + D | 0002 (tarea 6.3) |
| F-157 | Los cambios de prompt (`escritor`, `cronista`, `lector-suspense`, `editor-estilo`, `arquitecto`, `trazador` y `sonda`) no tienen TDD, y los siete umbrales provisionales salen de una sola novela | Un prompt que no cumple su contrato, o un umbral que para en falso, solo se ven en `humo-0002` | `humo-0002`: scores, intentos por gate y umbrales con su dato | D | 0002 (tarea 6.3); una sola ejecución, U (§5.16) |
| F-158 | Los briefings de los fixtures de revisores se generan una vez sobre `demo-24` y se versionan (tarea 6.1) | Tras cambiar una receta, el script de release mide briefings que el CLI ya no produce | Ninguno. Haría falta un test que regenere cada briefing de fixture y lo compare, como el golden | T | propuesto |
| F-159 | El script de release decide mal su veredicto | Un revisor que no detecta sale en verde | `test_fixtures_validan` y `test_veredicto_en_seco` (3 de 4 → 0,75; 6 al plano → rojo) | T | 0002 (CA-25, tarea 6.1) |
| F-160 | El canario del orquestador pasa en vacío: la sesión no obedece la invitación a leer, o el impostor no llega a correr | Verde sin haber probado la trayectoria | `test_sin_tool_use_es_no_concluyente`, `test_gate_paro_al_impostor` y `test_trayectoria_marca_la_lectura` | T + D | 0002 (CA-27, tarea 6.2) |

**Matriz RF → filas**

| Requisito | Filas |
|---|---|
| RF-01 | F-97, F-98, F-99, F-100 |
| RF-02 | F-98, F-101, F-103, F-162 |
| RF-03 | F-102 a F-107 |
| RF-04 | F-98, F-100, F-129 a F-135, F-162, F-164, F-166 |
| RF-05 | F-80, F-81, F-82, F-83, F-91, F-155, F-156 |
| RF-06 | F-80, F-93, F-94, F-161 |
| RF-07 | F-93, F-95 |
| RF-08 | F-93, F-96 |
| RF-09 | F-92 |
| RF-10 | F-82, F-84, F-85 |
| RF-11 | F-86 a F-89 |
| RF-12 | F-88, F-90 |
| RF-13 | F-142, F-143, F-150 |
| RF-14 | F-100, F-101, F-108, F-109, F-110 |
| RF-15 | F-127 |
| RF-16 | F-119 a F-122 |
| RF-17 | F-123 |
| RF-18 | F-128, F-165, F-166 |
| RF-19 | F-83, F-84, F-110 a F-118, F-124, F-125, F-126, F-163, F-164 |
| RF-20 | F-106, F-134, F-137 a F-143, F-145, F-147 a F-150, F-166, F-167, F-168 |
| RF-21 | F-116, F-139, F-140, F-145, F-146, F-151, F-152, F-166 |
| RF-22 | F-144, F-150 |
| RF-23 | fuera de la spec |
| RF-24 | F-139, F-142, F-150, F-168 |
| RF-25, RF-26 | F-158, F-159 |
| RF-27 | F-160 |
| RF-28 | F-91, F-95 |
| RF-29 | F-114, F-121, F-125, F-151, F-152, F-165 |
| RF-30 | F-132, F-133, F-136, F-156 |
| RNF | RNF-01: F-138; RNF-02: F-107; RNF-04: F-111, F-113, F-138, F-164; RNF-05: F-135, F-166; RNF-06: F-153; RNF-07: F-150. Transversales: F-154, F-157 |

Siguen en **propuesto** catorce filas: F-88, F-90, F-100, F-103, F-108, F-112, F-131, F-132, F-133, F-149, F-158, F-163, F-165 y F-168. Otras dieciocho tienen una parte en **propuesto**: F-83, F-86, F-89, F-96, F-99, F-106, F-109, F-116, F-118, F-123, F-134, F-138, F-139, F-143, F-151, F-152, F-166 y F-167. Entran en la spec 0002 por enmienda antes de implementarse la tarea que tocan, no se improvisan al implementarla. Las más caras de descubrir tarde son F-163, que deja pasar un capítulo sin validar hasta que la custodia lo para con un 5, y F-165 y F-166, que dejan una frontera de acto sin salida o sin su sonda y su auditoría.

---

## 5. Riesgos aceptados (U)

Cada uno con su condición de revisión: un riesgo aceptado sin criterio para reabrirlo es un riesgo olvidado.

**5.1 No hay corrección demostrable de la prosa.** No existe especificación. Lo mejor disponible es gates mecánicos más jueces. *Permanente.*

**5.2 Sin prueba formal de los invariantes.** Se sustituye por asserts de postcondición y property-based testing, que detectan en ejecución pero no demuestran. *Revisar si aparece un caso de corrupción de estado que los tests no cogieron.*

**5.3 Sin self-consistency ni debate.** Generar un capítulo tres veces cuesta el triple y no hay «mayoría» de prosa sobre la que votar. *Revisar si `fair_play` falla de forma recurrente; ahí sí hay una respuesta discreta sobre la que votar.* Excepción ya adoptada: las sondas de §4.15 responden con un id y votan tres veces.

**5.4 El juez comparte sesgos del escritor.** Mitigado puntuando contra hechos, con la calibración de §4.11 y sacando del juez lo que no puede evaluar (estilo y previsibilidad, §4.2). No eliminado. *Revisar si los scores se saturan en alto mientras las intervenciones suben — señal clásica de juez complaciente.*

**5.5 No determinismo del modelo.** El mismo briefing no produce el mismo capítulo. Consecuencia directa: un fallo de calidad no es reproducible, y por eso nada que llame a un modelo entra en `pytest`. *Permanente; sin `temperature` no hay palanca.*

**5.6 El sandbox no es aislamiento.** La contención son permisos, no un contenedor. *Deja de ser aceptable en cuanto el bucle corra desatendido en infraestructura compartida.*

**5.7 `novelas/` no está versionado.** El único rollback de datos es `checkpoints/`. Un `rm -rf` del workspace no tiene deshacer. *Aceptado: son datos regenerables a coste de cuota.*

**5.8 El orquestador no tiene método asignado.** El bucle lo implementa `.claude/commands/novela-continuar.md`: no es código —no le aplica el TDD— ni prosa de novela —no hay juez que la puntúe—. §4.10 verifica la máquina de estados que ese fichero debería seguir, no el fichero. Lo único que lo cubre de verdad es la novela de humo (D). Reducido, no cerrado, por `novela gate` y la auditoría de trayectoria (§4.16): el fichero sigue sin ejecutarse, pero cada sesión se contrasta con la máquina después de haber corrido. Eso detecta la divergencia y no la impide, y un capítulo que la sufre ya ha gastado su cuota. *Revisar en cuanto aparezca un fallo de orden que el model checking daba por imposible: significa que el procedimiento y la máquina han divergido.*

**5.9 Un error del `cronista` es permanente.** El invariante 2 protege contra reescribir la historia y, con el mismo mecanismo, fosiliza un hecho falso: no hay `UPDATE` que lo corrija, y todo capítulo posterior se escribe contra él. El gate de `cita` (§3.9) ataca la alucinación literal, no la interpretación equivocada de una escena. *Revisar si aparece una contradicción cuyo origen sea una entrada del libro de hechos y no un capítulo.* **Condición cumplida el 2026-09-24**, en la novela de humo: la cita de `hec-002` es literal y no contiene la fecha que afirma su texto, y el capítulo 3 chocó con ella (spec 0003 §13). La cita obligatoria que respalde el hecho y los invariantes narrativos de `validar-delta` son de la spec 0002.

**5.10 Las barreras dependen de comportamientos no contractuales de Claude Code.** `tools`, el alcance de los hooks en subagentes, lo que el hook `Stop` puede leer, el formato del transcript del que depende §4.16 y el modelo al que resuelve cada alias no son API estable. *Mitigado por el canario de §4.9 y por el registro del modelo resuelto (§4.13), no eliminado. Revisar en cada actualización mayor.*

**5.11 El contexto del orquestador no se mide.** El techo de `architecture.md` §6.5 lo comprueba `novela briefing` para los subagentes; para la sesión que los invoca, los 6.000–8.000 tokens por capítulo son una estimación que nadie ha contrastado, y es el único contexto que no se vacía entre pasos. *Revisar con los conteos por turno de la primera novela de humo.* Cuando exista §4.16, esos conteos salen de cada sesión y este riesgo pasa de aceptado a medido.

**5.12 Las sondas ciegas son de la misma familia de modelo.** Que la sonda de §4.15 no adivine al culpable no prueba que un lector humano tampoco lo haga: da una cota inferior de la fuga, no una garantía de que no la hay. Lo mismo al revés: que la sonda deduzca la solución en el capítulo de la revelación no prueba que el fair play funcione para un lector humano. *Revisar si un lector humano de la novela de humo acierta antes que la sonda.*

**5.13 Las invariantes narrativas cubren lo que se puede escribir como regla.** §3.9.8 detecta al muerto que reaparece y el hilo que se cierra sin haberse abierto. No detecta un cambio de carácter sin causa, ni una relación que evoluciona sin escena que la justifique: eso sigue siendo trabajo del `continuista` (I). *Revisar si las intervenciones por contradicción se concentran en `relaciones` o en `personajes.estado_emocional`, que son mutables y no llevan cita.*

**5.14 El hook no normaliza lo que solo el disco resuelve.** Los nombres cortos 8.3, las uniones y los enlaces simbólicos dentro de `novelas/` pueden llevar una escritura a `estado/` sin que la ruta lo diga (F-15). Resolverlos exigiría tocar el disco en cada llamada, y un fichero que aún no existe no se resuelve igual en Windows y en Linux. Debajo del hook quedan los triggers de `estado.db` y la reproducción de §4.14. *Revisar si aparece en `estado/` un fichero que no creó el CLI.*

**5.15 Revisores y editor comparten turno.** Los tres revisores corren en paralelo, y el `editor-estilo` reescribe el capítulo mientras los otros dos lo juzgan. La custodia ata cada veredicto al texto incrustado en su briefing, no a lo que el revisor haya leído del disco (F-07). *Revisar si un hallazgo del `continuista` o del `lector-suspense` cita un texto que no está en su briefing.*

**5.16 El primer baseline es una sola ejecución.** La novela de humo de la 0003 da un número por score y capítulo, y la σ entre ejecuciones no se conoce (F-70). Sirve para detectar un sistema roto, no para comparar dos prompts (§4.8). *Revisar al tener tres ejecuciones con el mismo sha.*

**5.17 Una sesión manual del harness puede no ir aislada.** El bucle y la documentación lanzan `claude --setting-sources project,local`, pero nada impide abrir una sesión sin el flag. En ella actúan los hooks y plugins del ámbito de usuario (F-51). El manifiesto no lo registra, porque no sabe con qué flags se lanzó la sesión. *Revisar si una ejecución interactiva produce trazas o reintentos que no reproduce el bucle.*

**5.18 El orden por mtime depende del reloj del sistema de ficheros.** La spec 0002 declara ilegible un informe más antiguo que el briefing de su revisor, e inválido un voto de la sonda más antiguo que el briefing que juzga, y el reintento del `escritor` solo toma los `qa/` posteriores a su último briefing (F-105, F-117, F-129). Los dos comparan `st_mtime_ns`, que avanza a saltos del reloj del sistema en NTFS, y de segundos en FAT o en una unidad de red (spec 0002 §13). *Revisar si aparece un `informe_ilegible` sobre un informe escrito después de su briefing, o si el workspace pasa a un volumen que no es NTFS local.*

**5.19 El `escritor` en reintento no ve la descripción de los revisores.** De continuidad y suspense solo le llegan `tipo`, `gravedad`, `referencia` y `ubicacion` (spec 0002 RF-03), porque `descripcion` y `correccion_sugerida` las escriben agentes que ven el misterio (F-102). *Revisar con la tasa de éxito del segundo intento de `humo-0002`: si el segundo intento repite el hallazgo del primero en la mayoría de los casos, la lista blanca es demasiado estrecha.*

**5.20 La tendencia negativa interviene con tres desviaciones de −1.** Puede ser ruido del juez (spec 0002 §13, F-122). *Revisar con la primera novela completa, o si una `tendencia_negativa` se resuelve sin cambiar nada.*

**5.21 Una sesión del harness sin `NOVELA_SESSION_ID` escapa a la trayectoria.** Sin la variable, `novela trayectoria` no hace nada, las líneas del log no llevan `sesion=` y `pendiente` no exige la trayectoria del capítulo que esa sesión cerró (F-145). Es la misma clase de hueco que §5.17: el bucle y la documentación la exportan, y nada impide abrir una sesión sin ella. *Revisar si aparece en un run del bucle una línea `checkpoint NN -> 0` sin `sesion=`.*

**5.22 `humo-0003` se lee solo en parte tras la spec 0002.** Sus frontmatters, sus deltas y su misterio no cumplen los contratos nuevos, y no se migra (spec 0002 RNF-06). Su estado sigue leyéndose, pero el índice de capítulos de la API da 404, y `exportar`, `briefing` y `auditar` salen con 4 (F-153). *Revisar si hace falta servirla por la API o por el panel: entonces se migra, y eso es otra spec.*

**5.23 La huella es una señal, no un gate.** Una deriva de estilo pasa el bucle: consta en `qa/NN-validacion.json` y puntúa en `estilo`, pero no para (spec 0002 §13, F-87). Con un solo baseline, la tolerancia de la longitud de frase habría rechazado los tres capítulos de `humo-0003`. *Revisar con `humo-0002`: si las tolerancias calibradas separan los capítulos sanos de los derivados, la huella puede pasar a gate por spec.*


**5.24 La calidad visual y la usabilidad de la escena solo se juzgan por inspección** y por la demostración de la spec 0004: ningún test dice si la estantería se recorre bien. *Revisar si el operador deja de usar Lectura en favor de la lista HTML.*

**5.25 CI renderiza WebGL por software.** Los e2e prueban los draw calls, no los fps en una GPU real. *Revisar si RNF-04 de la spec 0004 falla en la máquina de desarrollo.*

**5.26 La API no autentica.** Cualquier proceso local puede leer las novelas. Aceptado mientras corra en `127.0.0.1` en la máquina de desarrollo, como §5.6 acepta el sandbox. *Revisar si la API se expone en red.*

**5.27 La colisión de lecturas de la API con escrituras atómicas en Windows no se reproduce en CI**, que corre en Linux; la cubren los reintentos de `atomic.py` (§3.5, Plataforma) y la demostración de la spec 0004. *Revisar si `harness.log` registra un `PermissionError` con el panel abierto.*
---

## 6. Qué corre en cada punto

| Momento | Métodos | Clase | Coste |
|---|---|---|---|
| Pre-commit | Type checking, SAST, tests unitarios; `npm --prefix frontend run lint` si el índice tiene ficheros de `frontend/` (spec 0004) | A, T | segundos |
| Cada escritura o `Bash` de Claude Code | hook `PreToolUse`: `estado/`, salidas por rol, misterio y `estado.db` en órdenes (spec 0003) | A | < 300 ms |
| Antes del bucle desatendido y del canario | `novela comprobar-entorno`: `novela` en el PATH, `python` real, hook presente, `settings.local.json` solo con `enabledPlugins`, `.env` ignorado y, con el trazado de scores pedido, sus claves; con `--limpio` en el canario (spec 0003) | A | gratis |
| Tras cada sesión del bucle | freno: sin avance de `checkpoints/latest.json`, el bucle para (spec 0003) | A | gratis |
| CI del harness | + mutación sobre gates, contrato API, contrato de `.claude/`, model checking; job `frontend`: `npm ci`, `tipos:comprobar`, `lint`, `typecheck`, `test`, `build`, `presupuesto` y `npm audit --omit=dev --audit-level=high`; job `frontend-e2e`, en la imagen de Playwright de la versión fijada en `package-lock.json`: `uv sync --locked`, `npm ci` y `npm run e2e`, que genera los workspaces con `tests.fixtures.panel` y levanta la API y `vite preview` (spec 0004) | T, A | minutos |
| Tras el `trazador`, una vez | `novela validar-plan`: fair play del plan, ids, orden de pistas, forma de la curva de tensión, secreto por capítulo en las fichas | A | gratis |
| Al abrir `estado.db` | `schema_version`, triggers presentes, `quick_check` | A | gratis |
| Primer `briefing` de cada capítulo | sello de `canon/` y `plan/` contra el último checkpoint | A | gratis |
| Cada `briefing` | sello de los capítulos cerrados contra el último checkpoint (spec 0001) | A | gratis |
| Cada `briefing` de `escritor` o `editor-estilo` | secreto excluido por campo, solape con lo no revelado, `qa/` saneado en reintento | A | gratis |
| Primer capítulo de acto y capítulos que pagan pista | sonda ciega del briefing, tres votos | I + A | 3 llamadas baratas |
| `novela validar <cap>` | esquema, longitud, pistas presentes con cita literal en el cuerpo, hilos, léxico vetado, huella de estilo, gancho y pistas falsas con cita | A, T | gratis |
| Tras escribir el capítulo | `continuista`, `editor-estilo`, `lector-suspense` | I | 3 llamadas |
| Tras el `editor-estilo` | `novela validar` de nuevo, sobre el fichero final | A | gratis |
| Antes de `aplicar-delta` | cadena de hashes, citas presentes literales, hilos contra frontmatter (spec 0001); `novela gate`, cita obligatoria, invariantes narrativos, cruce con el plan, resúmenes acotados (spec 0002) | A | gratis |
| Cierre de capítulo | rastro completo de briefings y salidas, reproducción del estado, carga de preguntas abiertas, scores a Langfuse, checkpoint | A, T, D | gratis |
| Fin de sesión, hook `Stop` | auditoría de trayectoria: orden, lo que no deja artefacto, contexto y compactación, modelo resuelto | A | gratis |
| `novela pendiente` | parada si hay un `intervencion.md` sin resolver, una trayectoria ausente o con violaciones, o un cambio de modelo | A | gratis |
| Frontera de acto | `auditar` parcial: deriva contra el canon, tensión contra plan con banda y tendencia, huecos de `tension_real`, hilos, pistas; sonda ciega del texto | A, I | 3 llamadas |
| Cierre de novela | `novela auditar`: pistas huérfanas, hilos sin cerrar | A | gratis |
| Tercer intento de un gate | `intervencion.md` y parada | I | humano |
| Release del harness | suite adversaria, canario de barreras, canario del orquestador, control negativo y calibración de revisores, novela de humo de 3 capítulos | I, T, D | ~1 acto de cuota |

**Regla de orden: lo barato primero.** Un gate de Python que cuesta veinte milisegundos evita una llamada a opus que cuesta cuota y minutos. Ejecutar `novela validar` antes de cualquier agente de revisión no es una optimización, es el diseño. Invertir ese orden gasta el presupuesto en descubrir cosas que un `assert` ya sabía.
