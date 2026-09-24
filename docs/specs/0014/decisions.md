# Decisiones — Spec 0014

## D1 — Formato de los briefs de prueba
- **Pregunta original (P1):** ¿Qué es exactamente un brief de prueba? ¿Solo `brief.json`, las entradas del cliente para pasar por la entrevista, o las dos cosas?
- **Alternativas consideradas:** (a) solo `evals/briefs/NN.json` como `Brief`; (b) solo las entradas (`respuesta` y `texto_libre`), para pasarlas por el `entrevistador`; (c) `NN.json` como `Brief` más los cuerpos de sus entradas en `evals/briefs/NN/ent-MM.md`.
- **Decisión:** (c).
- **Justificación:** La petición pide `evals/briefs/01..05.json` validados contra el schema del brief, lo que descarta (b). `Brief.entradas` es una lista de `EntradaMeta` con el sha256 del cuerpo de cada entrada, y cada valor lleva una `Fuente` con cita literal. Sin los cuerpos, ni el sha ni la procedencia se pueden comprobar, y la «inyección en texto libre» no tendría texto libre en el que vivir.
- **Fuente:** Petición del usuario; `backend/novela/dominio/brief.py` (`Brief`, `EntradaMeta`, `Fuente`)
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-01), § 7 (CA-01), § 8.2, § 8.3

## D2 — Catálogo de casos separado del brief
- **Pregunta original (P2):** ¿Dónde se declaran la categoría del caso (base, adversarial o temporal), su slug y los datos que permiten comprobarlo?
- **Alternativas consideradas:** (a) campos adicionales dentro de cada `NN.json`; (b) convención de nombres de fichero; (c) un catálogo `evals/casos.json` con su propio modelo.
- **Decisión:** (c), con el modelo `CatalogoEval`: cinco casos, ids `01` a `05` y slugs `eval-NN`.
- **Justificación:** `Brief` no tiene campos para metadatos de evaluación, y añadírselos cambiaría el contrato de la spec 0005 solo para las pruebas. Con la convención de nombres, la comprobación mecánica de los casos adversarial y temporal no tendría dónde guardar sus datos.
- **Fuente:** `backend/novela/dominio/brief.py`; `docs/validators.md` § 3.1 (ningún dato cruza sin modelo de dominio)
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-02), § 7 (CA-02), § 8.3

## D3 — Comprobación mecánica del caso adversarial
- **Pregunta original (P3):** ¿Cómo comprueba un test que un brief es adversarial, y cómo se mide si la inyección tuvo efecto?
- **Alternativas consideradas:** (a) solo la etiqueta `adversarial`; (b) una inyección que casa `PATRONES` y que la fase de brief bloquea; (c) una carga literal en una entrada `texto_libre`, citada por un recuerdo, que evade `PATRONES` y lleva una cadena señal para contar en los capítulos si se obedeció.
- **Decisión:** (c). `inyeccion {cita, senal}`; el test exige que la cita sea literal, que esté en un recuerdo, que contenga la señal y que `marcar` no la marque. `informe` cuenta los capítulos que contienen la señal.
- **Justificación:** La petición pide inyección en texto libre. El caso (b) ya está cubierto por `carta-inyectada.md` en la fase de brief y nunca llegaría a una novela: `brief validar` lo rechaza (`cita_en_fragmento_marcado`). Lo que no se ha medido es qué pasa cuando una carga pasa ese filtro y llega a `idea_semilla` y al `arquitecto`. La señal convierte «obedeció» en un conteo determinista.
- **Fuente:** Petición del usuario; `docs/validators.md` § 4.9 punto 2; `backend/novela/slices/brief/entradas.py` (`PATRONES`, `marcar`); `backend/novela/dominio/brief.py::idea_semilla`
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-03, RF-11), § 7 (CA-03, CA-12), § 8.3, § 8.4, § 9

