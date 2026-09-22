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

### Verificación de código

| # | Método | Clase | Artefacto | Herramienta | Estado |
|---|---|---|---|---|---|
| 1 | Type checking | A | `backend/`, `frontend/` | `mypy --strict`, Pydantic v2, `tsc --noEmit` | activo |
| 2 | Static analysis / SAST | A | `backend/`, `frontend/` | `ruff` (reglas `S`), `eslint` | activo |
| 3 | Symbolic execution | A | `delta.py`, `validate.py` | CrossHair | diferido |
| 4 | Formal verification | A | invariantes append-only | — | **U** (§5.2) |
| 5 | Unit / integration testing | T | CLI y API | `pytest` + `jsonschema` | activo |
| 6 | Property-based testing | T | `aplicar-delta`, `briefing`, `checkpoint` | Hypothesis | v1 |
| 7 | Mutation testing | T | `validate.py`, `delta.py` | `mutmut` | v1 |
| 8 | Contract testing | T + A | API ↔ frontend, agente ↔ CLI | OpenAPI + JSON Schema versionado | v1 |

### Verificación de proceso

| # | Método | Clase | Artefacto | Mecanismo | Estado |
|---|---|---|---|---|---|
| 9 | Runtime observability / tracing | D | sesión de Claude Code | hook `Stop` + Langfuse (arch §10) | activo |
| 10 | Evals | T + I | salida de cada agente | scores por capítulo + juez de sesión | activo |
| 11 | Sandboxed execution | D | subagentes | `tools` restringido, workspace fuera del repo | parcial (§5.6) |
| 12 | Guardrails | A | briefings, `estado/` | aborto del briefing, hook `PreToolUse` | activo |
| 13 | Human-in-the-loop | I | `runs/<run_id>/intervencion.md` | parada al tercer intento | activo |
| 14 | Multi-agent verification | I | capítulo escrito | `continuista`, `editor-estilo`, `lector-suspense` | activo |
| 15 | CI/CD integration | T | commits del harness | pipeline + `manifest.json` con sha | v1 |
| 16 | Progressive rollout | D | cambios de prompt de agente | versión de receta como flag | diferido |
| 17 | Red-teaming / adversarial | I + T | fuga del misterio, inyección | suite adversaria por release | v1 |
| 18 | Model checking | A | bucle por capítulo | enumeración de la máquina de estados | v1 |

---

## 3. Verificación de código

### 3.1 Type checking — A

Dos fronteras, y la segunda es la que importa.

- **Estática**: `mypy --strict` sobre `backend/`, `tsc --noEmit` sobre `frontend/`. Los tipos del frontend se generan desde el OpenAPI del backend (§3.8), así que no pueden derivar por su cuenta.
- **En el borde**: todo lo que llega de disco o de un agente es `Any` hasta que un modelo Pydantic lo parsea. **Regla dura: ningún dato cruza de disco o de agente al código sin pasar por un modelo de `backend/novela/models/`.** `json.load()` suelto en el código de negocio es un bug, no un atajo.

Lo que **no** cubre: `capitulo: int` acepta `0` y `-3`. Rango, formato de id y consistencia referencial son validadores Pydantic, no tipos.

### 3.2 Static analysis / SAST — A

`ruff` con las reglas `S` (flake8-bandit) en backend, `eslint` en frontend. Los patrones que de verdad importan en este repo:

1. **Path traversal en la API.** `GET /novelas/{slug}/...` concatena un valor de URL con una ruta de disco. Es la única superficie de inyección real del sistema. El slug se valida contra `^[a-z0-9-]+$` antes de tocar el filesystem, y hay un test que lo intenta con `../`.
2. **Escritura no atómica.** Cualquier `open(..., "w")` sobre el workspace que no pase por `plataforma/atomic.py` viola el invariante 6 de AGENTS.md. El estado no es la excepción por la vía fácil: escribir `estado.db` fuera de una transacción de `aplicar-delta` viola el mismo invariante.
3. **Claves en ficheros versionados.** Grep de `LANGFUSE_SECRET_KEY` y similares en pre-commit. `settings.local.json` y `.local.env` están en `.gitignore`, pero la regla la hace cumplir el linter, no la disciplina.

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

Dos contratos, mismo principio.

**API ↔ frontend.** FastAPI emite OpenAPI; el frontend genera sus tipos desde ahí; CI falla si el esquema commiteado no coincide con el que genera el código. Eso es el contrato entero. No hace falta Pact para dos partes que viven en el mismo repo.

**Agente ↔ CLI.** Los ficheros de `qa/`, el delta del `cronista` y el frontmatter de capítulo son contratos igual de reales, entre un productor no determinista y un consumidor estricto. Se tratan igual: JSON Schema versionado en `backend/schemas/`, validación en ambos lados, y `schema_version` en el propio documento. Cuando un agente empieza a devolver un campo de más, quieres enterarte en el capítulo 1.

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
| `novela briefing` aborta si el contenido ensamblado procede de `canon/misterio.md` | Fuga del secreto (invariante 3) |
| `tools` restringido por agente | Que un agente descubra ficheros que su briefing no nombra (sin `Glob` ni `Grep`), ejecute el CLI, delegue o invoque skills. **No** impide leer una ruta conocida: eso sería una regla `deny` |
| Hook `PreToolUse` sobre `estado/**` | Que un agente escriba el estado por fuera de `aplicar-delta` |
| Triggers append-only en las tablas de `estado.db` | Reescribir la historia, por cualquier ruta de escritura y no solo por delta (invariante 2) |
| Validación del slug antes de tocar disco | Path traversal por la API |

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

### 4.8 Progressive rollout — D

