# Ontología de contexto — definiciones

Diccionario de referencia del harness multiagente de novela de suspense. Cada entrada declara qué es, cómo cambia y quién la escribe.

## Notación

Cada definición lleva una línea de atributos: `tipo` · **mutabilidad** · escribe → lee.

Clases de mutabilidad:

- **INMUTABLE** — se fija una vez y no cambia durante la ejecución.
- **VERSIONADO** — puede cambiar, pero solo por decisión del orquestador y dejando la versión anterior; el número de versión viaja en los metadatos de cada traza.
- **APPEND-ONLY** — solo se amplía. Corregir una entrada existente es un error de diseño, no una operación permitida.
- **MUTABLE** — se reescribe en cada ciclo.
- **DERIVADO** — se recalcula a partir de otra rama; nunca es fuente de verdad.

---

## 1. CONFIGURACIÓN DE EJECUCIÓN

Todo lo que el usuario decide antes de que el sistema arranque y que el sistema no puede renegociar por su cuenta.

**`idea_semilla`** — Texto libre del usuario que origina la obra. Puede ser una frase o tres páginas. Es la única entrada humana obligatoria.
`string` · **INMUTABLE** · usuario → arquitecto

**`parametros_obra.longitud_total_palabras`** — Objetivo global. Sirve de divisor para derivar el presupuesto por capítulo y de criterio de cierre.
`int` · **INMUTABLE** · usuario → trazador, orquestador

**`parametros_obra.num_capitulos`** — Número de capítulos a producir. Si el usuario fija longitud y número, `palabras_por_capitulo` se deriva; si fija solo uno, el trazador propone el otro.
`int` · **INMUTABLE** · usuario → trazador

**`parametros_obra.palabras_por_capitulo`** — Terna `{objetivo, min, max}`. El rango, no el objetivo, es lo que evalúa el gate de longitud: exigir un número exacto degrada la prosa. Derivada, es `objetivo = longitud_total_palabras // num_capitulos` con `min` y `max` a ±20 %.
`objeto` · **INMUTABLE** · usuario o derivado → escritor, gates

**`parametros_obra.subgenero`** — `thriller_psicologico | noir | domestic_suspense | procedural`. Condiciona el canon de estilo y las expectativas de fair play. Añadir un valor es cambio de esquema.
`enum` · **INMUTABLE** · usuario → arquitecto

**`parametros_obra.punto_de_vista`** — `primera_persona | tercera_limitada | multiple | narrador_no_fiable`. En suspense es una decisión estructural, no estilística: determina qué puede saber el lector.
`enum` · **INMUTABLE** · usuario → arquitecto, escritor

**`parametros_obra.tiempo_verbal` / `idioma` / `restricciones_contenido`** — `presente | pasado`; lengua de salida; límites explícitos de contenido que ningún agente puede cruzar.
`enum` / `string` / `lista` · **INMUTABLE** · usuario → todos

**`parametros_sistema.modelo_por_agente`** — Asignación de modelo a cada rol. Permite usar un modelo caro para el escritor y uno barato para el cronista.
`mapa` · **INMUTABLE** · usuario → orquestador

**`parametros_sistema.temperatura_por_agente`** — Temperatura por rol. Alta en escritor y arquitecto, baja o cero en continuista y cronista. Requiere acceso directo a API; no está disponible vía interfaz de suscripción.
`mapa` · **INMUTABLE** · usuario → orquestador

**`parametros_sistema.presupuesto`** — `{requests_dia, tokens_por_llamada, tokens_contexto_por_agente}`. El límite de requests diarias es la restricción operativa dominante y gobierna la política de degradación.
`objeto` · **INMUTABLE** · usuario → orquestador

**`parametros_sistema.politica_reintentos`** — Máximo de intentos por gate y qué se le pasa al agente en el reintento. La regla es pasar el informe de QA, nunca un "está mal" genérico.
`objeto` · **INMUTABLE** · usuario → orquestador

