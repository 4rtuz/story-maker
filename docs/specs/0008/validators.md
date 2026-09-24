# Validadores — Spec 0008
Spec: `docs/specs/0008/spec.md` · Plan: `docs/implementation-plans/0008.md` · Fecha de análisis: 2026-09-24

### Discrepancias spec ↔ plan
| ID | Tipo (requisito sin cubrir / paso sin requisito / contradicción) | Detalle | Ref. spec | Ref. plan |
|----|------|---------|-----------|-----------|
| D1 | requisito sin cubrir | §8.1 dice que «la custodia de `aplicar-delta` queda satisfecha aunque el orquestador se salte el paso 5, siempre que la última escritura del capítulo pase». Ningún paso ejecuta `aplicar-delta` con un `qa/NN-validacion.json` escrito solo por el hook | R20 — §8.1 | — |
| D2 | requisito sin cubrir | O-03 exige que el hook no cambie «la cuenta de intentos del procedimiento ni su tabla de reanudación». La cuenta se mide en T4.2; la reanudación solo se analiza leyendo `novela-continuar.md:121-131` (§3 del plan), sin tarea ni test | R1 — §3.1 O-03 | P1, P9 |
| D3 | requisito sin cubrir | §3.2 deja sin cambios `novela-continuar.md`, `novela-nueva.md`, `.claude/agents/*.md`, `backend/schemas/`, `InformeQA` y la API. El plan solo comprueba en T3.1 que el diff no incluya `settings.local.json` ni `denegar-escritura-estado.py`, con un árbol de trabajo que ya tiene cambios sin commitear en `.claude/agents/` y `backend/schemas/` | R2 — §3.2 | P6 |
| D4 | contradicción | RF-11 pide la documentación «en el mismo commit que el código», CA-12 la revisa sobre «el commit que implementa la spec» y T-05 la sitúa en «el commit de T-02/T-03». El plan (D4) la reparte entre los commits de T1.1, T3.1 y T3.2 y revisa CA-12 sobre el diff acumulado | R13 — §5 RF-11, §7 CA-12, §12 T-05 | P1, P6, P7, P8 |
| D5 | requisito sin cubrir | §9: «`novela validar` sale con 2, 3 o 4, o con un traceback → Fallo del harness». Un traceback de Python sale con 1, y ningún paso distingue ese 1 del 1 con hallazgos; el plan (D7) solo evita volcar el traceback | R6 — §9 | P4 |
| D6 | contradicción | RF-09 y CA-10 fijan `matcher` `Write\|Edit\|MultiEdit`; T3.1 solo comprueba que el matcher «cuyo conjunto es {`Write`, `Edit`, `MultiEdit`}», lo que admite otro orden o separadores | R11 — §5 RF-09, §7 CA-10 | P6 |
| D7 | paso sin requisito | T3.2 modifica la fila de `comprobar-entorno` de `docs/validators.md` §6 y `docs/architecture.md:743`, que RF-11 no enumera (solo la fila nueva de §6, §4.17, §3.1, §7.1 y la descripción de `validar`) | — | P7 |

### Validadores
#### VAL-1: Las líneas del hook no gastan intentos ni desvían la reanudación
- Requisito: R1 — "Las validaciones del hook no cambian la cuenta de intentos del procedimiento ni su tabla de reanudación" (§3.1 O-03)
- Punto de fallo: si alguna regla de `novela-continuar.md` (regla de lectura 1, cuenta, reanudación) casa `validar-hook 08 -> 1`, el orquestador agota los dos reintentos antes de usarlos o reanuda desde el paso equivocado
- Precondiciones: `harness.log` sintético con, en este orden: `validar-hook 08 -> 1`, `validar-hook 08 -> 1`, `validar-hook 08 -> 1`, `validar 08 -> 0`, `validar-hook 08 -> 1`
- Cómo validarlo: aplicar a ese fichero, literalmente, los patrones de las secciones «Cuenta de intentos», regla de lectura 1 y tabla de reanudación de `.claude/commands/novela-continuar.md` (p. ej. `grep -c "validar 08 -> 1"` y la búsqueda de «la última línea `validar 08`»)
- Resultado esperado: 0 coincidencias con `validar 08 -> 1`; la última línea `validar 08` seleccionada es la cuarta (`-> 0`); el paso de reanudación resultante es el mismo que con un log que solo contiene `validar 08 -> 0`
- Tipo de prueba sugerida: unitaria (sobre el log) + revisión manual del procedimiento
- Severidad: Alta — una cuenta inflada dispara `intervencion.md` sin fallo real y para el bucle desatendido

#### VAL-2: Superficies declaradas fuera de alcance intactas
- Requisito: R2 — "No se modifican `.claude/commands/novela-continuar.md` ni `novela-nueva.md` … los prompts de ningún agente … ningún modelo Pydantic, esquema de `backend/schemas/` ni `InformeQA` … ni la API" (§3.2)
- Punto de fallo: el árbol de partida tiene cambios sin commitear en `.claude/agents/*.md`, `backend/schemas/*.json` y `backend/api/`; un `git add` amplio los mete en los commits de la 0008
- Precondiciones: rama con todos los commits de la spec 0008
- Cómo validarlo: `git diff --name-only <base>..HEAD` restringido a los commits de la 0008
- Resultado esperado: ninguna ruta bajo `.claude/commands/`, `.claude/agents/`, `backend/schemas/`, `backend/novela/dominio/`, `backend/api/`, `frontend/`, ni `.claude/hooks/denegar-escritura-estado.py` ni `.claude/settings.local.json`; ningún fichero de hook `SubagentStop` en `settings.json`
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — mezclar cambios rompe la atribución por sha del prompt de agentes, pero se corrige reescribiendo el commit

#### VAL-3: Disparo con cada herramienta, rol y ancho de capítulo
- Requisito: R3 — RF-01 "Cuando un `Write`, `Edit` o `MultiEdit` termina con éxito … `agent_type` … `escritor`, `editor-estilo` o no viene … `novela validar <slug> <NN como entero> --origen hook`" (§5, CA-01, CA-03)
- Punto de fallo: que una de las nueve combinaciones herramienta × rol no dispare, o que `NN` se pase con ceros (`08`) o sin convertir en un workspace de tres dígitos
- Precondiciones: `demo-24` en `tmp_path` con `capitulos/08.md` inválido (CA-02); un workspace sintético de 120 capítulos con `capitulos/100.md`; `NOVELA_RUN_ID=r-20260923-1000`
- Cómo validarlo: ejecutar el script con `{Write, Edit, MultiEdit} × {escritor, editor-estilo, sin campo}` sobre `…/novelas/demo-24/capitulos/08.md`; después un `Write`/`escritor` sobre `…/capitulos/100.md`
- Resultado esperado: las nueve primeras salen con 2 y cada una añade exactamente una línea que contiene `validar-hook 08 -> 1`; la última añade una línea con `validar-hook 100 -> `
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Crítica — O-01 es el objetivo principal: un rol o una herramienta sin disparo deja el gate sin ejecutar

