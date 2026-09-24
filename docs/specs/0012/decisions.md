# Decisiones — Spec 0012

## D1 — Momento del gate y significado de «publicar»
- **Pregunta original (P1):** ¿En qué punto del bucle corre el gate de Lean y qué significa que «la versión no se publica»? Si corre después de `aplicar-delta`, la incoherencia ya está en tablas append-only y el `escritor` no puede retirarla.
- **Alternativas consideradas:** (a) después de `aplicar-delta`, sobre `estado.db` tal cual, bloqueando `checkpoint`; (b) antes de `aplicar-delta`, sobre `estado.db` más el delta pendiente en solo lectura, con precondición en `aplicar-delta`, más una comprobación final antes de `novela exportar`; (c) solo al final, antes de exportar.
- **Decisión:** (b). `novela lean <slug> <cap>` corre entre el `cronista` y `aplicar-delta` y proyecta el delta sin escribir. `aplicar-delta` exige `qa/NN-lean.json` aprobado para ese mismo delta. Un capítulo rechazado no se cierra y, por tanto, no se exporta. Además, `novela lean <slug>` vuelve a comprobar la historia escrita antes de `novela exportar`, y `exportar` exige `qa/lean.json` aprobado. «Publicar» es exportar.
- **Justificación:** con (a), una violación queda fosilizada en `linea_temporal`, que es append-only, y el capítulo solo podría acabar en intervención. Con (c), el fallo se descubre cuando ya se ha gastado la cuota de la novela entera. La petición pide leer `estado.db` sin escribirlo y devolver el fallo, y eso solo es posible antes de aplicar. `exportar` solo saca capítulos cerrados, así que bloquear el cierre ya bloquea la publicación. La comprobación final es la que corresponde literalmente a «la versión no se publica».
- **Fuente:** Petición del usuario; `AGENTS.md` § Invariantes 1 y 2; `docs/architecture.md` § 2.1 (el `cronista` después de los gates); `docs/validators.md` § 5.9; `backend/novela/slices/export/cmd.py` (exporta los capítulos cerrados según el checkpoint).
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1, 5 (RF-02, RF-12, RF-13, RF-17, RF-18, RF-20), 8.1, 8.5, 9

## D2 — Destino del fallo: el `escritor`
- **Pregunta original (P2):** La petición dice que el fallo «vuelve al editor». ¿A qué rol del harness corresponde: `editor-estilo`, `escritor` o `cronista`?
- **Alternativas consideradas:** (a) `editor-estilo`; (b) `escritor`, con el reintento estándar desde el paso 3; (c) `cronista`, como un fallo de `aplicar-delta`.
- **Decisión:** (b). Un 1 de `novela lean` produce un reintento del `escritor` con `reintento: qa/NN-lean.json` y vuelta al paso 3. Los intentos se cuentan con las líneas `lean NN -> 1`, y la intervención usa `gate: formal`.
- **Justificación:** en este harness, el rol que corrige el contenido de un capítulo a partir de un informe de QA es el `escritor` (`architecture.md` § 2.1, «Reintentos»). El `editor-estilo` solo corrige voz, ritmo y prohibiciones, y su receta no incluye estado. Reintentar al `cronista` presupone que el delta está mal, cuando el delta lleva cita literal del capítulo, y lo normal es que la incoherencia esté en la prosa. El «editor» de la petición se interpreta como el rol que reescribe en un reintento.
- **Fuente:** Petición del usuario; `docs/architecture.md` § 2.1 y § 7.5; `.claude/commands/novela-continuar.md` § Por capítulo, paso 6.
- **Confianza:** media
- **Secciones de la spec afectadas:** 1, 3.1, 4, 5 (RF-19), 8.5, 9

