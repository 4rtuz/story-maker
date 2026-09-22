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

**Estado a 2026-09-22: ninguno de estos métodos corre todavía.** `backend/` y `frontend/` están vacíos, `.claude/` contiene solo `settings.json` con plugins de desarrollo, y no hay agentes, hooks, tests ni CI. La columna dice qué se espera de cada método cuando la spec 0001 esté implementada, no qué se ejecuta hoy; pasa a describir ejecución real conforme cierra cada fase del plan de implementación.

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
| 22 | Detección de deriva a escala de novela | A + T | la novela entera | métricas entre capítulos en `auditar` | v1 |
| 23 | Reproducción del estado | A + T | `estado.db`, `memoria/` | replay de `estado/deltas/*.json` sobre base vacía | v1 |

---

## 3. Verificación de código

### 3.1 Type checking — A

Dos fronteras, y la segunda es la que importa.

- **Estática**: `mypy --strict` sobre `backend/`, `tsc --noEmit` sobre `frontend/`. Los tipos del frontend se generan desde el OpenAPI del backend (§3.8), así que no pueden derivar por su cuenta.
- **En el borde**: todo lo que llega de disco o de un agente es `Any` hasta que un modelo Pydantic lo parsea. **Regla dura: ningún dato cruza de disco o de agente al código sin pasar por un modelo de `backend/novela/dominio/`.** `json.load()` suelto en el código de negocio es un bug, no un atajo.

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
- **Plataforma**: en Windows, `os.replace` falla con `PermissionError` si otro proceso tiene abierto el destino —la API sirviendo ese capítulo, un antivirus—. El test abre el destino con otro handle y escribe: `atomic.py` reintenta con espera acotada y, si agota, sale con error dejando el fichero anterior intacto. CA-04 inyecta la excepción; esto la provoca de verdad, que no es lo mismo.
- **Sink caído**: con `TRACE_TO_LANGFUSE="true"` y Langfuse inalcanzable o colgado, `checkpoint` escribe igual, sale con 0 dentro de un timeout fijo y deja el fallo en `harness.log`. CA-22 prueba el sink apagado; el que para una novela es el encendido sin red.

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

**API ↔ frontend.** FastAPI emite OpenAPI; el frontend genera sus tipos desde ahí; CI falla si el esquema commiteado no coincide con el que genera el código. Eso es el contrato entero. No hace falta Pact para dos partes que viven en el mismo repo.

**Agente ↔ CLI.** Los ficheros de `qa/`, el delta del `cronista` y el frontmatter de capítulo son contratos igual de reales, entre un productor no determinista y un consumidor estricto. Se tratan igual: JSON Schema versionado en `backend/schemas/`, validación en ambos lados, y `schema_version` en el propio documento. Cuando un agente empieza a devolver un campo de más, quieres enterarte en el capítulo 1.

**Harness ↔ Claude Code.** El tercero, y el que nadie mira porque no parece un contrato: los ficheros de `.claude/`. El frontmatter de cada agente —`name`, `model`, `tools`— es lo que sostiene los invariantes 1 y 3 (§4.4), y es texto que se edita a mano sin que nada lo compruebe. Un test estático sobre los siete ficheros —cada agente con exactamente las herramientas de `architecture.md` §7.4, ninguno con `Bash`, `Task`, `Skill`, `Glob` ni `Grep`, el modelo que le toca por rol— cuesta una función y falla en el commit en vez de en el capítulo 9. Vale igual para los hooks: si `CLAUDE.md` da por existente `PreToolUse`, que CI compruebe que el fichero está y es ejecutable.

Y el cruce entre ambos, que es donde hoy hay un conflicto escrito: el hook deniega todo `Write` bajo `estado/` (`architecture.md` §7.1) y la salida declarada del `cronista` es `estado/deltas/NN.json` (§7.5). Tal como están, o el hook bloquea al `cronista` o lleva una excepción que nadie ha declarado. El test ejecuta el script del hook contra cada ruta de salida de la tabla de §7.5 —debe permitirla— y contra `estado/estado.db` —debe denegarla—, y el conflicto aparece en CI en vez de en el primer capítulo.