#### VAL-4: `NOVELAS_DIR` sale de la ruta y el resto del entorno se hereda
- Requisito: R3 — RF-01 "con `NOVELAS_DIR` igual al directorio `novelas` de esa ruta y el resto del entorno heredado" (§5)
- Punto de fallo: que el hook use el `NOVELAS_DIR` del entorno o del `cwd`, validando otro workspace, o que no propague `NOVELA_RUN_ID`/`NOVELA_SESSION_ID` y la línea caiga en otro run o sin `sesion=`
- Precondiciones: dos copias de `demo-24`, en `tmp_path/a/novelas` y `tmp_path/b/novelas`; entorno con `NOVELAS_DIR=tmp_path/b/novelas`, `NOVELA_RUN_ID=r-20260923-1000`, `NOVELA_SESSION_ID=11111111-1111-4111-8111-111111111111`
- Cómo validarlo: `Write`/`escritor` sobre `tmp_path/a/novelas/demo-24/capitulos/08.md` con `cwd` = `tmp_path/b`
- Resultado esperado: existe `tmp_path/a/novelas/demo-24/qa/08-validacion.json` y no `tmp_path/b/…/qa/08-validacion.json`; `tmp_path/a/novelas/demo-24/runs/r-20260923-1000/harness.log` gana una línea con `sesion=11111111-1111-4111-8111-111111111111` y `validar-hook 08 -> `
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Alta — validar otro workspace da un aprobado falso sobre el capítulo escrito

#### VAL-5: Aprobado en silencio
- Requisito: R4 — RF-02 "Cuando `novela validar` sale con 0, el hook debe salir con 0 sin escribir nada en stdout ni en stderr" (§5, CA-01)
- Punto de fallo: que se filtre la salida estándar del CLI o un aviso propio, que Claude Code muestra al modelo
- Precondiciones: `demo-24` con `capitulos/08.md` válido
- Cómo validarlo: `Write`/`escritor` sobre `capitulos/08.md`; capturar stdout y stderr como bytes
- Resultado esperado: código 0; `stdout == b""` y `stderr == b""`; `qa/08-validacion.json` con veredicto `aprobado` y `capitulo_sha256` igual al sha256 de `capitulos/08.md`
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Alta — ruido en cada escritura correcta consume contexto del agente en todas las invocaciones

#### VAL-6: El rechazo lista todos los hallazgos con sus cuatro campos
- Requisito: R5 — RF-03 "nombre `qa/NN-validacion.json` y liste cada hallazgo de ese informe con `tipo`, `gravedad`, `ubicacion` y `descripcion`" (§5, CA-02; O-02)
- Punto de fallo: que se liste solo el primer hallazgo, que falte un campo o que se lea un informe distinto del recién escrito
- Precondiciones: `demo-24` con `capitulos/08.md` con `pistas_plantadas: []` (el plan manda `pis-004`) y un segundo defecto que genere otro hallazgo (p. ej. longitud por debajo del mínimo)
- Cómo validarlo: `Write`/`escritor`; comparar stderr con los hallazgos de `qa/08-validacion.json`
- Resultado esperado: código 2; stderr empieza por `validar-capitulo:`, contiene `qa/08-validacion.json`, `pis-004` y, por cada hallazgo del informe, su `tipo`, su `gravedad`, su `ubicacion` (o `sin ubicación`) y su `descripcion`; el número de líneas `- ` es igual a `len(hallazgos)`
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Alta — sin el detalle el agente no puede corregir y el gate del orquestador acaba pagando el reintento

#### VAL-7: Truncado a 4.000 caracteres
- Requisito: R5 — RF-03 "con un máximo de 4.000 caracteres" (§5; §9 «Informe con muchos hallazgos»)
- Punto de fallo: que un informe con decenas de hallazgos sature el contexto o que el truncado corte a mitad de un carácter multibyte
- Precondiciones: capítulo que produzca al menos 60 hallazgos, o `qa/08-validacion.json` sintético con 200 hallazgos de `descripcion` de 100 caracteres con tildes
- Cómo validarlo: ejecutar el script (o `mensaje_rechazo`) y decodificar stderr como UTF-8
- Resultado esperado: `len(stderr.decode("utf-8")) <= 4000`, la decodificación no lanza error y el texto termina en `…`; `qa/08-validacion.json` conserva los 200 hallazgos
- Tipo de prueba sugerida: unitaria
- Severidad: Media — caso secundario; el informe completo sigue en `qa/`

#### VAL-8: Falla cerrado en cada causa de RF-04
- Requisito: R6 — RF-04 "Si la entrada no es JSON, si falta `tool_input.file_path` o no es texto, si `novela` no resuelve en el `PATH`, si `novela validar` sale con un código distinto de 0 y 1 o tarda más de 45 s … el hook debe salir con 2" (§5, CA-05; O-04)
- Punto de fallo: que alguna causa termine con 0 o con 1 (no bloqueante en Claude Code) y el agente siga como si el capítulo estuviera validado
- Precondiciones: `demo-24`; `lock_ajeno` disponible
- Cómo validarlo: ejecutar el script con: `b"no es json"`; `b""`; `{"tool_name":"Write","tool_input":{}}`; `{"tool_name":"Write","tool_input":{"file_path":42}}`; `Write` válido con un `PATH` sin `novela`; `…/novelas/no-existe/capitulos/08.md` (→ 4); `…/demo-24/capitulos/99.md` (→ 2); `capitulos/08.md` con `state.lock` tomado (→ 3)
- Resultado esperado: los ocho salen con 2; stderr empieza por `validar-capitulo: fallo del harness, no del capítulo` y termina con `No reescribas el capítulo: termina e informa.`
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Crítica — un guardarraíl que falla abierto da por validado un capítulo que no se ha validado

#### VAL-9: Un traceback de `validar` no se confunde con hallazgos
- Requisito: R6 — "`novela validar` sale con 2, 3 o 4, o con un traceback → Fallo del harness, exit 2" (§9)
- Punto de fallo: un traceback de Python sale con 1; si queda un `qa/08-validacion.json` de una validación anterior, el hook reenvía hallazgos obsoletos como si fueran del capítulo recién escrito
- Precondiciones: `demo-24` con un `qa/08-validacion.json` rechazado de una ejecución previa; un `novela` falso en el `PATH` que escribe un traceback en stderr y sale con 1 sin tocar `qa/`
- Cómo validarlo: `Write`/`escritor` sobre `capitulos/08.md` con ese `PATH`
- Resultado esperado: código 2 y stderr que empieza por `validar-capitulo: fallo del harness, no del capítulo`, sin ninguna línea `- <tipo> (…)` del informe previo
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Alta — el agente corrige defectos que ya no existen y el fallo real del CLI queda oculto

#### VAL-10: Límite de 45 s antes de los 60 s de Claude Code
- Requisito: R6 — RF-04 "o tarda más de 45 s" (§5; §9 «`validar` no termina en 45 s … antes de que Claude Code mate el hook a los 60 s»)
- Punto de fallo: sin límite propio, Claude Code mata el hook a los 60 s y lo trata como no bloqueante
- Precondiciones: `novela` falso en el `PATH` que duerme 50 s
- Cómo validarlo: `Write`/`escritor` sobre `capitulos/08.md`; medir el tiempo de pared; alternativa sin coste: revisión del código (spec §13)
- Resultado esperado: código 2 entre 45 y 50 s; stderr que empieza por `validar-capitulo: fallo del harness, no del capítulo`; el proceso `novela` falso ya no existe al terminar el hook
- Tipo de prueba sugerida: revisión manual (o integración marcada como lenta)
- Severidad: Alta — un bloqueo del CLI convierte el hook en fallo abierto

