# Decisiones — Spec 0005

## D1 — Ubicación y ciclo de vida del brief
- **Pregunta original (P1):** ¿Dónde vive el brief mientras la novela aún no existe, si `novela nueva` reclama el slug con un `mkdir` sin `exist_ok` y el workspace es lo único que toca el backend?
- **Alternativas consideradas:** (a) `novelas/<slug>/brief/`, creado por un `novela brief iniciar` que reclama el slug, y `novela nueva --brief` completa el workspace; (b) un área fuera de los workspaces, `novelas/_briefs/<slug>/`, al estilo de la cola de `docs/architecture.md` §12.8; (c) que `novela nueva` cree el workspace completo antes del brief, con una `idea_semilla` provisional.
- **Decisión:** (a). `novela brief iniciar` crea `brief/entradas/`, `estado/` (para el lock) y `runs/`. El brief se cierra en cuanto existe `config.yaml`: los subcomandos de `novela brief` salen entonces con 1 (RF-07).
- **Justificación:** el backend es lo único que toca `novelas/<slug>/`, y `novelas/` ya está en `.gitignore`, lo que importa aquí porque el brief lleva datos personales. Con (a), el lock, el run y el hook funcionan sin cambios. `WorkspaceRepository.existe()` comprueba `config.yaml`, así que la API y `GET /novelas` ignoran un workspace que solo tiene el brief. (b) obliga a patrones de ruta especiales en el hook. (c) rompe `Config.idea_semilla` (`min_length=1`) y deja la API sirviendo una novela sin canon.
- **Fuente:** `AGENTS.md` § Monorepo y § Separación repo / workspace; `docs/architecture.md` §4; `backend/novela/plataforma/workspace.py` (`existe`) y `backend/novela/slices/nueva/cmd.py` (código consultado)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-04, RF-07), 8.3, 8.4, 9

## D2 — Invocación del entrevistador sin código que llame a modelos
- **Pregunta original (P2):** La petición pide «código que invoca» al agente. ¿Cómo se hace si ningún código Python puede llamar a un modelo?
- **Alternativas consideradas:** (a) un procedimiento `.claude/commands/novela-brief.md`, que sigue la sesión de Claude Code, más un subcomando determinista `novela brief preparar` que genera el briefing; (b) un cliente de modelos en Python; (c) invocar `claude -p` desde el CLI.
- **Decisión:** (a).
- **Justificación:** `AGENTS.md` prohíbe añadir un SDK o un gateway de modelos. En `docs/architecture.md` §2.1 la lógica del bucle vive en `.claude/commands/`, y el CLI solo hace operaciones deterministas entre delegaciones. (c) haría que el CLI lanzara modelos y gastara cuota, en contra de «Operaciones deterministas. No llaman a ningún modelo» (`AGENTS.md` § CLI). La petición también fija «todo corre sobre la suscripción de Claude Code».
- **Fuente:** Petición del usuario; `AGENTS.md` § Nunca y § CLI; `docs/architecture.md` §2.1
- **Confianza:** alta
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-01, RF-02, RF-08), 8.1, 8.4, 8.5

## D3 — Canal de entrada: ocasión por flag, respuestas y textos por fichero
- **Pregunta original (P3):** ¿Cómo llegan al workspace las respuestas y los textos del cliente, si la sesión principal no puede escribir en el workspace y un subagente no puede conversar con el operador?
- **Alternativas consideradas:** (a) el operador guarda cada aportación en un fichero fuera del repositorio y `novela brief entrada --fichero` la ingiere; (b) el orquestador pasa el texto como argumento (`--texto '…'`), escapado para bash; (c) ampliar la regla 3 del hook para que la sesión principal escriba en `brief/entradas/`.
- **Decisión:** (a) para respuestas y textos libres. La ocasión llega como flag cerrado de `novela brief iniciar`.
- **Justificación:** la regla 3 del hook solo deja a la sesión principal escribir `intervencion.md` en el workspace, y relajarla debilita una barrera de la spec 0003. Con (b), el modelo tendría que reescribir y escapar texto ajeno dentro de una orden Bash, lo que abre inyección en la shell y no garantiza literalidad. (a) conserva los bytes del cliente, deja la custodia en el CLI y cumple «cada orden `novela` va sola en su llamada a Bash».
- **Fuente:** `docs/architecture.md` §7.1 (regla 3); `CLAUDE.md` § Hooks; `.claude/commands/novela-nueva.md` § Códigos de salida del CLI
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-04, RF-05), 8.4, 8.5, 10