### 3.9 Gates de artefacto — A + T

Un gate es código barato en una frontera. El sistema tiene hoy uno solo, `novela validar` sobre el capítulo recién escrito, y varias fronteras que se cruzan sin nada.

**1. `plan/` y `canon/`, antes del capítulo 1.** Es el punto de mayor apalancamiento del sistema entero y no tiene verificación. El fair play (invariante 4) es comprobable sobre el plan sin leer una línea de prosa: toda `rev-` tiene al menos una `pis-` plantada en un capítulo anterior, ninguna pista se paga antes de plantarse, todo id citado en una ficha de capítulo existe en el canon, y las palabras planificadas suman lo que dice `config.yaml`. `novela auditar` ya calcula casi esto, pero al cerrar la novela. Las mismas cuentas antes del capítulo 1 son un gate; después del 24 son una autopsia, y el coste de la diferencia es una novela entera de cuota.

**2. El delta contra el capítulo, antes de `aplicar-delta`.** `aplicar-delta` valida forma —esquema, ids únicos, cursor monótono— y nada comprueba que lo que el `cronista` fija haya ocurrido en el texto. El campo `cita` de `libro_de_hechos` lo hace mecánico: debe ser subcadena literal del capítulo aprobado. Es gratis, y es la única defensa contra que una alucinación entre en un registro que el invariante 2 ya no permite corregir (§5.9). Que el `cronista` sea el agente más barato del bucle no es un argumento en contra: es la razón.

**3. El capítulo después del `editor-estilo`.** `validar` corre antes de los tres revisores, y el `editor-estilo` reescribe `capitulos/NN.md` después (`architecture.md` §7.5). El fichero que el `cronista` lee, que se exporta y que queda como salida final nunca ha pasado un gate en su forma definitiva: el editor puede dejar el frontmatter desincronizado con el texto, bajar las palabras del mínimo o deshacer la frase donde estaba plantada una pista. Y el veredicto del `continuista` es sobre una versión que ya no existe. Re-ejecutar `validar` tras el editor cuesta milisegundos y cierra el hueco, con la condición del punto 4: sin él, la pista borrada no se ve.

**4. La pista, contra la prosa.** `validar` comprueba que las pistas del plan figuran en el frontmatter, y el frontmatter lo escribe el mismo `escritor` que puede haberse olvidado de plantarla: es una declaración, no una prueba. El remedio es el de `cita` en el delta. Cada pista plantada o pagada lleva en el frontmatter el pasaje que la contiene, y ese pasaje debe ser subcadena literal del cuerpo. Es lo que da al punto 3 la capacidad que promete: sin cita, re-validar tras el `editor-estilo` ve el frontmatter intacto aunque la frase haya desaparecido. Añadir el campo es un cambio de modelo, así que entra por spec.

**5. Canon y plan, entre dos capítulos.** `ColeccionAppendOnly` (spec 0001, RF-28) protege las colecciones del canon dentro de un proceso. Entre procesos el canon es markdown en disco y se edita sin que nada lo note. `checkpoint` guarda el hash de `canon/` y `plan/`, y el primer `briefing` del capítulo siguiente lo compara. Si difiere, para: cambiar el canon a mitad de novela es una decisión del orquestador (AGENTS.md) y tiene que constar, no descubrirse. Si además alguna colección append-only del canon anterior no es prefijo de la nueva, el cambio es inválido con o sin autorización.

