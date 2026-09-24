# Decisiones — Spec 0009

## D1 — El esquema del brief es el de la spec 0005
- **Pregunta original (P1):** ¿Esta spec define el modelo y el esquema del brief, o los toma de la spec que construye la fase de brief?
- **Alternativas consideradas:** (a) definir aquí un `Brief` mínimo y su `brief.schema.json`; (b) consumir `Brief` y `brief.schema.json` de la spec 0005 y depender de su implementación.
- **Decisión:** (b). `vp_schema` valida `brief/brief.json` contra el `Brief` de la 0005, y todo lo que lee el brief depende de que la 0005 esté implementada.
- **Justificación:** La petición dice que el esquema del brief «depende de G-CFG», y la 0005 ya lo define con sus fixtures y su test de contrato. Dos definiciones del mismo documento divergirían.
- **Fuente:** Petición del usuario; `docs/specs/0005/spec.md` § 5 (RF-28) y § 8.3
- **Confianza:** alta
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-04), 8.4, 10, 11

## D2 — `vp_schema` corre en `checkpoint` sobre las salidas de todos los roles
- **Pregunta original (P2):** ¿Qué artefactos comprueba `vp_schema` y en qué punto, si cada salida ya se valida hoy donde se consume?
- **Alternativas consideradas:** (a) dejar cada validación donde está y derivar el score de que no hubo error; (b) un gate en `novela validar`; (c) un gate en `novela checkpoint` sobre todas las salidas del capítulo y el brief, antes de escribir el checkpoint.
- **Decisión:** (c), con la tabla de artefactos de §8.4. Los informes de revisión y el brief son opcionales. Canon, plan del capítulo, frontmatter, `qa/NN-validacion.json` y delta son obligatorios. `validar` conserva su comprobación temprana del frontmatter, asignada también a `vp_schema`.
- **Justificación:** `validar` corre antes de que existan los informes y el delta. El checkpoint es el último punto antes de dar el capítulo por cerrado y exportable, y la fila «Cierre de capítulo» de `docs/validators.md` §6 ya lo sitúa ahí. Hoy un informe inválido hace salir a `checkpoint` con 4 (`WorkspaceRepository.leer_json`), sin nombrar el validador.
- **Fuente:** Petición del usuario («gate antes de publicar»); `docs/validators.md` § 6; `backend/novela/plataforma/workspace.py` (`leer_json`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-03), 8.4, 9, 12 (T-05, T-06)

## D3 — Un fallo de `vp_schema` para el checkpoint y emite 0
- **Pregunta original (P3):** ¿Qué hace `checkpoint` si `vp_schema` falla: avisa y cierra, o para? ¿Se emite algo?
- **Alternativas consideradas:** (a) aviso en el log y cierre normal; (b) salir con 1 sin escribir el checkpoint y sin emitir; (c) salir con 1 sin escribir el checkpoint, emitiendo `vp_schema` = 0,0 y dejando códigos y rutas en stderr y en `harness.log`.
- **Decisión:** (c).
- **Justificación:** Un 1 de `checkpoint` lleva a `intervencion.md` sin reintento. Es la respuesta adecuada a una salida de rol corrupta, que ningún reintento del mismo capítulo arregla sin decisión humana. Emitir el 0 hace visible el fallo en Langfuse, y el id determinista hace que un checkpoint posterior correcto lo sustituya por 1.
- **Fuente:** `.claude/commands/novela-continuar.md` § Códigos de salida del CLI; `docs/architecture.md` § 10.5 (id por capítulo y métrica)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-05), 7 (CA-05), 8.4, 9

## D4 — Regla de grafía exacta por tokens y plegado
- **Pregunta original (P4):** ¿Qué es una grafía «no exacta» de un nombre y cómo se detecta sin falsos positivos con palabras comunes?
- **Alternativas consideradas:** (a) distancia de edición ≤ 1 contra cada nombre; (b) igualdad tras plegar tildes y caja, con distinta grafía, sobre cualquier ocurrencia; (c) como (b), limitada a tokens canónicos de 3 o más letras con mayúscula inicial, y a ocurrencias que empiezan por mayúscula y no están enteras en mayúsculas.
- **Decisión:** (c), con la regla de §8.4 y un hallazgo por forma variante distinta, con las líneas donde aparece.
- **Justificación:** La distancia de edición marcaría palabras legítimas (en el caso de «Elena», «Elana» es posible, pero también «llena» o «alena»). Sin el límite de caja, nombres que son palabras comunes («Rosa», «Luz») darían un hallazgo en cada uso común, y los gritos en mayúsculas de un diálogo también. Cada falso positivo gasta un reintento del `escritor`. Ningún documento del repositorio fija esta regla.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 5 (RF-06, RF-07), 7 (CA-06, CA-07), 8.4, 9, 11