## D4 — Significado de «género»
- **Pregunta original (P4):** ¿«Género» es el género literario o el del destinatario? Si es literario, ¿qué valores admite?
- **Alternativas consideradas:** (a) género literario, con los cuatro `subgenero` de `config.py`; (b) género literario con valores nuevos (aventura, romance…); (c) sexo o pronombres del destinatario.
- **Decisión:** (a). `Genero` es un alias de `Subgenero`.
- **Justificación:** el ejemplo de contradicción de la petición, «edad frente a género o tono», solo tiene sentido con el género literario. El harness es de novelas de suspense, y añadir un valor a `subgenero` es un cambio de esquema que afecta al canon de estilo y al fair play. (c) añade un dato personal que la petición no pide (D19).
- **Fuente:** Petición del usuario; `AGENTS.md` § Qué es este proyecto; `docs/definitions.md` §1 (`parametros_obra.subgenero`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 8.3, 5 (RF-17, RF-25)

## D5 — Vocabulario de tono
- **Pregunta original (P5):** ¿El tono es texto libre o un vocabulario cerrado? ¿Con qué valores?
- **Alternativas consideradas:** (a) enum `ligero | tierno | emotivo | intrigante | oscuro`; (b) texto libre; (c) una escala numérica de oscuridad.
- **Decisión:** (a).
- **Justificación:** un enum hace verificable la contradicción edad-tono y cierra una vía de inyección: un texto libre en `tono` llegaría a `idea_semilla` sin control. Los cinco valores cubren un regalo de suspense desde lo infantil hasta lo adulto, y `oscuro` es el que activa C-02. Ningún documento del repositorio define tonos.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 8.3, 5 (RF-17)

## D6 — Extensión y número de capítulos
- **Pregunta original (P6):** La petición fija 10 capítulos de 1.000 a 1.500 palabras y pide recoger la «extensión». ¿Qué elige el cliente?
- **Alternativas consideradas:** (a) 10 capítulos fijos y `extension` `corta | media | larga` → objetivo 1.000, 1.250 y 1.500, con `min` 1.000 y `max` 1.500; (b) un número libre de palabras por capítulo entre 1.000 y 1.500; (c) también el número de capítulos.
- **Decisión:** (a).
- **Justificación:** 10 capítulos y el rango de 1.000 a 1.500 los fija la petición. `palabras_por_capitulo` es una terna `{objetivo, min, max}` y el gate compara con el rango, no con el objetivo, así que fijar `min` y `max` al rango pedido y dejar elegir solo el objetivo respeta los dos. Un enum de tres valores es más fácil de responder y de citar que un número libre.
- **Fuente:** Petición del usuario; `docs/definitions.md` §1 (`parametros_obra.palabras_por_capitulo`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1 (O-04), 5 (RF-25), 8.3

## D7 — Contradicciones que se detectan
- **Pregunta original (P7):** ¿Qué contradicciones detecta el CLI y con qué umbrales?
- **Alternativas consideradas:** (a) C-01 edad < 12 con `noir` o `thriller_psicologico`, C-02 edad < 12 con tono `oscuro` y C-03 término vetado presente en un recuerdo o rasgo; (b) solo C-01; (c) añadir ocasión frente a edad (boda o jubilación a edades bajas).
- **Decisión:** (a). C-01 y C-02 son Must y C-03 es Should.
- **Justificación:** la petición exige al menos un tipo y pone de ejemplo edad frente a género o tono. C-03 cuesta una búsqueda y detecta un brief que se contradice con sus propios vetos. El umbral de 12 años es una decisión de producto sin respaldo en el repositorio. (c) produciría falsos positivos (jubilaciones anticipadas, una ocasión «hijo» para un adulto).
- **Fuente:** Petición del usuario (tipo de contradicción); Supuesto (umbral y C-03)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-17, RF-18), 8.3, 9, 10

## D8 — Procedencia literal y aislamiento del texto libre
- **Pregunta original (P8):** ¿Cómo se comprueba sin un modelo que un texto libre con instrucciones inyectadas no altere el brief?
- **Alternativas consideradas:** (a) que todo valor textual del brief sea subcadena literal de una cita, que toda cita sea subcadena literal de su entrada y que los campos cerrados, el nombre, la edad y los vetos solo citen entradas `respuesta`, con custodia por sha256; (b) confiar en el prompt del agente y en los delimitadores; (c) un segundo agente que revise el brief.
- **Decisión:** (a), junto con la delimitación de D9 y los fragmentos marcados de D18.
- **Justificación:** es el patrón que el repositorio ya usa para que una alucinación no entre en el estado: la `cita` literal del delta, comprobada tras NFC y colapso de espacios. Con (a), un borrador que obedezca a la carta se rechaza por aritmética, que es lo que la petición pide probar con un test sin modelo. (b) no es verificable. (c) es otro juicio de modelo, del mismo tipo que `docs/validators.md` §4.6 desaconseja cuando existe un dato contra el que comparar.
- **Fuente:** Petición del usuario (texto no confiable, test de injection); `docs/architecture.md` §7.6; `docs/validators.md` §3.9.2 y §4.9 (amenaza 2)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1 (O-03), 5 (RF-09, RF-19, RF-20, RF-22), 6 (RNF-02), 9

## D9 — Marca de los delimitadores
- **Pregunta original (P9):** ¿La marca de apertura y cierre de cada bloque es aleatoria o determinista?
- **Alternativas consideradas:** (a) los 16 primeros hexadecimales del sha256 de `run_id`, id y texto; (b) aleatoria (`secrets.token_hex`); (c) un delimitador fijo con el texto escapado.
- **Decisión:** (a). Si el texto contiene su propia marca, `preparar` sale con 1 (RF-10).
- **Justificación:** el briefing tiene que salir igual byte a byte en un test golden, y una marca aleatoria lo impide. Un texto no puede contener el hash que depende de él mismo, así que el autor de la carta no puede anticipar el cierre. (c) altera el texto, y entonces las citas que copia el agente no casarían con la entrada guardada.
- **Fuente:** `docs/validators.md` §4.2 (golden dataset: «workspace fijo → briefing esperado, byte a byte»)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-09, RF-10), 8.4, 7 (CA-08, CA-09)

