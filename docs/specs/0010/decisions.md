# Decisiones — Spec 0010

## D1 — Qué abre el navegador: una previa HTML por secciones
- **Pregunta original (P1):** La petición pide que el navegador «abre la novela, navega capítulos y verifica índice, ficha y portada». ¿Qué artefacto abre?
- **Alternativas consideradas:** (a) una previa HTML multipágina que genera el CLI desde el mismo `Libro` y la misma `Ficha` del PDF de la spec 0006; (b) `export/novela.pdf` en el visor de PDF de Chromium; (c) el epub descomprimido; (d) el lector del panel de `frontend/`; (e) un formato de exportación `--formato html` entregable.
- **Decisión:** (a). Una página por sección (`portada`, `indice`, `capitulo-KK`, `ficha`), con markdown inerte, CSP restrictiva y la fuente de la 0006 embebida.
- **Justificación:** (d) queda fuera por la petición («el lector web es el panel de frontend/ (spec 0004, fuera de este alcance)»). (c) no tiene portada ni ficha (0006 §3.2: «El epub sigue sin portada ni ficha»). Para (b) se supone, sin respaldo en el repositorio, que el visor de PDF de Chromium no expone al árbol de accesibilidad ni a los clics de Playwright el índice ni los enlaces internos del documento, y que en modo headless no se muestra. (e) añade un entregable que el ADR de la 0006 no contempla. (a) reutiliza las estructuras de la 0006 (§8.3 y §8.4), así que lo que se inspecciona tiene el mismo contenido y el mismo orden que el PDF. El precio es que no se inspeccionan los defectos propios de la maquetación PDF, un riesgo que queda registrado en §11.
- **Fuente:** Petición del usuario; `docs/specs/0006/spec.md` § 3.2 y § 8.3–8.4; Supuesto (comportamiento del visor de PDF en headless)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 1, 3.2, 5 (RF-07, RF-09), 8.1, 8.2, 11

## D2 — Punto del bucle: por capítulo, entre el gate de revisión y el cronista
- **Pregunta original (P2):** La petición admite el paso «en `.claude/commands/novela-continuar.md` o en el gate de publicación». ¿Dónde va?
- **Alternativas consideradas:** (a) en cada capítulo, después del gate de revisión (paso 6) y antes del `cronista` (paso 7); (b) una sola vez al final, en `/novela-auditar`, tras exportar; (c) en cada capítulo, entre `aplicar-delta` y `checkpoint`.
- **Decisión:** (a).
- **Justificación:** la petición exige que un error «vuelva al writer». Con (b), el capítulo ya está cerrado y reescribirlo rompe el invariante 7 (`AGENTS.md` § Invariantes). Con (c), el delta ya se ha aplicado, y reintentar el `escritor` dejaría el estado por delante del texto, «la forma más cara de corromper una novela» (`docs/architecture.md` §2.1). El nombre de salida pedido, `qa/NN-visual.json`, es también por capítulo. Consecuencia: la ficha del capítulo en curso se construye sin delta, con `apply.apariciones` sobre el frontmatter y la ficha de plan (RF-11).
- **Fuente:** Petición del usuario; `AGENTS.md` § Invariantes (7); `docs/architecture.md` §2.1 («El `cronista` queda fuera del abanico…»)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 5 (RF-11, RF-24, RF-25), 8.1, 8.4, 8.5

