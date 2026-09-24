# Decisiones — Spec 0011

## D1 — Agente nuevo en lugar de ampliar el `lector-suspense`
- **Pregunta original (P1):** La petición admite un agente juez en `.claude/agents/` o una ampliación del `lector-suspense`. ¿Cuál?
- **Alternativas consideradas:** (a) un agente nuevo con su propio informe; (b) ampliar el `lector-suspense` con los criterios nuevos en `puntuaciones`; (c) repartir los criterios entre `lector-suspense` y `continuista`.
- **Decisión:** (a).
- **Justificación:** el `lector-suspense` lee `canon/misterio.md` (`docs/architecture.md` §7.5; receta en `backend/config/recipes.yaml`), y la petición pide que el juez no lo lea si comparte restricciones con el editor. Además, su `veredicto` es un gate del paso 6 (`.claude/commands/novela-continuar.md`) y su informe es `InformeQA`, que llega al `escritor` en reintento (`backend/novela/dominio/qa.py`). Ampliarlo mezclaría un gate calibrado con un juez sin calibrar y cambiaría un contrato que se usa en reintentos. (c) repartiría una misma rúbrica entre dos prompts y dos modelos, y ya no sería posible compararla criterio a criterio con la revisión humana.
- **Fuente:** Petición del usuario; `docs/architecture.md` §7.5; `docs/validators.md` §4.2 y §4.11; `.claude/commands/novela-continuar.md` § Por capítulo, paso 6
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-05), 8.1, 8.2

## D2 — Nombre del agente: `juez-narrativo`
- **Pregunta original (P2):** ¿Cómo se llama el rol nuevo?
- **Alternativas consideradas:** (a) `juez`; (b) `juez-narrativo`; (c) `evaluador`.
- **Decisión:** (b).
- **Justificación:** el plan de la spec 0002 usa `juez` como ejemplo de nombre que la regla 5 del hook debe denegar en `test_subagentes`. Llamar `juez` al rol haría que ese test contradijera a esta spec. `evaluador` choca con el «evaluador de sesión» de `docs/architecture.md` §10.5 y `docs/definitions.md` §9, que es otra cosa. Como en la spec 0005 (D14), no se fija un número de roles en la documentación.
- **Fuente:** `docs/implementation-plans/0002-verificacion/fase-4-tension-y-secreto-por-acto.md` (fila `(SESION, "Agent", "juez", 2)`); `docs/architecture.md` §10.5; `docs/specs/0005/spec.md` § 2 (D14)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-05, RF-06, RF-27), 7 (CA-05), 8.2

## D3 — Modelo del juez: `sonnet`
- **Pregunta original (P3):** El repositorio se contradice: `docs/architecture.md` §2.2 y `backend/config/default.yaml` dan `sonnet` a los revisores, y `CONTRATO` de `test_contratos.py` y los frontmatter les dan `haiku`. ¿Qué modelo lleva el juez, y se tocan los demás?
- **Alternativas consideradas:** (a) `sonnet` para el juez sin tocar a los demás; (b) `haiku`, como los revisores en `CONTRATO`; (c) `sonnet` para todos los revisores.
- **Decisión:** (a).
- **Justificación:** la petición lo fija explícitamente («modelo del frontmatter fijado por rol (sonnet para revisión)»), y coincide con `docs/architecture.md` §2.2. Cambiar el modelo de los demás revisores no forma parte de la petición, y según la auditoría el `haiku` actual se cambió a mano por el usuario. Esta spec registra la discrepancia y no la resuelve.
- **Fuente:** Petición del usuario; `docs/architecture.md` §2.2; `docs/auditoria-entregable.md` § Recuento
- **Confianza:** alta
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-05, RF-07), 7 (CA-04, CA-06)

