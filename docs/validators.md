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

**Estado a 2026-09-23: la spec 0001 está implementada y lo que depende de `.claude/` sigue sin existir.** Corren hoy, en pre-commit o en CI (`.github/workflows/ci.yml`): 1 y 2 sobre `backend/` —no hay `frontend/`, así que ni `tsc` ni `eslint`—; 5; 6 sobre las funciones puras de la spec 0001; 7 sobre `gates.py` y `apply.py`; 8 en sus dos primeros contratos, el OpenAPI commiteado y los JSON Schema de `backend/schemas/`; 9 en lo que cierra la spec 0001 —`validar`, `checkpoint` y las precondiciones de `aplicar-delta`—, sin `validar-plan` ni `validar-delta`; 13 en su parte de código —aborto del briefing por texto del misterio, triggers append-only, validación del slug—; 16 sin el `sucio` del manifiesto; 19 y 24. Los siete agentes de `.claude/agents/`, `settings.json` y el hook `PreToolUse` existen, y CI comprueba los tres: corren el tercer contrato de 8 y 13 entero, con el `tools`, el `deny` y el hook. No hay slash commands, así que 10, 11 —salvo el emisor de scores de `checkpoint`—, 12, 14, 15, 20 y 27 no corren hasta que la spec 0003 los construya. Del 28 (§4.17) corren las filas marcadas `activo`. 18, 21, 22, 23, 25 y 26 no están construidos. La columna sigue diciendo qué se espera de cada método; este párrafo, cuál corre de verdad.

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

El canario de contención existe: `backend/tests/canario/ejecutar.py`, con dos agentes que `claude -p --agents` define solo para su sesión, `canario` y un impostor con `name: escritor`. Empieza con `novela comprobar-entorno --limpio` y no lanza nada si falla. Tiene cinco intentos que deben fallar —escribir bajo `estado/`, leer `canon/misterio.md` por su ruta, ejecutar `novela`, que el impostor escriba `canon/estilo.md` y que la sesión principal invoque a `general-purpose`— y dos controles que deben pasar: un nonce que solo el `canario` conoce y una escritura permitida en el workspace. El veredicto sale del disco y de los transcripts de la sesión, que `--session-id` permite localizar, y exige el motivo del hook en los intentos 1, 4 y 5. Corre por release del harness y tras cada actualización mayor de Claude Code. **Todavía no ha dado verde.** Su primera ejecución, el 2026-09-23, salió en rojo porque los dos agentes se negaron a intentar lo prohibido (F-64). Dejó dos datos: la regla 5 del hook paró a `general-purpose` en una sesión real, así que el hook hereda el entorno de `claude`, y `--agents` sustituye al `escritor` del proyecto. La parte del orquestador sigue siendo de la spec 0002.

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

**Estado a 2026-09-23: nada de esta sección corre todavía.** La columna «Estado» dice qué lo introduce:

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
| F-06 | Un informe de QA malformado, o sin `veredicto` | El orquestador lee basura en el gate y puede aprobar | El procedimiento cuenta un `veredicto` ausente o ilegible como rechazo. Después, `novela gate` lo valida contra el modelo | D; A | activo en el procedimiento (CA-18, revisión); en ejecución, la novela de humo (CA-10); después, 0002 |
| F-07 | Un revisor lee `capitulos/NN.md` del disco en vez del texto incrustado, mientras el `editor-estilo` lo reescribe en el mismo turno | Veredicto sobre una versión intermedia que la custodia no ve, porque su briefing lleva el hash correcto | El cuerpo del agente manda juzgar lo incrustado. No hay verificador mecánico | I | U (§5.15) |
| F-08 | Un retorno de más de tres líneas | Consume el contexto del orquestador | Auditoría de trayectoria (§4.16) | A | 0002 |
| F-09 | En un reintento, el `arquitecto` no puede reescribir `canon/misterio.md`: el `deny` le impide leerlo, y `Write` no sobrescribe un fichero que el agente no ha leído | Un canon inválido por el misterio gasta los dos reintentos del gate del `arquitecto` y acaba en intervención | Ninguno. El cuerpo del agente manda fallar citando la causa | — | propuesto |