## D3 — Origen de los datos temporales: contrato con G-MEM
- **Pregunta original (P3):** ¿Amplía esta spec `esquema.sql` y el delta con momento, lugar, presencias, nacimientos y exclusiones, o los consume de G-MEM?
- **Alternativas consideradas:** (a) esta spec amplía el esquema y el delta; (b) esta spec consume la ampliación de G-MEM, fija el contrato mínimo que necesita y concentra el SQL en un solo adaptador.
- **Decisión:** (b). § 8.3 lista la información exigida. `estado_db.hechos_temporales` y `temporal.proyectar` son los únicos sitios que conocen los nombres de G-MEM. Sin esa información, `novela lean` sale con 4.
- **Justificación:** la petición dice expresamente que `linea_temporal` «se amplía en G-MEM». Duplicar esa migración aquí crearía dos specs sobre la misma tabla append-only. G-MEM no tiene spec en `docs/specs/`, así que el contrato se deja explícito como dependencia y riesgo.
- **Fuente:** Petición del usuario; `docs/auditoria-entregable.md` § MEM (MEM-02).
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-01, RF-16), 8.3, 10, 11

## D4 — Representación del tiempo y de las fechas de nacimiento
- **Pregunta original (P4):** ¿Cómo se representan en SQLite y en Lean los momentos de los eventos y las fechas de nacimiento?
- **Alternativas consideradas:** (a) tiempo relativo («día N, HH:MM») y nacimientos en años; (b) ISO 8601 absoluto en SQLite, convertido por Python a minutos enteros desde `0001-01-01T00:00` en el calendario gregoriano proléptico; (c) tuplas de fecha en Lean con aritmética de calendario en Lean.
- **Decisión:** (b). Los eventos van como `AAAA-MM-DDTHH:MM` y los nacimientos como `AAAA-MM-DD` (00:00). En Lean todo es `Nat` en minutos.
- **Justificación:** una sola escala hace triviales el solape y la comparación con el nacimiento. La conversión en Python con `datetime` es exacta y determinista y deja la aritmética de calendario fuera de Lean. El tiempo relativo no permite comparar con una fecha de nacimiento sin una fecha de origen. Ninguna fuente del repositorio fija el formato de G-MEM, así que la decisión se apoya en buenas prácticas y se marca para revisar.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-03), 8.3, 8.4, 10

## D5 — Invariantes y prioridades
- **Pregunta original (P5):** ¿Qué invariantes se implementan de los ejemplos de la petición (orden temporal, edad coherente con el nacimiento, dos lugares a la vez, aparecer tras un evento que excluye) y con qué prioridad?
- **Alternativas consideradas:** (a) las cuatro como Must; (b) ubicuidad y nacimiento como Must, exclusión como Could condicionada a que G-MEM registre exclusiones, y fuera el orden temporal y la edad declarada; (c) solo ubicuidad.
- **Decisión:** (b). Ubicuidad (RF-07) y nacimiento (RF-08, «nadie aparece antes de nacer») son Must. Exclusión (RF-09) es Could. El orden de escenas y la edad declarada quedan como no objetivos.
- **Justificación:** la petición exige al menos dos invariantes. Ubicuidad y nacimiento solo necesitan los datos que LEAN-01 enumera. La edad declarada no está en `estado.db` (vive en `canon/personajes/*.md`, `identidad.edad`), y el generador lee solo SQLite. Un orden estricto de escenas daría falsos positivos con cualquier analepsis. La exclusión necesita un dato que LEAN-01 no enumera.
- **Fuente:** Petición del usuario; `docs/definitions.md` § 2.3 (`identidad.edad`) y § 4 (`linea_temporal`).
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 3.2, 5 (RF-07, RF-08, RF-09), 8.4, 9

## D6 — Ejecución de Lean y obtención del detalle
- **Pregunta original (P6):** ¿Cómo se invoca Lean («lake build o lean») y cómo obtiene el CLI qué personaje y qué escenas fallan, para devolverlo como informe?
- **Alternativas consideradas:** (a) un teorema por invariante con `decide`, sin detalle; (b) `lake build Invariantes` para la biblioteca y `lake env lean Hechos.lean` para los hechos, con un `#eval` que imprime una línea JSON por violación y un teorema `violaciones hechos = [] := by native_decide` que decide el código de salida; (c) solo un ejecutable `lake exe` que imprime violaciones, sin teorema.
- **Decisión:** (b), con la tabla de coherencia entre salida y código de § 8.4. Todo desacuerdo entre las dos da código 4.
- **Justificación:** (a) no da feedback accionable, y la petición exige que el fallo vuelva como feedback. (c) no es una verificación formal. `lake env lean` sobre un fichero del workspace mantiene los datos de la novela fuera del repositorio (`AGENTS.md` § Separación repo / workspace). `native_decide` es la única opción razonable para cientos de eventos. `decide` en el kernel no escala a ese tamaño. Es un supuesto de rendimiento que se mide en T-01.
- **Fuente:** Supuesto (con la restricción de `AGENTS.md` § Separación repo / workspace)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-04, RF-05, RF-12), 8.4, 8.5, 10, 11