## D4 — El juez no lee el misterio y hereda las guardas del `editor-estilo`
- **Pregunta original (P4):** ¿Lee el juez `canon/misterio.md`? La petición lo condiciona a que comparta restricciones con el editor.
- **Alternativas consideradas:** (a) receta con `excluir: [canon/misterio]` y las mismas guardas que el `editor-estilo`; (b) darle el misterio para juzgar el arco contra la solución.
- **Decisión:** (a).
- **Justificación:** ninguno de los seis criterios necesita la solución: se juzgan contra el estado, el estilo, las fichas, la ficha del capítulo y el brief. `docs/validators.md` §4.2 explica que un juez que conoce la respuesta no puede puntuar lo que percibe el lector. El guardarraíl de `novela briefing` ya se activa por `excluir` (`backend/novela/slices/briefing/assemble.py`), así que la protección es mecánica y no una petición en el prompt. Por la misma razón se excluye `plan/escaleta`, que el `lector-suspense` recibe junto al misterio.
- **Fuente:** Petición del usuario; `AGENTS.md` § Invariantes 3; `docs/validators.md` §4.2 y §4.4; `docs/architecture.md` §6.3
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-08, RF-09), 6 (RNF-02), 7 (CA-08), 8.4

## D5 — Fuente de verdad de la rúbrica: `backend/config/rubrica.yaml`, con `docs/rubrica.md` generado
- **Pregunta original (P5):** ¿Dónde vive la rúbrica, si la petición propone `docs/rubrica.md` o `backend/config/rubrica.yaml` y además pide «plantilla y rúbrica en docs/»?
- **Alternativas consideradas:** (a) YAML en `backend/config/` como fuente, y `docs/rubrica.md` generado y comprobado por test; (b) `docs/rubrica.md` con frontmatter como fuente, leído por el CLI; (c) dos ficheros escritos a mano.
- **Decisión:** (a).
- **Justificación:** el CLI necesita leer la rúbrica para el briefing y para comprobar el informe, y la configuración que lee el CLI vive en `backend/config/` (`recipes.yaml`, `default.yaml`). `AGENTS.md` separa la documentación de referencia de todo lo demás, así que hacer de `docs/` una entrada de ejecución mezclaría tipos de documento. El repositorio ya tiene el patrón «generado, commiteado y comprobado por test» para `backend/schemas/` (`test_state_schema_al_dia` con `REGENERAR=1`), y para las tablas de docs (`test_tabla_de_validadores`). (c) derivaría sin aviso.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: modificar documentación; `backend/tests/test_contratos.py` (`test_state_schema_al_dia`, `test_tabla_de_validadores`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 5 (RF-01, RF-02, RF-04, RF-12, RF-25), 8.2, 8.3

## D6 — Versión de la rúbrica: sha256 truncado del fichero
- **Pregunta original (P6):** ¿Cómo se identifica la versión de la rúbrica?
- **Alternativas consideradas:** (a) los 12 primeros hexadecimales del sha256 de `rubrica.yaml`; (b) un campo `version` semver escrito a mano; (c) el sha del commit.
- **Decisión:** (a).
- **Justificación:** la versión de recetas ya es «el sha256 de este fichero» (`backend/config/recipes.yaml`, cabecera). Así la versión cambia con el contenido sin depender de la disciplina de nadie, igual que `docs/validators.md` §4.7 hace depender la atribución de un dato y no de commitear. (c) no distingue un árbol sucio. El truncado a 12 caracteres lo hace legible para el revisor humano.
- **Fuente:** `backend/config/recipes.yaml` (cabecera); `docs/validators.md` §4.7
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-03, RF-12, RF-20), 7 (CA-02, CA-17), 8.4