#### VAL-11: Ancho de capítulo distinto al del workspace
- Requisito: R6 — RF-04 "si tras un 1 no existe `qa/<NN tal como se escribió>-validacion.json`" (§5, CA-06)
- Punto de fallo: que el hook busque `qa/08-validacion.json` (normalizado) en lugar de `qa/008-validacion.json` y reenvíe el informe de otro fichero
- Precondiciones: `demo-24` (dos dígitos) sin `capitulos/08.md` y con `capitulos/008.md`
- Cómo validarlo: `Write`/`escritor` sobre `capitulos/008.md`
- Resultado esperado: código 2; stderr empieza por `validar-capitulo: fallo del harness, no del capítulo` y contiene `qa/008-validacion.json`
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Media — nombre mal formado, poco probable con el briefing actual

#### VAL-12: Fuera de alcance no ejecuta `novela`
- Requisito: R7 — RF-05 "Si la ruta no acaba en `novelas/<slug>/capitulos/<NN>.md`, si `tool_name` no es `Write`, `Edit` ni `MultiEdit`, o si `agent_type` es un valor distinto … salir con 0 sin ejecutar `novela`" (§5, CA-04)
- Punto de fallo: un disparo falso valida en sesiones de desarrollo, toma el lock y añade líneas a `harness.log`
- Precondiciones: `demo-24`; `novela` falso al frente del `PATH` que crea `tmp_path/llamado` si se ejecuta
- Cómo validarlo: rutas `qa/08-estilo.json`, `versiones/v1/capitulos/01.md`, `capitulos/08.md.tmp`, `capitulos/8.md`, `capitulos/0008.md`, `docs/capitulos/08.md` (fuera de `novelas/`); `capitulos/08.md` con `agent_type: Explore` y con `agent_type: general-purpose`; `tool_name: Read` sobre `capitulos/08.md`
- Resultado esperado: todas salen con 0, stdout y stderr vacíos, `tmp_path/llamado` no existe y `harness.log` no existe o tiene los mismos bytes
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Alta — el hook corre en cada escritura de cualquier sesión del repositorio

#### VAL-13: `--origen hook` cambia solo la orden del log
- Requisito: R8 — RF-06 "Con `hook`, debe registrar su línea de `harness.log` con la orden `validar-hook NN` … Todo lo demás … debe ser idéntico" (§5, CA-07)
- Punto de fallo: que cambie el código de salida, el contenido del informe o la salida estándar, o que la línea conserve la subcadena `validar 08 -> `
- Precondiciones: `demo-24` con `capitulos/08.md` válido y otro inválido (CA-02)
- Cómo validarlo: por cada capítulo, `novela validar demo-24 8` y `novela validar demo-24 8 --origen hook`; guardar código, stdout, bytes de `qa/08-validacion.json` y la línea añadida
- Resultado esperado: mismos códigos (0/0 y 1/1), mismo stdout, mismo `qa/08-validacion.json` byte a byte y mismo `capitulo_sha256`; líneas `validar 08 -> k` y `validar-hook 08 -> k`, la segunda sin `validar 08 -> `
- Tipo de prueba sugerida: unitaria (CLI)
- Severidad: Alta — cualquier divergencia hace que el hook y el orquestador den veredictos distintos del mismo gate

#### VAL-14: `--origen` inválido no escribe nada
- Requisito: R9 — RF-07 "Si `--origen` recibe un valor distinto de `orquestador` o `hook`, entonces `novela validar` debe salir con 2 sin escribir `qa/` ni `harness.log`" (§5, CA-08)
- Punto de fallo: que el lock o el run se abran antes de validar la opción, o que `HOOK` en mayúsculas se acepte
- Precondiciones: `demo-24` con `capitulos/08.md`; instantánea de `qa/` y `runs/`
- Cómo validarlo: `novela validar demo-24 8 --origen otro`, `--origen HOOK` y `--origen ""`
- Resultado esperado: las tres salen con 2; `qa/` y `runs/` tienen los mismos ficheros y bytes que antes; `estado/state.lock` no queda tomado
- Tipo de prueba sugerida: unitaria (CLI)
- Severidad: Media — solo lo provoca una llamada manual mal escrita

#### VAL-15: Solo stdlib y ninguna escritura propia
- Requisito: R10 — RF-08 "solo debe importar módulos de la biblioteca estándar, no debe importar `novela` … y no debe escribir ningún fichero"; R18 — RNF-05 "Módulos importados por el script fuera de `sys.stdlib_module_names` | 0" (§5, §6, CA-09)
- Punto de fallo: el hook corre fuera del venv; un import de terceros lo hace fallar con 1 (abierto) en la máquina real, y un fichero temporal propio ensucia el workspace
- Precondiciones: script en `.claude/hooks/validar-capitulo.py`; `demo-24` con instantánea de todo el árbol (rutas y sha256)
- Cómo validarlo: `ast` sobre el script; ejecutar CA-01 y CA-02 y comparar la instantánea
- Resultado esperado: todos los módulos de primer nivel en `sys.stdlib_module_names` y ninguno `novela`; los únicos ficheros nuevos o modificados son `qa/08-validacion.json`, `runs/<run_id>/harness.log` (y el manifiesto del run si no existía) y `estado/state.lock`
- Tipo de prueba sugerida: unitaria + integración
- Severidad: Alta — con un import ajeno el hook falla abierto en todas las invocaciones reales

#### VAL-16: Registro `PostToolUse` sin tocar lo existente
- Requisito: R11 — RF-09 "`hooks.PostToolUse` una entrada con `matcher` `Write|Edit|MultiEdit` y una orden `python "$CLAUDE_PROJECT_DIR/.claude/hooks/validar-capitulo.py"` con `timeout` de 60 s. El registro `PreToolUse`, `permissions` y `.claude/settings.local.json` no deben cambiar" (§5, CA-10)
- Punto de fallo: registro con matcher o ruta distintos (el hook no corre) o edición accidental de `PreToolUse`/`permissions`
- Precondiciones: `.claude/settings.json` en `HEAD` y en la base
- Cómo validarlo: cargar el JSON; comparar `permissions` y `hooks.PreToolUse` con los de la base; inspeccionar `hooks.PostToolUse`
- Resultado esperado: `len(hooks.PostToolUse) == 1`; `matcher == "Write|Edit|MultiEdit"`; una orden `python "$CLAUDE_PROJECT_DIR/.claude/hooks/validar-capitulo.py"` con `timeout == 60` y el fichero existe; `permissions` y `PreToolUse` iguales a la base; `git diff` no incluye `settings.local.json`
- Tipo de prueba sugerida: unitaria (contrato)
- Severidad: Alta — sin registro no hay hook y HAR-04 sigue en «falta»

#### VAL-17: `comprobar-entorno` avisa del hook ausente
- Requisito: R12 — RF-10 "debe informar del hallazgo `falta .claude/hooks/validar-capitulo.py` y salir con el mismo código que para el hook `PreToolUse` ausente" (§5, CA-11)
- Punto de fallo: el fallo abierto por script ausente (§9) no lo detecta nadie antes del bucle desatendido
- Precondiciones: repositorio sintético en `tmp_path` con el resto del entorno correcto; variantes sin `validar-capitulo.py`, sin `denegar-escritura-estado.py` y con ambos
- Cómo validarlo: `novela comprobar-entorno` en cada variante
- Resultado esperado: sin el nuevo, la salida contiene `falta .claude/hooks/validar-capitulo.py` y el código es igual al de la variante sin `denegar-escritura-estado.py` (1); con ambos, el hallazgo no aparece y sale con 0
- Tipo de prueba sugerida: unitaria
- Severidad: Media — hay alternativa: los pasos 3 y 5 siguen validando

