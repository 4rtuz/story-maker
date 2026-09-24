# Decisiones — Spec 0008

## D1 — PostToolUse y no SubagentStop
- **Pregunta original (P1):** ¿En qué evento se engancha el hook: `PostToolUse` sobre la escritura o `SubagentStop` al terminar el agente?
- **Alternativas consideradas:** (a) `PostToolUse` con matcher `Write|Edit|MultiEdit`; (b) `SubagentStop`, que valida una vez al final y bloquea la parada; (c) los dos.
- **Decisión:** (a) `PostToolUse`.
- **Justificación:** la petición pide un hook «acotado a escrituras en `novelas/<slug>/capitulos/NN.md`», y esa ruta solo viene en la entrada de `PostToolUse` (`tool_input.file_path`). `SubagentStop` obligaría a sacar el capítulo del transcript o del prompt, dependería de más comportamiento no contractual (`docs/validators.md` §5.10) y trae el riesgo de parada en bucle. El precio es el ruido en los `Edit` intermedios del `editor-estilo`, que queda como riesgo medido en T-07.
- **Fuente:** Petición del usuario; `docs/validators.md` §5.10
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 8.1, 8.4, 11

## D2 — Quién dispara la validación
- **Pregunta original (P2):** ¿Se valida cualquier escritura sobre `capitulos/NN.md` o solo las de ciertos `agent_type`? ¿Qué pasa si falta `agent_type`?
- **Alternativas consideradas:** (a) solo `escritor` y `editor-estilo`, ignorando el resto; (b) cualquier escritura, sea del agente que sea; (c) `escritor`, `editor-estilo` o `agent_type` ausente, ignorando los demás valores.
- **Decisión:** (c).
- **Justificación:** la petición nombra al escritor y al editor. La sesión principal ya no puede escribir en el workspace (regla 3 de `.claude/hooks/denegar-escritura-estado.py`), así que un `agent_type` ausente sobre un capítulo solo indica que Claude Code ha dejado de mandar el campo (F-12). En ese caso validar es fallar cerrado. Los agentes de desarrollo (`Explore`, `general-purpose`) no son roles y se dejan pasar, igual que en la regla 2 del hook existente.
- **Fuente:** Petición del usuario; `.claude/hooks/denegar-escritura-estado.py` (reglas 2 y 3); `docs/validators.md` §4.17 F-12 y F-19
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-01, RF-05), 7 (CA-03, CA-04), 9

## D3 — Que las validaciones del hook no cuenten como intentos
- **Pregunta original (P3):** `novela validar` deja `validar NN -> 1` en `harness.log`, y el procedimiento cuenta esas líneas como intentos consumidos. ¿Cómo se evita que el hook gaste intentos?
- **Alternativas consideradas:** (a) llamar a `validar` tal cual y aceptar la cuenta doble; (b) una opción `--origen hook` que registre la orden como `validar-hook NN`; (c) una variable de entorno con el mismo efecto; (d) cambiar la cuenta del procedimiento.
- **Decisión:** (b) `novela validar … --origen orquestador|hook`, con `orquestador` por defecto. Con `hook` la línea dice `validar-hook NN -> k` y no contiene la subcadena `validar NN -> `.
- **Justificación:** la cuenta (`novela-continuar.md` § Cuenta de intentos), la regla de lectura 1 y la tabla de reanudación buscan `validar NN`. Con (a), una autocorrección que acaba bien gastaría un intento. Con (d), habría que cambiar el procedimiento, que queda fuera de alcance (D7). AGENTS.md pide pasar por spec los cambios de superficie del CLI, y una opción explícita se prueba mejor que una variable. El test que protege la subcadena (F-44, CA-12 de la 0003) no cambia.
- **Fuente:** `.claude/commands/novela-continuar.md` § Cuenta de intentos y § Punto de reanudación; `docs/validators.md` §4.17 F-44; `AGENTS.md` § Proceso: generar código (TDD)
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-06, RF-07), 7 (CA-01, CA-07, CA-08), 8.4, 12 (T-01)

## D4 — El hook escribe el informe de validación como cualquier otra
- **Pregunta original (P4):** ¿La validación del hook escribe `qa/NN-validacion.json` (y con él el sha de la custodia) o solo informa?
- **Alternativas consideradas:** (a) comportamiento idéntico salvo la línea del log; (b) un modo que no escriba `qa/`.
- **Decisión:** (a).
- **Justificación:** `validar` escribe el informe «siempre, pase o no, con el sha256 del fichero que validó» (docstring de `backend/novela/slices/validacion/cmd.py`), y eso es lo que compara la custodia. Si el hook lo escribe, la custodia de `aplicar-delta` se cumple aunque el orquestador se salte el paso 5, que es el objetivo de la petición («que la validación no dependa de que el orquestador se acuerde»). Un modo sin informe sería una segunda variante de `validar` que habría que probar aparte.
- **Fuente:** Petición del usuario; `backend/novela/slices/validacion/cmd.py` (docstring); `docs/validators.md` §3.9 punto 7
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-06), 8.1