## D7 — Seis criterios, con calidad narrativa desglosada en tres
- **Pregunta original (P7):** ¿«Calidad narrativa (arco, coherencia de personajes, ritmo)» es un criterio o tres? ¿Contra qué dato se juzga cada uno?
- **Alternativas consideradas:** (a) seis criterios: `continuidad`, `tono`, `arco`, `coherencia_personajes`, `ritmo` y `personalizacion`, agrupados por `bloque`; (b) cuatro criterios con subpuntuaciones; (c) cuatro criterios con una sola puntuación para calidad narrativa.
- **Decisión:** (a), y cada criterio declara su `contra`.
- **Justificación:** la petición pide «puntuación y justificación por criterio» y enumera arco, coherencia de personajes y ritmo. Puntuarlos por separado permite compararlos uno a uno con la revisión humana y ver cuál se degrada. `bloque` conserva la agrupación que pide la petición. El campo `contra` responde a la pregunta de `docs/validators.md` §4.6 para un rol de revisión nuevo.
- **Fuente:** Petición del usuario; `docs/validators.md` §4.2 y §4.6
- **Confianza:** media
- **Secciones de la spec afectadas:** 1, 5 (RF-01, RF-02), 8.3

## D8 — Escala entera de 1 a 5 con anclas en 1, 3 y 5
- **Pregunta original (P8):** ¿Qué escala usa la rúbrica y cuántos niveles se describen?
- **Alternativas consideradas:** (a) 1 a 5 entera, con anclas en 1, 3 y 5; (b) 1 a 10, como `tension`; (c) 0 a 1 continua.
- **Decisión:** (a).
- **Justificación:** con 3 capítulos de calibración, una escala corta hace que «diferencia ≤ 1» signifique algo, y las anclas en los extremos y el centro bastan para que un humano y un modelo la apliquen igual. Ningún documento del repositorio fija la escala de una rúbrica; es buena práctica general.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-01, RF-14), 6 (RNF-07, RNF-08), 8.3

## D9 — Esquema de salida nuevo, `InformeRubrica`, sin tocar `InformeQA`
- **Pregunta original (P9):** ¿La salida del juez amplía `InformeQA` o es un modelo propio?
- **Alternativas consideradas:** (a) modelo nuevo `InformeRubrica` con `rubrica-informe.schema.json`; (b) ampliar `InformeQA` con `criterios`; (c) usar `puntuaciones` de `InformeQA` con claves nuevas.
- **Decisión:** (a).
- **Justificación:** `InformeQA` «es lo único que recibe el escritor en un reintento» y su vocabulario es cerrado por productor (`backend/novela/dominio/qa.py`). El juez no produce hallazgos ni veredicto, y (c) no tiene sitio para justificación ni citas. Un modelo propio deja intacto `qa-informe.schema.json` (RNF-06).
- **Fuente:** `backend/novela/dominio/qa.py` (docstring); `docs/architecture.md` §7.3
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-13, RF-14), 6 (RNF-06), 8.3

## D10 — Evidencia: citas literales y custodia comprobadas por el CLI
- **Pregunta original (P10):** ¿Cómo se comprueba que la justificación se apoya en el capítulo, y en el capítulo correcto?
- **Alternativas consideradas:** (a) 1 a 3 citas literales por criterio aplicable, comprobadas en `checkpoint` tras normalizar, y custodia por el `capitulo_sha256` del briefing del juez; (b) confiar en la justificación; (c) pedir al juez el sha256 del capítulo.
- **Decisión:** (a).
- **Justificación:** la cita literal comprobada por el CLI es el patrón del repositorio contra la alucinación (`docs/architecture.md` §7.6, «Toda `cita` presente tiene que ser literal»). El briefing ya guarda `capitulo_sha256` del texto que vio el agente (`FrontmatterBriefing`, `backend/novela/dominio/artefactos.py`). (c) contradice «un modelo no calcula un sha256, lo inventaría» (`backend/novela/dominio/qa.py`).
- **Fuente:** `docs/architecture.md` §7.6; `backend/novela/dominio/artefactos.py`; `backend/novela/dominio/qa.py`
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-14, RF-20), 7 (CA-17), 8.4