**`parametros_sistema.politica_checkpoint`** — Cada cuántos pasos se serializa el estado completo. Determina cuánto trabajo se pierde ante un fallo.
`enum` · **INMUTABLE** · usuario → orquestador

---

## 2. CANON

La verdad del mundo narrativo. No describe lo que ha pasado en el texto, sino lo que es cierto con independencia de que se haya escrito.

### 2.1 Premisa

**`logline`** — Una frase que contiene protagonista, deseo, obstáculo y apuesta. Es el resumen más comprimido del contexto y aparece en casi todos los prompts.
`string` · **VERSIONADO** · arquitecto → todos

**`pregunta_dramatica`** — La pregunta binaria que el lector quiere ver respondida y que el clímax responde. Distinta del misterio: el misterio es "quién lo hizo", la pregunta dramática es "¿conseguirá X sobrevivir a saberlo?".
`string` · **VERSIONADO** · arquitecto → trazador, lector de suspense

**`tema`** — Lo que la novela argumenta bajo la trama. Criterio de desempate cuando dos giros son igual de válidos estructuralmente.
`string` · **VERSIONADO** · arquitecto → trazador

**`promesa_al_lector`** — Contrato implícito del subgénero: qué tipo de satisfacción se está prometiendo y, por tanto, qué finales constituirían una traición.
`string` · **VERSIONADO** · arquitecto → lector de suspense

### 2.2 Mundo

**`escenarios[]`** — Lugares con identidad propia. Cada uno lleva `{id, nombre, descripción, detalle_sensorial, quién_tiene_acceso}`. El campo de acceso es material de trama: quién puede entrar a un sitio determina quién pudo hacer qué.
`lista` · **VERSIONADO** · arquitecto → escritor, continuista

**`epoca_y_tecnologia`** — `{epoca, existe, no_existe}`: qué existe y qué no. En suspense define el espacio de soluciones: si hay cobertura móvil, cámaras o ADN, media trama se cae o se sostiene.
`objeto` · **INMUTABLE tras canon** · arquitecto → escritor, continuista

**`reglas_del_mundo`** — Restricciones que no pueden violarse, realistas o no. El continuista las trata como axiomas verificables.
`lista` · **VERSIONADO** · arquitecto → continuista

**`instituciones`** — Policía, prensa, empresas, hospitales, con sus procedimientos. Fuente habitual de errores de verosimilitud si no se fija por escrito.
`lista` · **VERSIONADO** · arquitecto → escritor

### 2.3 Personajes

Una ficha por personaje en `canon/personajes/<id>.md`: todos los campos de abajo en el frontmatter YAML y prosa libre en el cuerpo. El modelo `Personaje` rechaza cualquier campo desconocido. `secreto` y `coartada_y_cronologia_privada` son campos propios, no prosa, para que puedan filtrarse del briefing del `escritor` (spec 0002).

**`identidad`** — `{id, nombre, alias, edad, rol_narrativo}`. El `id` es la clave de unión con todo el estado narrativo; el nombre visible puede cambiar en la trama, el id no.
`objeto` · **INMUTABLE** (el id) · arquitecto → todos

**`fisico`** — Rasgos observables y estables. Existe para que el continuista pueda detectar contradicciones triviales pero destructivas.
`objeto` · **VERSIONADO** · arquitecto → escritor, continuista

**`voz`** — Idiolecto, muletillas, registro y al menos un fragmento de diálogo canónico. El fragmento es más útil que la descripción: el escritor imita mejor de lo que obedece.
`objeto` · **VERSIONADO** · arquitecto → escritor, editor de estilo

**`psicologia`** — `{deseo, necesidad, miedo, herida}`. Deseo es lo que el personaje persigue; necesidad es lo que le falta y no sabe; el arco es el trayecto entre ambos.
`objeto` · **VERSIONADO** · arquitecto → escritor

**`secreto`** — `{que_oculta, a_quien}`: qué oculta el personaje y a quién (ids de personaje o `lector`). En suspense casi todos los personajes tienen uno, y no todos son el del misterio central. Opcional.
`objeto` · **VERSIONADO** · arquitecto → escritor con filtro, continuista