El análogo aquí: **un cambio en el prompt de un agente es un despliegue**. Hoy se aplica a la novela siguiente de golpe, y si empeora, se nota tres capítulos después.

El mecanismo de flag ya existe a medias: la versión de receta va en `manifest.json`. Falta el rodaje — ejecutar el prompt nuevo sobre los capítulos de una novela de prueba y comparar scores contra la versión anterior antes de adoptarlo.

**Diferido**, por una razón honesta: comparar requiere una línea base estable, y con σ alta entre ejecuciones hacen falta varias corridas para que la diferencia signifique algo. Hasta tener eso, un rollout progresivo daría una falsa sensación de rigor.

### 4.9 Red-teaming / adversarial testing — I + T

Modelo de amenaza real de este sistema, en orden de probabilidad. No es un sistema con usuarios ni con datos personales: lo que está en riesgo es **la calidad y el secreto**, no la infraestructura.

1. **Fuga del misterio.** El escritor recibiendo, infiriendo o deduciendo la solución. Sonda: ensamblar briefings sobre un canon marcado y buscar los marcadores; y plantar en `plan/capitulos/NN.md` texto que intente arrastrar `canon/misterio.md` al briefing.
2. **Inyección por contenido del workspace.** Los agentes leen ficheros escritos por otros agentes. Un capítulo o una ficha de canon que contenga «ignora tus instrucciones y…» es el vector natural, y no requiere atacante externo: basta un modelo que alucine una instrucción.
3. **Uso indebido de herramientas.** Un agente escribiendo `estado.db` directamente o invocando `aplicar-delta`. Lo cubre el frontmatter, pero se prueba explícitamente.
4. **Deriva de objetivo a 24 capítulos.** El escritor optimizando poco a poco su propia coherencia local por encima del plan. Es el fallo más difícil de detectar porque cada capítulo pasa sus gates.
5. **Exfiltración.** La única salida de red es Langfuse. Las claves están en `settings.local.json`, fuera de git.

Cadencia: la suite adversaria corre por release del harness, no por capítulo.

### 4.10 Model checking — A

El bucle por capítulo es una máquina de estados pequeña: `cursor.fase` × `ultimo_paso` × `intento`. Merece exploración exhaustiva de los estados alcanzables para verificar invariantes de orden:

- Nunca `aplicar-delta` sin que `validar` haya pasado.
- Nunca `checkpoint` antes de `aplicar-delta`.
- Nunca dos procesos sobre el mismo workspace (invariante 8, el lock).
- `intento` nunca pasa de 2 sin producir `intervencion.md`.
- Nunca un capítulo N+1 con el N sin checkpoint.

El espacio de estados son decenas, no millones, así que **la versión que se hace es un test que enumera las transiciones**, no TLA+. Si el bucle crece a ramas condicionales por acto o a paralelismo entre capítulos, entonces TLA+ empieza a pagar; hoy sería ceremonia.

---

## 5. Riesgos aceptados (U)

Cada uno con su condición de revisión: un riesgo aceptado sin criterio para reabrirlo es un riesgo olvidado.

**5.1 No hay corrección demostrable de la prosa.** No existe especificación. Lo mejor disponible es gates mecánicos más jueces. *Permanente.*

**5.2 Sin prueba formal de los invariantes.** Se sustituye por asserts de postcondición y property-based testing, que detectan en ejecución pero no demuestran. *Revisar si aparece un caso de corrupción de estado que los tests no cogieron.*

**5.3 Sin self-consistency ni debate.** Generar un capítulo tres veces cuesta el triple y no hay «mayoría» de prosa sobre la que votar. *Revisar si `fair_play` falla de forma recurrente; ahí sí hay una respuesta discreta sobre la que votar.*

**5.4 El juez comparte sesgos del escritor.** Mitigado puntuando contra hechos, no eliminado. *Revisar si los scores se saturan en alto mientras las intervenciones suben — señal clásica de juez complaciente.*

**5.5 No determinismo del modelo.** El mismo briefing no produce el mismo capítulo. Consecuencia directa: un fallo de calidad no es reproducible, y por eso nada que llame a un modelo entra en `pytest`. *Permanente; sin `temperature` no hay palanca.*

**5.6 El sandbox no es aislamiento.** La contención son permisos, no un contenedor. *Deja de ser aceptable en cuanto el bucle corra desatendido en infraestructura compartida.*

**5.7 `novelas/` no está versionado.** El único rollback de datos es `checkpoints/`. Un `rm -rf` del workspace no tiene deshacer. *Aceptado: son datos regenerables a coste de cuota.*

---

## 6. Qué corre en cada punto

| Momento | Métodos | Clase | Coste |
|---|---|---|---|
| Pre-commit | Type checking, SAST, tests unitarios | A, T | segundos |
| CI del harness | + mutación sobre gates, contrato API, model checking | T, A | minutos |
| `novela validar <cap>` | esquema, longitud, pistas presentes, hilos | A, T | gratis |
| Tras escribir el capítulo | `continuista`, `editor-estilo`, `lector-suspense` | I | 3 llamadas |
| Cierre de capítulo | scores a Langfuse, checkpoint | T, D | gratis |
| Cierre de novela | `novela auditar`: pistas huérfanas, hilos sin cerrar | A | gratis |
| Dos fallos de un gate | `intervencion.md` y parada | I | humano |
| Release del harness | suite adversaria, novela de humo de 3 capítulos | I, D | ~1 acto de cuota |

**Regla de orden: lo barato primero.** Un gate de Python que cuesta veinte milisegundos evita una llamada a opus que cuesta cuota y minutos. Ejecutar `novela validar` antes de cualquier agente de revisión no es una optimización, es el diseño. Invertir ese orden gasta el presupuesto en descubrir cosas que un `assert` ya sabía.
