# Decisiones — Spec 0013

## D1 — Qué es publicar en el modelo
- **Pregunta original (P1):** La petición exige que «no se publica nada sin validar», pero el harness no tiene ningún paso llamado «publicar». ¿Qué acción del modelo cuenta como publicación?
- **Alternativas consideradas:** (a) Solo `novela exportar`. (b) Solo `novela checkpoint`, que cierra y sella el capítulo. (c) Las dos: el capítulo se publica con `Checkpoint` (o `Reaplicar`) y la novela con `Exportar` tras `Auditar`.
- **Decisión:** (c). `PublicaSoloValidado` exige los validadores a todo capítulo cerrado. Exige además que `etapa = "publicada"` solo se alcance tras una auditoría aprobada y con todos los capítulos cerrados.
- **Justificación:** El checkpoint es el punto de no retorno de un capítulo: «`novela checkpoint` confirma una sola vez» y, tras él, «el siguiente puede empezar y este no se toca». La exportación es lo que sale del harness, y `novela-auditar.md` solo exporta si `novela auditar` sale con 0. Si la invariante cubriera solo uno de los dos puntos, el otro quedaría sin protección.
- **Fuente:** `docs/architecture.md` § 2.1 («Estado del bucle»); `backend/novela/slices/checkpoint/cmd.py::checkpoint` (docstring); `.claude/commands/novela-auditar.md` pasos 1 a 3.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-09, RF-13), 7 (CA-09, CA-13), 8.4.

## D2 — TLA+ puro en vez de PlusCal
- **Pregunta original (P2):** La petición admite TLA+ o PlusCal. ¿Cuál se usa?
- **Alternativas consideradas:** (a) PlusCal traducido a TLA+. (b) TLA+ puro con acciones con nombre.
- **Decisión:** (b). Sin bloques `--algorithm`.
- **Justificación:** El README tiene que mapear cada acción al código (TLA-05), y el test tiene que leer las acciones de `Next`. En PlusCal las acciones reciben el nombre de etiquetas que genera el traductor, y el `.tla` resultante mezcla código generado con el escrito a mano. Con TLA+ puro, cada disyunto de `Next` es una acción con el mismo nombre que su fila del README, y la equidad por acción se escribe de forma directa.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-01), 7 (CA-01).

## D3 — Un contador de intentos por gate
- **Pregunta original (P3):** ¿El límite de reintentos es por gate o compartido? La enumeración de `test_bucle.py` usa un solo `intento`, y `docs/architecture.md` § 2.1 dice que «Dos formas distintas de fallar agotan el presupuesto igual que la misma dos veces».
- **Alternativas consideradas:** (a) Un contador compartido por capítulo, como `test_bucle.py`. (b) Un contador por gate (`arquitecto`, `mecanico`, `revision`, `delta`), como el procedimiento.
- **Decisión:** (b). Los contadores van de 1 a `MaxIntentos = 3` (2 reintentos) y se reinician en cada capítulo. El fallo con 3 consumidos lleva a `Intervencion`.
- **Justificación:** El procedimiento es lo que se ejecuta y cuenta por gate con líneas distintas de `harness.log`. `CLAUDE.md` y `architecture.md` dicen «Máximo dos por gate». El modelo tiene que reflejar la implementación para que el README pueda mapearla. El riesgo de lectura contraria queda en § 11 de la spec.
- **Fuente:** `CLAUDE.md` § Bucle por capítulo («Máximo dos reintentos por gate»); `docs/architecture.md` § 2.1 («Reintentos. Máximo dos por gate»); `.claude/commands/novela-continuar.md` § Cuenta de intentos; `.claude/commands/novela-nueva.md` paso 3.
- **Confianza:** alta
- **Secciones de la spec afectadas:** 2, 5 (RF-05, RF-06, RF-16), 8.3, 9, 11.