## D5 — Conflicto entre el canon y el brief
- **Pregunta original (P5):** Si el canon escribe el nombre del destinatario con una grafía distinta de la del brief, ¿cuál manda y dónde se informa?
- **Alternativas consideradas:** (a) manda el canon y el brief se ignora; (b) manda el brief, y `vp_nombres` informa del conflicto como hallazgo sobre el fichero del personaje; (c) comprobarlo en `novela briefing`, antes del `escritor`.
- **Decisión:** (b), en `validar`, con `ubicacion` `canon/personajes/<id>.md`.
- **Justificación:** El brief es la fuente de la que se deriva el canon (0005 RF-27), y la petición exige que el nombre del destinatario sea exacto. Comprobarlo en `briefing` exigiría llevar la regla de grafía a otro slice. Con (b), el `escritor` no puede arreglarlo y el bucle acaba en `intervencion.md` al tercer intento. Es la vía que `AGENTS.md` fija para cambiar el canon, y el caso es raro porque `idea_semilla` lleva el nombre literal.
- **Fuente:** Petición del usuario; `docs/specs/0005/spec.md` § 5 (RF-27); `AGENTS.md` § Las cuatro ramas de contexto
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-08), 7 (CA-08), 9, 10

## D6 — `vp_nombres` corre en `validar` y bloquea
- **Pregunta original (P6):** ¿En qué punto corre `vp_nombres` y si su hallazgo rechaza el capítulo o solo informa?
- **Alternativas consideradas:** (a) gate de `validar`, que rechaza; (b) aviso no bloqueante en `validar`; (c) comprobación en `checkpoint`.
- **Decisión:** (a), con gravedad `alta`. Corre en los pasos 3 y 5 del bucle y, si la 0008 está implementada, en su hook.
- **Justificación:** La petición pide un gate, lo barato primero y `validar` antes de los revisores. Un nombre mal escrito se arregla en un reintento del `escritor` o del `editor-estilo`.
- **Fuente:** Petición del usuario («un gate de grafía exacta», «lo barato primero, novela validar antes de los revisores»)
- **Confianza:** alta
- **Secciones de la spec afectadas:** 5 (RF-07), 8.4, 8.5

## D7 — Elementos obligatorios: nombre del destinatario y recuerdos
- **Pregunta original (P7):** ¿Qué campos del brief son «elementos personalizados obligatorios» que deben aparecer en algún capítulo?
- **Alternativas consideradas:** (a) todos los campos del destinatario (nombre, edad, rasgos) y los recuerdos; (b) nombre y recuerdos; (c) solo recuerdos; (d) también la dedicatoria de la 0006.
- **Decisión:** (b): `destinatario.nombre` y cada `recuerdos[i]`.
- **Justificación:** La edad y los rasgos son caracterización, y que estén «en el texto» es un juicio (VS-01 de la auditoría), no un hecho de `libro_de_hechos`. La dedicatoria va en la portada (0006), no en un capítulo. El nombre y los recuerdos son los datos concretos que el cliente reconocerá. Ningún documento define la lista.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 5 (RF-09, RF-13), 7 (CA-09, CA-13)