**6. El rastro del capítulo, en el checkpoint.** `CLAUDE.md` exige generar el briefing antes de delegar y nada lo comprueba (§5.8). `checkpoint` puede hacerlo: antes de confirmar, exige que cada paso del capítulo tenga su `runs/<run_id>/briefings/NN-<agente>.md` y su salida declarada (capítulo, `qa/NN-*.json`, delta). Un agente invocado sin briefing no deja ese fichero, y el capítulo no se confirma. De paso cubre el borrado de briefings contra el que advierte §4.1.

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
| `novela pendiente` sale con un código propio, distinto de 0, mientras exista un `intervencion.md` sin marcar como resuelto | Que el bucle desatendido siga lanzando sesiones sobre una novela parada. Su `\|\| break` depende hoy del código de salida de `claude -p`, que ningún test fija (§5.8); `pendiente` sí es código y se prueba |

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

1. **Fuga del misterio.** El escritor recibiendo, infiriendo o deduciendo la solución. Sonda: ensamblar briefings sobre un canon marcado y buscar los marcadores; y plantar en `plan/capitulos/NN.md` texto que intente arrastrar `canon/misterio.md` al briefing.
2. **Inyección por contenido del workspace.** Los agentes leen ficheros escritos por otros agentes. Un capítulo o una ficha de canon que contenga «ignora tus instrucciones y…» es el vector natural, y no requiere atacante externo: basta un modelo que alucine una instrucción.
3. **Uso indebido de herramientas.** Un agente escribiendo `estado.db` directamente o invocando `aplicar-delta`. Lo cubre el frontmatter, pero se prueba explícitamente.
4. **Deriva de objetivo a 24 capítulos.** El escritor optimizando poco a poco su propia coherencia local por encima del plan. Es el fallo más difícil de detectar porque cada capítulo pasa sus gates; lo único que lo ve son las métricas entre capítulos de §4.13.
5. **Exfiltración.** La única salida de red es Langfuse. Las claves están en `settings.local.json`, fuera de git.
6. **Regresión silenciosa del entorno.** No es un atacante: es una actualización. Que `tools` restrinja el descubrimiento, que `PreToolUse` se dispare para las llamadas de un subagente —hoy sin verificar, `architecture.md` §12.7— y que el hook `Stop` vea el transcript son supuestos sobre un producto que se actualiza solo y que no promete ninguna de las tres cosas. Si una barrera deja de disparar, el sistema no avisa: sigue reportando que está protegido.

Contra la sexta, un **canario**: un agente de prueba que intenta deliberadamente lo prohibido —escribir bajo `estado/`, abrir `canon/misterio.md` por ruta conocida, ejecutar el CLI— y cuya invocación debe fallar. Si algún día pasa, la barrera ya no existe y te enteras a propósito, no por una base corrupta. Corre con la suite adversaria y además tras cada actualización mayor de Claude Code (§5.10).

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

Con un límite que conviene no perder de vista: esto verifica la máquina que el procedimiento *debería* seguir. Quien la implementa es `.claude/commands/novela-continuar.md`, prosa que ningún test ejecuta (§5.8).

### 4.11 Control negativo de los revisores — T + I

Un revisor que aprueba siempre es indistinguible de un sistema sano: los scores suben, los reintentos bajan y todo parece ir bien. La mutación de §3.7 hace exactamente esta pregunta sobre el código —«si rompo esto, ¿lo nota alguien?»— y nadie la hace sobre los agentes, que son la mitad cara de la verificación.

El ensayo es el mismo, aplicado a prosa: capítulos fixture con un defecto conocido sembrado —una contradicción contra el `libro_de_hechos`, un hilo cerrado que nunca se abrió, una pista pagada sin plantar, una filtración del misterio— y una tasa de detección por revisor. Un `continuista` que no coge la contradicción marcada no está revisando, y sin este control no hay forma de saberlo.

Y el control inverso: capítulos fixture sin defecto, para medir la tasa de falsos positivos. Un revisor que lo marca todo no se nota en los scores sino en las intervenciones, cuando ya ha agotado los reintentos de capítulos sanos.

Llama a modelos, así que no entra en `pytest` (§3.5): corre por release, con la suite adversaria. Los fixtures sí se versionan, porque el defecto sembrado es el único caso de este sistema en el que existe una respuesta correcta conocida, y eso es demasiado escaso como para no guardarlo.