## D7 — Rutas de los ficheros generados y de los informes
- **Pregunta original (P7):** ¿Dónde se escriben `Hechos.lean` y el informe? La petición ofrece `qa/NN-lean.json` o `qa/lean.json`.
- **Alternativas consideradas:** (a) `Hechos.lean` dentro de `formal/lean/` del repositorio; (b) `novelas/<slug>/formal/NN/Hechos.lean` y `formal/novela/Hechos.lean` en el workspace, con `qa/NN-lean.json` por capítulo y `qa/lean.json` para la historia completa; (c) solo `qa/lean.json`.
- **Decisión:** (b), las dos rutas de informe, cada una en su modo.
- **Justificación:** escribir datos de una novela en el repositorio mezcla harness y workspace. `qa/NN-<agente>.json` es la convención de los informes por capítulo, y `qa/auditoria.json` lo es para los de la novela entera. Los dos modos de la petición encajan en ella.
- **Fuente:** Petición del usuario; `AGENTS.md` § Separación repo / workspace; `docs/definitions.md` § 6 (`qa/NN-<agente>.json`, `qa/auditoria.json`).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-12, RF-13), 8.3, 8.4

## D8 — Modelo del informe: `InformeQA` ampliado
- **Pregunta original (P8):** ¿El informe de Lean usa un modelo propio o amplía `InformeQA`?
- **Alternativas consideradas:** (a) un `InformeLean` nuevo con su esquema; (b) `InformeQA` con productor `lean`, tres tipos nuevos y los campos opcionales `delta_sha256` y `hechos_sha256`.
- **Decisión:** (b).
- **Justificación:** `InformeQA` es el único formato que el `escritor` sabe leer en un reintento, con un vocabulario cerrado de tipos por productor. Ya lleva un sha que solo escribe el CLI (`capitulo_sha256`), y los dos nuevos siguen el mismo patrón. Un modelo aparte obligaría a tocar el procedimiento y `vp_schema` con otro tipo de artefacto.
- **Fuente:** `docs/architecture.md` § 7.3; `backend/novela/dominio/qa.py` (docstring y `capitulo_sha256`).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-14, RF-21), 8.3

## D9 — Gate obligatorio y comportamiento sin Lean
- **Pregunta original (P9):** ¿El gate es obligatorio o se activa por configuración? ¿Qué hace el CLI si Lean no está instalado?
- **Alternativas consideradas:** (a) opcional con un parámetro en `config.yaml`; (b) obligatorio, con `comprobar-entorno` fallando antes del bucle y `novela lean` saliendo con 4 si falta el toolchain; (c) obligatorio, pero aprobando con un aviso si falta Lean.
- **Decisión:** (b).
- **Justificación:** la petición pide que el validador «bloquee la publicación si falla». Un gate que se desactiva o que aprueba sin ejecutarse no bloquea nada. `docs/validators.md` § 4.4 advierte contra los guardarraíles silenciados. `comprobar-entorno` ya es el punto donde se para antes del bucle por problemas de entorno.
- **Fuente:** Petición del usuario; `docs/validators.md` § 2 (párrafo sobre el catálogo) y § 6 (fila «Antes del bucle desatendido»).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-15, RF-24), 9

## D10 — Sin dependencias de Lake y sin red
- **Pregunta original (P10):** ¿El proyecto Lean puede depender de Mathlib u otros paquetes? ¿Cómo se evita que Lake o elan descarguen algo?
- **Alternativas consideradas:** (a) Mathlib para las listas y la aritmética; (b) solo el núcleo de Lean 4, `lakefile.lean` sin `require`, toolchain estable fijado y comprobación de que está instalado sin descargar.
- **Decisión:** (b).
- **Justificación:** la petición prohíbe que el CLI acceda a la red. Una dependencia de Lake se descarga al compilar, y elan descarga un toolchain que falte. Las invariantes solo usan `Nat`, `String` y `List`, que están en el núcleo.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: ejecución («El CLI no accede a la red salvo para emitir scores a Langfuse»).
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-06, RF-24), 6 (RNF-04), 10