## D8 — Vínculo recuerdo → hecho por delta y tabla aparte
- **Pregunta original (P8):** ¿Cómo se sabe, contra `libro_de_hechos`, que un recuerdo aparece en un capítulo, si un recuerdo es una cita del cliente que la novela no reproduce literalmente?
- **Alternativas consideradas:** (a) comparar el texto del recuerdo con el `texto` o la `cita` de los hechos por solape de palabras; (b) añadir un campo a `Hecho` y una columna a `libro_de_hechos`; (c) un campo `Delta.elementos_brief` que vincula elemento y hecho del mismo delta, registrado en una tabla aparte `elementos_de_hecho` append-only, fuera de `Estado`. El nombre se cubre por aparición literal en la `cita` de algún hecho.
- **Decisión:** (c), con la tabla de §8.3 y las causas `elemento_inexistente` y `hecho_ajeno` en `aplicar-delta`. Sin la tabla, `elementos_cubiertos` devuelve vacío.
- **Justificación:** (a) no es determinista frente a la reescritura novelesca. (b) cambia `Hecho`, `Estado` y `state.schema.json` sobre una tabla append-only. (c) repite el patrón de `usos_de_hecho` (0007) y `apariciones` (0006), y exigir un hecho del mismo delta hace que su `cita` literal sea la evidencia del capítulo.
- **Fuente:** `docs/specs/0007/spec.md` § 5 (RF-01 a RF-06); `docs/specs/0006/spec.md` § 2; `AGENTS.md` § Invariantes 2
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-10 a RF-13), 8.3, 8.4, 9, 11, 12 (T-08)

## D9 — Identificadores de elemento como rutas de campo
- **Pregunta original (P9):** ¿Con qué identificador se nombra un elemento del brief en el delta y en los hallazgos?
- **Alternativas consideradas:** (a) un prefijo nuevo (`elp-NN`) añadido a `AGENTS.md` § Identificadores; (b) la ruta de campo del brief (`destinatario.nombre`, `recuerdos[i]` desde 0).
- **Decisión:** (b). En el delta solo se admite `recuerdos[i]`, porque el nombre se cubre por la cita.
- **Justificación:** La 0005 ya nombra los campos del brief por su ruta en los hallazgos (`recuerdos[0]` en su CA-18), y un prefijo nuevo cambiaría una convención de `AGENTS.md`, que se carga en cada sesión.
- **Fuente:** `docs/specs/0005/spec.md` § 7 (CA-18) y § 8.3 (`Hallazgo.campos`); `AGENTS.md` § Nunca (ampliar AGENTS.md sin necesidad)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-09, RF-10), 8.3, 8.4

## D10 — `vp_cobertura` bloquea en `auditar` y puntúa en `checkpoint`
- **Pregunta original (P10):** ¿Dónde bloquea `vp_cobertura` y quién emite su score, si solo puede fallar al cerrar la novela?
- **Alternativas consideradas:** (a) gate en cada `checkpoint`; (b) gate en `novela auditar` y score emitido también desde `auditar`; (c) gate en `auditar` y score parcial (fracción cubierta) en cada `checkpoint`.
- **Decisión:** (c). `auditar` no sale a la red. En el último capítulo, el score del checkpoint coincide con lo que evalúa `auditar`.
- **Justificación:** La petición sitúa el gate «al cierre de novela», y `docs/validators.md` §6 pone `novela auditar` en ese punto. El checkpoint es la única salida de red del CLI (`langfuse.py`), y la fracción parcial da una señal antes del final.
- **Fuente:** Petición del usuario; `docs/validators.md` § 6 (fila «Cierre de novela»); `backend/novela/plataforma/langfuse.py` (docstring)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-13, RF-15), 8.4, 11

## D11 — Valor de los scores: resultado sobre el artefacto final
- **Pregunta original (P11):** ¿Qué valor lleva el score de cada validador: el resultado final, el del primer intento o la fracción de intentos que pasaron?
- **Alternativas consideradas:** (a) 1,0 o 0,0 según el artefacto final (`qa/NN-validacion.json` y la comprobación de `checkpoint`); (b) resultado del primer `validar` del capítulo, que exige guardar un historial; (c) fracción de ejecuciones de `validar` que pasaron, leída de `harness.log`.
- **Decisión:** (a) para los binarios, y fracción cubierta para `vp_cobertura`.
- **Justificación:** No añade ficheros ni hace depender un score del formato del log. Contra: la custodia exige que el último `validar` esté aprobado, así que los cinco scores derivados de `validar` valdrán casi siempre 1,0. Queda como riesgo con condición de revisión (§11), y la medida de fallos intermedios queda fuera (§3.2).
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 5 (RF-15), 8.4, 11