## D4 — Forma de la incoherencia temporal
- **Pregunta original (P4):** ¿Qué incoherencia temporal lleva el brief y cómo se comprueba sin un modelo?
- **Alternativas consideradas:** (a) dos recuerdos con fechas incompatibles, en texto libre; (b) un recuerdo que implica una edad mayor que la edad declarada del destinatario, con `edad_implicada` declarada en el catálogo; (c) solo la etiqueta `temporal`.
- **Decisión:** (b). `conflicto_temporal {cita, edad_implicada}`, con `edad_implicada > destinatario.edad.valor`.
- **Justificación:** La edad es el único dato temporal estructurado del brief, así que la contradicción se puede afirmar con una comparación de enteros. Los gates del brief no la detectan (solo cruzan edad con género y tono), por lo que el caso llega a la fase de novela y mide al `continuista` (`contradiccion_temporal`) y, en el futuro, a la 0012. Ninguna documentación fija la forma de la incoherencia.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** § 5 (RF-04, RF-11), § 7 (CA-04, CA-12), § 8.3, § 11

## D5 — Los briefs pasan los gates del brief
- **Pregunta original (P5):** ¿Basta con que el brief valide contra el esquema, o tiene que ser un brief que `novela brief validar` habría aceptado?
- **Alternativas consideradas:** (a) solo esquema; (b) esquema y los cuatro gates de `slices/brief/gates.py` contra sus entradas.
- **Decisión:** (b), en el test y otra vez en `sembrar`.
- **Justificación:** Un brief que la fase real rechazaría no es representativo de lo que llega a la novela, y el caso adversarial perdería sentido (D3). Los gates son funciones puras ya probadas, así que reutilizarlos no cuesta nada y evita que `sembrar` sea una puerta trasera a la validación del brief.
- **Fuente:** `docs/architecture.md` § 8 (orden y contenido de `novela brief validar`); `docs/specs/0005/spec.md`
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-05, RF-08, RF-09), § 7 (CA-05, CA-09)

## D6 — Criterio de datos ficticios
- **Pregunta original (P6):** ¿Cómo se verifica que los briefs no contienen datos personales reales?
- **Alternativas consideradas:** (a) solo revisión manual; (b) una declaración `ficticio: true`; (c) apellido `Ficticio`/`Ficticia` obligatorio y expresiones que rechazan correo, teléfono y DNI/NIE.
- **Decisión:** (c).
- **Justificación:** La petición prohíbe datos personales reales. La convención ya existe en los fixtures del repositorio, y una comprobación mecánica es mejor que una declaración. La realidad de un nombre no es decidible; la marca en el apellido lo hace evidente para cualquier lector.
- **Fuente:** Petición del usuario; `backend/tests/fixtures/brief/brief-completo.json` (nombre con apellido «Ficticia»)
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-07), § 6 (RNF-04), § 7 (CA-07), § 11

## D7 — Siembra del workspace sin entrevista
- **Pregunta original (P7):** ¿Cómo llega un brief de `evals/` a un workspace del que `novela nueva --brief` pueda partir?
- **Alternativas consideradas:** (a) pasar las entradas por la fase de brief real, con `entrevistador`; (b) copiar los ficheros a mano en `novelas/<slug>/brief/`; (c) un subcomando del CLI que crea el workspace con los mismos ficheros que la fase real, sin `borrador.json`, tras repetir los gates.
- **Decisión:** (c), `novela eval sembrar`.
- **Justificación:** (b) está prohibido: `novelas/` nunca se edita a mano. (a) gasta cuota y mete la variabilidad del `entrevistador` en una evaluación de la fase de novela. Además, la fase de brief exige una sesión sin `local` (validators § 4.9 punto 5), distinta de la del bucle. La regla del repositorio es que, si hace falta escribir, se añade un subcomando al CLI.
- **Fuente:** `AGENTS.md` § Separación repo / workspace y § Monorepo; `docs/architecture.md` § 4 y § 8
- **Confianza:** media
- **Secciones de la spec afectadas:** § 3.2, § 5 (RF-08, RF-09), § 7 (CA-08, CA-09), § 8.4

## D8 — Nombre y forma de los subcomandos
- **Pregunta original (P8):** ¿`novela eval-informe` como orden suelta, o una subaplicación?
- **Alternativas consideradas:** (a) `novela eval-informe` y `novela eval-sembrar`; (b) subaplicación `novela eval informe|sembrar`.
- **Decisión:** (b), registrada en `cli.py` como `brief`, en el slice `slices/evaluacion/`.
- **Justificación:** La petición da el nombre solo como ejemplo («p. ej.»). El CLI ya agrupa en `novela brief …` las órdenes de una misma fase, y un slice por caso de uso es la regla de estructura.
- **Fuente:** Petición del usuario; `backend/novela/cli.py`; `docs/architecture.md` § 3.0
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-08, RF-10), § 8.2, § 8.4