## D10 — Tres modelos y tres esquemas
- **Pregunta original (P10):** ¿Un solo modelo con campos opcionales, o uno para lo que escribe el agente y otro para el brief validado?
- **Alternativas consideradas:** (a) `BorradorBrief` (con `null`), `Brief` (estricto) e `InformeBrief`, cada uno con su esquema; (b) solo `Brief`, con campos opcionales; (c) `Brief` y un informe sin esquema.
- **Decisión:** (a): `brief-borrador.schema.json`, `brief.schema.json` y `brief-informe.schema.json`.
- **Justificación:** para detectar faltantes hay que poder representar un borrador incompleto. Si `Brief` admitiera `null`, un `brief.json` escrito podría estar incompleto y el esquema no lo diría. El contrato agente ↔ CLI exige un esquema versionado para lo que escribe el agente, y el informe lo lee el procedimiento, así que también es contrato. `test_state_schema_al_dia` ya recorre todo `esquemas.generar()` y exige `schema_version`.
- **Fuente:** `docs/validators.md` §3.8 (Agente ↔ CLI); `AGENTS.md` § Cómo trabaja cada rol; `backend/tests/test_contratos.py` (`test_state_schema_al_dia`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-14, RF-15, RF-24, RF-28), 8.3

## D11 — Modelo del entrevistador
- **Pregunta original (P11):** ¿`opus`, `sonnet` o `haiku`?
- **Alternativas consideradas:** (a) `sonnet`; (b) `haiku`, como el `cronista`; (c) `opus`.
- **Decisión:** (a).
- **Justificación:** es trabajo de estructurar y citar contra un esquema, como la verificación de los revisores («el rigor lo da el prompt y el esquema de salida»). Además redacta preguntas para una persona, lo que pide más que la extracción mecánica del `cronista`. `opus` se reserva a lo que condiciona la novela entera, y aquí el CLI verifica cada valor.
- **Fuente:** `docs/architecture.md` §2.2
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-01), 8.1