## D3 — Quién decide: `novela gate <slug> <cap> visual`, con el contrato del ADR 0002
- **Pregunta original (P3):** ¿Quién lee `qa/NN-visual.json` y decide volver al rol? ¿La sesión, como hoy con el gate de revisión, o el CLI? ¿Y cómo encaja con el ADR 0002, que avisa contra un gate que elige qué agente reintentar?
- **Alternativas consideradas:** (a) un subcomando `novela gate <slug> <cap> visual` con los códigos 0, 1 y 5 del ADR 0002, donde el 1 siempre significa reintentar al `escritor` y todo lo demás es intervención con el rol escrito en `intervencion.md`; (b) que la sesión lea el veredicto como en el paso 6; (c) un gate con un código por rol.
- **Decisión:** (a).
- **Justificación:** la petición pide «test del gate que lee qa/NN-visual.json y devuelve al rol», y eso exige código. El ADR 0002 ya decidió que los gates y la cuenta los lleva el CLI, por el fallo F-31 de contar en la sesión. (c) sería el gate «planificando», el caso que el ADR marca para reabrirse. Con (a), el gate solo decide avanzar, reintentar o intervenir. El agente del reintento está fijado en el procedimiento, y el «rol correspondiente» de la petición queda registrado en `intervencion.md` para los orígenes que el bucle no puede corregir.
- **Fuente:** Petición del usuario; `docs/adr/0002-los-gates-los-decide-el-cli.md` § Decisión y § Cuándo reabrirla; `docs/specs/0002-verificacion-a-escala-de-novela.md` § RF-19
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1, 3.2, 5 (RF-17 a RF-23), 8.4, 10

## D4 — Vocabulario de hallazgos y rol por origen del dato
- **Pregunta original (P4):** ¿Qué tipos de hallazgo visual hay y cómo se atribuye cada uno a un rol?
- **Alternativas consideradas:** (a) seis tipos cerrados, un campo `seccion`, y el origen determinado por reglas fijas (primero el tipo, después la sección y el capítulo), según de dónde sale cada dato de la previa; (b) que el agente escriba el rol responsable; (c) todos los fallos al `escritor`.
- **Decisión:** (a). `enlace_roto`, `seccion_ausente` y `contenido_no_coincide` se atribuyen a `harness`, porque lo esperado y las páginas salen de las mismas entradas y una discrepancia solo puede venir del generador. En el resto de tipos, el capítulo en curso y su título se atribuyen al `escritor`; los capítulos cerrados, a `escritor (capítulo cerrado)`, que es intervención; la ficha, al `arquitecto`; y la portada, al `operador`. Precedencia entre orígenes: capítulo cerrado, `arquitecto`, `operador`, `harness`.
- **Justificación:** `docs/validators.md` §4.6 pide que un revisor nuevo verifique contra un dato, y la procedencia de cada dato ya está fijada en `docs/architecture.md` §7.5: el `escritor` escribe `capitulos/NN.md` y su frontmatter, el `arquitecto` escribe `canon/personajes/*.md` y `canon/mundo.md` (de donde la 0006 saca la ficha, RF-26), y el título y la dedicatoria llegan por el operador y el brief (0006 RF-08 y RF-11). (b) deja la decisión de parar en manos de un modelo. (c) reintenta en balde cuando el defecto no está en el capítulo. El canon lo cambia solo el orquestador con autorización (`AGENTS.md` § Las cuatro ramas), así que un fallo de la ficha no se reintenta: se interviene. La precedencia es un supuesto de orden: primero lo que obliga a decidir sobre la trama (capítulo cerrado), después el canon, la entrega y el código.
- **Fuente:** `docs/validators.md` §4.6; `docs/architecture.md` §7.5; `AGENTS.md` § Las cuatro ramas de contexto e § Invariantes (7); `docs/specs/0006/spec.md` § RF-08, RF-11, RF-26; Supuesto (precedencia)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-08, RF-16, RF-19, RF-20), 8.4, 9

## D5 — Informe propio: `InformeVisual` y `qa-visual.schema.json`
- **Pregunta original (P5):** ¿Se reutiliza `InformeQA` y `qa-informe.schema.json`, o hace falta un modelo propio?
- **Alternativas consideradas:** (a) un modelo nuevo, `InformeVisual`, en `dominio/qa.py`, con `seccion`, `capitulo` por hallazgo, `previa` e `inspeccion`, y su propio esquema generado; (b) ampliar `InformeQA` con campos opcionales y tipos nuevos en `TipoHallazgo`; (c) texto libre en `ubicacion`.
- **Decisión:** (a).
- **Justificación:** la petición nombra «schema en backend/schemas/» para `qa/NN-visual.json`. El gate necesita `seccion` y `capitulo` estructurados para decidir sin interpretar texto: `docs/architecture.md` §7.3 exige vocabulario cerrado, porque «un hallazgo con tipo libre es uno que el reintento no sabe leer» (docstring de `dominio/qa.py`). (b) cambiaría `qa-informe.schema.json`, que leen los tres revisores y la 0009, y mezclaría campos que solo tienen sentido para un productor. `inspeccion` es el registro del resultado que pide la petición y la evidencia de CC-04. Vive en el mismo módulo para mantener una sola ontología (`AGENTS.md` § Monorepo).
- **Fuente:** Petición del usuario; `docs/architecture.md` §7.3; `backend/novela/dominio/qa.py` (docstring)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-15, RF-16), 6 (RNF-11), 8.3