## D11 — El test con Lean no entra en CI
- **Pregunta original (P11):** ¿Se instala Lean en CI para ejecutar el test marcado, o se omite?
- **Alternativas consideradas:** (a) job nuevo de CI con elan; (b) sin cambios en CI. El test lleva la marca `lean` y se omite sin `lake`, y se ejecuta en local y en la novela de humo.
- **Decisión:** (b).
- **Justificación:** la petición pide que ningún test dependa de Lean «salvo uno marcado y omitible», sin pedir CI. Añadir un job se puede revisar más adelante sin tocar la spec, y el riesgo queda anotado en § 11.
- **Fuente:** Petición del usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-25), 11, 13

## D12 — Contradicción con `validators.md` § 3.4 y § 5.2, y ADR 0005
- **Pregunta original (P12):** `docs/validators.md` § 3.4 descarta la verificación formal y § 5.2 la acepta como riesgo U. ¿Cómo se concilia esta spec con eso, y hace falta un ADR?
- **Alternativas consideradas:** (a) no tocar `validators.md`; (b) actualizar § 3.4 y § 5.2 para declarar verificado formalmente el subconjunto temporal, y registrar la decisión en un ADR; (c) solo actualizar `validators.md`.
- **Decisión:** (b). El ADR es el 0005, porque las specs 0006 y 0007 reservan el 0003 y el 0004.
- **Justificación:** la documentación de referencia describe lo que hay, así que tiene que dejar de decir «descartado» cuando exista. Introducir Lean como dependencia de entorno y como gate que bloquea la publicación es caro de revertir, que es el criterio del repositorio para escribir un ADR.
- **Fuente:** `docs/validators.md` § 3.4 y § 5.2; `AGENTS.md` § Proceso: modificar documentación (fila `docs/adr/NNNN-<slug>.md`); `docs/specs/0006/spec.md` (ADR 0003); `docs/specs/0007/spec.md` (ADR 0004).
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-28), 12 (T-13)

## D13 — Caso de LEAN-04: novela de humo real más caso sembrado
- **Pregunta original (P13):** ¿De dónde sale el «caso real» de LEAN-04? ¿Vale el workspace fixture?
- **Alternativas consideradas:** (a) solo el fixture sembrado; (b) ejecutar el validador sobre una novela de humo real y comparar con los demás validadores, justificando con datos si no encuentra nada, y añadir el fixture como caso reproducible marcado como sembrado; (c) esperar a una novela completa de 24 capítulos.
- **Decisión:** (b), con la ubicuidad como defecto sembrado del fixture.
- **Justificación:** la petición admite la justificación si no se encuentra un caso. Presentar un fixture como caso real sería engañoso. La novela de humo es el medio de validación que el repositorio usa para lo que no es determinista. La ubicuidad garantiza que ningún validador determinista actual la detecta, porque la spec 0002 sacó de su alcance el solape de escenas.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: generar código (novela de humo de 3 capítulos); `docs/specs/0002-verificacion-a-escala-de-novela.md` § 1, «Fuera del alcance».
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 5 (RF-26, RF-27), 8.6, 12 (T-10, T-12)

## D14 — Score `vp_lean` binario
- **Pregunta original (P14):** ¿Con qué nombre y valor se emite el score de Lean en Langfuse, y dónde?
- **Alternativas consideradas:** (a) `lean` como fracción de invariantes cumplidas; (b) `vp_lean` binario en el catálogo de validadores, emitido por `checkpoint`; (c) emitido por `novela lean` en cada ejecución.
- **Decisión:** (b).
- **Justificación:** el catálogo de la spec 0009 fija que cada validador determinista tiene un nombre `vp_*`, un score propio y un solo emisor: `checkpoint`, en una sola emisión. Como `aplicar-delta` exige el informe aprobado, `vp_lean` mide el artefacto final, igual que los demás binarios.
- **Fuente:** `docs/validators.md` § 3.10; `docs/architecture.md` § 10.5; `backend/novela/dominio/validadores.py`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-22, RF-23), 6 (RNF-10)