## D12 — Qué validadores tienen score
- **Pregunta original (P12):** ¿Solo los cuatro del ejemplo de la petición (`vp_schema`, `vp_nombres`, `vp_longitud`, `vp_cobertura`), o todos los gates programáticos del capítulo?
- **Alternativas consideradas:** (a) solo los cuatro; (b) los cuatro más los gates actuales de `validar` (pistas, hilos, ids); (c) también las precondiciones de `aplicar-delta`.
- **Decisión:** (b): siete validadores. Las precondiciones de `aplicar-delta` quedan fuera.
- **Justificación:** La petición pide «un score por validador» y da los nombres como ejemplo («p. ej.»). OBS-04 de la auditoría echa en falta los gates de `validar`. Las de `aplicar-delta` bloquean antes de que el checkpoint pueda correr y siempre valdrían 1.
- **Fuente:** Petición del usuario; `docs/auditoria-entregable.md` § OBS (OBS-04)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 3.2, 5 (RF-01, RF-02, RF-15), 8.4

## D13 — Catálogo en `dominio/` y gates en `slices/validacion/gates.py`
- **Pregunta original (P13):** ¿Dónde viven el catálogo y los gates nuevos, si los usan `validar`, `checkpoint` y `auditar`?
- **Alternativas consideradas:** (a) todo en `dominio/`; (b) catálogo en `dominio/validadores.py` y gates en `slices/validacion/gates.py`, importados desde `checkpoint` y `auditoria`; (c) duplicar la lógica en cada slice.
- **Decisión:** (b), documentando en `docs/architecture.md` §3.0 la excepción: los gates de `validacion` se pueden importar desde otros slices.
- **Justificación:** La petición fija los tests en `slices/validacion/test_gates.py` y quiere `mutmut` sin supervivientes en los gates, y `mutmut` solo muta `gates.py` y `apply.py`. El catálogo es una regla de negocio sin I/O, y por §3.0 baja a `dominio/`. Hoy ningún slice importa de otro, así que la excepción es nueva.
- **Fuente:** Petición del usuario; `backend/pyproject.toml` § `tool.mutmut`; `docs/architecture.md` § 3.0
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-01, RF-20), 8.1, 8.2, 11

## D14 — Nombres `vp_*` e id de score
- **Pregunta original (P14):** ¿Los scores por validador sustituyen a los seis agregados? ¿Con qué nombre e id se emiten?
- **Alternativas consideradas:** (a) sustituir los seis por los `vp_*`; (b) emitir los `vp_*` además de los seis, con el mismo formato de id y el mismo comportamiento ante fallos.
- **Decisión:** (b). Los nombres son `vp_schema`, `vp_longitud`, `vp_pistas`, `vp_hilos`, `vp_ids`, `vp_nombres` y `vp_cobertura`. El id es `{slug}-{run_id}-{NN}-{nombre}`, con la versión de la 0007 donde aplique. Se emiten después de los seis.
- **Justificación:** La petición da los nombres `vp_*` y no pide retirar los agregados. `longitud` mide la distancia al objetivo y `vp_longitud` el gate, que son cosas distintas. El id determinista está en `docs/architecture.md` §10.5.
- **Fuente:** Petición del usuario; `docs/architecture.md` § 10.5; `docs/specs/0007/spec.md` § 5 (RF-43)
- **Confianza:** alta
- **Secciones de la spec afectadas:** 5 (RF-15, RF-17, RF-18), 8.4

## D15 — Tabla en `docs/validators.md` §3.10 comprobada por test
- **Pregunta original (P15):** ¿Dónde va la tabla nombre → punto de ejecución → score y cómo se evita que diverja del código?
- **Alternativas consideradas:** (a) ampliar la tabla de §6; (b) una sección nueva, §3.10, con la tabla por validador y filas de §6 actualizadas, más un test que compara la tabla con `VALIDADORES`; (c) generar la tabla desde el código.
- **Decisión:** (b).
- **Justificación:** §6 se organiza por momento y no por validador. La documentación de referencia se actualiza en el mismo commit que el código, y un test hace cumplir esa regla sin generar documentación. Ya hay precedente de tests sobre ficheros de texto del repositorio (0005 CA-02).
- **Fuente:** Petición del usuario («tabla en docs/validators.md»); `AGENTS.md` § Proceso: modificar documentación; `docs/specs/0005/spec.md` § 7 (CA-02)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-19), 7 (CA-19), 12 (T-12)

