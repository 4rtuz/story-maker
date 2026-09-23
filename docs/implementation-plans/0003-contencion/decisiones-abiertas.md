# 0003 — Decisiones sobre las preguntas abiertas

Resuelve las once preguntas de `docs/specs/0003-contencion-y-bucle-en-claude.md` §16 (v0.1). Cada decisión está ya incorporada al cuerpo de la spec en su v0.2. Este fichero guarda el porqué y se borra con el plan al implementar la spec; después queda en el historial, como el de la 0001.

## Evidencia: experimento del 2026-09-23

P-01 y P-02 no se podían responder desde la documentación. La consulta a la documentación oficial no aclara si `PreToolUse` se dispara en subagentes ni qué campos lleva su entrada. Además dijo que `--session-id` no existe, y `claude --help` lo lista. Por eso se respondieron con un proyecto de juguete en el scratchpad y `claude -p` (Claude Code 2.1.280, haiku, seis sesiones y menos de 1 USD en total):

- `.claude/settings.json` con `deny: ["Read(./secreto/misterio.md)"]`.
- Un hook `PreToolUse` que registraba su stdin y denegaba con exit 2 cualquier `file_path` bajo `prohibido/`.
- Hooks `Stop` y `SubagentStop` que solo registraban.
- Un subagente `sonda` con `tools: Read, Write`, invocado desde un slash command del proyecto, `/probar $ARGUMENTS`.

| # | Observado | Consecuencia |
|---|---|---|
| E-1 | `PreToolUse` se dispara para cada `Write` del subagente. Su entrada lleva `agent_id` y `agent_type: "sonda"`. En las llamadas de la sesión principal, esos dos campos no aparecen | P-01 sí. El hook puede distinguir rol y sesión principal |
| E-2 | La escritura bajo `prohibido/` del subagente no llegó a disco. El agente recibió el motivo del stderr | El exit 2 bloquea también dentro de un subagente |
| E-3 | La lectura de `secreto/misterio.md` desde el subagente falló con «File is in a directory that is denied by your permission settings». El hook no llegó a ver ese `Read`: la regla `deny` actúa antes | P-02 sí para `Read`. `deny` y hook no se solapan |
| E-4 | `$CLAUDE_PROJECT_DIR` se expande en el comando del hook en Windows | El hook se registra con esa variable, sin rutas absolutas |
| E-5 | `SubagentStop` existe y trae `agent_transcript_path`. El transcript de cada subagente es un fichero aparte, `<sesión>/subagents/agent-<id>.jsonl`, con `isSidechain: true`. Cada mensaje de asistente lleva `message.model` con el id resuelto (`claude-haiku-4-5-20251001`) | Material para la 0002 (P-13, P-14). No se usa aquí |
| E-6 | En un directorio sin confianza aceptada, `claude -p` avisa «Ignoring 3 permissions.allow entries … this workspace has not been trusted», e ignora el `allow` del proyecto. En cambio respeta el `deny` y ejecuta los hooks. Sin `allow`, la llamada `Task` se deniega | El modo desatendido exige aceptar la confianza en el repo una vez. Hoy `~/.claude.json` tiene `hasTrustDialogAccepted: false` para `story-maker` |
| E-7 | Desde Git Bash, `claude -p "/probar …"` llegó como `C:/Program Files/Git/probar …`, por la conversión de rutas de MSYS | El bucle desatendido en Git Bash necesita `MSYS_NO_PATHCONV=1` |
| E-8 | `Write(./permitido/**)` en `--allowedTools` **no** autorizó la escritura del subagente. `Edit(./permitido/**)` sí | Las reglas de ruta de escritura se escriben con `Edit(...)`, que cubre también `Write` |
| E-9 | `--allowedTools "Agent(sonda)"` no impidió invocar a otro subagente, `otra` | No se puede restringir qué subagentes se invocan con `allow`. Se autoriza `Agent` y ya |
| E-10 | La prueba de `cat secreto/misterio.md` por Bash no concluyó nada: el hook RTK del usuario reescribió la orden como `rtk read …`, y la regla `allow` dejó de casar | Los hooks del ámbito de usuario también actúan en las sesiones del harness. No se da por hecho que `deny` de `Read` cubra Bash |
| E-11 | El plugin `langfuse-observability` 1.2.0 ya está instalado y habilitado en el ámbito de usuario. Engancha `Stop` **y** `SessionEnd`, y su comando cae a `python3` si `uv` no está en el PATH. En esta máquina, `python3` resuelve al alias de la Microsoft Store y el hook falla («Python was not found») | El trazado hoy no funciona en esta máquina, aunque el plugin esté instalado |