### 4.12 Ensayos: reanudación y degradación — D

Dos procedimientos escritos y nunca ejecutados, y los dos se estrenan en el peor momento posible: uno después de una caída, el otro al borde del límite de cuota.

- **Reanudación.** `restore(checkpoint(e)) == e` (§3.6) prueba la función, no el procedimiento. Nadie ha matado el bucle entre `aplicar-delta` y `checkpoint` para ver si `/novela-continuar` repite el paso correcto sobre un workspace real. Un checkpoint que nunca se ha restaurado no es un checkpoint, es un fichero. Se ensaya con el agente falso, cortando en cada frontera de paso.
- **Degradación por cuota.** Los cinco niveles de `architecture.md` §9 no se han ejercitado nunca. Forzar cada nivel con el agente falso y comprobar qué agentes se invocan y cuáles no cuesta un test de integración, y evita descubrir que el nivel 4 estaba mal escrito justo cuando ya no queda cuota para arreglarlo.

### 4.13 Deriva a escala de novela — A + T

Los evals de §4.2 puntúan capítulos. La amenaza 4 de §4.9 —el escritor optimizando su coherencia local por encima del plan— y la convergencia de prosa de `architecture.md` §12.1 son propiedades de la novela entera, y hoy nada las mide: cada capítulo pasa sus gates mientras la curva se aplana.

Lo mecánico, barato y sin modelo:

| Señal | Se calcula con |
|---|---|
| `tension_real` contra la curva objetivo del plan | resta sobre `estado.db`; el dato ya está |
| Convergencia de aperturas y de vocabulario | n-gramas repetidos entre capítulos |
| Deriva de longitud y de ritmo | `metricas.desviacion_vs_plan` acumulada |
| Hilos sin cerrar, pistas plantadas sin pagar | lo que ya hace `auditar` |

Lo que falta no es el cálculo, es la **cadencia**: `auditar` corre al cerrar la novela. Las mismas cuentas en cada frontera de acto son un gate. Es además la única forma de saber si la restricción de apertura de `architecture.md` §2.2 sirve de algo: hoy es una mitigación declarada y sin un solo dato detrás.

### 4.14 Reproducción del estado — A + T

`estado.db` es la única fuente de verdad y no tiene copia: `checkpoints/NN.json` guarda cursor, versiones y `run_id`, no la base (spec 0001, RF-20). Pero el estado tiene una definición reproducible, que es aplicar en orden `estado/deltas/*.json` sobre una base vacía. Eso da un verificador sin modelo en dos puntos:

- **Al abrir la base.** `meta.schema_version` coincide con el código, los triggers append-only de las cinco tablas siguen en `sqlite_master` y `PRAGMA quick_check` devuelve `ok`. CA-02 prueba que los triggers se crean; esto prueba que siguen ahí. Una base a la que alguien quitó uno funciona sin dar un solo error, y ese es precisamente el problema.
- **En cada `checkpoint`.** Se reproducen los deltas en una base en memoria y se compara con `estado.db` tabla a tabla. Después se regenera `memoria/resumenes/` y se compara también. Una diferencia significa una de tres cosas: algo escribió la base por fuera de `aplicar-delta` (un `sqlite3` desde Bash, un hook que dejó de disparar, §5.10), un delta cambió después de aplicarse, o la base está corrupta. En cualquiera de los tres casos el checkpoint no confirma.

Requisito: `aplicar-delta` registra el hash de cada delta aplicado junto a su capítulo. Es la misma clave que necesita la idempotencia de §3.6, y es lo que permite detectar que un delta se editó después de aplicarse.

Hay un efecto más. Ni el `restore(checkpoint(e)) == e` de §3.6 ni el «se restaura del último checkpoint» de `architecture.md` §6.4 se cumplen con un JSON de cursor. Con la reproducción sí: restaurar es reproducir hasta el cursor del checkpoint. Con 24 deltas cuesta milisegundos.