## D6 — Herramientas mínimas del agente
- **Pregunta original (P6):** ¿Qué herramientas lleva el `revisor-visual`?
- **Alternativas consideradas:** (a) `Read`, `Write` y seis herramientas de Playwright MCP: `browser_navigate`, `browser_navigate_back`, `browser_snapshot`, `browser_click`, `browser_take_screenshot` y `browser_close`; (b) todas las del servidor (`mcp__playwright`); (c) sin capturas, solo el árbol de accesibilidad.
- **Decisión:** (a).
- **Justificación:** la petición pide «tools mínimas», sin `Skill` y sin escritura fuera de su salida. Con `docs/architecture.md` §7.4, cada ausencia hace mecánica una regla. Se excluyen las herramientas que ejecutan código en la página (`browser_evaluate` y la de ejecutar código), las que suben ficheros, las que escriben texto o rellenan formularios, las que instalan navegadores y las de pestañas o red: ninguna hace falta para mirar una página estática. (c) no ve glifos ausentes ni solapamientos, que solo se aprecian en la imagen. Los nombres exactos son un supuesto sobre la versión que se fije, y se comprueban en T-01.
- **Fuente:** Petición del usuario; `docs/architecture.md` §7.4; Supuesto (nombres de las herramientas de `@playwright/mcp`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-05, RF-28), 6 (RNF-01), 10

## D7 — Modelo del agente: sonnet
- **Pregunta original (P7):** ¿Qué `model` lleva el `revisor-visual`?
- **Alternativas consideradas:** (a) `sonnet`; (b) `haiku`, que es el que llevan hoy los revisores en `CONTRATO`; (c) `opus`.
- **Decisión:** (a).
- **Justificación:** `CLAUDE.md` § Subagentes dice «sonnet para los de revisión», y `docs/architecture.md` §2.2 asigna `sonnet` a los tres revisores. Hay una discrepancia: `backend/tests/test_contratos.py` (`CONTRATO`) y `docs/auditoria-entregable.md` registran `haiku` para `continuista`, `editor-estilo` y `lector-suspense`, cambiado a mano. Esta spec sigue la convención escrita y no toca los demás roles. Juzgar capturas e interpretar la maquetación es la tarea menos mecánica de la revisión.
- **Fuente:** `CLAUDE.md` § Subagentes; `docs/architecture.md` §2.2; `backend/tests/test_contratos.py` (`CONTRATO`); `docs/auditoria-entregable.md` § Recuento
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-05)

## D8 — Forma de `.mcp.json`
- **Pregunta original (P8):** ¿Qué lleva exactamente `.mcp.json`: versión, modo, perfil, carpeta de salida y lanzador en Windows?
- **Alternativas consideradas:** (a) un único servidor `playwright` con `@playwright/mcp` fijado a `X.Y.Z`, `--headless`, `--isolated`, Chromium, viewport de 1280×800 y `--output-dir .playwright-mcp` ignorado por git, lanzado con `cmd /c npx`; (b) `@latest`; (c) Chrome MCP (DevTools); (d) `npx` directo, sin `cmd /c`.
- **Decisión:** (a).
- **Justificación:** la petición nombra Playwright MCP en la raíz. Sin versión fijada no hay forma de atribuir un cambio de comportamiento, igual que con los prompts (`docs/architecture.md` §10.4), y una actualización silenciosa es la amenaza 6 de `docs/validators.md` §4.9. `--isolated` evita un perfil persistente en disco. `--output-dir` deja las capturas en una ruta conocida e ignorada. `.mcp.json` no lleva claves (`AGENTS.md` § Nunca). El bucle corre en Windows (`docs/architecture.md` §2.3 y §11.1), y la necesidad de `cmd /c` para `npx`, igual que los nombres de los flags, es un supuesto que se comprueba en T-01. Si `file://` exige un flag adicional, se añade entonces.
- **Fuente:** Petición del usuario; `docs/architecture.md` §2.3, §10.4, §11.1; `docs/validators.md` §4.9 (amenaza 6); `AGENTS.md` § Nunca; Supuesto (flags y `cmd /c`)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-01, RF-03), 8.4, 10