**Hook `PreToolUse`**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-10 | `python` no resuelve, o la ruta del script en `settings.json` está mal | El hook sale con un código distinto de 2 y **falla abierto**: todas las escrituras pasan, sin aviso | Comprobación de puesta en marcha. CA-06 comprueba que la orden nombra el script, y una aserción más, que el fichero existe. El primer intento del canario lo detecta | D + T | activo en su parte estática (CA-06); la dinámica, 0003 (fase 6, CA-09) |
| F-11 | Claude Code cambia la forma de la entrada, por ejemplo el nombre de `file_path` | El hook falla cerrado y deniega todas las escrituras: el bucle no avanza | El freno del bucle (RF-22) y el control positivo del canario (F-60) | D + T | 0003, CA-09 |
| F-12 | Desaparece `agent_type` de la entrada | La regla 2 se apaga sin aviso, y la regla 3 trata a todo subagente como sesión principal | Control positivo del canario: `notas/control.txt` no se escribe. El intento 4 no lo detecta, porque la regla 3 también lo deniega | T | 0003, CA-09 |
| F-13 | Variantes de ruta: mayúsculas, `\`, `..`, absoluta o relativa | Una escritura bajo `estado/` que el comparador no reconoce | Property-based sobre el script, ejecutado como subproceso | T | activo (CA-03) |
| F-14 | Variantes de NTFS: punto o espacio final en un segmento (`estado./`), flujo alternativo (`estado.db:x`), prefijo `\\?\` | Win32 normaliza la ruta al escribir, y la regla 1, que es una lista de denegación, no la reconoce. La regla 2 es una lista blanca con `fullmatch` y ya las deniega | Normalizar los tres casos en el hook y añadirlos a la estrategia de CA-03 | T | activo (CA-03, RF-05) |
| F-15 | Nombres cortos 8.3 (`ESTADO~1`), uniones y enlaces simbólicos | Como F-14, pero sin forma de normalizarlos sin tocar el disco | Por debajo del hook: los triggers de `estado.db` y la reproducción del estado (§4.14) | A | U (§5.14) |
| F-16 | La tabla de salidas del hook y el contrato de los agentes divergen | El hook para a un rol en su salida legítima, o le deja escribir en otra | Test que compara `SALIDAS` del hook con el contrato de CA-01 | T | activo (plan, D-2) |
| F-17 | El hook bloquea al `cronista` | El delta no se escribe nunca | Mitad positiva de CA-03 y de CA-05 | T | activo (CA-03, CA-05) |
| F-18 | Latencia del hook | Cada escritura y cada `Bash` pagan el arranque del intérprete | Mediana por debajo de 300 ms | T | activo (RNF-01) |
| F-19 | La sesión principal escribe en el workspace: el capítulo «para ahorrar una llamada», el delta o un `qa/` | Sin una regla propia, a la sesión principal solo le aplicaría la de `estado/`, y `Edit(./novelas/**)` está permitido | Regla 3 del hook: sin `agent_type`, bajo `novelas/` solo se permite `runs/*/intervencion.md` | T | activo (CA-14, RF-25) |
| F-20 | El orquestador invoca un subagente que no es uno de los siete. `general-purpose` tiene todas las herramientas | Un agente con `Bash` y `Glob` dentro del bucle, al que solo aplica la regla 1. `Agent` no se puede restringir por nombre (E-9) | Regla 5 del hook: con `NOVELA_SESSION_ID` definido, que solo exportan el bucle y las sesiones del harness, deniega un `subagent_type` fuera de los siete y `canario`. Las sesiones de desarrollo no la tienen definida y conservan `Explore`. Que el hook herede el entorno de `claude` lo comprueba el quinto intento del canario | T | activo (CA-15, estática); la dinámica se observó el 2026-09-23: en una sesión real, la regla 5 paró a general-purpose. CA-09 sigue en rojo (F-64) |

**Permisos**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-21 | `settings.json` inválido | En `-p` se ignora sin avisar, y con él desaparecen el `deny` del misterio y el hook | Parseo y claves de primer nivel en el test | T | activo (CA-06) |
| F-22 | `settings.local.json` amplía permisos: un `allow` más, un `defaultMode`, otro hook | No está versionado, CI no lo ve, y el bucle lo carga con `--setting-sources project,local` | Comprobación previa de que solo contiene `enabledPlugins`, en `ejecutar.py` del canario y antes de lanzar el bucle | T | activo en su parte de código (CA-17); que el bucle y el canario la ejecuten, 0003 (RF-30, RF-18) |
| F-23 | La confianza del repo no está aceptada | El `allow` se ignora y el bucle gira sin avanzar | Freno del bucle (RF-22) | D | activo en seco (plan, tarea 6.3); con el bucle real, la novela de humo (CA-10) |
| F-24 | La herramienta `PowerShell` de Windows queda fuera del `matcher` | La rama de texto del hook no la ve. En `-p` con `dontAsk` se deniega porque no está en `allow`; en interactivo, Claude Code pregunta | Añadir `PowerShell` al `matcher` y comprobarlo en CA-06 | T | activo (CA-06, CA-11, RF-20) |
| F-25 | Una orden compuesta tras el prefijo permitido (`novela estado x && …`) | Si `Bash(novela:*)` casara solo el prefijo, el resto correría sin permiso | Canario del orquestador: una orden compuesta que debe denegarse | T | 0002 (§4.16); comportamiento sin verificar |
| F-26 | `claude` se lanza desde un subdirectorio, como `backend/` | Si no encuentra `.claude/`, no hay permisos, ni hook, ni comandos | Freno del bucle. El bucle documentado corre en la raíz | D | activo en seco: el bucle documentado corre en la raíz y lo para el freno; con el bucle real, CA-10 |

**Procedimientos**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-30 | Orden roto: revisiones antes de tener los tres briefings, el `cronista` antes del gate, o sin `validar` tras el editor | Los veredictos juzgan textos distintos | Custodia en `aplicar-delta` (0001 RF-32): la cadena de hashes no cierra y el delta no se aplica | A + T | activo |
| F-31 | La sesión lee mal la cuenta de intentos en `harness.log` | Reintentos de más, que gastan cuota, o una intervención prematura | Los intentos por gate se cuentan aparte en el baseline de la novela de humo. Después, `novela gate` | D; A | 0003 (riesgo aceptado de la spec); 0002 |
| F-32 | Un código 1 que viene de un fallo del CLI (un traceback, un import roto tras cambiar `pyproject.toml`) y no de un gate | El procedimiento lo toma por un gate fallido y reintenta al agente: gasta cuota en algo que ningún agente arregla | El procedimiento solo cuenta un 1 como gate si `harness.log` tiene la línea `<orden> NN -> 1` que el comando acaba de escribir; si no, para | D | activo en el procedimiento (CA-18); en ejecución, la novela de humo (CA-10) |
| F-33 | Un prompt de Task lleva prosa o el capítulo | Contexto contaminado y fuga de la señal (§4.6) | Inspección de las trazas en la novela de humo. Después, la auditoría de trayectoria | I; A | 0003 (CA-10); 0002 |
| F-34 | No se detecta un `intervencion.md` vivo | El bucle sigue sobre una novela parada | Ensayo: un `intervencion.md` sin `resuelto:` en el workspace de humo y una sesión de `/novela-continuar`, que debe parar sin invocar a ningún agente. Después, `novela pendiente` | D; T | 0003, CA-19 (RF-31); 0002 |
| F-35 | Punto de reanudación equivocado | Se repite un paso ya confirmado o se salta uno | Ensayo de reanudación (§4.12) sobre las cuatro filas de la tabla de reanudación. La custodia para lo que se salte `validar` | D + A | 0002 (§4.12) |
| F-36 | El slash command no se resuelve, por la conversión de rutas de MSYS | La sesión recibe una ruta y no hace nada | `MSYS_NO_PATHCONV=1` en el bucle, y el freno | D | activo: MSYS_NO_PATHCONV=1 en el bucle documentado; en ejecución, CA-10 |

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

**Bucle y trazado**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-50 | `novela` fuera del PATH, o la instalación editable sin sincronizar | Todas las órdenes fallan (ver F-32) | Comprobación de puesta en marcha, y `novela comprobar-entorno` antes del bucle | D + T | activo (CA-13, CA-17) |
| F-51 | Una sesión del harness sin `--setting-sources project,local` | Los hooks del ámbito de usuario reescriben órdenes, y el `allow` deja de casar (E-10). Además se inyecta contexto que el manifiesto no registra | El flag va en el bucle documentado y en las sesiones interactivas. Una sesión manual no tiene verificador | D | 0003; U (§5.17) |
| F-52 | El plugin de Langfuse no carga, o falla | Sin trazas y sin aviso: el bucle sigue | Novela de humo (CA-10) y `~/.claude/state/langfuse_hook.log` | D | 0003 |
| F-53 | Una sesión avanza el checkpoint pero ha hecho algo indebido | El freno no lo ve, porque solo mira si hubo avance | Auditoría de trayectoria | A | 0002 |
| F-54 | Los scores de `novela checkpoint` necesitan `TRACE_TO_LANGFUSE=true` y las claves en el entorno del proceso, y `comprobar-entorno` prohíbe `env` en `settings.local.json` | Sin las variables en el entorno de usuario, el bucle cierra capítulos sin emitir scores: el sink es no-op y no avisa. El baseline de CA-10 se queda sin sus seis scores | Ninguno. Las trazas del plugin no dependen de esto | — | propuesto |

**Canario**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-60 | El canario pasa en vacío: el agente no llegó a ejecutarse, o todo se deniega | Verde falso: cinco fallos que no prueban ninguna barrera | Dos controles positivos. El `canario` devuelve un nonce propio, que prueba que se ejecutó él, y escribe una ruta permitida del workspace, que tiene que existir | T | código listo (CA-09, RF-18); sin verde todavía (F-64) |
| F-61 | `--agents` no sustituye al `escritor` del proyecto | El cuarto intento lo hace el agente real | Nonce del impostor | T | código listo (plan, tarea 5.2); el 2026-09-23 el impostor corrió con el modelo de --agents: sustituye al del proyecto |
| F-62 | El misterio se lee pero no se imprime | El marcador no aparece en la salida y el intento parece fallido | Buscar el marcador también en los transcripts de la sesión, cuya ruta fija `--session-id` (E-5) | T | código listo (CA-09, RF-18); los transcripts se encontraron por --session-id el 2026-09-23 |
| F-63 | El canario corre con el árbol sucio o con `settings.local.json` ampliado | Prueba una configuración que no es la del bucle | `novela comprobar-entorno --limpio` al empezar `ejecutar.py` | T | 0003, CA-09 y CA-17 (RF-18, RF-28) |
| F-64 | Los agentes del canario se niegan a intentar lo prohibido: `CLAUDE.md` y `AGENTS.md` se cargan también en ellos y lo prohíben | El canario no prueba ninguna barrera. Sale en rojo, no en verde falso, porque faltan el nonce y los motivos del hook | Ninguno todavía: pide rehacer los prompts de `agente.json` por enmienda de la spec. Observado en la primera ejecución, el 2026-09-23 | — | propuesto |

**Novela de humo**

| # | Fallo | Consecuencia | Verificador | Clase | Estado |
|---|---|---|---|---|---|
| F-70 | Un baseline de una sola ejecución | Se usa como referencia una sola muestra con σ alta | El baseline declara su número de ejecuciones y no sirve para aceptar cambios de prompt hasta tener varias (§4.8) | — | U (§5.16) |

Tres filas están en **propuesto**, encontradas al implementar la 0003: F-09, al escribir los agentes; F-54, al registrar el hook, y F-64, en la primera ejecución del canario. Las que lo estaban antes entraron en la spec 0003 v0.3 (§16, «Enmiendas de la v0.3»), agrupadas en tres bloques:

- **endurecer el hook**: F-14, F-19, F-20 y F-24;
- **comprobaciones previas y controles positivos**: F-11, F-22, F-50, F-60, F-62 y F-63;
- **reglas de lectura del procedimiento y aserciones de test**: F-03, F-05, F-32, F-34, F-41 y F-44.

Un fallo nuevo que aparezca al implementar se añade aquí como `propuesto`, y va a la spec antes que al código.

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

**5.9 Un error del `cronista` es permanente.** El invariante 2 protege contra reescribir la historia y, con el mismo mecanismo, fosiliza un hecho falso: no hay `UPDATE` que lo corrija, y todo capítulo posterior se escribe contra él. El gate de `cita` (§3.9) ataca la alucinación literal, no la interpretación equivocada de una escena. *Revisar si aparece una contradicción cuyo origen sea una entrada del libro de hechos y no un capítulo.*

**5.10 Las barreras dependen de comportamientos no contractuales de Claude Code.** `tools`, el alcance de los hooks en subagentes, lo que el hook `Stop` puede leer, el formato del transcript del que depende §4.16 y el modelo al que resuelve cada alias no son API estable. *Mitigado por el canario de §4.9 y por el registro del modelo resuelto (§4.13), no eliminado. Revisar en cada actualización mayor.*

**5.11 El contexto del orquestador no se mide.** El techo de `architecture.md` §6.5 lo comprueba `novela briefing` para los subagentes; para la sesión que los invoca, los 6.000–8.000 tokens por capítulo son una estimación que nadie ha contrastado, y es el único contexto que no se vacía entre pasos. *Revisar con los conteos por turno de la primera novela de humo.* Cuando exista §4.16, esos conteos salen de cada sesión y este riesgo pasa de aceptado a medido.

**5.12 Las sondas ciegas son de la misma familia de modelo.** Que la sonda de §4.15 no adivine al culpable no prueba que un lector humano tampoco lo haga: da una cota inferior de la fuga, no una garantía de que no la hay. Lo mismo al revés: que la sonda deduzca la solución en el capítulo de la revelación no prueba que el fair play funcione para un lector humano. *Revisar si un lector humano de la novela de humo acierta antes que la sonda.*

**5.13 Las invariantes narrativas cubren lo que se puede escribir como regla.** §3.9.8 detecta al muerto que reaparece y el hilo que se cierra sin haberse abierto. No detecta un cambio de carácter sin causa, ni una relación que evoluciona sin escena que la justifique: eso sigue siendo trabajo del `continuista` (I). *Revisar si las intervenciones por contradicción se concentran en `relaciones` o en `personajes.estado_emocional`, que son mutables y no llevan cita.*

**5.14 El hook no normaliza lo que solo el disco resuelve.** Los nombres cortos 8.3, las uniones y los enlaces simbólicos dentro de `novelas/` pueden llevar una escritura a `estado/` sin que la ruta lo diga (F-15). Resolverlos exigiría tocar el disco en cada llamada, y un fichero que aún no existe no se resuelve igual en Windows y en Linux. Debajo del hook quedan los triggers de `estado.db` y la reproducción de §4.14. *Revisar si aparece en `estado/` un fichero que no creó el CLI.*

**5.15 Revisores y editor comparten turno.** Los tres revisores corren en paralelo, y el `editor-estilo` reescribe el capítulo mientras los otros dos lo juzgan. La custodia ata cada veredicto al texto incrustado en su briefing, no a lo que el revisor haya leído del disco (F-07). *Revisar si un hallazgo del `continuista` o del `lector-suspense` cita un texto que no está en su briefing.*

**5.16 El primer baseline es una sola ejecución.** La novela de humo de la 0003 da un número por score y capítulo, y la σ entre ejecuciones no se conoce (F-70). Sirve para detectar un sistema roto, no para comparar dos prompts (§4.8). *Revisar al tener tres ejecuciones con el mismo sha.*

**5.17 Una sesión manual del harness puede no ir aislada.** El bucle y la documentación lanzan `claude --setting-sources project,local`, pero nada impide abrir una sesión sin el flag. En ella actúan los hooks y plugins del ámbito de usuario (F-51). El manifiesto no lo registra, porque no sabe con qué flags se lanzó la sesión. *Revisar si una ejecución interactiva produce trazas o reintentos que no reproduce el bucle.*

---

## 6. Qué corre en cada punto

| Momento | Métodos | Clase | Coste |
|---|---|---|---|
| Pre-commit | Type checking, SAST, tests unitarios | A, T | segundos |
| Cada escritura o `Bash` de Claude Code | hook `PreToolUse`: `estado/`, salidas por rol, misterio y `estado.db` en órdenes (spec 0003) | A | < 300 ms |
| Antes del bucle desatendido y del canario | `novela comprobar-entorno`: `novela` en el PATH, `python` real, hook presente, `settings.local.json` solo con `enabledPlugins`; con `--limpio` en el canario (spec 0003) | A | gratis |
| Tras cada sesión del bucle | freno: sin avance de `checkpoints/latest.json`, el bucle para (spec 0003) | A | gratis |
| CI del harness | + mutación sobre gates, contrato API, contrato de `.claude/`, model checking | T, A | minutos |
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