**`arco_previsto`** — Estado inicial → estado final, con los capítulos donde se producen los cambios de escalón. Es plan, no estado: lo real vive en la rama 4.
`objeto` · **VERSIONADO** · arquitecto → trazador

**`relaciones[]`** — `{con, tipo, tensión, historia compartida}`. Define el punto de partida; la evolución se registra en `estado.relaciones`.
`lista` · **VERSIONADO** · arquitecto → escritor

**`coartada_y_cronologia_privada`** — `[{momento, ubicacion, detalle}]`, con `momento` en texto como `linea_temporal.inicio` y `ubicacion` un id de escenario. Dónde estuvo realmente cada personaje en cada momento crítico, se cuente o no. Es la estructura que hace verificable el misterio: sin ella, el culpable puede estar en dos sitios a la vez y nadie lo detecta.
`lista` · **INMUTABLE tras canon** · arquitecto → continuista

### 2.4 Misterio

Subárbol de acceso restringido. Es la única parte del canon sujeta a aislamiento por rol.

**`verdad_oculta`** — Qué ocurrió realmente, completo y sin elipsis. Se escribe una sola vez, al principio, antes de cualquier capítulo.
`texto` · **APPEND-ONLY** · arquitecto → continuista, trazador. **Vedado al escritor.**

**`culpable_o_amenaza`** — El agente del daño. Puede ser una persona, un colectivo o una circunstancia.
`ref` · **INMUTABLE** · arquitecto → continuista

**`motivo_medio_oportunidad`** — Los tres requisitos clásicos, cada uno anclado a un hecho verificable del mundo. Si alguno no puede sostenerse, el misterio no cierra.
`objeto` · **INMUTABLE** · arquitecto → continuista

**`pistas[]`** — Unidad central del género. `{id, contenido, capitulo_plantado, capitulo_pagado, quien_la_percibe, es_fair_play}`. Una pista es información verdadera que el lector puede usar; existe en dos momentos distintos y el ciclo de vida entre ambos es lo que audita el sistema.
`lista` · **APPEND-ONLY** · arquitecto → trazador, escritor filtrado, auditoría final

**`pistas_falsas[]`** — Información que apunta a una conclusión equivocada sin mentir al lector. Lleva `{a_quién_apunta, cuándo_se_desmonta}`: una pista falsa que nunca se desmonta es un cabo suelto, no un giro.
`lista` · **APPEND-ONLY** · arquitecto → trazador

**`revelaciones[]`** — Momentos en que una parte de la verdad oculta pasa al conocimiento del lector. `{id, contenido, pistas_que_la_pagan, capitulo_previsto, quien_la_recibe, impacto}`. `pistas_que_la_pagan` es una lista de referencias a `pistas[]` con **mínimo uno**: es lo que hace el fair play verificable por aritmética en vez de por inferencia, y lo que lo convierte en guardarraíl —una revelación sin pista no se puede ni escribir— en lugar de en un hallazgo de la auditoría final. `quien_la_recibe` distingue `lector`, `personaje` o `ambos`, porque una revelación a un personaje no mueve `conocimiento_lector`.
`lista` · **APPEND-ONLY** · arquitecto → trazador, lector de suspense

**`giros[]`** — Revelaciones que además invalidan una creencia previa del lector: llevan los campos de `revelaciones[]` más `que_creia_el_lector_antes`, obligatorio, porque sin ese campo el giro no es evaluable.
`lista` · **APPEND-ONLY** · arquitecto → lector de suspense

**`reloj`** — El límite temporal de la trama: qué ocurre si no se resuelve y cuándo. Es lo que convierte misterio en suspense.
`objeto` · **VERSIONADO** · arquitecto → trazador, escritor

### 2.5 Estilo

**`guia_de_voz_narrativa`** — Cómo suena el narrador, en prescripciones accionables, no en adjetivos.
`texto` · **VERSIONADO** · arquitecto → escritor, editor de estilo