Lo que no cubre: perder `estado/` entero se lleva los deltas junto con la base (§5.7). Tampoco cubre un delta fiel que fija una interpretación equivocada: la reproducción la reproduce igual (§5.9).

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

**5.8 El orquestador no tiene método asignado.** El bucle lo implementa `.claude/commands/novela-continuar.md`: no es código —no le aplica el TDD— ni prosa de novela —no hay juez que la puntúe—. §4.10 verifica la máquina de estados que ese fichero debería seguir, no el fichero. Lo único que lo cubre de verdad es la novela de humo (D). *Revisar en cuanto aparezca un fallo de orden que el model checking daba por imposible: significa que el procedimiento y la máquina han divergido.*

**5.9 Un error del `cronista` es permanente.** El invariante 2 protege contra reescribir la historia y, con el mismo mecanismo, fosiliza un hecho falso: no hay `UPDATE` que lo corrija, y todo capítulo posterior se escribe contra él. El gate de `cita` (§3.9) ataca la alucinación literal, no la interpretación equivocada de una escena. *Revisar si aparece una contradicción cuyo origen sea una entrada del libro de hechos y no un capítulo.*

**5.10 Las barreras dependen de comportamientos no contractuales de Claude Code.** `tools`, el alcance de los hooks en subagentes y lo que el hook `Stop` puede leer no son API estable. *Mitigado por el canario de §4.9, no eliminado. Revisar en cada actualización mayor.*

**5.11 El contexto del orquestador no se mide.** El techo de `architecture.md` §6.5 lo comprueba `novela briefing` para los subagentes; para la sesión que los invoca, los 6.000–8.000 tokens por capítulo son una estimación que nadie ha contrastado, y es el único contexto que no se vacía entre pasos. *Revisar con los conteos por turno de la primera novela de humo.*

---

## 6. Qué corre en cada punto

| Momento | Métodos | Clase | Coste |
|---|---|---|---|
| Pre-commit | Type checking, SAST, tests unitarios | A, T | segundos |
| CI del harness | + mutación sobre gates, contrato API, contrato de `.claude/`, model checking | T, A | minutos |
| Tras el `trazador`, una vez | `novela validar-plan`: fair play del plan, ids, orden de pistas | A | gratis |
| Al abrir `estado.db` | `schema_version`, triggers presentes, `quick_check` | A | gratis |
| Primer `briefing` de cada capítulo | sello de `canon/` y `plan/` contra el último checkpoint | A | gratis |
| `novela validar <cap>` | esquema, longitud, pistas presentes con cita literal en el cuerpo, hilos | A, T | gratis |
| Tras escribir el capítulo | `continuista`, `editor-estilo`, `lector-suspense` | I | 3 llamadas |
| Tras el `editor-estilo` | `novela validar` de nuevo, sobre el fichero final | A | gratis |
| Antes de `aplicar-delta` | `novela validar-delta`: `cita` literal presente en el capítulo | A | gratis |
| Cierre de capítulo | rastro completo de briefings y salidas, reproducción del estado, scores a Langfuse, checkpoint | A, T, D | gratis |
| `novela pendiente` | parada si hay un `intervencion.md` sin resolver | A | gratis |
| Frontera de acto | `auditar` parcial: deriva, tensión contra plan, hilos, pistas | A | gratis |
| Cierre de novela | `novela auditar`: pistas huérfanas, hilos sin cerrar | A | gratis |
| Tercer intento de un gate | `intervencion.md` y parada | I | humano |
| Release del harness | suite adversaria, canario de barreras, control negativo de revisores, novela de humo de 3 capítulos | I, T, D | ~1 acto de cuota |

**Regla de orden: lo barato primero.** Un gate de Python que cuesta veinte milisegundos evita una llamada a opus que cuesta cuota y minutos. Ejecutar `novela validar` antes de cualquier agente de revisión no es una optimización, es el diseño. Invertir ese orden gasta el presupuesto en descubrir cosas que un `assert` ya sabía.