## D11 — El juez no es un gate
- **Pregunta original (P11):** ¿El juez decide el avance del capítulo o solo emite scores?
- **Alternativas consideradas:** (a) solo scores; (b) gate con umbral por criterio; (c) gate solo sobre `personalizacion`.
- **Decisión:** (a).
- **Justificación:** «Si el plano recibe 6 o más […] el juez está saturado y sus puntuaciones no valen como gate hasta que se corrija su prompt» (`docs/validators.md` §4.11). Un juez sin calibrar no debe gastar los intentos del `escritor`. La petición pide scores en Langfuse y una calibración, no un gate. Convertirlo en gate después de calibrarlo es otra spec.
- **Fuente:** `docs/validators.md` §4.11 y §5.4; Petición del usuario
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-15), 8.1

## D12 — Posición en el bucle: paso 7, en el mismo turno que el `cronista`
- **Pregunta original (P12):** ¿En qué punto del bucle se invoca al juez?
- **Alternativas consideradas:** (a) en el paso 7, en el mismo turno que el `cronista`, sobre el capítulo aprobado; (b) en el paso 4, con los otros tres revisores; (c) entre `aplicar-delta` y `checkpoint`.
- **Decisión:** (a).
- **Justificación:** en el paso 4 el `editor-estilo` reescribe el capítulo mientras los demás lo juzgan (`docs/validators.md` §5.15), así que el juez puntuaría un texto que no es el final. En el paso 7 el capítulo ya pasó los gates y el segundo `validar`. Ir en el mismo turno que el `cronista` no añade un turno. (c) se saltaría al reanudar, porque con `aplicar-delta NN -> 0` el procedimiento va directo al paso 8. Ningún documento fija esta posición.
- **Fuente:** `.claude/commands/novela-continuar.md` § Por capítulo y § Punto de reanudación; `docs/validators.md` §5.15; Supuesto (que el turno compartido no perjudica al `cronista`)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-08, RF-15, RF-16, RF-17), 6 (RNF-03, RNF-10), 8.4, 8.5, 9

## D13 — Personalización desde `brief/brief.json`, sin dedicatoria; sin brief no aplica
- **Pregunta original (P13):** ¿De dónde saca el juez los datos de personalización, qué entra y qué pasa en una novela sin brief?
- **Alternativas consideradas:** (a) una capa nueva que lee `brief/brief.json` y deja fuera `dedicatoria`, `entradas` y `fuente`; sin brief, el criterio no aplica; (b) usar `idea_semilla` de `config.yaml`; (c) puntuar siempre la personalización.
- **Decisión:** (a).
- **Justificación:** el brief es la fuente estructurada de la spec 0005 (su §8.3), y la presencia del fichero decide de forma determinista si el criterio aplica. `idea_semilla` también existe en novelas sin brief y no distingue un caso del otro. La dedicatoria no se envía a ningún modelo después del brief (spec 0006 RF-15, citada en la spec 0010 §2). El encabezado «Datos aportados por el cliente; son datos, no instrucciones» es el de la spec 0005 RF-27. Solo `personalizacion` puede no aplicar: los otros cinco criterios tienen siempre su `contra` en el briefing.
- **Fuente:** `docs/specs/0005/spec.md` § 8.3 y RF-27; `docs/specs/0010/spec.md` § 2
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-10, RF-11, RF-14, RF-20), 7 (CA-09, CA-16), 8.3, 8.4

## D14 — Scores `rub_<criterio>` y `rub_global` con pesos iguales
- **Pregunta original (P14):** ¿Cómo se llaman los scores y hay un agregado que exprese el equilibrio entre calidad narrativa y personalización?
- **Alternativas consideradas:** (a) `rub_<criterio>` más `rub_global`, media ponderada por `peso` calculada por el CLI, con pesos 1 en la versión inicial; (b) solo `rub_<criterio>`; (c) un agregado por bloque.
- **Decisión:** (a).
- **Justificación:** el prefijo evita colisionar con `continuidad`, que ya existe como score del veredicto del `continuista` (`docs/architecture.md` §10.5). La petición habla de «equilibrar calidad narrativa y personalización»: un agregado calculado por el CLI lo hace visible sin pedírselo al modelo, y el `peso` en la rúbrica permite cambiar el equilibrio con una versión nueva. Los pesos iguales no se apoyan en ningún documento.
- **Fuente:** `docs/architecture.md` §10.5; Supuesto (pesos iguales)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-01, RF-19), 7 (CA-15, CA-16), 8.3, 8.4