**`ritmo`** — Longitud media de frase y proporción objetivo entre diálogo, acción e interioridad. Medible, y por tanto verificable por el editor.
`objeto` · **VERSIONADO** · arquitecto → editor de estilo

**`prohibiciones`** — Clichés, tics y palabras vetadas. Lista viva: crece cuando el editor detecta un patrón repetido.
`lista` · **APPEND-ONLY** · arquitecto y editor → escritor

**`parrafos_canonicos[]`** — Fragmentos de referencia que definen el objetivo por ejemplo. Son el ancla contra la que se mide la deriva de voz a lo largo de la novela.
`lista` · **VERSIONADO** · arquitecto → escritor, editor de estilo

**`convenciones_formato`** — Títulos, separadores de escena, estructura del `.md`. Parte del contrato de salida, no de la estética.
`objeto` · **INMUTABLE** · arquitecto → escritor

---

## 3. PLAN

Lo que debería ocurrir. Se genera una vez a partir del canon y puede revisarse, pero cada revisión es un evento versionado y trazado.

**`escaleta_macro.actos[]`** — Bloques estructurales con su función dramática y los capítulos que abarcan.
`lista` · **VERSIONADO** · trazador → orquestador

**`escaleta_macro.puntos_de_giro`** — Detonante, punto medio, crisis, clímax, resolución, anclados a capítulos concretos.
`objeto` · **VERSIONADO** · trazador → escritor

**`curva_tension_objetivo`** — Valor de 1 a 10 previsto para cada capítulo. Existe para poder comparar contra la curva real y detectar mesetas.
`lista` · **VERSIONADO** · trazador → lector de suspense

**`capitulos[].objetivo_dramatico`** — Qué ha cambiado cuando el capítulo termina. Si no cambia nada, el capítulo sobra.
`string` · **VERSIONADO** · trazador → escritor

**`capitulos[].escenas[]`** — `{id, lugar, tiempo_diegético, personajes, beat, conflicto}`. La unidad mínima de planificación; el escritor recibe escenas, no resúmenes de capítulo.
`lista` · **VERSIONADO** · trazador → escritor

**`capitulos[].pistas_a_plantar[]` / `pistas_a_pagar[]`** — Referencias a `canon.misterio.pistas`. Es el mecanismo de aislamiento: el escritor recibe el contenido de estas pistas concretas y nada más del misterio.
`refs` · **VERSIONADO** · trazador → escritor, gates

**`capitulos[].hilos_que_abre[]` / `hilos_que_cierra[]`** — Contrato de subtramas del capítulo. Alimenta el balance de hilos abiertos del estado.
`refs` · **VERSIONADO** · trazador → cronista

**`capitulos[].gancho_final`** — Tipo de cliffhanger y su función. Se especifica el tipo, no el texto, para no encorsetar al escritor.
`enum` · **VERSIONADO** · trazador → escritor

**`capitulos[].dependencias`** — Capítulos que deben estar escritos antes. Permite detectar si la planificación admite paralelismo o es estrictamente secuencial.
`refs` · **VERSIONADO** · trazador → orquestador

---

## 4. ESTADO NARRATIVO

Lo que ya ocurrió. Fuente única de verdad sobre el texto existente. Vive en `estado/estado.db`, una base SQLite con una tabla por colección, no en la conversación de ningún agente. La mutabilidad que declara cada entrada de abajo la impone el esquema: las colecciones append-only tienen triggers que abortan cualquier `UPDATE` o `DELETE`.

**`cursor`** — `{capitulo, fase, ultimo_paso, intento}`. Lo primero que lee el orquestador al reanudar. Sin él no hay recuperación posible tras un corte. `fase` es `escritura | revision | registro | cerrado`; `ultimo_paso` es uno de los nueve pasos del bucle; `intento` se persiste porque la parada al tercero depende de él.
`objeto` · **MUTABLE** · orquestador → orquestador