## D9 — Habilitación del servidor y permisos en `settings.json`
- **Pregunta original (P9):** ¿Dónde se habilita el servidor del proyecto y cómo se autorizan sus herramientas en `dontAsk`?
- **Alternativas consideradas:** (a) `enabledMcpjsonServers: ["playwright"]` y las seis herramientas en el `allow` de `.claude/settings.json`, versionado, ajustando `test_settings_de_claude`; (b) en `.claude/settings.local.json`; (c) `enableAllProjectMcpServers: true`.
- **Decisión:** (a).
- **Justificación:** `CLAUDE.md` § Claves y trazado limita `settings.local.json` a `enabledPlugins`, «nada más». El bucle corre con `--permission-mode dontAsk`, que deniega lo que no está en el `allow` (`.claude/commands/novela-continuar.md` § Códigos). (c) habilitaría cualquier servidor que se añadiera después sin revisarlo. `test_settings_de_claude` fija hoy las claves y el `allow` exactos, así que el test se amplía en el mismo commit. Que la habilitación funcione con `--setting-sources project,local` y `-p` es un supuesto de T-01.
- **Fuente:** `CLAUDE.md` § Claves y trazado; `.claude/commands/novela-continuar.md` § Códigos de salida del CLI; `backend/tests/test_contratos.py::test_settings_de_claude`; Supuesto (comportamiento de Claude Code)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-02), 10

## D10 — Contención de las llamadas MCP en el hook
- **Pregunta original (P10):** ¿Cómo se impide que otro rol o la sesión principal usen el navegador, y que el revisor navegue fuera de su previa?
- **Alternativas consideradas:** (a) ampliar el `matcher` del registro `PreToolUse` existente con `mcp__playwright__.*` y añadir al hook una regla: solo `revisor-visual`, solo las seis herramientas, sin `filename`, y `browser_navigate` solo a `file://` de su directorio de previa; (b) un segundo registro `PreToolUse` con otro script; (c) confiar en `tools` y en el `allow`.
- **Decisión:** (a).
- **Justificación:** los permisos valen para la sesión entera, no por subagente (`docs/architecture.md` §6.3), así que el `allow` también autoriza a la sesión principal. El hook distingue por `agent_type` (regla 3 y E-1 de la spec 0003). `test_settings_de_claude` exige un único registro `PreToolUse`, y la 0008 añade el suyo en `PostToolUse`, así que (b) choca con el contrato. La regla reutiliza `_normalizar`. `filename` se deniega porque dejaría escribir una captura en una ruta elegida por el modelo, que el hook no ve como escritura. `SALIDAS` gana la fila del rol sin fijar un número de roles (0005 D14). Que `PreToolUse` reciba las llamadas MCP de un subagente es un supuesto de T-01.
- **Fuente:** `docs/architecture.md` §6.3 y §7.1; `.claude/hooks/denegar-escritura-estado.py` (reglas 2, 3 y 5, `_CAMPO`); `backend/tests/test_contratos.py::test_settings_de_claude`; `docs/specs/0005/decisions.md` § D14; Supuesto (disparo del hook para MCP)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-26 a RF-28), 6 (RNF-02, RNF-08), 8.4, 10