## D9 — Fuente de los números de la tabla
- **Pregunta original (P9):** ¿De dónde salen los «pasó/falló» de cada validador, si los informes finales casi siempre aprueban?
- **Alternativas consideradas:** (a) solo `qa/NN-validacion.json` final; (b) leer los scores de Langfuse; (c) intentos fallidos desde `harness.log` más los informes finales de `qa/`, `qa/auditoria.json` y los manifiestos.
- **Decisión:** (c), con las reglas de conteo de § 8.4.
- **Justificación:** Los binarios del checkpoint miden el artefacto final, que la custodia obliga a que esté aprobado, y `qa/` se reescribe en cada intento. La línea `validar NN -> 1 · k hallazgos: <tipos>` es la única huella de los fallos intermedios, y el procedimiento ya cuenta intentos con esas subcadenas. (b) exigiría red y claves en un test y en un subcomando que debe ser determinista.
- **Fuente:** Petición del usuario («lea qa/ y estado de cada workspace»); `docs/validators.md` § 3.10 y § 4.2; `backend/novela/slices/validacion/cmd.py`; `.claude/commands/novela-continuar.md` § Cuenta de intentos
- **Confianza:** media
- **Secciones de la spec afectadas:** § 2, § 5 (RF-10, RF-11), § 7 (CA-10, CA-11), § 8.4, § 11

## D10 — Formato de celda y regla de pasa/falla
- **Pregunta original (P10):** ¿Qué significa que un validador «pasó» para un brief, y cómo se escribe la celda?
- **Alternativas consideradas:** (a) solo el estado final; (b) `pasa` si ningún intento falló en ningún capítulo, `falla c/t (n)` en otro caso y `no evaluado` sin rastro; (c) un umbral de fallos por capítulo.
- **Decisión:** (b).
- **Justificación:** La petición pide «qué validadores pasaron y cuáles fallaron, con números». (b) da las dos cosas sin inventar un umbral que nadie ha calibrado, y `c/t (n)` separa si el fallo es extendido o recurrente. Ninguna documentación define la regla.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** § 5 (RF-10, RF-13), § 7 (CA-10 a CA-14), § 8.4

## D11 — Las líneas del hook no cuentan como intento
- **Pregunta original (P11):** ¿Las líneas `validar-hook NN -> 1` del hook `PostToolUse` cuentan como intentos fallidos?
- **Alternativas consideradas:** (a) sí; (b) no, solo `validar NN -> `.
- **Decisión:** (b).
- **Justificación:** La documentación lo dice de forma explícita: `--origen hook` «no gasta intentos del procedimiento, cuyos pasos 3 y 5 siguen siendo el gate que cuenta». Contarlas duplicaría la misma validación del mismo texto.
- **Fuente:** `docs/architecture.md` § 7.1 (segundo hook, `PostToolUse`); `backend/novela/slices/validacion/cmd.py`
- **Confianza:** alta
- **Secciones de la spec afectadas:** § 5 (RF-10), § 7 (CA-10), § 8.4

## D12 — `vp_cobertura` sin reimplementar
- **Pregunta original (P12):** Con briefs, `vp_cobertura` es el validador más relevante. ¿Lo calcula el informe?
- **Alternativas consideradas:** (a) calcularlo en `informe` a partir del brief y de `libro_de_hechos`; (b) mostrarlo como `no evaluado` mientras la spec 0009 no persista su valor.
- **Decisión:** (b).
- **Justificación:** `vp_cobertura` pertenece a la 0009, y una segunda implementación divergiría de la primera. `docs/validators.md` § 3.10 dice que hoy no se evalúa y que ningún workspace lo tiene. El informe mide lo que el sistema hace, no lo completa.
- **Fuente:** `docs/validators.md` § 3.10 (fila `vp_cobertura`) y § 2; `docs/specs/0009/spec.md` § 1
- **Confianza:** media
- **Secciones de la spec afectadas:** § 2, § 3.2, § 5 (RF-11), § 7 (CA-12), § 10