#### VAL-18: Documentación de referencia actualizada
- Requisito: R13 — RF-11 "describir el hook en `docs/validators.md` §6 … en §4.17 … y en `docs/architecture.md` §3.1 (árbol) y §7.1 (hooks), además de la opción `--origen`" (§5, CA-12; O-05)
- Punto de fallo: documentación que sigue describiendo un solo hook, o filas de §4.17 sin estado
- Precondiciones: diff de `docs/` de la implementación
- Cómo validarlo: revisar §6 de `docs/validators.md`, §4.17, y §3.1, §7.1 y la descripción de `validar` en `docs/architecture.md`
- Resultado esperado: §6 contiene la fila «Cada escritura de `capitulos/NN.md` por el `escritor` o el `editor-estilo`»; cada fila nueva de §4.17 lleva `activo` o `propuesto`; `architecture.md` §3.1 y §7.1 contienen `validar-capitulo.py` y `PostToolUse`; la firma documentada de `validar` contiene `--origen`
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — no rompe ejecución, pero incumple la regla de docs de referencia

#### VAL-19: Coste fuera de alcance
- Requisito: R14 — RNF-01 "Mediana del tiempo de pared del subproceso en 20 ejecuciones | ≤ 300 ms" (§6, CA-04)
- Punto de fallo: el hook se paga en toda escritura de cualquier sesión; resolver `novela` o importar de más encarece cada `Write`
- Precondiciones: entradas de CA-04
- Cómo validarlo: 20 ejecuciones con `sys.executable` de entradas fuera de alcance; mediana con `time.perf_counter`
- Resultado esperado: mediana ≤ 300 ms
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Media — degrada todas las sesiones pero no rompe nada

#### VAL-20: Coste de una validación
- Requisito: R15 — RNF-02 "Coste del hook al validar un capítulo del fixture `demo-24` | Mediana … en 5 ejecuciones | ≤ 3.000 ms" (§6)
- Punto de fallo: cada `Edit` del `editor-estilo` paga una validación completa
- Precondiciones: `demo-24` con `capitulos/08.md` válido
- Cómo validarlo: 5 ejecuciones de CA-01; mediana del tiempo de pared
- Resultado esperado: mediana ≤ 3.000 ms
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Media — alarga la invocación sin romperla

#### VAL-21: `estado/` intacto
- Requisito: R16 — RNF-03 "El hook no escribe bajo `estado/` | … sin contar `state.lock`, y sha256 de `estado.db` antes y después | 0 ficheros; sha256 idéntico" (§6, CA-09)
- Punto de fallo: `estado.db` es la única fuente de verdad; cualquier escritura fuera de `aplicar-delta` la corrompe
- Precondiciones: `demo-24`; instantánea (ruta relativa y sha256) de `estado/`
- Cómo validarlo: ejecutar CA-01, CA-02 y los casos de CA-05; instantánea después
- Resultado esperado: 0 ficheros nuevos o modificados bajo `estado/` salvo `state.lock`; sha256 de `estado.db` idéntico; ningún `estado/deltas/*.json` nuevo
- Tipo de prueba sugerida: integración
- Severidad: Crítica — viola la invariante 1 de `AGENTS.md`

#### VAL-22: El feedback no lleva prosa del capítulo ni texto del canon
- Requisito: R17 — RNF-04 "El feedback no lleva prosa del capítulo ni texto del canon, y no satura el contexto del agente" (§6, CA-02)
- Punto de fallo: la métrica de la spec solo mide el cuerpo del capítulo; un hallazgo cuya `descripcion` cite `canon/misterio.md` filtraría el secreto al `escritor` y al `editor-estilo`
- Precondiciones: CA-02 y una variante con `capitulos/08.md` con frontmatter no válido (error de Pydantic)
- Cómo validarlo: calcular todas las ventanas de 8 palabras del cuerpo de `capitulos/08.md` y de `canon/misterio.md` de `demo-24`; buscarlas en stderr
- Resultado esperado: 0 ventanas del cuerpo y 0 ventanas de `canon/misterio.md` en stderr; `len(stderr) <= 4000`
- Tipo de prueba sugerida: integración
- Severidad: Crítica — viola la invariante 3 (`canon/misterio.md` es secreto)

#### VAL-23: Suite y analizadores en verde
- Requisito: R19 — RNF-06 "Tests fallidos en `uv run pytest`; errores de `mypy --strict` y de `ruff`; clientes de modelo detectados por `test_sin_clientes_de_modelo` | 0 en los cuatro" (§6; O-04)
- Punto de fallo: el script vive fuera de `backend/`, donde CI no aplica `mypy` ni `ruff`
- Precondiciones: rama con la implementación
- Cómo validarlo: desde `backend/`: `uv run pytest`, `uv run mypy --strict .`, `uv run ruff check .`, y los dos analizadores sobre `../.claude/hooks/validar-capitulo.py`
- Resultado esperado: las cinco órdenes salen con 0; `test_sin_clientes_de_modelo` en verde
- Tipo de prueba sugerida: integración (CI) + revisión manual
- Severidad: Media — una regresión de tipos en el hook no rompe la suite pero puede romper el hook

#### VAL-24: La custodia de `aplicar-delta` acepta el informe del hook
- Requisito: R20 — "la custodia de `aplicar-delta` queda satisfecha aunque el orquestador se salte el paso 5, siempre que la última escritura del capítulo pase" (§8.1)
- Punto de fallo: que la custodia exija algo que solo deja la validación del orquestador (p. ej. una línea `validar NN -> 0`), o que acepte un informe cuyo último veredicto del hook fue rechazo
- Precondiciones: `demo-24` con `capitulos/08.md` válido y `estado/deltas/08.json` válido; sin ejecutar `novela validar` sin `--origen`
- Cómo validarlo: (a) script con `Write`/`escritor` (sale 0) y `novela aplicar-delta demo-24 8`; (b) repetir con un último `Edit` que deja el capítulo inválido (hook sale 2) y `aplicar-delta`
- Resultado esperado: (a) `aplicar-delta` sale con 0; (b) `aplicar-delta` sale con código distinto de 0 y la huella de `estado.db` no cambia
- Tipo de prueba sugerida: integración
- Severidad: Alta — es el beneficio declarado cuando el orquestador se salta el paso 5

#### VAL-25: Solo se leen cuatro campos de la entrada
- Requisito: R21 — "se leen solo `tool_name`, `tool_input.file_path`, `cwd` y `agent_type`, nunca el resto de `tool_input` ni `tool_response` … El stdin se lee como bytes" (§8.4)
- Punto de fallo: leer `tool_response` o `content` hace depender el hook de campos no contractuales; decodificar stdin como texto de consola falla con rutas no ASCII
- Precondiciones: `demo-24` copiado bajo una ruta con `ñ` (p. ej. `tmp_path/año/novelas`)
- Cómo validarlo: `Write`/`escritor` válido con `tool_input.content` de 2 MB, `tool_response` con tipos inesperados (`[1, null]`) y la entrada codificada en UTF-8; variante con bytes no UTF-8 (`b"\xff\xfe"`)
- Resultado esperado: la primera sale con 0 y valida el capítulo del directorio `año`; la variante sale con 2 y el mensaje de fallo del harness
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Media — afecta a rutas con caracteres no ASCII o a cambios de formato de Claude Code