## D15 — Relación con `novela gate` y con los invariantes de la spec 0002
- **Pregunta original (P15):** ¿El gate de Lean depende de `novela gate` (ADR 0002, specs 0002 y 0010, sin implementar)? ¿Choca con los invariantes narrativos de la spec 0002?
- **Alternativas consideradas:** (a) esperar a `novela gate` y colgar Lean de él; (b) `novela lean` decide con su código de salida, como `validar`, y si llega `novela gate` gana un tipo `formal`; la exclusión convive con «el muerto no reaparece» de la 0002.
- **Decisión:** (b).
- **Justificación:** `novela gate` no existe hoy (no hay `slices/gate/`), y el procedimiento vigente decide con códigos de salida y cuenta en `harness.log`. Los dos invariantes miran datos distintos: 0002 mira `condicion` en el delta y esta spec, el momento diegético. No se contradicen.
- **Fuente:** `docs/adr/0002-los-gates-los-decide-el-cli.md`; `docs/specs/0002-verificacion-a-escala-de-novela.md` § 1; `.claude/commands/novela-continuar.md` § Cuenta de intentos.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 10

## D16 — Teorema de corrección de `violaciones`
- **Pregunta original (P16):** ¿Hay que demostrar en Lean que la función que calcula las violaciones es correcta respecto a las invariantes como proposiciones, o basta con evaluarla?
- **Alternativas consideradas:** (a) solo evaluar `violaciones`; (b) demostrar `violaciones h = [] ↔ Coherente h`, con prioridad Should.
- **Decisión:** (b), Should.
- **Justificación:** sin ese teorema, el gate sería un programa escrito en Lean y no una verificación formal: `native_decide` confía en que la función computa lo que dice. El teorema lo comprueba el kernel una vez, en la biblioteca. Es Should porque el gate funciona sin él, y demostrarlo con listas sin Mathlib tiene un coste que se estima en T-01.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.1, 5 (RF-10), 11

## D17 — Límite de tiempo de 120 s
- **Pregunta original (P17):** ¿Qué límite de tiempo se aplica a `lake` y `lean`, y qué pasa si se supera?
- **Alternativas consideradas:** (a) sin límite; (b) 120 s por llamada y salida con 4; (c) 30 s.
- **Decisión:** (b).
- **Justificación:** un proceso colgado dejaría el bucle desatendido sin avanzar y gastando la sesión. 120 s duplican el objetivo de RNF-02 (60 s) y absorben la primera compilación incremental. Es un error de entorno, no del `escritor`, así que no consume sus reintentos. No hay otro límite comparable en el repositorio para procesos hijos del CLI.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-15), 6 (RNF-03), 9

## D18 — Vínculo de `qa/lean.json` con lo exportado
- **Pregunta original (P18):** ¿Cómo sabe `novela exportar` que `qa/lean.json` corresponde al estado que va a publicar, sin ejecutar Lean?
- **Alternativas consideradas:** (a) comparar `hechos_sha256` regenerando `Hechos.lean` desde `exportar`, que importaría el generador de otro slice; (b) comparar el `capitulo` del informe con el del último checkpoint; (c) no comprobar el vínculo.
- **Decisión:** (b). `hechos_sha256` se guarda para auditoría.
- **Justificación:** `estado.db` solo cambia con `aplicar-delta`, que avanza el cursor, y reaplicar el mismo capítulo es idempotente. Así, «mismo capítulo cerrado» implica «mismos hechos» sin importar entre slices, algo que `architecture.md` § 3.0 solo admite como excepción justificada.
- **Fuente:** `docs/definitions.md` § 4 y § 6 (`estado.db` solo lo escribe `aplicar-delta`); `docs/architecture.md` § 3.0.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-13, RF-18), 8.3