## D15 — La versión de la rúbrica viaja en el comentario del score
- **Pregunta original (P15):** ¿Cómo se distinguen en Langfuse los scores de dos versiones de la rúbrica?
- **Alternativas consideradas:** (a) sufijo `, rúbrica <version>` en el `comment` de los `rub_*`, con un parámetro opcional en `ScoreSink.emitir`; (b) la versión en el nombre del score; (c) no llevarla a Langfuse.
- **Decisión:** (a).
- **Justificación:** (b) rompería las series por nombre en cada cambio de redacción y cambiaría el formato de id que fija la spec 0007 RF-43. (c) mezclaría en silencio scores de rúbricas distintas, que es lo que `docs/validators.md` §4.7 intenta evitar al atribuir cambios. Un parámetro opcional no cambia el comentario de los scores actuales (RNF-06).
- **Fuente:** `docs/validators.md` §4.7; `docs/specs/0007/spec.md` RF-43; Supuesto (el comentario basta para filtrar)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-22), 7 (CA-19), 8.4

## D16 — `vp_schema` valida el informe; la incoherencia semántica no bloquea el cierre
- **Pregunta original (P16):** ¿Qué hace `checkpoint` con un informe del juez inválido, incoherente o ausente?
- **Alternativas consideradas:** (a) `vp_schema` lo valida como opcional (inválido: sale con 1); incoherente o ausente: sin `rub_*`, con la causa en el log, y el capítulo cierra; (b) todo fallo del juez cierra sin scores; (c) todo fallo del juez impide cerrar.
- **Decisión:** (a).
- **Justificación:** la spec 0009 valida en `vp_schema` todas las salidas de rol del capítulo, y trata los informes de revisión como opcionales (`artefactos` en `backend/novela/slices/checkpoint/cmd.py`). Un JSON inválido es un contrato roto, y la petición exige salida válida contra esquema. La coherencia (versión, citas, custodia) es una propiedad del juicio, no del contrato, y un juez que no es gate (D11) no debe parar la novela: «el trazado nunca puede ser la razón por la que un capítulo no cierra» (`backend/novela/plataforma/langfuse.py`).
- **Fuente:** `docs/specs/0009/spec.md` § 1 y O-02; `backend/novela/slices/checkpoint/cmd.py`; `backend/novela/plataforma/langfuse.py` (docstring)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-18, RF-20, RF-21), 7 (CA-14, CA-17, CA-18), 8.4, 9, 11

## D17 — Ningún texto del juez sale a Langfuse ni al log
- **Pregunta original (P17):** ¿Se envían a Langfuse las justificaciones? Pueden contener datos personales del brief.
- **Alternativas consideradas:** (a) solo valores numéricos y un comentario sin texto del juez; en el log, solo códigos; (b) la justificación como `comment` del score; (c) justificación resumida.
- **Decisión:** (a).
- **Justificación:** la spec 0005 minimiza la salida de datos del destinatario («el log solo con códigos», su D16). `CLAUDE.md` § Claves y trazado y `docs/architecture.md` §10.1 hacen de Langfuse la única salida de red. Una justificación que nombra al destinatario o cita un recuerdo sería un dato personal fuera de la máquina. El texto completo queda en `qa/NN-rubrica.json`, dentro del workspace, que está en `.gitignore` (`AGENTS.md` § Separación repo / workspace).
- **Fuente:** `docs/specs/0005/decisions.md` D16; `AGENTS.md` § Separación repo / workspace; `docs/architecture.md` §10.1
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 5 (RF-23), 6 (RNF-01), 7 (CA-20), 9, 11