## D5 — Contenido del feedback
- **Pregunta original (P5):** ¿Qué devuelve el hook al agente cuando `validar` sale con 1?
- **Alternativas consideradas:** (a) solo la línea de stdout de `validar` («rechazado, N hallazgos en …»); (b) esa línea más `tipo`, `gravedad`, `ubicacion` y `descripcion` de cada hallazgo, leídos de `qa/NN-validacion.json` y con un límite de caracteres; (c) el informe JSON entero.
- **Decisión:** (b), con un límite de 4.000 caracteres y sin prosa del capítulo.
- **Justificación:** con (a) el agente tendría que leer el informe. Lo permite su herramienta `Read`, pero cuesta un turno. El procedimiento ya pasa `qa/NN-validacion.json` al `escritor` en reintento (paso 3), así que esos campos se consideran seguros respecto al invariante 3. El límite protege el contexto del agente. El valor 4.000 no sale de ningún documento.
- **Fuente:** `.claude/commands/novela-continuar.md` § Por capítulo, paso 3; `AGENTS.md` § Invariantes (3). Umbral: Supuesto
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-03), 6 (RNF-04), 7 (CA-02), 8.4

## D6 — Qué significa fallar cerrado en PostToolUse
- **Pregunta original (P6):** La escritura ya se ha hecho. ¿Qué hace el hook ante una entrada que no entiende o un fallo del CLI, y qué le dice al agente?
- **Alternativas consideradas:** (a) exit 2 con un mensaje que distingue fallo del harness de capítulo rechazado y pide no reescribir; (b) exit 2 con el mismo mensaje que un rechazo; (c) exit 0 y dejar el fallo al paso 3 del orquestador.
- **Decisión:** (a). Salida 2 ante: entrada no JSON, `file_path` ausente o que no es texto, `novela` que no resuelve, código de salida distinto de 0 y 1, más de 45 s o informe esperado ausente. Una herramienta fuera de `Write|Edit|MultiEdit` sale con 0, porque el matcher y CA-10 la excluyen.
- **Justificación:** la petición exige fallar cerrado, y el hook existente aplica la misma regla: lo que no entiende sale con 2, porque cualquier otro código no bloquea. Distinguir el mensaje evita que el agente reescriba en bucle un capítulo que no tiene la culpa. Coincide con la regla de lectura 1 del procedimiento: un fallo del CLI no se arregla con un agente.
- **Fuente:** Petición del usuario; `.claude/hooks/denegar-escritura-estado.py` (docstring); `.claude/commands/novela-continuar.md` § Reglas de lectura (1)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-04), 7 (CA-05, CA-06), 8.4, 9

## D7 — Los pasos 3 y 5 del procedimiento no cambian
- **Pregunta original (P7):** Con el hook, ¿el orquestador sigue llamando a `novela validar` en los pasos 3 y 5?
- **Alternativas consideradas:** (a) sí, sin tocar el procedimiento; (b) quitar los pasos y confiar en el hook; (c) sustituirlos por una lectura de `qa/NN-validacion.json`.
- **Decisión:** (a).
- **Justificación:** la petición no pide cambiar el procedimiento: pide un punto de ejecución adicional y su documentación en `docs/validators.md` §6. Los pasos 3 y 5 son los que cuentan intentos, los que escriben la línea que usa la tabla de reanudación y la red si el hook falla abierto. Cambiarlos afectaría a la cuenta que la spec 0002 va a trasladar a `novela gate`.
- **Fuente:** Petición del usuario; `CLAUDE.md` § Bucle por capítulo; `docs/specs/0002` (archivo `docs/specs/0002-verificacion-a-escala-de-novela.md` §8)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 8.1, 8.5

## D8 — Sin límite de autocorrecciones en el hook
- **Pregunta original (P8):** ¿El hook limita cuántas veces rechaza al mismo agente dentro de una invocación?
- **Alternativas consideradas:** (a) sin límite; (b) contar las líneas `validar-hook NN -> 1` desde el último briefing y dejar de bloquear al llegar a K; (c) cortar la invocación.
- **Decisión:** (a). El límite sigue siendo el del gate del orquestador (tres intentos). T-07 mide las líneas `validar-hook NN -> 1` por invocación, y la decisión se reabre si alguna pasa de 3.
- **Justificación:** contar exigiría que el hook leyera y entendiera `harness.log` y los briefings. Eso duplica lógica del procedimiento en un script de stdlib y abre un fallo nuevo. Ninguna fuente del repositorio fija un límite, y el umbral de reapertura (3) solo imita el máximo de intentos por gate.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 11