## D4 — Validadores que entran en el modelo
- **Pregunta original (P4):** ¿Qué son «todos los validadores» que un capítulo tiene que pasar antes de publicarse?
- **Alternativas consideradas:** (a) Solo `novela validar`. (b) Los gates que existen hoy: mecánico (`validar` tras el `escritor` y otra vez tras el `editor-estilo`), revisión (veredictos de continuidad y suspense), delta (custodia y violaciones de `aplicar-delta`), `vp_schema` en `checkpoint` y, para la novela, `novela auditar`. (c) Los de (b) más `novela gate` (0002) y el gate Lean (0012).
- **Decisión:** (b). `novela gate` y el gate Lean se añaden cuando existan, en el commit de la spec que los implemente.
- **Justificación:** Son los gates de § 2.1 y del procedimiento, más el bloqueo de `vp_schema` que añadió la 0009. Modelar gates que no existen describiría lo que habrá y no lo que hay. Las líneas `validar-hook` de la 0008 no cuentan intentos, y por eso no son un gate en el modelo.
- **Fuente:** `docs/architecture.md` § 2.1 (tabla «Gates»); `.claude/commands/novela-continuar.md` pasos 3 a 8; `docs/validators.md` § 3.10 y § 6 («Cierre de capítulo»); `docs/specs/0012/spec.md` § 1; `AGENTS.md` § Proceso: modificar documentación.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-04, RF-06, RF-13), 10.

## D5 — Caídas acotadas y reanudación con la tabla del procedimiento
- **Pregunta original (P5):** ¿Cómo se modelan la caída y la reanudación desde checkpoint sin que el espacio de estados sea infinito ni la liveness falle por caídas sin fin?
- **Alternativas consideradas:** (a) Sin caídas: solo reanudar tras una parada. (b) Caída posible en cualquier estado no final, sin límite. (c) Caída posible en cualquier estado no final, acotada por `MaxCaidas`, y `Reanudar` con la tabla literal de § Punto de reanudación.
- **Decisión:** (c), con `MaxCaidas = 2` en `Harness.cfg`. La caída pierde solo el estado volátil de la sesión.
- **Justificación:** La petición pide verificar que la reanudación no pierde ni duplica capítulos, y § 4.12 reconoce que nunca se ha cortado en cada frontera. Con caídas sin límite, `Termina` fallaría por una sucesión infinita de caídas que ningún sistema puede evitar. Con dos caídas se cubren la caída en cualquier frontera y la caída durante una reanudación.
- **Fuente:** `.claude/commands/novela-continuar.md` § Situación y § Punto de reanudación; `docs/validators.md` § 4.12; `docs/architecture.md` § 1 (principio 6) y § 8 («Reanudación»).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-07, RF-14), 6, 7 (CA-07, CA-14), 8.3, 9.

## D6 — Estados finales y equidad de la propiedad de liveness
- **Pregunta original (P6):** ¿Qué cuenta como «terminar deteniéndose con error» y con qué equidad se comprueba `Termina`?
- **Alternativas consideradas:** (a) `<>(etapa = "publicada")`, que es falso porque hay paradas legítimas. (b) `<>[](etapa ∈ {"publicada", "detenida"})` con equidad débil sobre todas las acciones. (c) Como (b), pero sin equidad sobre `Caida`, `FalloCLI`, `Detener`, `SinAvance` y `Cambio`, con `Terminado` como paso tartamudo e `Intervencion` como estado final.
- **Decisión:** (c). Hay un solo estado final `detenida`, con `motivo` `intervencion`, `cli`, `auditoria`, `sin_avance` o `panel`, y cada motivo se corresponde con los finales de `novela producir`.
- **Justificación:** Las acciones del entorno (caídas, errores, el panel, un cambio del lector) no se pueden exigir: son posibles, no obligatorias. Las del sistema sí, con equidad débil, porque el procedimiento siempre da el siguiente paso si está habilitado. La intervención humana y el relanzamiento quedan fuera: el modelo verifica que el sistema para, no lo que decide una persona. `Terminado` evita que TLC confunda los estados finales con un bloqueo.
- **Fuente:** Supuesto. La petición del usuario fija el enunciado («termina publicando o deteniéndose con error»). `backend/novela/slices/producir/flujo.py` (`Final`) y `docs/architecture.md` § 8 («Parada») respaldan los estados finales, pero la elección de la equidad es una práctica general.
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 5 (RF-08, RF-12, RF-18), 7 (CA-12, CA-18), 8.4.