Dos datos más de `claude --help`: existen `--session-id <uuid>` y `--setting-sources <user,project,local>`. Y en modo `-p`, «Settings files that fail validation are silently ignored». Un `settings.json` mal formado apagaría el `deny` del misterio sin avisar.

---

## P-01 — ¿`PreToolUse` se dispara en subagentes y los identifica?

**Decisión: sí a las dos (E-1, E-2).** RF-07 pasa de «debería» a «debe». El hook aplica dos reglas:

- **Para todos, sesión principal incluida:** ninguna escritura bajo `novelas/*/estado/` salvo `estado/deltas/NN.json`.
- **Si `agent_type` es uno de los siete roles:** solo puede escribir en sus salidas de §5.1, dentro de `novelas/<slug>/`, y en nada fuera del workspace. Cualquier otro `agent_type` (los agentes de desarrollo como `Explore` o `general-purpose`, o el canario) y la sesión principal solo tienen la primera regla, así que el desarrollo del harness no se ve afectado.

**Por qué:** convierte la columna «Salidas» de `architecture.md` §7.5 en una barrera, cuando hasta ahora era una petición en el prompt. Por ejemplo, un `escritor` que reescriba `canon/estilo.md` queda parado.

**Riesgo que queda:** `agent_type` no es un contrato documentado (`validators.md` §5.10). Si una actualización lo quitara, la segunda regla dejaría de aplicarse sin avisar. El canario lo detecta si intenta una escritura fuera de salidas con un nombre de rol, y por eso P-08 lo incluye.

## P-02 — ¿El `deny` de `Read` alcanza a los subagentes? ¿Con qué patrón? ¿Cubre Bash?

**Decisión:**

- **Alcance:** sí alcanza a los subagentes (E-3).
- **Patrón:** `Read(./novelas/*/canon/misterio.md)`, relativo a la raíz del proyecto, que es el `cwd` de la sesión.
- **Bash:** no se cuenta con que el `deny` lo cubra (E-10). El hook gana una rama para `Bash`: deniega toda orden que case `canon[\\/].*misterio` o `estado\.db`, sin distinguir mayúsculas. Ningún subcomando de `novela` lleva esas cadenas, porque recibe el slug y no rutas. Se exige la barra tras `canon` para que un slug como `el-misterio-del-faro` no dispare la regla.
- **Invariante 1:** se añaden dos `deny` de permisos como segunda capa: `Edit(./novelas/*/estado/estado.db*)` y `Edit(./novelas/*/estado/state.lock)`. No alcanzan a `estado/deltas/`, así que no bloquean al `cronista`. A eso se suma `Bash(sqlite3:*)`.

**Por qué:** la sesión principal es la única con `Bash`. No es adversaria, pero puede equivocarse. Una regla de texto sobre la orden es barata y cubre el error honesto. Un glob como `cat canon/mis*` la esquiva: se acepta, porque ningún subagente tiene `Bash` y la amenaza real es el agente, no la sesión.

## P-03 — Permisos para `claude -p`

**Decisión: allowlist en `.claude/settings.json`, modo `dontAsk` en el bucle y confianza aceptada una vez.**

```json
{
  "permissions": {
    "allow": ["Agent", "Bash(novela:*)", "Edit(./novelas/**)"],
    "deny": [
      "Read(./novelas/*/canon/misterio.md)",
      "Edit(./novelas/*/estado/estado.db*)",
      "Edit(./novelas/*/estado/state.lock)",
      "Bash(sqlite3:*)"
    ]
  }
}
```