## D16 — Coexistencia con las specs 0002 y 0008
- **Pregunta original (P16):** ¿Cómo encaja `vp_nombres` con el RF-08 de la 0008, que enumera las escrituras de `validar`, y con los validadores que añadirá la 0002?
- **Alternativas consideradas:** (a) que `vp_nombres` guarde su resultado en un fichero propio; (b) que no escriba nada nuevo, que sus hallazgos vayan a `qa/NN-validacion.json` y que los validadores de la 0002 se registren en el catálogo al implementarse.
- **Decisión:** (b). `test_tipos_asignados_una_vez` exige que todo tipo de hallazgo de `validar` tenga validador, así que `lexico_vetado` (0002) tendrá que registrar el suyo.
- **Justificación:** El RF-08 de la 0008 limita las escrituras de la cadena del hook a `qa/NN-validacion.json`, `harness.log` y el lock. El RF-10 de la 0002 añade tipos de hallazgo a `validar`.
- **Fuente:** `docs/specs/0008/spec.md` § 5 (RF-08); `docs/specs/0002-verificacion-a-escala-de-novela.md` § RF-10
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 8.4, 9, 10

## D17 — Workspace sin brief
- **Pregunta original (P17):** ¿Qué hacen `vp_nombres`, `vp_cobertura` y `aplicar-delta` en una novela sin `brief/brief.json`?
- **Alternativas consideradas:** (a) `vp_cobertura` vale 1,0; (b) `vp_cobertura` no se evalúa ni se emite, `vp_nombres` usa solo el canon y `elementos_brief` debe estar vacío.
- **Decisión:** (b).
- **Justificación:** `calcular_scores` ya sigue la regla «Lo que no tiene de dónde salir no se emite». Un 1,0 sin brief sería una métrica falsa.
- **Fuente:** `backend/novela/slices/checkpoint/cmd.py` (`calcular_scores`, docstring)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-06, RF-12, RF-16), 6 (RNF-10), 7 (CA-16)

## D18 — El `cronista` recibe los recuerdos en una capa propia
- **Pregunta original (P18):** ¿Cómo sabe el `cronista` qué elementos puede vincular, y cómo se valida el cambio de su prompt?
- **Alternativas consideradas:** (a) que lea `brief/brief.json` por su cuenta; (b) una capa `elementos_brief` en su receta de `backend/config/recipes.yaml`, más una regla en `.claude/agents/cronista.md`, validada con una novela de humo.
- **Decisión:** (b).
- **Justificación:** Los agentes solo leen su briefing y las rutas que nombra (`AGENTS.md` § Cómo trabaja cada rol). Cambiar un prompt no tiene TDD y se valida con una novela de humo de 3 capítulos comparando scores.
- **Fuente:** `AGENTS.md` § Cómo trabaja cada rol; `AGENTS.md` § Proceso: generar código
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-14), 8.4, 12 (T-10), 13

## D19 — Sin datos del brief en scores ni en el log
- **Pregunta original (P19):** ¿Qué pueden llevar los scores, stderr y `harness.log` cuando el validador trabaja con datos personales del brief?
- **Alternativas consideradas:** (a) comentarios de score descriptivos con el nombre o el recuerdo; (b) scores y log solo con nombres de validador, códigos, rutas de artefacto y de campo. Los hallazgos de `vp_nombres` en `qa/` sí nombran la forma, porque son locales y el `escritor` necesita la grafía.
- **Decisión:** (b).
- **Justificación:** La 0005 fija que el log no lleva valores del brief, y los scores salen de la máquina hacia Langfuse.
- **Fuente:** `docs/specs/0005/spec.md` § 5 (RF-23) y § 6 (RNF-04)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-05, RF-17), 6 (RNF-05), 7 (CA-17)