## D7 — Regeneración modelada según la spec 0007, marcada como no implementada
- **Pregunta original (P7):** La petición pide modelar la regeneración por cambio del lector, pero `novela cambio` no existe: la spec 0007 está Propuesta. ¿Se modela, y con qué mapeo?
- **Alternativas consideradas:** (a) Dejarla fuera hasta que se implemente la 0007. (b) Modelarla según el texto de la 0007 y marcar sus filas del README como «spec 0007, sin implementar». (c) Modelarla con un diseño propio.
- **Decisión:** (b). `Cambio` y `Reaplicar` siguen la 0007 RF-19, RF-24, RF-25, RF-27 y RF-34. `MaxCambios = 1` sigue el ADR 0004 («Un cambio a la vez, y solo sobre una novela terminada»). La 0007 tiene que actualizar el modelo al implementarse.
- **Justificación:** La petición la pide de forma explícita (TLA-01), y comprobar el diseño antes de codificarlo es justo lo que el model checking aporta. Un contraejemplo sobre la 0007 cambiaría una spec, que es barato, en vez de código. La marca en el README evita describir como existente lo que no existe.
- **Fuente:** Petición del usuario; `docs/specs/0007/spec.md` § 5; `docs/adr/0004-versiones-de-la-novela.md` § Consecuencias; `AGENTS.md` § Proceso: modificar documentación.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-10, RF-15, RF-24), 7 (CA-10, CA-15, CA-24), 8.4, 10, 11.

## D8 — Lock con dos procesos en el modelo
- **Pregunta original (P8):** § 4.10 de `validators.md` incluye «Nunca dos procesos sobre el mismo workspace». ¿Se modela el lock?
- **Alternativas consideradas:** (a) No modelarlo, porque lo cubren `lock.py` y su test. (b) Modelar dos procesos completos que ejecutan el bucle. (c) Modelar `Procesos = {p1, p2}`, donde solo el poseedor del lock ejecuta acciones que escriben y el otro sale con 3 sin efecto.
- **Decisión:** (c), con prioridad Should.
- **Justificación:** Mantiene en el modelo la regla de § 4.10 y el invariante 8 sin duplicar el espacio de estados, porque el segundo proceso no ejecuta el bucle. El código de salida 3 es el que usa el procedimiento para el lock ocupado.
- **Fuente:** `docs/validators.md` § 4.10; `AGENTS.md` § Invariantes 8; `.claude/commands/novela-continuar.md` § Códigos de salida; `backend/tests/test_bucle.py::test_la_cli_rechaza_lo_que_la_maquina_prohibe`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-11, RF-17), 7 (CA-11, CA-17), 8.3.

## D9 — Nombres que compara el test y cómo se leen del `.tla`
- **Pregunta original (P9):** El `.tla` necesita etapas que no existen en los enums del dominio (configuración, planificación, auditoría). ¿Qué nombres se comparan con los enums y cómo los lee el test?
- **Alternativas consideradas:** (a) Comparar todas las cadenas del `.tla` con los enums. (b) Comparar tres conjuntos con formato fijo: `Fases` con `FASES`, `Pasos` con `PASOS` y `Finales` con `Final` de `producir/flujo.py`. Las etapas propias del modelo se atan con la tabla del README. (c) Añadir las etapas del modelo a un enum nuevo del dominio.
- **Decisión:** (b). Cada conjunto va en una definición `Nombre == {…}` que se lee con una expresión regular entre `Nombre ==` y su `}`.
- **Justificación:** `FASES` y `PASOS` ya son la fuente de la que `test_bucle.py` comprueba sus nombres, y `Final` es el conjunto de finales de `novela producir`. La opción (c) cambiaría el dominio y el contrato de la API sin necesidad. Un formato fijo mantiene el test sin dependencias ni parser de TLA+.
- **Fuente:** `backend/novela/dominio/estado.py` (`FASES`, `PASOS`); `backend/novela/slices/producir/flujo.py` (`Final`); `backend/tests/test_bucle.py` (línea 94); `AGENTS.md` § Monorepo («Una sola ontología»).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-02, RF-25), 7 (CA-02, CA-25), 8.4.

## D10 — TLC en un job de CI propio, fuera de pytest
- **Pregunta original (P10):** ¿TLC corre dentro de `pytest` (con un marcador que lo omite sin Java, como el test `lean` de la 0012) o en un job de CI aparte?
- **Alternativas consideradas:** (a) Test de pytest marcado `tla` que se omite sin Java. (b) Job `tla` en `ci.yml` con el comando documentado, y pytest solo con comprobaciones estáticas. (c) Las dos.
- **Decisión:** (b). El job `backend` no necesita Java, y el comando es el mismo en el README y en CI.
- **Justificación:** La petición exige el comando documentado y en `.github/workflows/ci.yml`, y restringe TLC a desarrollo y CI. Un job propio mantiene la suite del backend sin Java (RNF-06) y deja el fallo de TLC identificable por su nombre en CI.
- **Fuente:** Petición del usuario («comando documentado y en .github/workflows/ci.yml», «TLC solo en desarrollo y CI»); `.github/workflows/ci.yml` (jobs actuales); `docs/specs/0012/spec.md` RF-25 como alternativa.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-22, RF-23, RF-25), 6, 7 (CA-22, CA-23).