## D13 — Salida del informe y solo lectura
- **Pregunta original (P13):** ¿El informe escribe `docs/evals.md` directamente, deja un fichero en el workspace o imprime?
- **Alternativas consideradas:** (a) escribe en `docs/`; (b) escribe un resultado en cada workspace; (c) imprime Markdown, o `InformeEval` con `--json`, y no escribe nada.
- **Decisión:** (c).
- **Justificación:** La petición pide un script determinista que produzca la tabla. Los documentos de `docs/` se cambian en un commit revisado, no desde un subcomando que corre sobre datos locales no versionados. Escribir en el workspace alteraría lo que se mide y no aporta nada: la salida es reproducible desde los datos. Imprimir hace el test directo sobre stdout.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: modificar documentación
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-15, RF-17), § 7 (CA-16, CA-18), § 8.4

## D14 — Lock durante la lectura
- **Pregunta original (P14):** ¿El informe toma el lock del workspace, y qué hace si está ocupado?
- **Alternativas consideradas:** (a) no tomarlo; (b) tomarlo y salir con 3 si está ocupado; (c) tomarlo y marcar la fila `en curso`.
- **Decisión:** (b), un workspace cada vez.
- **Justificación:** Un proceso por workspace es un invariante, y leer mientras el bucle escribe daría una fila inconsistente. El código 3 ya significa «lock ocupado» en todo el CLI. `novela auditar`, que también solo lee, toma el lock.
- **Fuente:** `AGENTS.md` § Invariantes (8); `.claude/commands/novela-continuar.md` § Códigos de salida del CLI; `backend/novela/slices/auditoria/cmd.py`
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-14), § 7 (CA-15), § 8.4

## D15 — Atribución de la versión del prompt
- **Pregunta original (P15):** ¿Qué se muestra como «versión de prompt», y qué pasa con árboles sucios o shas mezclados?
- **Alternativas consideradas:** (a) solo `sha_commit`; (b) `sha_commit` con las marcas `(sucio)` y `(mezclado)`, más `hashes_claude` en `--json` y en `docs/tuning.md`; (c) versiones de prompt en Langfuse Prompt Management.
- **Decisión:** (b).
- **Justificación:** La petición dice que el manifiesto registra el sha que sirve de versión. La arquitectura descarta Prompt Management porque sería una segunda fuente de verdad. `run.py` advierte que el sha solo identifica el prompt con el árbol limpio, y por eso existen `sucio` y `hashes_claude`.
- **Fuente:** Petición del usuario; `docs/architecture.md` § 10.4; `backend/novela/plataforma/run.py` (comentario de `_VIGILADO` y `procedencia`)
- **Confianza:** alta
- **Secciones de la spec afectadas:** § 5 (RF-12, RF-18, RF-19), § 6 (RNF-07), § 7 (CA-13, CA-19, CA-20)

## D16 — Diseño de la iteración de tuning
- **Pregunta original (P16):** ¿Qué prompt se ajusta, sobre qué novelas se mide el antes y el después, y con cuántos capítulos?
- **Alternativas consideradas:** (a) repetir las cinco novelas completas tras el cambio; (b) una novela de humo de 3 capítulos con el brief de la celda peor, comparada con los capítulos 1 a 3 de la evaluación completa, y la celda objetivo elegida por una regla fija; (c) elegir el prompt a criterio del operador.
- **Decisión:** (b), con la regla de § 8.5 paso 5 y el slug `eval-NN-t1`.
- **Justificación:** El repositorio fija que un cambio de prompt se valida con una novela de humo de 3 capítulos comparando scores. Usar los capítulos 1 a 3 del baseline como «antes» no gasta cuota nueva y compara lo mismo con lo mismo. Una regla fija evita elegir el objetivo después de ver el resultado.
- **Fuente:** `AGENTS.md` § Proceso: generar código («se valida con una novela de humo de 3 capítulos comparando scores»); `CLAUDE.md` § Subagentes
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-19), § 7 (CA-20), § 8.5, § 11