## D11 — La dedicatoria no llega al revisor
- **Pregunta original (P11):** La portada contiene la dedicatoria, y la spec 0006 garantiza que no se envía a ningún modelo después del brief. ¿Cómo se inspecciona la portada sin romperlo?
- **Alternativas consideradas:** (a) sustituirla en la previa por `[dedicatoria: L líneas]`, que conserva la forma sin el texto; (b) mostrarla literal y aceptar que llegue al modelo y a la traza; (c) no inspeccionar la portada.
- **Decisión:** (a).
- **Justificación:** la spec 0006 fija en RF-15 y D16 que la dedicatoria no sale del libro, y en §11 declara «Esta spec no la envía a ningún modelo después del brief». (b) contradice esa garantía. (c) incumple la petición, que pide verificar la portada. La literalidad de la dedicatoria ya la comprueba sin modelo la 0006 (CA-11), así que el revisor solo necesita la presencia y la forma. Las líneas de `intervencion.md` tampoco llevan `descripcion` (RF-22).
- **Fuente:** `docs/specs/0006/spec.md` § RF-15, RF-16, CA-11 y § 11; Petición del usuario
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-10, RF-22), 6 (RNF-04)

## D12 — Score `visual`, fuera del catálogo de la 0009
- **Pregunta original (P12):** ¿Con qué nombre y valor va el score a Langfuse, y entra en el catálogo `VALIDADORES` de la spec 0009?
- **Alternativas consideradas:** (a) `visual`, calculado del veredicto (1, 0,5, 0) igual que `continuidad` y `estilo`, emitido por `checkpoint` con el formato de id vigente y fuera del catálogo; (b) `vp_visual` dentro de `VALIDADORES`; (c) una puntuación por sección.
- **Decisión:** (a).
- **Justificación:** `docs/architecture.md` §10.5 define `continuidad` y `estilo` como «veredicto (1, 0,5 o 0)», emitidos por `novela checkpoint`. El catálogo de la 0009 es de validadores programáticos (su O-01), con puntos `validar | checkpoint | auditar` y valor binario o fracción calculados por código (`backend/novela/dominio/validadores.py`), y el revisor es un agente (clase I). Meterlo ahí mezclaría las dos preguntas que separa `docs/validators.md` §1. El id sigue el formato de la 0009 (RF-17) y el versionado de la 0007 si existe. (c) multiplica los scores sin decisión asociada.
- **Fuente:** `docs/architecture.md` §10.5; `docs/specs/0009/spec.md` § O-01 y RF-17; `backend/novela/dominio/validadores.py`; `docs/validators.md` §1
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-29, RF-30), 6 (RNF-10)

## D13 — Presupuesto de contexto y límites de navegación
- **Pregunta original (P13):** Una previa con 24 capítulos cabe en disco, pero no en una invocación. ¿Qué límites se fijan?
- **Alternativas consideradas:** (a) páginas separadas por sección; briefing de 15.000 tokens como máximo; el revisor inspecciona portada, índice, ficha y el capítulo en curso, sigue hasta dos enlaces a otros capítulos y toma como máximo seis capturas; (b) una sola página con el libro entero; (c) sin límites.
- **Decisión:** (a).
- **Justificación:** el techo es de 100.000 tokens por invocación, con 10.000 fijos y 15.000 de margen (`docs/architecture.md` §6.5). Con una salida de unos 5.000 tokens quedan unos 70.000 para el briefing y lo que devuelven las herramientas. Estimación, que es un supuesto a medir en la T-12: tres capítulos de 3.300 palabras en snapshot (unos 8.000 tokens cada uno, porque el capítulo pesa unos 4.700 según §6.5, más la estructura), unos 10.000 para portada, índice y ficha, seis capturas y 15.000 de briefing. Salen unos 59.000. (b) mete toda la novela en un snapshot y supera el techo pasado el capítulo 12.
- **Fuente:** `docs/architecture.md` §6.5; Supuesto (tokens por snapshot y por captura)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-06, RF-07, RF-08), 6 (RNF-07), 8.5