## D11 — Obtención y verificación de Java y `tla2tools.jar`
- **Pregunta original (P11):** ¿De dónde salen Java y `tla2tools.jar` en CI y en local, y se versiona el jar?
- **Alternativas consideradas:** (a) Versionar el jar en el repo. (b) Descargar la última versión en cada ejecución. (c) Fijar versión y sha256 en `formal/tla/tla2tools.version`, descargar esa versión y verificar el sha256 antes de ejecutar, con Java 17 Temurin mediante `actions/setup-java@v4`.
- **Decisión:** (c). El jar, `states/` y las trazas `*_TTrace_*.tla` van al `.gitignore`. La versión concreta es la estable más reciente en el momento de implementar.
- **Justificación:** Un binario de varios MB en git no se revisa. Descargar «la última» haría no reproducible el resultado de TLC. Fijar y verificar el hash es lo mínimo para ejecutar en CI un binario descargado. Java 17 cumple el mínimo de Java 11 que exige TLC y está disponible en `actions/setup-java`.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-21, RF-22), 6 (RNF-04), 7 (CA-21, CA-22), 10.

## D12 — Tamaño del modelo y umbrales de TLC
- **Pregunta original (P12):** ¿Qué valores de las constantes lleva `Harness.cfg` y qué umbrales de tiempo y tamaño se exigen?
- **Alternativas consideradas:** (a) Solo los valores de la petición (5 capítulos, 2 reintentos), sin caídas, cambios ni procesos. (b) Los de la petición más `MaxCaidas = 2`, `MaxCambios = 1` y dos procesos, con umbrales de ≤ 10 min, ≤ 5 000 000 estados y un `timeout` de 15 min. (c) Un modelo mayor, con 24 capítulos como la novela real.
- **Decisión:** (b). Si se superan los umbrales, se reduce primero `MaxCaidas` y después `Procesos`, nunca `NumCapitulos` ni `MaxIntentos`.
- **Justificación:** La petición fija 5 capítulos y 2 reintentos. Las demás constantes son las mínimas que ejercitan cada rama (una caída durante una reanudación, un cambio y un lock disputado). Los umbrales mantienen el job en el orden de minutos de la fila «CI del harness» de § 6. Con 24 capítulos, el espacio crecería sin aportar ramas nuevas.
- **Fuente:** Petición del usuario (5 capítulos, 2 reintentos); `docs/validators.md` § 6 («CI del harness», coste «minutos»); el resto es Supuesto.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-19), 6 (RNF-01 a RNF-03), 8.4, 9, 11.

## D13 — Configuración mutante como control negativo
- **Pregunta original (P13):** ¿Cómo se demuestra que las invariantes no son vacías y que TLC detecta de verdad una publicación sin validar?
- **Alternativas consideradas:** (a) Confiar en el verde de TLC. (b) Mutaciones solo durante el desarrollo, anotadas en el registro. (c) Una configuración mutante versionada (`HarnessMutante.cfg`, `Mutante = TRUE` omite `ValidarFinal`) que CI exige ver fallar, más mutaciones puntuales durante el desarrollo.
- **Decisión:** (c).
- **Justificación:** «Un test que nunca has visto en rojo no prueba nada»: una invariante que TLC no ha visto violarse puede ser vacía. La mutante elegida reproduce el riesgo que § 4.10 y § 3.9 señalan como principal: aplicar sobre un capítulo reescrito por el `editor-estilo` sin validar después. Deja además en el registro un contraejemplo reproducible (TLA-06).
- **Fuente:** `AGENTS.md` § Proceso: generar código (paso 2); `docs/validators.md` § 4.10 (quinta regla) y § 4.12.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1 (O-04), 5 (RF-20, RF-22), 7 (CA-13, CA-20, CA-22), 11.