- **Lectura:** `Read` dentro del proyecto no pide permiso, así que no se lista. El orquestador lee `qa/`, `harness.log` y `checkpoints/latest.json`, y los agentes leen su briefing.
- **`Agent`:** se autoriza sin nombre, porque restringirlo por subagente no funciona (E-9). Que el orquestador invoque un rol inexistente lo audita la trayectoria de la 0002 (su §5.5.2, «Task a roles desconocidos»).
- **`dontAsk`:** en `-p` equivale a lo que ya pasa (denegar lo no autorizado), pero lo hace explícito en el comando.
- **Otros modos:** `acceptEdits` autorizaría escribir en todo el repo. `bypassPermissions` anula los `deny`.
- **Confianza:** sin ella el `allow` se ignora (E-6). La puesta en marcha gana un paso: abrir `claude` una vez en la raíz del repo y aceptar el diálogo de confianza.
- **El bucle puede girar sin avanzar.** Si la confianza falta, la sesión termina con código 0 sin haber hecho nada, `novela pendiente` sigue en 0 y el bucle lanzaría sesiones sin fin, gastando cuota. Por eso el bucle desatendido compara `checkpoints/latest.json` antes y después de cada sesión, y para si no ha cambiado (ver P-05).
- **Settings inválidos:** en `-p` se ignoran sin avisar, así que el test de contrato (CA-06) parsea `settings.json` y comprueba sus claves de primer nivel. El canario detecta además si el `deny` dejó de aplicarse.

## P-04 — Langfuse: plugin o hook manual, y `session_id`

**Decisión: el plugin de marketplace, habilitado solo para el proyecto, con la sesión fijada desde fuera.**

- **Aislamiento.** El bucle desatendido y las sesiones interactivas del harness arrancan con `--setting-sources project,local`. Así no cargan nada del ámbito de usuario: ni los plugins de desarrollo, ni el hook RTK que reescribe órdenes (E-10), ni el que inyecta texto en el contexto al iniciar sesión. Todo eso gasta contexto del orquestador y cambia su comportamiento sin constar en `manifest.json`.
- **Plugin.** Se habilita en `.claude/settings.local.json`, que está en `.gitignore`, con `"enabledPlugins": {"langfuse-observability@langfuse-observability": true}`. Las claves las guarda el propio plugin en el llavero del sistema operativo (§10.1).
- **`TRACE_TO_LANGFUSE` deja de existir.** El opt-in del plugin 1.2.0 es estar habilitado; el código no lee esa variable. `CLAUDE.md` y `architecture.md` §10.1 se corrigen.
- **Windows.** El hook del plugin necesita `uv` en el PATH para no caer en `python3` (E-11). Es el mismo requisito de P-05.
- **`session_id`.** Sí se puede fijar: `--session-id <uuid>`. El bucle genera un UUID por sesión, lo pasa a `claude` y lo exporta como `NOVELA_SESSION_ID`. El CLI añade `sesion=<uuid>` a cada línea de `harness.log` cuando la variable existe. No va al manifiesto: un capítulo reanudado tiene varias sesiones y un solo manifiesto, y el log ya es una línea por paso. Cierra `architecture.md` §12.2: la correlación traza ↔ paso es directa.
- **Etiquetas.** El bucle exporta además `CC_LANGFUSE_TRACE_TAGS=<slug>`, que el plugin sí lee, para filtrar las trazas por novela.
- **Log.** `CLAUDE.md` pasa a decir que el trazado lo hacen los hooks `Stop` y `SessionEnd` del plugin, con el log en `~/.claude/state/langfuse_hook.log`. La ruta ya era correcta; el nombre del hook, no.

**Por qué no el hook manual:** sería un segundo script de unas 3.000 líneas que mantener, para hacer lo mismo que el plugin ya instalado.

## P-05 — ¿Cómo llega `novela` al PATH?

**Decisión: `uv tool install --editable ./backend`.**