**`linea_temporal[]`** — Cada escena escrita con su momento diegético y duración. Permite detectar el error más común del formato largo: dos cosas ocurriendo simultáneamente en sitios distintos.
`lista` · **APPEND-ONLY** · cronista → continuista

**`personajes[]`** — Por personaje: ubicación, estado físico y emocional, condición vital, objetivo activo y última aparición. Es el estado de entrada de la siguiente escena en que aparezca.
`mapa` · **MUTABLE** · cronista → escritor, continuista

**`conocimiento[]`** — Qué sabe cada personaje y desde qué capítulo. En suspense es la estructura más importante del estado: casi todo el género consiste en administrar asimetrías de información.
`mapa` · **APPEND-ONLY** · cronista → escritor, continuista

**`relaciones`** — Aristas entre personajes con su estado actual de confianza, sospecha o alianza. Evoluciona; el canon solo fijó el punto de partida.
`grafo` · **MUTABLE** · cronista → escritor

**`objetos[]`** — `{id, poseedor, ubicacion, capitulo_intro, relevancia}`, con `relevancia` en `alta | media | baja`. Los objetos con relevancia alta son pistas materiales y no pueden desaparecer sin explicación.
`lista` · **MUTABLE** · cronista → continuista

**`libro_de_hechos[]`** — Registro de hechos afirmados por el texto, con capítulo de origen y cita. Es el contrato de no contradicción: una vez que el texto afirma algo, es verdad para siempre. El continuista valida contra esta lista antes que contra ninguna otra cosa.
`lista` · **APPEND-ONLY, INMUTABLE por entrada** · cronista → continuista

**`hilos[]`** — Subtramas y preguntas pendientes, en una sola colección con `estado` (`abierto | cerrado`) como discriminante, y el capítulo en que se abrieron. Un hilo abierto sin cerrar a tres capítulos del final es una alerta.
`listas` · **MUTABLE** · cronista → orquestador, auditoría

**`pistas[]`** — Ciclo de vida de cada pista: `plantada`, `pagada`, `pendiente`, `huérfana`. Derivado del cruce entre plan y texto escrito; una pista plantada y nunca pagada es el fallo de calidad más caro del género.
`mapa` · **DERIVADO** · cronista → auditoría final

**`conocimiento_lector`** — Qué sabe el lector en este punto, frente a lo que saben los personajes. La diferencia entre ambos es la ironía dramática, y es un parámetro que se dosifica, no un subproducto.
`objeto` · **APPEND-ONLY** · cronista → lector de suspense

**`tension_real[]`** — Puntuación efectiva por capítulo escrito, emitida por el lector de suspense. Se compara contra la curva objetivo del plan.
`lista` · **APPEND-ONLY** · lector de suspense → orquestador

**`metricas`** — Palabras totales y desviación respecto al plan. `desviacion_vs_plan` es una fracción con signo, no un porcentaje. Alimenta la decisión de comprimir o expandir los capítulos restantes.
`objeto` · **DERIVADO** · cronista → orquestador

Los nombres de esta rama son los del documento serializado de `architecture.md` §7.1, que es el que valida `state.schema.json`, el que responde la API y el que nombra las tablas de `esquema.sql`. Un nombre por campo: no hay alias.

---

## 5. MEMORIA

No es información nueva: es la política de qué porción del contexto entra en cada prompt y con qué grado de compresión.

**`inmediata`** — Texto íntegro del capítulo anterior, o al menos su escena de cierre. Garantiza continuidad de tono y de gancho entre capítulos consecutivos.
`texto` · **DERIVADO** · cronista → escritor

**`reciente`** — Resúmenes detallados de los últimos N capítulos. N se calibra contra el presupuesto de tokens del escritor.
`lista` · **DERIVADO** · cronista → escritor

**`remota`** — Resúmenes jerárquicos por capítulo en tres granularidades (una línea, un párrafo, detallado), más resúmenes por acto y uno global. La jerarquía permite elegir el nivel de detalle según lo que quede de presupuesto.
`arbol` · **DERIVADO** · cronista → escritor, continuista