## D14 — Contenido del registro de contraejemplos
- **Pregunta original (P14):** TLA-06 pide documentar los contraejemplos «con el cambio que provocaron en el código». ¿Qué se registra si un contraejemplo solo cambia el modelo, o si ninguno obliga a cambiar código?
- **Alternativas consideradas:** (a) Registrar solo los que cambian código. (b) Registrar todos, con su ámbito (`modelo`, `código`, `procedimiento` o `documentación`), fichero y sha, y declarar de forma explícita si ninguno cambió código. (c) Sembrar un defecto en el código para tener un caso que contar.
- **Decisión:** (b). El registro incluye siempre el contraejemplo de la mutante, marcado como control negativo, y los hallazgos de liveness sobre la cuenta de intentos de revisión tras una reanudación, si aparecen.
- **Justificación:** Inventar un cambio de código que no ocurrió falsearía el registro. Omitir los que cambian el modelo o el procedimiento perdería justo la información que explica por qué el modelo es como es. La spec 0012 resolvió igual su documento de caso, con el caso real o una justificación con datos y un caso sembrado marcado como tal.
- **Fuente:** Petición del usuario (TLA-06); `docs/specs/0012/spec.md` § 8.6 como precedente.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-26), 7 (CA-26), 9, 13.

## D15 — Ubicación del diagrama
- **Pregunta original (P15):** ¿Dónde va el diagrama de la máquina de estados que pide la verificación: en `docs/domain-knowledge.md`, en `formal/tla/README.md` o en un fichero nuevo de `docs/`?
- **Alternativas consideradas:** (a) `formal/tla/README.md`. (b) Un fichero nuevo en `docs/`. (c) Una sección 7 en `docs/domain-knowledge.md`.
- **Decisión:** (c), como Mermaid `stateDiagram-v2` con los nombres de acción del `.tla`.
- **Justificación:** `AGENTS.md` asigna los diagramas a `domain-knowledge.md`, que ya tiene el grafo de orquestación (§ 4). La petición lo pide en `docs/`. Un fichero nuevo repartiría los diagramas.
- **Fuente:** `AGENTS.md` (encabezado: «`docs/domain-knowledge.md` (diagramas)»); petición del usuario («diagrama de la máquina de estados en docs/»).
- **Confianza:** alta
- **Secciones de la spec afectadas:** 5 (RF-27), 7 (CA-27), 8.1.

## D16 — Número del ADR
- **Pregunta original (P16):** ¿Qué número lleva el ADR que revierte § 4.10?
- **Alternativas consideradas:** (a) 0003, el primer hueco en `docs/adr/`. (b) 0005, el siguiente al último existente. (c) 0006.
- **Decisión:** (c) `docs/adr/0006-model-checking-con-tla.md`.
- **Justificación:** En `docs/adr/` existen 0001, 0002 y 0004. La spec 0006 reserva el 0003, según recoge la 0007, y la 0012 reserva el 0005. Tomar cualquiera de los dos chocaría con una spec propuesta.
- **Fuente:** `docs/specs/0007/spec.md` § 2 (0006 reserva `docs/adr/0003-…`); `docs/specs/0012/spec.md` § 2 («el de esta spec es el 0005»).
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-28), 7 (CA-28).

## D17 — Destino de la enumeración de `test_bucle.py`
- **Pregunta original (P17):** ¿Qué pasa con `test_maquina_del_bucle_y_sus_invariantes` y con el assert que argumenta «TLA+ sería ceremonia»?
- **Alternativas consideradas:** (a) Borrar la enumeración. (b) Conservarla y cambiar solo el mensaje del assert y el docstring para remitir al `.tla`. (c) Generarla a partir del `.tla`.
- **Decisión:** (b).
- **Justificación:** La enumeración corre en `pytest` sin Java, en segundos y en el pre-commit, y protege el uso de `FASES` y `PASOS`. Borrarla quitaría una red rápida. Generarla desde el `.tla` exigiría un parser. El mensaje, en cambio, pasaría a contradecir el ADR 0006.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-29), 7 (CA-29), 8.2.