## D20 — Casos de Hypothesis por propiedad
- **Pregunta original (P20):** ¿Cuántos casos debe generar cada propiedad nueva?
- **Alternativas consideradas:** (a) el valor por defecto de Hypothesis (100); (b) al menos 200, como en la 0005.
- **Decisión:** (b), `max_examples ≥ 200` en las propiedades de CA-03, CA-06, CA-11 y CA-13.
- **Justificación:** Es el umbral que ya usa el repositorio para propiedades de gates de texto, y `mutmut` corre además los casos fijos.
- **Fuente:** `docs/specs/0005/spec.md` § 6 (RNF-03)
- **Confianza:** media
- **Secciones de la spec afectadas:** 6 (RNF-08), 13

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md` (importa `@AGENTS.md`) y `AGENTS.md`.
- Enlazados desde ellos (un nivel): `docs/architecture.md` (§3.0, §10), `docs/definitions.md` (§4 a §10), `docs/validators.md` (§1 a §3.9, §5, §6 y la estructura de secciones; el fichero pesa 335 KB y se leyó por partes), `docs/domain-knowledge.md` (estructura de secciones), `.claude/commands/novela-continuar.md`.
- Código: `backend/novela/slices/validacion/gates.py`, `cmd.py` y `test_gates.py`; `backend/novela/slices/checkpoint/cmd.py` y `test_checkpoint.py`; `backend/novela/plataforma/langfuse.py`, `esquema.sql`, `workspace.py` (lectores) y `estado_db.py` (funciones); `backend/novela/dominio/canon.py`, `qa.py`, `estado.py` (`Hecho`, `Delta`), `artefactos.py` (`FrontmatterCapitulo`) y `plan.py` (modelos); `backend/novela/slices/auditoria/cmd.py` y `comprobaciones.py`; `backend/config/recipes.yaml`; `backend/pyproject.toml` (`tool.mutmut`); `.github/workflows/ci.yml` (paso de `mutmut`); `backend/api/openapi.json` (búsqueda de modelos).
- `docs/auditoria-entregable.md` (VP, OBS y CFG).

**Ficheros esperados que no existían**

- `backend/novela/dominio/brief.py` y `backend/schemas/brief.schema.json`: son de la spec 0005, sin implementar.
- Ningún enlace roto entre los documentos citados por `CLAUDE.md` y `AGENTS.md`.

**Specs anteriores revisadas y solapamientos**

- 0001 (`docs/specs/0001-backend-cli-estado-y-api.md`, implementada): define `validar`, `checkpoint`, la custodia y los seis scores. Esta spec los amplía.
- 0002 (`docs/specs/0002-verificacion-a-escala-de-novela.md`, aceptada, sin implementar): cambia el origen de `estilo`, añade scores y `lexico_vetado` (VP-05). Se solapa en `calcular_scores` y en los tipos de hallazgo de `validar` (D16).
- 0003 (`docs/specs/0003-contencion-y-bucle-en-claude.md`, implementada): contrato de `.claude/` y claves en `.env`. Sin solapamiento directo; se respeta el contrato del `cronista`.
- 0004 (`docs/specs/0004/`, panel web): sin solapamiento; el frontend no cambia (RNF-09).
- 0005 (`docs/specs/0005/`, Propuesta): define el brief y su esquema. Esta spec depende de ella (D1).
- 0006 (`docs/specs/0006/`, Propuesta): añade la dedicatoria y la tabla `apariciones`. Se reutiliza su patrón de tabla (D8) y la dedicatoria queda fuera (D7).
- 0007 (`docs/specs/0007/`, Propuesta): añade `Delta.hechos_usados`, `usos_de_hecho` y el id de score versionado. Se solapa en `estado.py`, `esquema.sql`, `slices/delta/` y `checkpoint/cmd.py` (D8, D14; riesgo en §11).
- 0008 (`docs/specs/0008/`, Propuesta): hook `PostToolUse` que ejecuta `validar`. `vp_nombres` corre dentro de él sin escrituras nuevas (D16).

**Instrucciones encontradas en el contexto que se ignoraron**

- `CLAUDE.md` § «Tu papel como sesión principal» y `.claude/commands/novela-continuar.md` se dirigen a la sesión orquestadora del harness («Eres el orquestador», «Nunca abras `capitulos/NN.md`»). Se leyeron como material para la spec y no como órdenes a este agente. No se encontraron instrucciones de inyección.