## D12 — El entrevistador fuera de `Agente` y de `recipes.yaml`
- **Pregunta original (P12):** ¿Se añade `entrevistador` al enum `Agente` y a `backend/config/recipes.yaml`, para que genere su briefing con `novela briefing`?
- **Alternativas consideradas:** (a) no: el slice `brief` ensambla su propio briefing, y el rol solo entra en `CONTRATO` y en `SALIDAS`; (b) sí: `novela briefing <slug> <cap> entrevistador` con una receta nueva.
- **Decisión:** (a).
- **Justificación:** `recipes.validar` exige una receta por cada valor de `Agente`, y las capas de receta hablan de canon, estado, plan y capítulos, que no existen en la fase de brief. `novela briefing` exige además un número de capítulo. Con vertical slices, el briefing del brief vive en su slice, y así el alcance no toca `recipes.yaml` ni el prompt de nadie.
- **Fuente:** `docs/architecture.md` §3.0 (vertical slices); `backend/novela/slices/briefing/recipes.py` y `test_recipes.py` (código consultado)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 8.2

## D13 — Documentación que se actualiza
- **Pregunta original (P13):** Además de `docs/definitions.md` y `docs/architecture.md`, que pide la petición, ¿qué documentos se tocan? ¿También `AGENTS.md` y `CLAUDE.md`, que hablan de «siete roles»?
- **Alternativas consideradas:** (a) los dos pedidos más `docs/validators.md`, `docs/domain-knowledge.md` y ediciones mínimas de `AGENTS.md` y `CLAUDE.md`; (b) solo los dos pedidos.
- **Decisión:** (a):
  - `docs/definitions.md` §1 (brief y sus campos), §6 (`brief/`) y §7 (`entrevistador`).
  - `docs/architecture.md` §2.2 (modelo), §3.1 (árbol), §4 (workspace), §5 (id `ent-NN`), §7.1 (reglas 2 y 5), §7.4 (tabla de `tools`), §7.5 (entradas y salidas) y §8 (comando y subcomandos).
  - `docs/validators.md` §2, §4.9 (el sistema maneja datos personales; amenaza 2 con la entrada del cliente; resultado de T-12) y §5 (riesgos aceptados de §11 de la spec).
  - `docs/domain-knowledge.md` §1 y §5.
  - `AGENTS.md` § Qué es este proyecto y § CLI; `CLAUDE.md` § Subagentes y § Hooks, sin fijar el número de roles (D14).
- **Justificación:** la documentación de referencia describe lo que hay y se actualiza en el mismo commit que el código que la cambia. `AGENTS.md` y `CLAUDE.md` solo se tocan si cambia una convención, y el conjunto de roles y el CLI lo son. `validators.md` §4.9 afirmaría algo falso («sin datos personales») si no se toca.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: modificar documentación y § Nunca (no ampliar sin necesidad)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1 (O-06), 5 (RF-30), 8.2, 12 (T-11)