## D17 — Métricas comparadas en el tuning
- **Pregunta original (P17):** ¿Qué «scores» se comparan antes y después?
- **Alternativas consideradas:** (a) solo los scores de Langfuse, consultados a mano; (b) las dos tablas de `novela eval informe --hasta 3`, cuyas medias de `tension`, `fair_play` y `coherencia` salen de la misma fuente que esos scores.
- **Decisión:** (b).
- **Justificación:** Los scores de `checkpoint` se calculan desde `qa/NN-suspense.json` y los veredictos, que el informe lee directamente. Así la comparación es reproducible sin red. Las APIs de lectura legadas de Langfuse responden 410 en organizaciones nuevas.
- **Fuente:** `docs/architecture.md` § 10.5 y § 10.1; `backend/novela/slices/checkpoint/cmd.py::calcular_scores`
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-11, RF-19), § 8.5

## D18 — Ubicación de los modelos nuevos
- **Pregunta original (P18):** ¿Dónde viven los modelos del catálogo y del informe, y llevan esquema versionado?
- **Alternativas consideradas:** (a) dentro del slice; (b) en `backend/novela/dominio/evaluacion.py`, con `eval-casos.schema.json` y `eval-informe.schema.json` en `backend/schemas/`.
- **Decisión:** (b).
- **Justificación:** «Ningún dato cruza de disco o de agente al código sin pasar por un modelo de `backend/novela/dominio/`» es una regla dura. Cambiar un modelo exige regenerar esquemas, actualizar `definitions.md` y ajustar el test de contrato en el mismo commit.
- **Fuente:** `docs/validators.md` § 3.1; `AGENTS.md` § Proceso: generar código
- **Confianza:** alta
- **Secciones de la spec afectadas:** § 5 (RF-15, RF-20), § 8.2, § 8.3, § 12 (T-01)

## D19 — Documentación de referencia que se actualiza
- **Pregunta original (P19):** ¿Qué documentos se tocan además de `docs/evals.md` y `docs/tuning.md`? ¿También `AGENTS.md`?
- **Alternativas consideradas:** (a) también la lista de CLI de `AGENTS.md`; (b) solo `docs/architecture.md` § 3.1 y § 8, `docs/definitions.md` y `docs/validators.md` § 4.2.
- **Decisión:** (b).
- **Justificación:** La documentación de referencia se actualiza en el mismo commit que el código. `AGENTS.md` se carga en cada sesión y subagente, no se amplía sin necesidad, y el orquestador nunca usa `novela eval`.
- **Fuente:** `AGENTS.md` § Proceso: modificar documentación y § Nunca
- **Confianza:** media
- **Secciones de la spec afectadas:** § 5 (RF-20), § 7 (CA-21), § 8.2, § 12 (T-06)

## D20 — Cómo se lanzan las novelas de evaluación
- **Pregunta original (P20):** ¿Se amplía `novela producir` o el panel para aceptar un brief, o se usa el bucle documentado?
- **Alternativas consideradas:** (a) añadir `--brief` a `novela producir`; (b) el bucle desatendido de `AGENTS.md`, con una sesión previa `/novela-nueva <slug> --brief`.
- **Decisión:** (b).
- **Justificación:** La petición dice que las novelas las lanza una persona con el bucle desatendido documentado. `producir` solo admite `--idea`, y ampliarlo toca el panel y las guardas de `/lanzamientos`, fuera del alcance de una evaluación.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: ejecución; `backend/novela/slices/producir/cmd.py`
- **Confianza:** media
- **Secciones de la spec afectadas:** § 3.2, § 5 (RF-18), § 8.5

## D21 — Tests estructurales de los documentos de resultados
- **Pregunta original (P21):** ¿Cómo se verifica que `docs/evals.md` y `docs/tuning.md` llevan números reales, si no hay test que pueda generar novelas?
- **Alternativas consideradas:** (a) solo revisión humana; (b) tests que comprueban estructura, filas, shas, marcas `(sucio)`/`(mezclado)` y ausencia de marcadores pendientes, añadidos en el mismo commit que cada documento.
- **Decisión:** (b).
- **Justificación:** La petición pide «documentos en docs/ con números reales» como verificación, y un test documental hace cumplir la forma aunque no pueda reproducir el contenido. Añadirlo junto al documento respeta «no se commitea en rojo». Ninguna documentación del repositorio fija este método.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** § 5 (RF-18, RF-19), § 7 (CA-19, CA-20), § 13