## D9 — Cómo encuentra el hook a `novela` y al workspace
- **Pregunta original (P9):** ¿Qué binario de `novela` ejecuta el hook, y cómo le indica el workspace si `NOVELAS_DIR` puede apuntar fuera del repo?
- **Alternativas consideradas:** (a) `shutil.which("novela")` sobre el `PATH` heredado y `NOVELAS_DIR` sacado de la propia ruta escrita; (b) `uv run novela` desde `backend/`; (c) una variable nueva con la ruta del binario.
- **Decisión:** (a).
- **Justificación:** la puesta en marcha deja `novela` en el `PATH` (`AGENTS.md` § Proceso: ejecución), y en la máquina con Device Guard es el de `backend\.venv\Scripts` (F-57). Tomar `NOVELAS_DIR` de la ruta garantiza que se valida el workspace escrito, que es como el hook existente trata `novelas/` («por segmento y no por prefijo, para que valga con NOVELAS_DIR fuera del repo»). (b) añade `uv` al camino de cada escritura. (c) añade una superficie sin necesidad.
- **Fuente:** `AGENTS.md` § Proceso: ejecución; `.claude/hooks/denegar-escritura-estado.py` (`_relativas`); `docs/validators.md` §4.17 F-50 y F-57
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-01), 8.4, 10

## D10 — Alcance de «no se escribe nada bajo estado/»
- **Pregunta original (P10):** `novela validar` toma el lock `estado/state.lock` y abre `estado.db` en solo lectura. ¿Choca con la restricción de la petición?
- **Alternativas consideradas:** (a) la restricción se aplica al hook y a lo nuevo; el lock sigue como hasta ahora; (b) un `validar` sin lock para el hook.
- **Decisión:** (a). El test comprueba que no aparecen ficheros nuevos ni modificados bajo `estado/`, salvo `state.lock`, y que el sha256 de `estado.db` no cambia.
- **Justificación:** el lock es el invariante 8 («Un proceso por workspace. Respeta `estado/state.lock`»), y `validar` ya lo toma cuando lo llama el orquestador. Saltárselo rompería un invariante que no se negocia. La lectura de `estado.db` es en solo lectura (`estado_db.abrir(..., solo_lectura=True)` en `cmd.py`).
- **Fuente:** `AGENTS.md` § Invariantes (1 y 8); `backend/novela/slices/validacion/cmd.py`; `backend/novela/plataforma/workspace.py` (`lock`)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-08), 6 (RNF-03), 7 (CA-09)

## D11 — `comprobar-entorno` vigila el hook nuevo
- **Pregunta original (P11):** ¿`novela comprobar-entorno` debe comprobar también que existe el script nuevo?
- **Alternativas consideradas:** (a) sí, con el mismo hallazgo que el hook `PreToolUse`; (b) no, basta con el test de contrato.
- **Decisión:** (a), con prioridad Should.
- **Justificación:** si falta el script, el hook falla abierto sin avisar, igual que en F-10, y `comprobar-entorno` existe para parar antes del bucle ante una configuración así (`docs/validators.md` §6, «hook presente»). El test de contrato corre en CI, no en la máquina que lanza el bucle.
- **Fuente:** `docs/validators.md` §4.17 F-10 y §6; `backend/novela/slices/entorno/comprobaciones.py` (docstring)
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-10), 7 (CA-11), 12 (T-04)

## D12 — Coherencia con la spec 0002
- **Pregunta original (P12):** La spec 0002 (aceptada) añade `validar --final` para el fichero del editor y `novela gate` con repetición idempotente. ¿Cómo encaja el hook?
- **Alternativas consideradas:** (a) el hook ejecuta `validar` sin `--final`, y la spec que implemente la 0002 decide si el hook del editor lo pasa; (b) adelantar aquí `--final`; (c) esperar a la 0002.
- **Decisión:** (a).
- **Justificación:** la 0002 no está implementada (`docs/validators.md` §2), y adelantar `--final` metería en esta spec parte de otra. Las líneas `validar-hook` no casan `gate NN <tipo> -> 1`, así que no alteran la cuenta de `novela gate`. Solo rompen su repetición idempotente cuando el capítulo se ha reescrito entre dos llamadas, y en ese caso las entradas del gate también han cambiado.
- **Fuente:** `docs/specs/0002-verificacion-a-escala-de-novela.md` §8 (tabla de gates, «Cuenta» y «Repetición») y RNF-04; `docs/validators.md` §2
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 10, 11