## D14 — Informe obsoleto: identificador `previa` y custodia del capítulo
- **Pregunta original (P14):** ¿Cómo sabe el gate que el informe corresponde a la previa actual y no a la de un intento anterior, y que la previa se hizo del capítulo validado?
- **Alternativas consideradas:** (a) el briefing publica un `previa` de 16 hexadecimales, derivado del sha256 de las páginas; el agente lo copia y el gate lo compara. El briefing exige además un `qa/NN-validacion.json` aprobado con el mismo `capitulo_sha256`; (b) comparar mtimes; (c) no comprobarlo.
- **Decisión:** (a).
- **Justificación:** un modelo no calcula un hash, pero sí copia un valor (docstring de `dominio/qa.py`: «Solo lo escribe el CLI: un modelo no calcula un sha256»). La custodia por `capitulo_sha256` es la de la spec 0001 (`docs/architecture.md` §7.3). `docs/validators.md` §5.18 documenta que el orden por mtime depende del reloj del sistema de ficheros. Para que el identificador sea estable, la previa tiene que ser determinista (RF-14).
- **Fuente:** `backend/novela/dominio/qa.py`; `docs/architecture.md` §7.3; `docs/validators.md` §5.18
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-08, RF-12, RF-14, RF-18), 8.3

## D15 — Cuenta de intentos y efecto sobre el gate de revisión
- **Pregunta original (P15):** ¿Cómo se cuentan los intentos del gate visual, y qué pasa con el presupuesto del gate de revisión cuando el reintento lo provoca el visual?
- **Alternativas consideradas:** (a) el gate cuenta sus propias líneas `gate NN visual -> 1`, con dos reintentos como máximo. Se acepta que un reintento visual, al regenerar `briefing NN continuista`, consuma también un intento de revisión; (b) un presupuesto compartido por capítulo; (c) excluir del recuento de revisión los reintentos visuales.
- **Decisión:** (a).
- **Justificación:** el ADR 0002 fija que «el gate cuenta sus propias líneas `gate NN <tipo> -> 1`». «Máximo dos reintentos por gate» (`CLAUDE.md` § Bucle por capítulo). `docs/architecture.md` §2.1 ya acepta que «dos formas distintas de fallar agotan el presupuesto igual que la misma dos veces». (c) exigiría cambiar la regla de recuento de revisión del procedimiento, que la 0002 va a sustituir.
- **Fuente:** `docs/adr/0002-los-gates-los-decide-el-cli.md` § Decisión; `CLAUDE.md` § Bucle por capítulo; `docs/architecture.md` §2.1 (Reintentos); `.claude/commands/novela-continuar.md` § Cuenta de intentos
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-21, RF-23, RF-24), 9

## D16 — Documento de uso real con control negativo
- **Pregunta original (P16):** CC-04 pide documentar «qué inspeccionó, qué detectó y qué cambio provocó». Una novela de humo sin defectos visuales no detectaría nada. ¿Qué sesiones se documentan?
- **Alternativas consideradas:** (a) la novela de humo de 3 capítulos más un control negativo con defectos sembrados (marcado visible en un título y un nombre vacío en la ficha) y un control inverso sin defecto, todo con datos ficticios; (b) solo la novela de humo; (c) una sesión manual fuera del bucle.
- **Decisión:** (a).
- **Justificación:** la petición exige validar el prompt con una novela de humo de 3 capítulos y documentar una sesión real. `docs/validators.md` §4.11 establece el control negativo con defecto sembrado, y el inverso sin defecto, como la forma de saber si un revisor revisa. El título sembrado debe producir un reintento del `escritor` y la ficha una intervención de `arquitecto`, que son el «cambio provocado». Los datos son ficticios (`AGENTS.md` y la 0005 RNF-05).
- **Fuente:** Petición del usuario; `docs/validators.md` §4.11; `AGENTS.md` § Proceso: generar código
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-32), 11, 12 (T-12)

## D17 — Workspaces sin apariciones: dependencia de la spec 0006
- **Pregunta original (P17):** ¿Qué hace el briefing si el workspace no tiene la tabla `apariciones` o le faltan capítulos, por ejemplo uno creado antes de la 0006?
- **Alternativas consideradas:** (a) salir con 4, nombrar los capítulos y que el procedimiento pare con intervención `workspace`; (b) generar la ficha vacía; (c) omitir la ficha de la previa.
- **Decisión:** (a).
- **Justificación:** es la misma regla que la 0006 aplica al exportar en PDF (su RF-25 y D6). Una ficha vacía produciría un falso `seccion_ausente` y un reintento del `escritor` sin sentido. El código 4 ya significa «workspace inválido: `intervencion.md` y para» (`.claude/commands/novela-continuar.md` § Códigos).
- **Fuente:** `docs/specs/0006/spec.md` § RF-25; `.claude/commands/novela-continuar.md` § Códigos de salida del CLI
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-13), 9, 10