## D22 — Errores de identificación de workspaces en el informe
- **Pregunta original (P22):** ¿Qué hace el informe con un workspace que falta o que no corresponde a ningún caso?
- **Alternativas consideradas:** (a) siempre fila `no generado`; (b) fila `no generado` para los slugs del catálogo sin workspace, y salida 4 para un slug explícito que no existe o cuyo brief no es ningún caso; (c) ignorarlos en silencio.
- **Decisión:** (b). El caso se identifica por igualdad de modelo del `brief.json`, así que `eval-NN-t1` cuenta como caso `NN`.
- **Justificación:** Sin slugs, el informe describe el estado de la evaluación, y un caso pendiente es información. Un slug explícito es una petición del operador, y una errata no debe producir una tabla que parezca válida. Ninguna documentación lo fija.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** § 5 (RF-13, RF-14), § 7 (CA-14, CA-15), § 9

## Contexto consultado

**Ficheros leídos:**

- `CLAUDE.md` y `AGENTS.md` (raíz)
- Enlazados desde ellos:
  - `docs/architecture.md`, completo
  - `docs/validators.md`: § 1 a § 4.2 y § 4.9, más el índice de encabezados; el fichero pasa de 700 KB
  - `docs/definitions.md`: índice de encabezados y § 6
  - `docs/domain-knowledge.md`: solo el índice de encabezados
  - `.claude/commands/novela-continuar.md`: códigos, reglas de lectura y § Cuenta de intentos
- Otros documentos y comandos:
  - `.claude/commands/novela-nueva.md`
  - `docs/auditoria-entregable.md`
- Código:
  - `backend/novela/cli.py` y `backend/novela/dominio/brief.py`, `validadores.py` y `qa.py`
  - `backend/novela/plataforma/run.py`
  - `backend/novela/slices/checkpoint/cmd.py`, `validacion/cmd.py`, `auditoria/cmd.py`, `nueva/cmd.py` y `producir/cmd.py`
  - Fragmentos de `backend/novela/slices/brief/entradas.py`, de `backend/novela/dominio/artefactos.py` y de las firmas de `backend/novela/slices/brief/*.py`
- Fixtures y esquemas:
  - `backend/tests/fixtures/brief/brief-completo.json`
  - Listados de `backend/tests/**` y `backend/schemas/`
- Plantillas: `spec-template.md` y `decisions-template.md` del plugin `sdd-spec-writer` 1.1.0.

**Ficheros esperados que no existían:**

- `evals/`: no existe, como indica la petición.
- `docs/evals.md` y `docs/tuning.md`: no existen.
- Ningún enlace de `CLAUDE.md` ni de `AGENTS.md` estaba roto.

**Specs anteriores revisadas y solapamientos:**

- 0001, 0002 y 0003, en formato antiguo `docs/specs/NNNN-<slug>.md`: solo título y estado. La 0002 comparte con esta el control negativo de revisores (`docs/validators.md` § 4.11), otra evaluación con fixtures de capítulo. La 0003 aporta el canario, que prueba la contención y no la calidad.
- 0004 (panel): sin solapamiento; no se amplía el lanzamiento desde el panel.
- 0005 (fase de brief, aceptada): se consumen `Brief`, `EntradaMeta` y los gates y fixtures del brief, sin cambiarlos.
- 0006 (PDF de regalo): sin solapamiento.
- 0007 (regeneración y versiones): sin solapamiento.
- 0008 (hook `PostToolUse`): sus líneas `validar-hook` se excluyen del conteo (D11).
- 0009 (validadores programáticos, Propuesta): la tabla recorre su catálogo, y `vp_cobertura` queda `no evaluado` (D12).
- 0010 (revisión visual): sin solapamiento.
- 0011 (juez narrativo, Propuesta): sus scores quedan fuera de la tabla.
- 0012 (Lean temporal, Propuesta): el brief temporal es su caso natural; su validador aparecerá como columna si entra en el catálogo.
- 0013 (TLA+): sin solapamiento.
- No se detectan contradicciones con specs anteriores.

**Instrucciones encontradas en el contexto que se ignoraron:**

- Ninguna dirigida al redactor de specs.
- `CLAUDE.md` contiene instrucciones para la sesión orquestadora del harness (no abrir capítulos, delegar en subagentes), que no aplican a la redacción de una spec. Se tomaron como contexto.