## D14 — Coordinación con la spec 0002
- **Pregunta original (P14):** La spec 0002, aceptada, añade el rol `sonda` y deja la regla 5 «con ocho roles». ¿Cómo convive con un rol más aquí?
- **Alternativas consideradas:** (a) ningún test ni texto fija el número: los tests usan `CONTRATO`, `ROLES` se deriva de `SALIDAS` y la documentación habla de «los roles de `.claude/agents/`»; quien se integre segundo añade su fila; (b) fijar nueve roles ahora; (c) bloquear esta spec hasta implementar la 0002.
- **Decisión:** (a).
- **Justificación:** `test_hook.py::test_salidas_casan_el_contrato` ya compara `ROLES`, `CONTRATO` y `SALIDAS` como conjuntos, sin contar. (b) rompería si la 0002 no llega o se descarta. (c) ata dos cambios independientes.
- **Fuente:** `docs/specs/0002-verificacion-a-escala-de-novela.md` § RF-30; `backend/tests/test_hook.py` (`test_salidas_casan_el_contrato`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-03), 10, 11

## D15 — Reintentos del agente y rondas con el operador
- **Pregunta original (P15):** ¿Cuántas veces se reintenta al `entrevistador` y cuántas rondas de preguntas se admiten? ¿Cómo distingue el procedimiento un caso del otro?
- **Alternativas consideradas:** (a) 2 reintentos seguidos del agente ante hallazgos `esquema` o `procedencia`, y 5 rondas con el operador ante faltantes o contradicciones, distinguidos por el prefijo `agente:` o `usuario:` de la línea de log; (b) sin tope de rondas; (c) un único contador.
- **Decisión:** (a). Al agotarse cualquiera de los dos topes, `intervencion.md` y parar. El briefing es idempotente (RF-13).
- **Justificación:** el tope de dos reintentos por gate y la decisión leída del log, no de la conversación, son las reglas del bucle actual. Un error del agente se corrige reintentando, y un dato que falta solo lo resuelve el cliente, así que mezclarlos en un contador (c) agotaría reintentos por preguntas legítimas. El tope de 5 rondas es un supuesto para que la entrevista no gaste cuota sin fin.
- **Fuente:** `CLAUDE.md` § Bucle por capítulo («Máximo dos reintentos por gate»); `.claude/commands/novela-nueva.md` («Nunca cuentes en la conversación: la cuenta sale del log»); Supuesto (5 rondas)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-02, RF-13, RF-23), 8.5

## D16 — Datos personales y trazado
- **Pregunta original (P16):** El brief contiene datos personales de un tercero. ¿Se trazan a Langfuse la entrevista y el log?
- **Alternativas consideradas:** (a) abrir la sesión de brief con `--setting-sources project` sin `local`, de modo que el plugin de Langfuse no cargue; el log solo con códigos; y documentar como riesgo aceptado que la escritura de la novela sí se traza; (b) trazar como el resto; (c) desactivar el trazado de toda la novela de regalo.
- **Decisión:** (a).
- **Justificación:** el plugin se habilita solo en `.claude/settings.local.json`, así que excluir el ámbito `local` lo deja fuera sin tocar configuración versionada. La entrevista concentra los datos en bruto (cartas, anécdotas) y la escritura solo lleva lo que ya está en el brief. (c) quita la observabilidad al producto entero y se sale del alcance. Que excluir `local` baste es un supuesto, que se comprueba en T-12 (RNF-07).
- **Fuente:** `docs/architecture.md` §10.1 (plugin habilitado en `settings.local.json`) y §2.3 (`--setting-sources`); `docs/validators.md` §4.9 (hoy «sin datos personales»); Supuesto (que la exclusión basta y el reparto de riesgo)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 2, 5 (RF-23), 6 (RNF-04, RNF-07), 8.5, 10, 11