## D18 — Ubicación de la previa: junto a los briefings
- **Pregunta original (P18):** ¿Dónde escribe el CLI las páginas de la previa?
- **Alternativas consideradas:** (a) `runs/<run_id>/briefings/NN-revisor-visual/`; (b) `export/previa/`; (c) `qa/NN-visual/`.
- **Decisión:** (a).
- **Justificación:** los briefings son «el único registro de qué vio cada agente» y no se borran (`CLAUDE.md` § Claves y trazado; `docs/architecture.md` §6.1), y la previa es exactamente lo que vio el revisor. (b) haría que `novela producir` tomase la novela por exportada, porque comprueba que `export/` no esté vacío (`backend/novela/slices/producir/flujo.py`). (c) mezcla un artefacto de entrada con las salidas de los revisores (`docs/definitions.md`, `qa/NN-<agente>.json`).
- **Fuente:** `CLAUDE.md` § Claves y trazado; `docs/architecture.md` §6.1; `backend/novela/slices/producir/flujo.py`; `docs/definitions.md` (`qa/NN-<agente>.json`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-07, RF-28), 8.2

## D19 — Comprobación de `.mcp.json` en `comprobar-entorno`
- **Pregunta original (P19):** ¿Se comprueba el servidor MCP antes de lanzar el bucle?
- **Alternativas consideradas:** (a) comprobar que `.mcp.json` existe y cumple RF-01 y que `npx` resuelve, sin lanzar nada; (b) lanzar el servidor y abrir una página de prueba; (c) no comprobar.
- **Decisión:** (a).
- **Justificación:** `novela comprobar-entorno` existe para parar antes de la primera sesión lo que, sin él, fallaría en silencio más tarde (`docs/architecture.md` §2.3 y §11.1). (b) tardaría y dependería de la red. El CLI no accede a la red salvo para Langfuse (`AGENTS.md` § Proceso: ejecución).
- **Fuente:** `docs/architecture.md` §2.3 y §11.1; `AGENTS.md` § Proceso: ejecución
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-04), 9