#### VAL-26: Normalización de la ruta
- Requisito: R22 — "se normaliza con `os.path.normpath(os.path.join(cwd, ruta))` y `\` → `/`. Se busca la última aparición … sin distinguir mayúsculas … Se conservan la grafía original del directorio `novelas` … y la del slug" (§8.4)
- Punto de fallo: rutas relativas, con `..` o con mayúsculas que no disparan, o que disparan con `NOVELAS_DIR` en otra grafía
- Precondiciones: `demo-24` bajo `tmp_path/Repo/Novelas` (directorio con mayúscula)
- Cómo validarlo: `file_path` = `Novelas\demo-24\Capitulos\08.md` con `cwd` = `tmp_path/Repo`; `file_path` = `tmp_path/Repo/x/../Novelas/demo-24/capitulos/08.md`; `file_path` = `…/novelas/a/capitulos/novelas/demo-24/capitulos/08.md` (con esa estructura creada)
- Resultado esperado: las tres disparan; en las dos primeras `NOVELAS_DIR` pasado al hijo termina en `/Repo/Novelas` y la orden lleva el slug `demo-24`; en la tercera el slug es `demo-24`
- Tipo de prueba sugerida: integración (subproceso con `novela` falso que registra argv y entorno)
- Severidad: Alta — en Windows las rutas llegan con `\` y mayúsculas variables

#### VAL-27: Formato literal de los mensajes
- Requisito: R23 — "`validar-capitulo: capitulos/NN.md rechazado por novela validar (<n> hallazgos en qa/NN-validacion.json). Corrige el capítulo y vuelve a escribirlo:` … `<ubicacion o «sin ubicación»>` … `No reescribas el capítulo: termina e informa.`" (§8.4)
- Punto de fallo: un texto distinto confunde al agente sobre si reescribir (rechazo) o parar (fallo del harness)
- Precondiciones: `qa/08-validacion.json` sintético con 2 hallazgos, uno sin `ubicacion`
- Cómo validarlo: generar el rechazo y un fallo con causa `novela salió con 4`
- Resultado esperado: primera línea `validar-capitulo: capitulos/08.md rechazado por novela validar (2 hallazgos en qa/08-validacion.json). Corrige el capítulo y vuelve a escribirlo:`; una de las líneas contiene `sin ubicación`; el fallo es una sola línea que empieza por `validar-capitulo: fallo del harness, no del capítulo: ` y termina en `No reescribas el capítulo: termina e informa.`
- Tipo de prueba sugerida: unitaria
- Severidad: Media — el agente puede reescribir ante un fallo del harness y gastar cuota

#### VAL-28: Informe ilegible tras un 1
- Requisito: R24 — "`qa/NN-validacion.json` ilegible tras un 1 | Fallo del harness, exit 2" (§9)
- Punto de fallo: un `json.loads` sin capturar termina con traceback y código 1 (fallo abierto)
- Precondiciones: `novela` falso que sale con 1 tras escribir en `qa/08-validacion.json` cada una de: `{`, `[]`, `{"hallazgos": "x"}`, `{"hallazgos": [{"tipo": 1}]}`
- Cómo validarlo: `Write`/`escritor` sobre `capitulos/08.md` con cada variante
- Resultado esperado: las cuatro salen con 2 y stderr empieza por `validar-capitulo: fallo del harness, no del capítulo`
- Tipo de prueba sugerida: unitaria (con `importlib.util`) o integración
- Severidad: Media — improbable con el CLI actual, pero su efecto es fallo abierto

#### VAL-29: Supuestos de Claude Code observados en una sesión real
- Requisito: R25 — "El `harness.log` del run tiene al menos una línea `validar-hook NN -> ` con `sesion=`, y el procedimiento cuenta igual que sin hook" (§12 T-07; supuestos §10)
- Punto de fallo: si `PostToolUse` no corre dentro de subagentes o su stderr no llega al subagente, todo lo anterior pasa en `pytest` y el hook no hace nada en producción
- Precondiciones: novela de humo; sesión abierta con `--setting-sources project,local` y `NOVELA_SESSION_ID`
- Cómo validarlo: `/novela-continuar <slug> --capitulos 1`; leer `harness.log` y la transcripción del `escritor`
- Resultado esperado: al menos una línea `validar-hook NN -> ` con `sesion=<NOVELA_SESSION_ID>`; si hubo un `-> 1`, la transcripción del subagente contiene `validar-capitulo:`; las líneas `validar NN -> 1` son exactamente las de los pasos 3 y 5; ninguna invocación deja más de 3 líneas `validar-hook NN -> 1`
- Tipo de prueba sugerida: e2e (demostración manual)
- Severidad: Alta — es la única prueba de que HAR-04 se cumple en ejecución real

### Verificadores
#### VER-1: `StrEnum` de Typer rechaza con 2 y sin efectos
- Paso del plan: P1 — "Un valor fuera del enum lo rechaza el parser antes de entrar en el cuerpo de `validar` … Que el código sea exactamente 2 lo fija CA-08 … no lo he comprobado" (§4 D2, T1.1)
- Punto de fallo: `con_codigos` o un callback de la app pueden remapear el error de Click a otro código o abrir el run antes del parseo
- Precondiciones: `demo-24`; `NOVELA_RUN_ID` fijado
- Cómo verificarlo: `CliRunner().invoke(app, ["validar", "demo-24", "8", "--origen", "otro"])`; listar `runs/` antes y después
- Resultado esperado: `exit_code == 2`; `runs/r-20260923-1000/` no se crea si no existía; `qa/08-validacion.json` ausente o con los mismos bytes
- Tipo de prueba sugerida: unitaria
- Severidad: Media — el test de CA-08 lo detecta en rojo; el riesgo es ajustarlo en vez del código

#### VER-2: Solo cambia la orden en `cmd.py:51`
- Paso del plan: P1 — "`abierto.registro("validar-hook" if origen is Origen.hook else "validar", nn)` en `cmd.py:51`" y "`test_sesion_en_el_log` y `test_informe_al_pasar` siguen en verde sin cambios" (T1.1)
- Punto de fallo: que el informe incluya algún campo dependiente del origen o de la hora, de modo que «mismo contenido» de CA-07 exija tocar el test; o que se modifiquen los tests de regresión
- Precondiciones: diff de T1.1
- Cómo verificarlo: `git diff` de `test_validacion.py` limitado a `test_sesion_en_el_log` y `test_informe_al_pasar`; comparar byte a byte los dos `qa/08-validacion.json` de CA-07
- Resultado esperado: cero líneas cambiadas en esos dos tests; los dos informes idénticos; `cmd.py` solo cambia la firma y la llamada a `registro`
- Tipo de prueba sugerida: revisión manual + unitaria
- Severidad: Media — una regresión en `validar NN -> ` rompe F-44

#### VER-3: Ninguna excepción del script sale con 1
- Paso del plan: P2 — "`subprocess.run([shutil.which("novela"), …], …, timeout=45)` sin shell" y P4 "todas las ramas de RF-04 con `mensaje_fallo`" (T2.1, T2.3)
- Punto de fallo: `shutil.which` devuelve `None` y `subprocess.run([None, …])` lanza `TypeError`; `TimeoutExpired`, `OSError` o `KeyError` sin capturar terminan con traceback y código 1, que Claude Code trata como no bloqueante
- Precondiciones: script cargado con `importlib.util`
- Cómo verificarlo: revisar que `main` envuelva todo en un `try` que convierta cualquier `Exception` en `mensaje_fallo` y `sys.exit(2)`; test que parchea `subprocess.run` para lanzar `OSError("x")` y `shutil.which` para devolver `None`
- Resultado esperado: en ambos casos código 2 y stderr con `validar-capitulo: fallo del harness, no del capítulo`; ningún `Traceback` en stderr
- Tipo de prueba sugerida: unitaria + revisión manual
- Severidad: Crítica — cualquier excepción no capturada convierte el guardarraíl en fallo abierto

#### VER-4: stderr en UTF-8 como bytes
- Paso del plan: P2 — "escribe en `sys.stderr.buffer` con un prefijo fijo" como el hook existente (§3, T2.1)
- Punto de fallo: en Windows la consola usa cp1252; escribir `…`, `«sin ubicación»` o descripciones con caracteres fuera de cp1252 por `sys.stderr` de texto lanza `UnicodeEncodeError` y sale con 1
- Precondiciones: entorno con `PYTHONIOENCODING` sin fijar y `PYTHONUTF8=0`
- Cómo verificarlo: CA-02 con una `descripcion` sintética que contenga `→` y `…`; decodificar stderr como UTF-8
- Resultado esperado: código 2; `stderr.decode("utf-8")` sin error y contiene `→`
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Alta — en la máquina de desarrollo (Windows) haría fallar abierto justo el caso de rechazo

#### VER-5: Invocación exacta del CLI
- Paso del plan: P2 — "`[shutil.which("novela"), "validar", slug, str(int(nn)), "--origen", "hook"]`, `env=os.environ | {"NOVELAS_DIR": …}`, `capture_output=True`, `timeout=45` sin shell" (T2.1)
- Punto de fallo: `shell=True`, una cadena en lugar de lista o un slug sin escapar permiten inyección con un nombre de directorio; `env` sustituido en vez de fusionado pierde `PATH` y `NOVELA_RUN_ID`
- Precondiciones: `novela` falso que vuelca `sys.argv` y `os.environ` a un JSON
- Cómo verificarlo: CA-01 con slug `demo-24`; y un workspace cuyo directorio de slug es `a;b` y otro `a&b`
- Resultado esperado: argv `["…novela…", "validar", "demo-24", "8", "--origen", "hook"]`; `NOVELAS_DIR` y `NOVELA_RUN_ID` presentes; con `a;b`/`a&b` el argv contiene el slug literal como un solo elemento (el CLI lo rechaza con 2 y el hook da fallo del harness); `shell` no aparece en la llamada
- Tipo de prueba sugerida: unitaria + revisión manual
- Severidad: Alta — una invocación con shell abre ejecución arbitraria desde un nombre de directorio

#### VER-6: Expresión de la ruta y casos límite del plan
- Paso del plan: P2 — "búsqueda al final de `/novelas/<slug>/capitulos/<\d{2,3}>.md` (literales sin distinguir mayúsculas, grafía original para `NOVELAS_DIR` y slug)" y §6 «Casos límite» (T2.1)
- Punto de fallo: expresión sin ancla final (casa `08.md.tmp`), `\d` que acepta dígitos Unicode (`٠٨.md`), slug que admite `/`, o `cwd` ausente que hace fallar `os.path.join`
- Precondiciones: `capitulo_de` cargado con `importlib.util`
- Cómo verificarlo: tabla de entradas: `…/novelas/demo-24/capitulos/08.md.tmp`, `…/capitulos/٠٨.md`, `…/novelas/demo-24/versiones/v1/capitulos/01.md`, `C:\R\NOVELAS\demo-24\CAPITULOS\08.md`, ruta relativa con `cwd`, y entrada sin `cwd`
- Resultado esperado: `None` para las tres primeras; `("C:/R/NOVELAS", "demo-24", "08")` para la cuarta; la relativa resuelve contra `cwd`; sin `cwd`, el comportamiento coincide con el decidido en Q8 y no lanza excepción
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — un falso negativo desactiva el hook para esa ruta

#### VER-7: Truncado por caracteres con `…`
- Paso del plan: P2 — "truncado a 4.000 caracteres con `…`" y §6 "unitario de `mensaje_rechazo` con un informe sintético largo" (T2.1)
- Punto de fallo: truncar a 4.000 y después añadir `…` (4.001), o truncar por bytes
- Precondiciones: informe sintético de 200 hallazgos
- Cómo verificarlo: `mensaje_rechazo(ruta, "08")`
- Resultado esperado: `len(resultado) == 4000` y `resultado.endswith("…")`; con un informe de 2 hallazgos, sin `…`
- Tipo de prueba sugerida: unitaria
- Severidad: Baja — un carácter de más no rompe nada, pero falla CA-02

#### VER-8: Precondición de `novela` y entorno de los tests
- Paso del plan: P2 — "`_hook(entrada, cwd, entorno)` … `NOVELA_RUN_ID` fijado, sin `NOVELA_SESSION_ID`" y D5 "un fixture … hace `assert shutil.which("novela")`" (T2.1, §4 D5)
- Punto de fallo: un `pytest.skip` o un `NOVELA_SESSION_ID` heredado de la sesión del desarrollador dejan la suite en verde sin probar el hook o con líneas que dependen del entorno
- Precondiciones: `backend/tests/test_hook_validacion.py`
- Cómo verificarlo: buscar `skip` en el fichero; ejecutar `.venv\Scripts\python -m pytest tests/test_hook_validacion.py` con un `PATH` sin `novela`; y con `NOVELA_SESSION_ID` exportado
- Resultado esperado: 0 apariciones de `pytest.skip`/`skipif`; sin `novela` la suite falla con un mensaje que contiene `uv run pytest`; con `NOVELA_SESSION_ID` exportado los tests pasan igual
- Tipo de prueba sugerida: revisión manual + integración
- Severidad: Media — un verde falso en la suite del guardarraíl

#### VER-9: El `novela` hijo no escribe fuera de `tmp_path`
- Paso del plan: P2 — riesgo "El `novela` hijo no hereda el parche de `run.RAIZ_REPO` … hashea el `.claude/` real y consulta `git` del repo real" (§8)
- Punto de fallo: que el hijo cree runs o ficheros bajo el repositorio real o bajo `novelas/` del repo
- Precondiciones: `git status --porcelain` del repositorio antes de la suite
- Cómo verificarlo: `uv run pytest tests/test_hook_validacion.py`; `git status --porcelain` después
- Resultado esperado: la misma salida de `git status --porcelain` antes y después; nada nuevo bajo `novelas/` ni `runs/` del repositorio
- Tipo de prueba sugerida: integración
- Severidad: Media — contamina el repositorio y los hashes de procedencia

#### VER-10: Salida temprana fuera de alcance
- Paso del plan: P3 — "Ajustar el script para que salga antes de resolver `novela`" y "mide la mediana de 20 ejecuciones … como `test_hook.py` hace con F-18" (T2.2)
- Punto de fallo: resolver `novela` o importar `subprocess`/`json` antes de filtrar `tool_name`
- Precondiciones: script; entradas de CA-04
- Cómo verificarlo: revisar el orden de `main` (filtro de `tool_name` y de ruta antes de `shutil.which`); parchear `shutil.which` para lanzar si se llama y ejecutar `main` con cada entrada de CA-04
- Resultado esperado: `shutil.which` no se invoca en ninguna entrada fuera de alcance; mediana medida ≤ 300 ms
- Tipo de prueba sugerida: unitaria
- Severidad: Media — coste en todas las escrituras

#### VER-11: `PATH` sin ningún `novela`
- Paso del plan: P4 — D6 "El test filtra las entradas de `PATH` para las que `shutil.which("novela", path=entrada)` no es `None`" (T2.3)
- Punto de fallo: dejar el `novela` de `uv tool` en `~/.local/bin` hace que el caso pase por la rama equivocada (exit 0 o 1) solo en máquinas con esa instalación
- Precondiciones: máquina con `novela` en el venv y en `~/.local/bin`
- Cómo verificarlo: dentro del test, afirmar `shutil.which("novela", path=path_filtrado) is None` antes de lanzar el script
- Resultado esperado: la afirmación pasa; el caso sale con 2 y la causa menciona `novela` no encontrado
- Tipo de prueba sugerida: integración
- Severidad: Media — test que prueba otra rama según la máquina

#### VER-12: Causa en una línea, sin volcado del CLI
- Paso del plan: P4 — D7 "la causa es una línea compuesta por el script (código de salida, `TimeoutExpired`, ausencia del informe), sin volcar el traceback del CLI" (§4 D7, T2.3)
- Punto de fallo: incluir `stderr` del hijo en la causa introduce varias líneas y texto no acotado
- Precondiciones: casos de CA-05 con salida 2, 3 y 4
- Cómo verificarlo: contar `\n` en stderr del hook
- Resultado esperado: exactamente una línea (0 o 1 `\n` final); la causa contiene el código (`2`, `3`, `4`) y no contiene `Traceback`
- Tipo de prueba sugerida: integración (subproceso)
- Severidad: Baja — afecta a la claridad del mensaje

#### VER-13: El timeout no deja el lock tomado
- Paso del plan: P4 — "El `timeout=45` se verifica por lectura del código" (T2.3)
- Punto de fallo: en Windows `novela.exe` es un lanzador; `subprocess.run` mata el lanzador al expirar y el Python hijo puede seguir con `estado/state.lock` tomado, de modo que el siguiente `validar` sale con 3
- Precondiciones: `novela` falso instalado como script del venv que toma `state.lock` y duerme 60 s; timeout del script reducido por parche a 2 s
- Cómo verificarlo: ejecutar el hook; tras su salida, intentar tomar `state.lock`
- Resultado esperado: el hook sale con 2 en ≤ 5 s y el lock se toma en ≤ 1 s tras su salida
- Tipo de prueba sugerida: integración (Windows)
- Severidad: Media — bloquea las validaciones siguientes hasta que el proceso huérfano termina

#### VER-14: Test del informe ilegible por `importlib`
- Paso del plan: P4 — "Añadir un test unitario del informe ilegible cargando el script con `importlib.util` (D1)" (T2.3)
- Punto de fallo: probar solo JSON mal formado y no estructuras válidas con forma inesperada
- Precondiciones: función de lectura del informe expuesta por el script
- Cómo verificarlo: revisar que el test cubre `{`, `[]`, `{"hallazgos": "x"}` y un hallazgo sin `descripcion`
- Resultado esperado: cuatro casos parametrizados; todos producen `mensaje_fallo` y ninguna excepción
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — el caso es improbable con el CLI actual

#### VER-15: Análisis `ast` completo
- Paso del plan: P5 — "`ast` sobre el script; todo módulo de primer nivel en `sys.stdlib_module_names` y ninguno `novela`" (T2.4)
- Punto de fallo: analizar solo `ast.Import` y no `ast.ImportFrom`, imports dentro de funciones, o `importlib.import_module`/`__import__` con literal
- Precondiciones: copia del script con `from yaml import safe_load` dentro de una función y otra con `importlib.import_module("novela")`
- Cómo verificarlo: ejecutar el comprobador del test contra las dos copias
- Resultado esperado: el comprobador falla en ambas
- Tipo de prueba sugerida: unitaria
- Severidad: Media — un import tardío pasa el test y falla abierto en producción

#### VER-16: `estado.db-wal`/`-shm` en la instantánea
- Paso del plan: P5 — P7 del plan "Si ocurre, se excluyen `-wal` y `-shm` de la instantánea … y se propone la enmienda a la spec antes de cerrar T2.4" (T2.4, §9)
- Punto de fallo: excluir los ficheros WAL sin enmendar la spec deja RNF-03 verde con una métrica distinta a la escrita
- Precondiciones: rojo de T2.4
- Cómo verificarlo: registrar si tras CA-01 aparecen o cambian `estado/estado.db-wal` o `-shm`; si el test los excluye, buscar la enmienda en `docs/specs/0008/`
- Resultado esperado: o el test no excluye nada y pasa, o la exclusión va acompañada de un cambio en RNF-03/CA-09 en el mismo commit; sha256 de `estado.db` idéntico en ambos casos
- Tipo de prueba sugerida: revisión manual + integración
- Severidad: Alta — el criterio se relajaría en silencio sobre la fuente única de verdad

#### VER-17: Test de contrato literal y diff limpio
- Paso del plan: P6 — "`matcher` cuyo conjunto es {`Write`, `Edit`, `MultiEdit`} … `timeout == 60`" y "`git diff --name-only` del commit no incluye `.claude/settings.local.json` ni `.claude/hooks/denegar-escritura-estado.py`" (T3.1)
- Punto de fallo: un test por conjunto acepta `Edit|Write|MultiEdit` o `Write, Edit, MultiEdit` (separador que Claude Code no interpreta igual)
- Precondiciones: `settings.json` alterado a `"matcher": "Write,Edit,MultiEdit"`
- Cómo verificarlo: ejecutar `test_hook_de_validacion_registrado` con esa alteración; `git diff --name-only` del commit de T3.1
- Resultado esperado: el test falla con la alteración; el diff no incluye las dos rutas; `test_settings_de_claude` sin líneas cambiadas
- Tipo de prueba sugerida: unitaria (contrato)
- Severidad: Alta — un matcher mal escrito deja el hook sin disparar

#### VER-18: Filas nuevas de §4.17 y §6
- Paso del plan: P6 — "§4.17 (bloque «Hook `PostToolUse`» con filas nuevas, ver P3 …)" y P3 del plan "F-71 en adelante" (T3.1)
- Punto de fallo: ids que chocan con F-01–F-70 o F-80+, o filas `activo` sin test que las respalde
- Precondiciones: diff de `docs/validators.md` de T3.1
- Cómo verificarlo: `rg "F-7[1-9]" docs/` y cruzar cada fila `activo` con el test que cita
- Resultado esperado: ids nuevos en F-71–F-79 sin duplicados; cada fila `activo` nombra un test existente (CA-02, CA-03, CA-06, CA-07, CA-10); las dependientes de T4.2 están en `propuesto`
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — documental

#### VER-19: `comprobar-entorno` con segundo parámetro
- Paso del plan: P7 — D3 "Se añade `HOOK_VALIDACION = ".claude/hooks/validar-capitulo.py"` y `hook_validacion_existe: bool` … la cáscara lo calcula igual que `:48`" y ajustes de `BIEN`, `test_por_cli`, `test_env_sin_ignorar_por_cli` (T3.2)
- Punto de fallo: calcular la existencia contra `cwd` en lugar de la raíz del repositorio, o ajustar los tests existentes relajando sus aserciones
- Precondiciones: diff de T3.2
- Cómo verificarlo: ejecutar `novela comprobar-entorno` desde `backend/` y desde la raíz; revisar el diff de `test_entorno.py`
- Resultado esperado: sin hallazgo `falta .claude/hooks/validar-capitulo.py` desde ambos directorios; `test_por_cli` sigue exigiendo exactamente una línea; la fila `({"hook_validacion_existe": False}, "falta .claude/hooks/validar-capitulo.py")` está en `test_un_hallazgo_por_condicion`
- Tipo de prueba sugerida: unitaria + revisión manual
- Severidad: Media — falso positivo o negativo del chequeo previo al bucle

#### VER-20: Analizadores sobre el script
- Paso del plan: P8 — "`uv run mypy --strict ../.claude/hooks/validar-capitulo.py` y `uv run ruff check --config pyproject.toml ../.claude/hooks/validar-capitulo.py` (comprobar que `mypy` acepta el nombre con guion …)" (T4.1)
- Punto de fallo: `mypy` rechaza el nombre con guion como módulo y la orden sale con error de uso, que se lee como «no aplica»
- Precondiciones: T3.2 cerrada
- Cómo verificarlo: ejecutar las dos órdenes desde `backend/` y anotar su código y salida
- Resultado esperado: ambas salen con 0; la salida de `mypy` contiene `Success: no issues found in 1 source file`
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — sin ello RNF-06 no se cumple para el script

#### VER-21: Evidencia de la demostración
- Paso del plan: P9 — "Medir las líneas `validar-hook NN -> 1` por invocación (reabrir spec D8 si alguna pasa de 3) … Anotar el resultado en `docs/validators.md` §4.17" (T4.2)
- Punto de fallo: dar la demostración por buena sin observar el stderr en el subagente o sin comparar las cuentas
- Precondiciones: run de la novela de humo
- Cómo verificarlo: `rg "validar-hook \d+ -> " runs/<run_id>/harness.log`; `rg -c "validar \d+ -> 1"` comparado con las llamadas del orquestador en la transcripción; revisar §4.17
- Resultado esperado: ≥ 1 línea `validar-hook` con `sesion=`; cuenta `validar NN -> 1` igual a las invocaciones del orquestador que salieron con 1; máximo por invocación ≤ 3 o spec D8 reabierta; §4.17 con fecha 2026-MM-DD y estado actualizado por fila
- Tipo de prueba sugerida: e2e (demostración manual)
- Severidad: Alta — sin evidencia, los supuestos de §10 quedan sin probar

### Matriz de cobertura
| Requisito | Validadores | Verificadores |
|-----------|-------------|---------------|
| R1 — O-03: sin efecto en cuenta de intentos ni reanudación | VAL-1 | VER-1, VER-2, VER-21 |
| R2 — §3.2: superficies fuera de alcance sin cambios | VAL-2 | VER-17, VER-18 |
| R3 — RF-01: disparo e invocación de `validar --origen hook` | VAL-3, VAL-4 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9, VER-21 |
| R4 — RF-02: 0 → exit 0 en silencio | VAL-5 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9 |
| R5 — RF-03: 1 → exit 2 con hallazgos, ≤ 4.000 caracteres | VAL-6, VAL-7 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9, VER-21 |
| R6 — RF-04: fallo del harness → exit 2 | VAL-8, VAL-9, VAL-10, VAL-11 | VER-11, VER-12, VER-13, VER-14 |
| R7 — RF-05: fuera de alcance → exit 0 sin `novela` | VAL-12 | VER-10 |
| R8 — RF-06: `--origen hook` y línea `validar-hook NN` | VAL-13 | VER-1, VER-2 |
| R9 — RF-07: `--origen` inválido → 2 sin escribir | VAL-14 | VER-1, VER-2 |
| R10 — RF-08: solo stdlib, sin escrituras propias | VAL-15 | VER-15, VER-16 |
| R11 — RF-09: registro `PostToolUse` en `settings.json` | VAL-16 | VER-17, VER-18, VER-21 |
| R12 — RF-10: `comprobar-entorno` avisa del script ausente | VAL-17 | VER-19 |
| R13 — RF-11: documentación de referencia | VAL-18 | VER-1, VER-2, VER-17, VER-18, VER-19, VER-20 |
| R14 — RNF-01: fuera de alcance ≤ 300 ms | VAL-19 | VER-10 |
| R15 — RNF-02: validación ≤ 3.000 ms | VAL-20 | VER-15, VER-16 |
| R16 — RNF-03: nada escrito bajo `estado/` | VAL-21 | VER-15, VER-16 |
| R17 — RNF-04: sin prosa ni canon en el feedback | VAL-22 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9, VER-20 |
| R18 — RNF-05: solo `sys.stdlib_module_names` | VAL-15 | VER-15, VER-16 |
| R19 — RNF-06: suite, `mypy --strict`, `ruff`, sin clientes de modelo | VAL-23 | VER-20 |
| R20 — §8.1: custodia satisfecha con el informe del hook | VAL-24 | SIN CUBRIR |
| R21 — §8.4: solo cuatro campos de la entrada, stdin en bytes | VAL-25 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9 |
| R22 — §8.4: normalización y búsqueda de la ruta | VAL-26 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9 |
| R23 — §8.4: formato literal de los mensajes | VAL-27 | VER-3, VER-4, VER-5, VER-6, VER-7, VER-8, VER-9 |
| R24 — §9: informe ilegible tras un 1 → fallo del harness | VAL-28 | VER-11, VER-12, VER-13, VER-14 |
| R25 — §12 T-07: demostración de los supuestos de §10 | VAL-29 | VER-21 |

### Preguntas abiertas
- Q1 — ¿`agent_type: null` o `agent_type: ""` cuentan como «no viene» (valida) o como «valor distinto» (no valida)? (R3/R7, §5 RF-01 y RF-05): RF-01 dice «o no viene» y RF-05 «un valor distinto de `escritor` y `editor-estilo`»; `null` y la cadena vacía caben en las dos lecturas y una de ellas falla abierto.
- Q2 — Con `capitulos/008.md` escrito y un `capitulos/08.md` válido en un workspace de dos dígitos, ¿el hook sale con 0 o con 2? (R6, §9 y §5 RF-02/RF-04): §9 dice que el hook «no encuentra `qa/008-validacion.json` y lo trata como fallo del harness», pero RF-04 solo mira el informe «tras un 1», y con un 0 RF-02 manda salir con 0.
- Q3 — ¿«Sin distinguir mayúsculas al comparar los literales» incluye la extensión `.md`? (R22, §8.4): en un sistema de ficheros que distingue mayúsculas, un `Write` sobre `capitulos/08.MD` dispararía `validar demo-24 8`, que valida `08.md`, otro fichero.
- Q4 — ¿La tabla de reanudación de `novela-continuar.md` consulta `qa/NN-validacion.json` o solo `harness.log`? (R1, §3.1 O-03): el hook reescribe ese informe en cada escritura, así que si la reanudación lo usa, O-03 no se cumple solo con cambiar la orden de la línea.
- Q5 — ¿Qué métrica y umbral miden «ni texto del canon» en RNF-04? (R17, §6): la métrica solo cuenta subcadenas del cuerpo del capítulo; no fija ventana ni ficheros de `canon/` a comparar.
- Q6 — ¿Cómo distingue el hook un 1 por traceback de un 1 con hallazgos? (R6, §9): §9 exige tratar el traceback como fallo del harness, pero los dos salen con 1; caben comprobar que el `capitulo_sha256` del informe coincide con el fichero, que el informe es posterior al lanzamiento, o que el stderr del hijo esté vacío.
- Q7 — ¿Debe añadirse `.claude/hooks/` a `ruff` y `mypy --strict` de CI y del pre-commit? (R19, §13): la spec da por hecho que `docs/validators.md` §2 «ya los aplica al hook», y el plan (P1) ha visto que `ci.yml` y `.githooks/pre-commit` solo cubren `backend/`.
- Q8 — ¿Qué hace el hook si la entrada no trae `cwd`? (R22, §8.4 y §10): la ruta se normaliza «contra `cwd`», el supuesto de §10 dice que llega, y RF-04 no lo lista entre las causas de fallo del harness; caben usar `os.getcwd()` (como el hook existente) o fallar cerrado.