## D17 — Consumo del brief por `novela nueva`
- **Pregunta original (P17):** ¿Cómo pasa el brief a la novela: flag nuevo, subcomando nuevo o cambio del `arquitecto`?
- **Alternativas consideradas:** (a) `novela nueva <slug> --brief`, excluyente con `--idea` y los flags de obra, que deriva `config.yaml` (idea_semilla generada, 10 capítulos, terna, subgénero y restricciones) sin cambiar `Config` ni el prompt del `arquitecto`; (b) un campo `brief` nuevo en `Config`, con cambio de esquema; (c) una receta nueva para que el `arquitecto` lea `brief/brief.json`.
- **Decisión:** (a).
- **Justificación:** el `config.yaml` lo escribe siempre el backend, desde los flags o desde otra fuente, y nunca hay dos fuentes de los mismos parámetros. `idea_semilla` ya es texto libre de «una frase o tres páginas», y el `arquitecto` ya lo lee. (b) cambia `config.schema.json` y el `openapi.json` que usa el panel. (c) cambia un prompt, que no tiene TDD. Sin `--brief`, `novela nueva` sigue igual, como exige la spec 0001.
- **Fuente:** Petición del usuario («para que el harness parta de un brief estructurado»); `docs/architecture.md` §12.8; `docs/definitions.md` §1 (`idea_semilla`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1 (O-04), 3.2, 5 (RF-25, RF-26, RF-27), 8.4, 8.5

## D18 — Fragmentos sospechosos
- **Pregunta original (P18):** ¿Qué hace el CLI con las frases de un texto libre que parecen instrucciones: nada, avisar o bloquear?
- **Alternativas consideradas:** (a) marcarlas con una lista cerrada de patrones, listar sus números de línea en el briefing sin repetir su texto y rechazar cualquier cita que se solape con ellas; (b) quitarlas del texto antes del briefing; (c) solo avisar.
- **Decisión:** (a).
- **Justificación:** D8 ya impide que la carta cambie campos cerrados, pero una cita literal de la frase inyectada podría entrar como «recuerdo» y llegar a `idea_semilla`. Bloquear solo la cita conserva la entrada intacta, que es lo que exige la custodia, y reduce el coste de un falso positivo a volver a aportar el dato como respuesta. (b) altera el texto y rompe la literalidad de las demás citas. La lista es heurística y no exhaustiva, y lo que no case sigue siendo el riesgo aceptado de §11.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-11, RF-21), 6 (RNF-01), 8.4, 9, 11

## D19 — Límites, mínimos y campos personales
- **Pregunta original (P19):** ¿Qué tamaños máximos, qué mínimos de rasgos y recuerdos y qué campos personales tiene el brief?
- **Alternativas consideradas:** (a) 20 entradas de hasta 20.000 caracteres, briefing de hasta 40.000 tokens, 1..10 rasgos, 1..20 recuerdos con citas de hasta 600 caracteres, 0..30 términos vetados, y solo nombre, edad, rasgos y recuerdos como datos personales; (b) sin límites; (c) mínimos más altos (3 recuerdos o más).
- **Decisión:** (a).
- **Justificación:** 40.000 tokens deja margen bajo el techo de 100.000 por invocación. Los límites de entrada lo hacen alcanzable, porque 20 × 20.000 caracteres a 3,5 caracteres por token son unos 114.000 tokens y el tope del briefing corta antes. Los mínimos de 1 evitan bloquear un brief por un umbral inventado. Limitar los campos personales a los cuatro que pide la petición es la minimización de datos. Las cifras concretas son supuestos.
- **Fuente:** `docs/architecture.md` §6.5 (techo y ratio 3,5); Petición del usuario (campos a recoger); Supuesto (cifras)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 5 (RF-06, RF-12, RF-16), 6 (RNF-06, RNF-11), 8.3

## D20 — Pruebas property-based
- **Pregunta original (P20):** ¿Qué partes del slice `brief` se prueban con Hypothesis y cuáles con ejemplos?
- **Alternativas consideradas:** (a) Hypothesis, con 200 casos o más, en la delimitación y en la literalidad de las citas, y ejemplos en faltantes y contradicciones; (b) todo con ejemplos; (c) todo property-based.
- **Decisión:** (a).
- **Justificación:** la regla dura de property-based es para los gates de `validate.py` y las ramas de `delta.py`, donde «los ejemplos no cubren». La delimitación y la normalización de citas son el mismo tipo de propiedad: ningún texto escapa del bloque y ninguna variante de espacios o de forma Unicode rompe una cita válida. Faltantes y contradicciones son reglas finitas que cubren los ejemplos.
- **Fuente:** `AGENTS.md` § Proceso: generar código (TDD); `docs/validators.md` §3.6
- **Confianza:** media
- **Secciones de la spec afectadas:** 6 (RNF-03), 7 (CA-09, CA-19), 13