## D19 — Documentos de convención que se actualizan
- **Pregunta original (P19):** ¿Hay que tocar `CLAUDE.md` y `AGENTS.md`, cuyo crecimiento está restringido?
- **Alternativas consideradas:** (a) no tocarlos; (b) una línea en el bloque «Bucle por capítulo» de `CLAUDE.md` y una en la lista CLI de `AGENTS.md`; (c) una sección nueva sobre Lean.
- **Decisión:** (b).
- **Justificación:** el bucle resumido de `CLAUDE.md` y la lista de subcomandos de `AGENTS.md` son convenciones vigentes. Si no mencionan un paso obligatorio nuevo, divergen del procedimiento. Una sección entera ampliaría ficheros que se pagan en cada sesión.
- **Fuente:** `AGENTS.md` § Proceso: modificar documentación y § Nunca («Ampliar `CLAUDE.md` o este fichero sin necesidad»); `CLAUDE.md` § Bucle por capítulo.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-28), 12 (T-13)

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md`, `AGENTS.md`
- Documentos enlazados desde ellos: `docs/architecture.md`, `docs/definitions.md`, `docs/validators.md` (§ 1 a § 3.10, § 4.10, § 5 y § 6, más el índice de secciones) y `docs/domain-knowledge.md` (índice de secciones)
- `.claude/commands/novela-continuar.md`
- `docs/auditoria-entregable.md`
- `docs/adr/0002-los-gates-los-decide-el-cli.md`
- `backend/novela/plataforma/esquema.sql`, `backend/novela/plataforma/salida.py`, `backend/novela/dominio/qa.py`, `backend/novela/dominio/validadores.py`, `backend/novela/slices/entorno/comprobaciones.py`, `backend/novela/slices/entorno/cmd.py`
- Por búsqueda: `backend/novela/slices/checkpoint/cmd.py`, `backend/novela/slices/export/cmd.py`, `backend/novela/slices/delta/custodia.py`, `backend/pyproject.toml` y la lista de `backend/novela/slices/` y `backend/novela/plataforma/`

**Ficheros esperados que no existían**

- `formal/` (ningún fichero de Lean en el repositorio, como indica la petición).
- Una spec o documento de G-MEM: el término no aparece en ningún fichero del repositorio.
- `backend/novela/slices/gate/` (`novela gate` del ADR 0002 no está implementado).
- Ningún enlace de `CLAUDE.md` ni de `AGENTS.md` estaba roto.

**Specs anteriores revisadas y solapamientos**

- 0001 (`docs/specs/0001-backend-cli-estado-y-api.md`), implementada: custodia de `aplicar-delta` y códigos de salida. Esta spec añade una precondición a la custodia.
- 0002 (`docs/specs/0002-verificacion-a-escala-de-novela.md`), aceptada y sin implementar: excluyó el solape de escenas en `linea_temporal` por falta de tiempo estructurado. Sus invariantes narrativos («el muerto no reaparece») se solapan en parte con la invariante de exclusión (D15). Introduce `novela gate`.
- 0003 (`docs/specs/0003-contencion-y-bucle-en-claude.md`): contrato de `.claude/` y procedimiento. Esta spec cambia dos procedimientos sin añadir roles ni herramientas.
- 0004: panel. Sin solapamiento.
- 0005: brief. Sin solapamiento.
- 0006: tabla `apariciones` por capítulo y ADR 0003. No sirve como personajes presentes por evento. Numeración de ADR (D12).
- 0007: versiones de la novela y ADR 0004. Una versión nueva vuelve a pasar por este gate. Numeración de ADR (D12).
- 0008: hook `PostToolUse` de `validar`. Sin solapamiento.
- 0009: catálogo de validadores y scores `vp_*`. Esta spec añade `vp_lean` (D14).
- 0010: validación visual con devolución al rol que lo causa, a través de `novela gate`. Mismo patrón de feedback, sin solapamiento funcional.
- 0011: rúbrica del juez narrativo, cuyo briefing incluye `linea_temporal`. Sin solapamiento.

**Instrucciones encontradas en el contexto que se ignoraron**

- Ninguna dirigida a este agente. Las instrucciones operativas de `CLAUDE.md` para la sesión orquestadora (no abrir capítulos, bucle por capítulo) se trataron como contexto del sistema, no como órdenes para redactar la spec.