## D18 — Sin cambios en `AGENTS.md` ni `CLAUDE.md`
- **Pregunta original (P18):** ¿Hay que añadir TLC a las convenciones de `AGENTS.md` o `CLAUDE.md`?
- **Alternativas consideradas:** (a) Añadir una línea al proceso TDD de `AGENTS.md`. (b) No tocarlos, y documentar el procedimiento en `formal/tla/README.md` y `docs/validators.md` § 4.10 y § 6.
- **Decisión:** (b).
- **Justificación:** No cambia ninguna convención de ejecución ni de agentes: TLC corre en CI y en desarrollo. Los dos ficheros solo se tocan si cambia una convención, y cada línea se paga en cada sesión y en cada subagente.
- **Fuente:** `AGENTS.md` § Proceso: modificar documentación (tabla, fila `AGENTS.md`, `CLAUDE.md`) y § Nunca (último punto).
- **Confianza:** alta
- **Secciones de la spec afectadas:** 3.2, 5 (RF-29), 8.2.

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md` y `AGENTS.md` (raíz).
- Documentos enlazados desde ellos: `docs/architecture.md` (índice, § 1 a § 3.1, § 8 a § 12), `docs/validators.md` (índice, § 1 a § 3.5, § 4.7 a § 4.16, § 5 y § 6), `docs/domain-knowledge.md` (índice de secciones), `docs/definitions.md` (índice de secciones) y `.claude/commands/novela-continuar.md`.
- Otros: `.claude/commands/novela-nueva.md`, `.claude/commands/novela-auditar.md`, `backend/novela/dominio/estado.py`, `backend/novela/dominio/artefactos.py`, `backend/novela/dominio/lanzamiento.py`, `backend/novela/dominio/validadores.py`, `backend/novela/slices/producir/flujo.py`, `backend/novela/slices/checkpoint/cmd.py` (líneas 120-189), `backend/novela/slices/delta/apply.py` (líneas 80-119), `backend/tests/test_bucle.py`, `.github/workflows/ci.yml`, `docs/adr/0004-versiones-de-la-novela.md`, `docs/auditoria-entregable.md` (recuento y § TLA por búsqueda), `docs/specs/0007/spec.md` (§ 1 a § 6) y `docs/specs/0012/spec.md` (§ 1 a § 9).
- Plantillas: `spec-template.md` y `decisions-template.md` del plugin `sdd-spec-writer` 1.1.0.

**Ficheros esperados que no existían**

- Ninguno. `CLAUDE.md` y `AGENTS.md` existen, y todos los documentos que enlazan existen.
- No existen carpetas `docs/specs/0005/` ni `docs/specs/0006/`, aunque otras specs las citan. No afecta al cálculo del número de esta spec.

**Specs anteriores revisadas y solapamientos**

- 0001 (`docs/specs/0001-backend-cli-estado-y-api.md`, implementada): cursor, custodia y checkpoint. Esta spec los modela, sin solapamiento funcional.
- 0002 (`docs/specs/0002-verificacion-a-escala-de-novela.md`, aceptada): amplía el model checking de § 4.10 con `novela gate` y la trayectoria. **Solapamiento parcial**: las dos tocan § 4.10. Esta spec no modela `novela gate` hasta que exista.
- 0003 (`docs/specs/0003-contencion-y-bucle-en-claude.md`, implementada): procedimientos de `.claude/commands/`, que son la fuente de las transiciones.
- 0004 (aceptada): `novela producir`, con la parada del panel, modelada como `Detener`.
- 0007 (Propuesta): regeneración por cambio del lector. **Solapamiento**: esta spec modela su diseño (D7) sin implementarlo.
- 0008 (aceptada): hook `PostToolUse`; sus líneas no cuentan intentos.
- 0009 (Propuesta; su parte de `vp_schema` en `checkpoint` ya está en el código según `docs/validators.md` § 2): `vp_schema` modelado como validador del cierre.
- 0010 y 0011 (Propuestas): revisadas por título, sin solapamiento.
- 0012 (Propuesta): verificación formal con Lean y bloqueo de la publicación. **Solapamiento conceptual**: las dos son verificación formal, y las dos usan `formal/`. La 0012 reserva el ADR 0005 y excluye un job de CI para Lean, mientras esta spec sí añade uno para TLC (D10). No es una contradicción, porque son herramientas distintas.
- Se detecta una posible contradicción con `docs/validators.md` § 4.10 («hoy sería ceremonia»), que esta spec revierte por el ADR 0006. También hay una tensión de lectura en `docs/architecture.md` § 2.1 sobre el presupuesto de intentos, resuelta en D3.

**Instrucciones encontradas en el contexto que se ignoraron**

- Ninguna dirigida a este agente. `CLAUDE.md` contiene instrucciones para la sesión orquestadora del harness («Tu papel como sesión principal»). Se trataron como contexto sobre el sistema, no como órdenes.