## D13 — Tiempos límite
- **Pregunta original (P13):** ¿Qué `timeout` se declara en `settings.json` y cuánto espera el hook a `novela validar`?
- **Alternativas consideradas:** (a) 60 s en `settings.json` y 45 s en el subproceso; (b) el valor por defecto de Claude Code sin límite propio; (c) límites más cortos.
- **Decisión:** (a).
- **Justificación:** si Claude Code mata el hook por tiempo, lo trata como error no bloqueante y el hook falla abierto. Un límite propio más corto convierte ese caso en un exit 2 con causa. `validar` tarda menos de 2 s con 4.000 palabras (`test_validacion.py::test_rendimiento`), así que 45 s dejan mucho margen. Los valores concretos no salen de ningún documento.
- **Fuente:** Supuesto (referencia de rendimiento: `backend/novela/slices/validacion/test_validacion.py::test_rendimiento`)
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-04, RF-09), 8.4, 9, 13

## D14 — Fichero de test propio
- **Pregunta original (P14):** ¿Los tests del hook van en `backend/tests/test_hook.py` o en un fichero nuevo?
- **Alternativas consideradas:** (a) `backend/tests/test_hook_validacion.py`; (b) ampliar `test_hook.py`.
- **Decisión:** (a).
- **Justificación:** la petición admite las dos. `test_hook.py` se presenta como el test del `PreToolUse` de la spec 0003 §5.2 y la spec 0007 le añade casos (RF-23). Separar evita mezclar dos hooks con fixtures distintos: este necesita un workspace real y el CLI.
- **Fuente:** Petición del usuario; `backend/tests/test_hook.py` (docstring); `docs/specs/0007/spec.md` RF-23
- **Confianza:** media
- **Secciones de la spec afectadas:** 8.2, 13, 14

## Contexto consultado

**Ficheros leídos**
- `CLAUDE.md`, `AGENTS.md`
- `docs/validators.md` (§1, §2, §3.9, §4.17, §5, §6), `docs/architecture.md` §7.1 e índice de secciones, `docs/definitions.md` (entradas `cursor` y `runs/<run_id>/`)
- `.claude/settings.json`, `.claude/hooks/denegar-escritura-estado.py`, `.claude/commands/novela-continuar.md`
- `backend/novela/slices/validacion/cmd.py`, `backend/novela/slices/validacion/test_validacion.py`, `backend/novela/slices/entorno/comprobaciones.py`, `backend/novela/plataforma/run.py` (parcial), `backend/novela/plataforma/workspace.py` (parcial), `backend/novela/plataforma/lock.py` (parcial), `backend/novela/dominio/qa.py` (parcial), `backend/novela/cli.py` (parcial)
- `backend/tests/test_hook.py` (parcial), `backend/tests/test_contratos.py` (parcial)
- `docs/auditoria-entregable.md` (fila HAR-04; fichero no versionado, encontrado al explorar)
- Plantillas del plugin `sdd-spec-writer`

**Ficheros esperados que no existían**
- Ninguno. Existen los cuatro documentos que enlaza `AGENTS.md` (`docs/architecture.md`, `docs/definitions.md`, `docs/domain-knowledge.md`, `docs/validators.md`). `docs/domain-knowledge.md` no se leyó porque no aporta a esta spec. `.claude/settings.local.json` existe y no se leyó a propósito: la spec no lo toca y puede contener configuración de la máquina. `~/.claude/state/langfuse_hook.log`, citado en `CLAUDE.md`, está fuera del repositorio y se ignoró.

**Specs anteriores revisadas y solapamientos**
- `0001` — Backend, CLI, estado y API (implementada, formato `docs/specs/0001-….md`): define `validar` y la custodia. Esta spec le añade `--origen`.
- `0002` — Verificación a escala de novela (aceptada, sin implementar): `validar --final` y `novela gate`. Coherencia registrada en D12.
- `0003` — Contención y bucle en `.claude/` (implementada): autora del hook `PreToolUse`, de `settings.json`, de `comprobar-entorno` y de CA-06. Esta spec añade un segundo hook y amplía su test de contrato.
- `0004` — Panel de lanzamiento, progreso y lectura (aceptada): sin solapamiento. El panel muestra las líneas de `harness.log` sin interpretarlas, así que `validar-hook` no le afecta.
- `0005` — Fase de brief de la novela de regalo (propuesta): sin solapamiento.
- `0006` — Entrega en PDF (propuesta): sin solapamiento.
- `0007` — Regenerar capítulos y versionar la novela (propuesta): toca `validar` (RF-31) y `test_hook.py` (RF-23). Compatible: el hook reenvía cualquier hallazgo y no se activa con `versiones/`.

**Instrucciones encontradas en el contexto que se ignoraron**
- Ninguna dirigida al redactor de specs. `CLAUDE.md` indica a la sesión principal que no abra `capitulos/NN.md`, y no se abrió ninguno. `AGENTS.md` fija el estado inicial de una spec como `borrador`; se ha usado `Propuesta`, como exige el procedimiento de este redactor, y conviene revisarlo al aceptarla.