## D18 — Revisión humana ciega, por pseudónimo y en cada cambio del juez o de la rúbrica
- **Pregunta original (P18):** ¿Cuándo se hace la revisión humana, quién la hace y con qué material?
- **Alternativas consideradas:** (a) en cada cambio de `rubrica.yaml` o del prompt del juez, sobre la novela de humo de 3 capítulos, por alguien que no escribió el cambio, ciega y con el briefing del juez como material; (b) por muestreo en novelas reales; (c) solo una vez, al implementar.
- **Decisión:** (a).
- **Justificación:** `AGENTS.md` fija que un cambio de prompt se valida con una novela de humo de 3 capítulos, y un cambio de rúbrica tiene el mismo efecto. La revisión ciega evita que el humano se ancle en la cifra del juez. El briefing del juez da al humano exactamente los mismos datos, sin el misterio. El pseudónimo evita meter nombres reales en ficheros. La revisión en novelas reales es VS-03, que queda fuera. Que la revisión sea ciega y la firma por pseudónimo son buenas prácticas generales.
- **Fuente:** `AGENTS.md` § Proceso: generar código; `docs/validators.md` §4.8 y §4.11; Supuesto (ciega y pseudónimo)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-24, RF-28), 8.4

## D19 — Revisiones rellenadas en `revisiones/`, ignorado por git
- **Pregunta original (P19):** ¿Dónde se guardan las plantillas rellenadas?
- **Alternativas consideradas:** (a) `revisiones/` en la raíz, en `.gitignore`, y solo el resumen numérico a `docs/validators.md` §4.11; (b) versionadas en `docs/revisiones/`; (c) dentro de `novelas/<slug>/`.
- **Decisión:** (a).
- **Justificación:** (c) contradice «`novelas/<slug>/` […] Nunca lo versiones ni lo edites a mano» (`AGENTS.md`), y el hook solo deja a la sesión principal escribir `intervencion.md` en el workspace. (b) versionaría citas de capítulos que, en una novela real, contienen datos del destinatario. El resumen numérico, sin citas, sí se versiona como registro de la calibración.
- **Fuente:** `AGENTS.md` § Separación repo / workspace; `docs/architecture.md` §7.1 (regla 3 del hook); Supuesto (ubicación en la raíz)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-24, RF-26), 7 (CA-22), 8.3, 8.4

## D20 — Umbrales de calibración
- **Pregunta original (P20):** ¿Qué resultado de la calibración con la novela de humo da por bueno al juez?
- **Alternativas consideradas:** (a) error absoluto medio ≤ 1,0, ≥ 80 % de pares con diferencia ≤ 1 y ≤ 70 % de cincos; (b) solo el error medio; (c) correlación entre juez y humano.
- **Decisión:** (a).
- **Justificación:** con 3 capítulos hay como mucho 18 pares, demasiado pocos para una correlación estable. El tope de cincos traduce a esta escala la señal de «juez complaciente» de `docs/validators.md` §5.4 y la saturación de §4.11. Los números concretos no salen de ningún documento, y §5.16 advierte de que un solo baseline detecta un sistema roto pero no compara prompts.
- **Fuente:** `docs/validators.md` §4.11, §5.4 y §5.16; Supuesto (valores de los umbrales)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 6 (RNF-07, RNF-08), 7 (CA-24)