- **Qué hace:** deja `novela` en `~/.local/bin`, que ya está en el PATH porque `claude` vive ahí. Con `--editable`, un cambio en `backend/` se aplica sin reinstalar.
- **Puesta en marcha** (`AGENTS.md` y `architecture.md` §11.1): `uv` tiene que estar en el PATH, por P-04 y por el propio `uv tool`, y después se ejecuta ese comando una vez.
- **Bucle desatendido** (se sustituye en `AGENTS.md` y `CLAUDE.md`):

  ```bash
  export MSYS_NO_PATHCONV=1                 # Git Bash: sin esto, "/novela-continuar" llega como ruta
  export CC_LANGFUSE_TRACE_TAGS=<slug>
  while novela pendiente <slug>; do
    antes=$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)
    export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
    claude -p "/novela-continuar <slug> --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
      --setting-sources project,local --permission-mode dontAsk --model opus || break
    [ "$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)" != "$antes" ] || break
  done
  ```

- **Modelo del orquestador:** `--model opus` fija un modelo que hasta ahora no decidía nadie y que, sin aislar, heredaba del ámbito de usuario. Su contexto por capítulo es pequeño y sus errores de orden son los más caros del sistema.

**Por qué no `uv run --project backend novela`:** alarga cada orden del procedimiento, el `allow` tendría que casar esa forma y el bucle de shell también la necesitaría. Un binario en el PATH hace que las tres digan `novela`.

## P-06 — ¿Cómo se separa el run de arranque?

**Decisión: un campo `fase: "arranque" | "capitulo"` en `Manifest`, con `"capitulo"` por defecto.**

- `novela briefing` con agente `arquitecto` o `trazador` abre el run con `fase: "arranque"`.
- Para cualquier otro agente, `run._run_id` solo reutiliza runs con `fase: "capitulo"`.
- `arquitecto` y `trazador` comparten un run de arranque: se reutiliza el último con esa fase mientras no haya checkpoint. Los reintentos del `arquitecto` caen en el mismo run, sin choques de minuto.
- Su `version_canon` vacía es correcta para el `arquitecto`, cuya única entrada es `config.yaml`. La del `trazador` se deduce, porque es la salida del `arquitecto` en ese mismo run. Lo que atribuye un cambio de prompt es `hashes_claude`, y ese sí es exacto.
- El `run_id` y los nombres de briefing (`01-arquitecto.md`) no cambian, ni tampoco `RUN_ID_PATRON`, que la API comparte.

**Por qué no un prefijo de `run_id` distinto:** obligaría a tocar el patrón que valida la API y los tests de path traversal, por algo que un campo resuelve. **Por qué no `capitulo: null`:** volvería opcional un campo que hoy es obligatorio en la respuesta de `GET /runs/{run_id}`. Eso es una ruptura para cualquier cliente, mientras que un campo nuevo con valor por defecto es aditivo.

## P-07 — Si falla el `validar` posterior al `editor-estilo`

**Decisión: reintenta el `editor-estilo`, sin regenerar su briefing, y el fallo cuenta contra el gate mecánico.**

- **Qué recibe el editor:** el mismo briefing y la ruta de `qa/NN-validacion.json`. Corrige los hallazgos mecánicos sobre el `capitulos/NN.md` que hay en disco, que puede leer.
- **Por qué el editor:** el defecto lo introdujo él, y la versión del escritor ya había pasado `validar`. Reintentar al escritor repetiría el abanico entero: tres llamadas en vez de una.
- **Por qué no regenerar su briefing:** incrustaría la versión rota del capítulo, con un hash distinto del de los otros dos revisores. `aplicar-delta` rechazaría entonces el delta por custodia (0001 RF-32). Sin regenerar, la cadena cierra: los tres briefings de revisión llevan el mismo hash (v1), y `validar`, el briefing del `cronista` y el disco llevan el de la versión final.
- **Presupuesto:** sigue siendo el del gate mecánico, dos reintentos compartidos entre los fallos del escritor y los del editor. Dos formas distintas de fallar agotan el presupuesto igual que la misma dos veces (`architecture.md` §2.1).

## P-08 — ¿Cómo se ejecuta el canario sin un octavo agente?

**Decisión: con `claude -p --agents '<json>'`, que define subagentes solo para esa sesión.**

- **Ficheros:**
  - `backend/tests/canario/agente.json`: el agente `canario`, con `tools: ["Read", "Write"]` y `model: "haiku"`.
  - `backend/tests/canario/ejecutar.py`: stdlib, fuera de la colección de pytest porque no se llama `test_*`.