**`permanente`** — Canon más libro de hechos. La única capa que nunca se comprime ni se omite, en ningún prompt de ningún agente.
`ref` · **DERIVADO** · — → todos

**`indice_recuperable`** — Índice vectorial sobre escenas para consultas puntuales del tipo "¿dónde se mencionó este objeto?". Opcional: solo se justifica a partir de cierta longitud.
`indice` · **DERIVADO** · cronista → continuista

**`recetas_de_ensamblado[]`** — Por cada agente: qué capas entran, en qué orden y con qué presupuesto de tokens. Es la pieza que materializa la gestión de contexto; cambiarla es el principal mecanismo de optimización del sistema y va versionada en los metadatos de Langfuse.
`mapa` · **VERSIONADO** · diseño → orquestador

---

## 6. ARTEFACTOS EN DISCO

El contexto persiste como ficheros, no como historial de conversación. Cada subagente de Claude Code arranca en frío y reconstruye lo que necesita leyendo.

**`config.yaml`** — Serialización de la rama 1. Se escribe al inicio y no se toca.

**`canon/`** — `premisa.md`, `mundo.md`, `personajes/*.md`, `misterio.md`, `estilo.md`. Un fichero por personaje permite cargar solo los que aparecen en el capítulo.

**`plan/`** — `escaleta.md` y `capitulos/NN.md`. La ficha de capítulo es el prompt de trabajo del escritor.

**`estado/estado.db`** — Rama 4 completa en SQLite. Cada escritura es una transacción y cada fila pasa por las restricciones del esquema: si alguna falla, la transacción se deshace entera y no se escribe estado corrupto. Se lee con `novela estado`; ningún agente la abre.

**`memoria/resumenes/NN.md`** — Resúmenes jerárquicos, un fichero por capítulo con las tres granularidades.

**`capitulos/NN.md`** — Salida final, con frontmatter que declara capítulo, pov, palabras y pistas tratadas.

**`qa/NN-<agente>.json`** — Un fichero por agente —`continuidad`, `estilo`, `suspense`— más `validacion`, que lo escribe el CLI. Formato en `architecture.md` §7.3. Es el único input del reintento.

**`checkpoints/`** — Snapshots de estado y cursor. Permiten reanudar sin reprocesar y sin gastar requests.

**`CLAUDE.md`** — Convenciones del repositorio. Todo agente lo lee antes de actuar, de modo que las reglas no se repiten en cada prompt.

---

## 7. AGENTES

Subagentes de Claude Code. Cada uno tiene un contrato explícito: `{rol, entradas_permitidas, esquema_de_salida, herramientas, modelo, max_tokens}`.

**`orquestador`** — Único proceso con visión del bucle. Invoca agentes, aplica gates, controla presupuesto y decide reintentos. No escribe prosa nunca.

**`arquitecto`** — Convierte la idea semilla en canon completo, misterio incluido. Es la llamada de mayor temperatura y mayor impacto de todo el sistema.

**`trazador`** — Convierte canon en plan. Su trabajo real es distribuir las pistas: decidir en qué capítulo se planta cada una y en cuál se paga.

**`escritor_capitulo`** — Produce prosa a partir de la ficha de capítulo, la memoria ensamblada y el estado. Es el único agente con acceso restringido al canon: recibe las pistas de su capítulo, no la solución.

**`continuista`** — Verifica el capítulo contra el libro de hechos, la cronología y el canon. Salida estructurada de contradicciones, no prosa. Temperatura cero.

**`editor_estilo`** — Corrige voz, ritmo y prohibiciones contra los párrafos canónicos. Reescribe; es el único agente además del escritor que toca el texto final.

**`lector_suspense`** — Evalúa tensión, fair play y previsibilidad. Emite puntuaciones que van directas a Langfuse como scores.

**`cronista`** — Extrae del capítulo aprobado los hechos nuevos, actualiza el estado y genera los resúmenes. Es el agente que hace posible el formato largo, y el más barato de todos.