## Contexto consultado

**Ficheros leídos**
- `CLAUDE.md` y `AGENTS.md` (raíz). `CLAUDE.md` importa `@AGENTS.md`.
- Documentos que enlazan o mencionan:
  - `docs/architecture.md` (entero).
  - `docs/definitions.md` (entero).
  - `docs/domain-knowledge.md` (entero).
  - `docs/validators.md` (§1 a §4.10).
  - `.claude/commands/novela-continuar.md` (primeras 60 líneas).
  - `.claude/settings.json`.
  - `.claude/settings.local.json` (solo `enabledPlugins`; no contiene claves).
- Código y configuración, para citar rutas reales:
  - `backend/novela/dominio/config.py`, `base.py`, `ids.py` (`Agente`) y `esquemas.py` (registro).
  - `backend/novela/slices/nueva/cmd.py`, `slices/briefing/recipes.py`, `slices/delta/violaciones.py` (`normalizar`) y `slices/delta/custodia.py` (búsqueda).
  - `backend/novela/plataforma/run.py`, `salida.py` y `workspace.py` (búsqueda).
  - `backend/novela/cli.py`, `backend/api/routers/novelas.py`, `.claude/hooks/denegar-escritura-estado.py`, `.claude/agents/cronista.md` y `.claude/commands/novela-nueva.md`.
  - `backend/tests/test_contratos.py` (`CONTRATO`, `ESQUEMAS`, `test_state_schema_al_dia`) y `backend/tests/test_hook.py` (búsqueda).
- `docs/auditoria-entregable.md` (§ Recuento y § CFG). No lo enlazan `CLAUDE.md` ni `AGENTS.md`. Está sin seguimiento en git y se leyó como contexto de la petición.

**Ficheros esperados que no existían**
- Ninguno. `CLAUDE.md` menciona `~/.claude/state/langfuse_hook.log`, que está fuera del repositorio y no se siguió.

**Specs anteriores revisadas y solapamientos**
- `docs/specs/0001-backend-cli-estado-y-api.md` (implementada; CLI, dominio, estado y API): solapa en `novela nueva` y en los códigos de salida. Esta spec amplía `novela nueva` con `--brief` y conserva el comportamiento sin el flag (RF-26).
- `docs/specs/0002-verificacion-a-escala-de-novela.md` (aceptada; verificación a escala de novela): solapa en el conjunto de roles (`sonda`, su RF-30), en el hook, en la regla 5 y en los mismos párrafos de `AGENTS.md` y `CLAUDE.md`. Su gate de léxico vetado sería quien haga cumplir los términos vetados en los capítulos. Ver D14.
- `docs/specs/0003-contencion-y-bucle-en-claude.md` (implementada; contención en `.claude/`): esta spec añade un rol a su contrato, a `SALIDAS` y a la regla 5 sin cambiar las reglas.
- `docs/specs/0004/spec.md` (aceptada; panel; leída §1 a CA-36) y el listado de `docs/specs/0004/`: Lanzar prepara `/novela-nueva ... --idea` y consulta `GET /novelas`. Esta spec no toca el panel ni la API. Un workspace de solo brief no aparece en `GET /novelas` (§9).
- `docs/specs/_plantilla.md`: listada, no leída.

**Instrucciones encontradas en el contexto que se ignoraron**
- Ninguna dirigida a este agente.
- Discrepancia de formato: `AGENTS.md` § Proceso: modificar documentación pide crear las specs con estado `borrador`, y el procedimiento de este redactor exige `estado: Propuesta` y `version: 2`. Se ha seguido el procedimiento. Queda anotado para quien acepte la spec.