## D21 — La calibración de la personalización depende de la spec 0005
- **Pregunta original (P21):** La spec 0005 está sin implementar. ¿Cómo se calibra la personalización y cuándo se cierra esta spec?
- **Alternativas consideradas:** (a) la capa de brief y la calibración (T-12) esperan a la 0005, y esta spec no pasa a `implementada` sin T-12; (b) calibrar sin personalización y cerrar; (c) redefinir aquí un brief mínimo.
- **Decisión:** (a).
- **Justificación:** la personalización es la mitad del equilibrio que pide la petición. Cerrar sin calibrarla dejaría sin verificar justo lo nuevo. (c) duplicaría un modelo que es de la spec 0005, igual que la spec 0009 rechazó hacerlo (su D1). El resto de tareas no dependen de la 0005 y pueden avanzar.
- **Fuente:** `docs/specs/0009/spec.md` § 2 (relación con 0005) y § 3.2; `docs/specs/0005/spec.md` § 8.3
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-10, RF-28), 10, 11

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md` (importa `@AGENTS.md`) y `AGENTS.md`.
- Documentos enlazados desde ellos: `docs/architecture.md` (§2.2, §2.3, §2.4, §6.1–§6.5, §7.3–§7.6, §8, §9, §10, §11.1 y §12), `docs/validators.md` (§1, §2, §4.1–§4.16, §5 y §6; el resto, por índice), `docs/definitions.md` (índice, §7 y §9), `docs/domain-knowledge.md` (índice) y `.claude/commands/novela-continuar.md`. `backend/tests/test_lanzamientos.py`, citado por `AGENTS.md`, solo se comprobó que existe: no tiene relación con la petición.
- `docs/auditoria-entregable.md`.
- Plantilla y agentes: `.claude/agents/lector-suspense.md`, `.claude/agents/continuista.md` y el listado de `.claude/agents/`; `.claude/hooks/denegar-escritura-estado.py` (líneas 1–40, y búsqueda de `SALIDAS` y `ROLES`).
- Código: `backend/novela/dominio/qa.py`, `backend/novela/slices/checkpoint/cmd.py`, `backend/novela/plataforma/langfuse.py`, `backend/tests/test_contratos.py`, `backend/config/recipes.yaml`, `backend/config/default.yaml`, `backend/novela/slices/briefing/recipes.py`, fragmentos de `backend/novela/dominio/estado.py` y `backend/novela/dominio/artefactos.py`, y búsquedas en `backend/novela/dominio/ids.py`, `config.py` y `slices/briefing/assemble.py` y `cmd.py`.
- `docs/implementation-plans/0002-verificacion/fase-4-tension-y-secreto-por-acto.md` (línea de `test_subagentes`, por búsqueda).

**Ficheros esperados que no existían**

- Ninguno. `CLAUDE.md` y `AGENTS.md` existen, y todos los enlaces que se siguieron resuelven. `docs/rubrica.md` y `docs/revision-humana.md` no existen, pero son los ficheros que esta spec propone crear.

**Specs anteriores revisadas y solapamientos**

- `0001-backend-cli-estado-y-api.md` (implementada), `0003-contencion-y-bucle-en-claude.md` (implementada), `0004/spec.md` (aceptada), `0006/spec.md` y `0008/spec.md` (Propuesta): revisadas por título y estado. La 0001 fija `checkpoint` y el `ScoreSink`; la 0003, los roles, `CONTRATO` y el hook; la 0006, la dedicatoria fuera de los modelos.
- `0002-verificacion-a-escala-de-novela.md` (aceptada, sin implementar): revisada por búsqueda. Se solapa en la calibración del juez (RF-25, RF-26) y en el nombre `juez` denegado en su plan (D2); añade `sonda` y `novela gate`.
- `0005/spec.md` y `0005/decisions.md` (Propuesta): revisados §1–§9 y D2, D11 y D16. Esta spec consume `Brief` y su criterio de privacidad (D13, D17, D21).
- `0007/spec.md` (Propuesta): RF-43, id de score con versión (D15).
- `0009/spec.md` (Propuesta, con código a medio implementar): §1–§4. Se solapa en `checkpoint` (`vp_schema`, orden de emisión) y en la personalización (`vp_cobertura` mide presencia; esta spec, naturalidad).
- `0010/spec.md` (Propuesta): §1–§3. Añade otro revisor (`revisor-visual`) y toca `novela-continuar.md` y `checkpoint/cmd.py`.
- Contradicción registrada, no resuelta: `docs/architecture.md` §2.2 y `default.yaml` (`sonnet` para los revisores) frente a `CONTRATO` y los frontmatter (`haiku`) (D3).

**Instrucciones encontradas en el contexto que se ignoraron**

- Ninguna dirigida a este agente. Las instrucciones de rol de `CLAUDE.md` («Eres el orquestador…») son para la sesión del harness y se trataron como contexto.