---

## 8. PROTOCOLO DE ORQUESTACIÓN

**`fases`** — `setup → canon → plan → loop_capitulos → cierre → export`. Cada transición produce un checkpoint.

**`loop_por_capitulo`** — `ensamblar contexto → escribir → verificar → corregir → evaluar → actualizar estado → checkpoint`.

**`gates`** — Condiciones que el capítulo debe cumplir para avanzar: continuidad sin contradicciones, longitud dentro de rango, pistas planificadas efectivamente presentes, tensión dentro de la banda objetivo. Un gate fallido devuelve al escritor con el informe de QA como única entrada nueva.

**`handoffs`** — Esquemas de entrada y salida entre agentes, como JSON o frontmatter. El acoplamiento entre agentes es por esquema, no por texto libre.

**`reintentos`** — Máximo por paso. Agotados los intentos, el sistema se detiene y emite un informe de intervención humana en lugar de degradar la calidad en silencio.

**`reanudacion`** — Lectura de cursor y checkpoint. Regla dura: el estado nunca se reconstruye a partir de la conversación.

**`presupuesto`** — Contador de requests y tokens, con política de degradación: qué pasos son prescindibles cuando queda poca cuota y en qué orden se sacrifican.

---

## 9. OBSERVABILIDAD (LANGFUSE)

**`session`** — Una ejecución completa de novela. `session_id = novela_id + run`.

**`trace`** — Un capítulo, o una fase de setup. Es el nivel donde se comparan ejecuciones entre sí.

**`span`** — Una invocación de agente dentro de un capítulo.

**`generation`** — Una llamada al modelo, con modelo, tokens de entrada y salida, coste y latencia.

**`metadata`** — `{capitulo_n, agente, version_canon, version_plan, receta_contexto, intento}`. Sin `receta_contexto` y `version_*` no se puede atribuir una mejora a un cambio concreto.

**`prompts_versionados`** — Un prompt por agente gestionado en Langfuse, con etiqueta de versión, de modo que un cambio de prompt sea un evento identificable en las trazas.

**`scores[]`** — Coherencia, continuidad, tensión, longitud, fair play, estilo. Se emiten por capítulo y se agregan por sesión.

**`evaluadores`** — LLM como juez a nivel de traza y de sesión. El evaluador de sesión compara ejecuciones y devuelve puntos a mejorar y mejoras propuestas.

**`datasets`** — Capítulos de referencia para test de regresión al modificar prompts o recetas de contexto.

---

## 10. GUARDARRAÍLES

**`esquema_validado`** — El estado lo validan las restricciones del esquema SQL de `estado.db` fila a fila, y los modelos Pydantic en la frontera: al leer un delta y al serializar para la API. El frontmatter de cada capítulo se valida contra JSON Schema. Escritura inválida, paso fallido.

**`inmutabilidad`** — El libro de hechos y la verdad oculta solo se amplían. Editar una entrada previa es reescribir la historia y rompe toda verificación posterior. No es una regla que se compruebe: los triggers de las tablas append-only la hacen imposible.

**`aislamiento_del_secreto`** — El escritor no recibe `misterio.verdad_oculta`. Un modelo que conoce la solución la filtra en el subtexto mucho antes de tiempo.

**`fair_play`** — Ninguna revelación sin al menos una pista plantada previamente. Se verifica automáticamente cruzando `revelaciones.pistas_que_la_pagan` con `pistas`: toda pista que paga una revelación tiene que estar plantada en un capítulo anterior.

**`limites_longitud`** — Por capítulo y acumulado, con corrección progresiva del objetivo de los capítulos restantes.

**`deteccion_deriva`** — Comparación periódica de la voz del texto reciente contra los párrafos canónicos. La deriva de estilo en formato largo es gradual e invisible capítulo a capítulo.

**`auditoria_pistas_huerfanas`** — Comprobación final: ninguna pista plantada sin pagar, ningún hilo abierto sin cerrar, ninguna pista falsa sin desmontar.