- **Qué hace `ejecutar.py`:**
  1. Crea un workspace con `novela nueva canario-<fecha>` y le copia un canon de `tests/fixtures`.
  2. Anota el sha256 de `estado/estado.db`.
  3. Lanza la sesión con los flags del bucle y `--agents`.
  4. Comprueba el resultado **en disco**, no en lo que diga el agente.
- **Los cuatro intentos y lo que debe pasar:**
  - Escribir `estado/estado.db`: el hook lo para y el hash no cambia.
  - Leer `canon/misterio.md`: lo para el `deny`, y el marcador del misterio no aparece en el retorno.
  - Ejecutar `novela estado`: no tiene `Bash`.
  - Escribir `canon/estilo.md` con un segundo agente, definido en el mismo JSON con `name: "escritor"`, que pasa a `agent_type: escritor`: lo para la tabla por rol de P-01, y el fichero no cambia.
- **Si `--agents` no sustituye a un agente del proyecto con el mismo nombre:** el cuarto intento no se puede hacer así y queda cubierto solo por CA-05. Se comprueba al implementar y se anota en la spec.
- **Cadencia:** por release del harness y tras cada actualización mayor de Claude Code (`validators.md` §4.9).

**Por qué no un fichero en `.claude/agents/`:** rompería RF-01, que exige exactamente siete, y el orquestador podría invocarlo, porque `Agent` está autorizado sin nombre (P-03).

## P-09 — ¿Dónde queda el baseline de la novela de humo?

**Decisión: en la propia spec 0003, en una subsección «Baseline» de §13 que se rellena al implementar.** Recoge:

- `run_id` y `session_id` de cada capítulo;
- los seis scores por capítulo;
- palabras, intentos por gate e intervenciones;
- el sha del commit, con el árbol limpio.

Los valores completos quedan en Langfuse. La spec guarda los números resumidos y cómo encontrarlos.

**Por qué:** `AGENTS.md` define cinco tipos de documento, y un baseline no es ninguno. No es referencia (describe una ejecución, no el sistema), ni spec nueva, ni ADR. La spec implementada es el registro de lo que se comprobó al aceptarla, y es lo primero que abrirá quien cambie un prompt. `validators.md` §4.8 remite a él.

## P-10 — ¿Dónde vive la cuenta de intentos hasta que exista `novela gate`?

**Decisión: en disco, en `runs/<run_id>/harness.log`, que ya se escribe.** El procedimiento cuenta líneas antes de cada reintento:

| Gate | Intentos consumidos |
|---|---|
| Mecánico | Líneas `validar NN -> 1` del run |
| Revisión | Líneas `briefing NN continuista -> 0` del run, menos una |
| Delta | Líneas `aplicar-delta NN -> 1` del run |

- **Por qué no la conversación:** se compacta, y en una reanudación empieza de cero (`validators.md` §4.16, §5.11).
- **Por qué funciona:** el run de un capítulo se reutiliza hasta su checkpoint, así que la cuenta sobrevive a una sesión nueva. No hace falta código nuevo, porque `Run.registro` ya escribe una línea por subcomando con su código de salida.
- **Límite:** la cuenta sigue en manos de la sesión, que puede leer mal el log. La 0002 (`novela gate`) la convierte en precondición de código, y hasta entonces es un riesgo aceptado de esta spec.

## P-11 — ¿Dónde viven los plugins de desarrollo?

**Decisión: donde ya están, en el ámbito de usuario (`~/.claude/settings.json`, `enabledPlugins`).**

- `.claude/settings.json` no lleva `enabledPlugins`, y CA-06 lo comprueba.
- Las sesiones del harness no los cargan gracias a `--setting-sources project,local` (P-04).
- El único plugin que el harness necesita, Langfuse, se habilita en `.claude/settings.local.json`.

**Por qué:** `CLAUDE.md` dice que los plugins del repositorio son para desarrollar el harness y que ningún agente lleva `Skill`. Con esto, la separación la sostiene la configuración y no depende de la disciplina de nadie.