## D20 — Documentación que se actualiza
- **Pregunta original (P20):** ¿Qué documentos de referencia y de convención cambian, y cómo se habla del número de roles?
- **Alternativas consideradas:** (a) en el mismo commit que el código: `docs/architecture.md` §2.1 (bucle y gates), §2.2 (modelo), §3.1 (árbol), §4 (workspace), §7.1 (reglas del hook), §7.3 (vocabulario), §7.4 y §7.5 (tools y entradas y salidas), §10.5 (score) y §11.1 (puesta en marcha: Node y Chromium); `docs/definitions.md` (`qa/NN-visual.json`); `docs/validators.md` §4.6, §6 y el riesgo de la previa frente al PDF en §5. Además, una línea en `CLAUDE.md` (bucle resumido) y en `AGENTS.md` (CLI y puesta en marcha), hablando de «los roles de `.claude/agents/`» sin fijar un número; (b) solo `docs/uso-browser-mcp.md`.
- **Decisión:** (a).
- **Justificación:** la documentación de referencia se actualiza en el mismo commit que el código que la cambia (`AGENTS.md` § Proceso: modificar documentación). `CLAUDE.md` y `AGENTS.md` solo se tocan si cambia una convención. Un subcomando, un paso del bucle y un paso de puesta en marcha nuevos lo son, y esas líneas se pagan en cada sesión (`AGENTS.md` § Nunca). El número de roles no se fija, como en la 0005 D14.
- **Fuente:** `AGENTS.md` § Proceso: modificar documentación y § Nunca; `docs/specs/0005/decisions.md` § D14
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-26, RF-33), 11, 12 (T-11, T-13)

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md` (importa `AGENTS.md` con `@AGENTS.md`) y `AGENTS.md`.
- Enlazados desde `AGENTS.md`: `docs/architecture.md` (entero), `docs/validators.md` (§1, §2, §4.6 a §4.11, §5 y §6), `docs/definitions.md` y `docs/domain-knowledge.md` (búsquedas puntuales).
- Mencionados en `CLAUDE.md`: `.claude/commands/novela-continuar.md`, `.claude/agents/` (`lector-suspense.md` completo; listado del resto) y `.claude/hooks/denegar-escritura-estado.py`. `~/.claude/state/langfuse_hook.log` no se leyó, porque está fuera del repositorio.
- Código y configuración: `.claude/settings.json`, `.claude/commands/novela-auditar.md`, `backend/tests/test_contratos.py`, `backend/novela/dominio/qa.py`, `backend/novela/dominio/validadores.py`, `backend/novela/slices/producir/flujo.py`, `backend/config/recipes.yaml`, `backend/novela/plataforma/salida.py`, `backend/novela/slices/checkpoint/cmd.py` y `backend/novela/slices/briefing/cmd.py` (búsquedas), y los nombres de test de `backend/tests/test_hook.py` y `test_bucle.py`.
- `docs/auditoria-entregable.md` y `docs/adr/0002-los-gates-los-decide-el-cli.md`.

**Ficheros esperados que no existían**

- `.mcp.json` en la raíz (ausencia confirmada, coherente con la petición).
- `backend/novela/slices/gate/` (el `novela gate` de la spec 0002 no está implementado).
- Ningún enlace roto entre los documentos citados por `CLAUDE.md` y `AGENTS.md`.

**Specs anteriores revisadas y solapamientos**

- `docs/specs/0001-backend-cli-estado-y-api.md` (implementada): custodia por `capitulo_sha256` y códigos de `salida.py`. Se reutilizan.
- `docs/specs/0002-verificacion-a-escala-de-novela.md` (aceptada, sin implementar): define `novela gate` con los tipos `plan|mecanico|final|revision|delta`. **Solapamiento:** esta spec crea el subcomando con el tipo `visual` y el mismo contrato (D3).
- `docs/specs/0003-contencion-y-bucle-en-claude.md` (implementada): hook, `settings.json` y contrato de agentes. Se amplían (D9, D10).
- `docs/specs/0004/` (panel): fuera de alcance por la petición.
- `docs/specs/0005/` (Propuesta): rol `entrevistador`, patrones de datos personales y la regla de no fijar el número de roles (D14 de la 0005).
- `docs/specs/0006/` (Propuesta): **solapamiento y dependencia principal.** Portada, índice, ficha, `Libro`, `Ficha`, `apariciones` y la garantía de que la dedicatoria no llega a ningún modelo (D1, D11, D17).
- `docs/specs/0007/` (Propuesta): toca `novela-continuar.md` y versiona los ids de score.
- `docs/specs/0008/` (Propuesta): segundo registro de hook, en `PostToolUse`; no choca con la ampliación del `matcher` de `PreToolUse`.
- `docs/specs/0009/` (Propuesta, con `validadores.py` ya en el árbol de trabajo sin commitear): excluye explícitamente VP-06 de su alcance («Implementar `lexico_vetado` (VP-05) o la validación visual (VP-06)»). Su catálogo y su formato de id condicionan D12.
- `docs/specs/_plantilla.md`: plantilla antigua, no aplicable.

**Discrepancias detectadas**

- `CLAUDE.md` y `docs/architecture.md` §2.2 asignan `sonnet` a los revisores, pero `CONTRATO` en `test_contratos.py` tiene `haiku`, cambiado a mano según `docs/auditoria-entregable.md` (D7).

**Instrucciones encontradas en el contexto que se ignoraron**

- Ninguna dirigida al redactor de la spec. Las instrucciones de `CLAUDE.md` («Eres el orquestador», no abrir `capitulos/NN.md`) son para la sesión del harness y no afectan a esta tarea: se tomaron como contexto.
