---
spec: 0003
titulo: "Contención y bucle en `.claude/`: agentes, hooks, permisos y procedimientos"
estado: borrador
autor: ""
fecha: 2026-09-23
version: 0.2
afecta: [agentes, backend, docs]
depende_de: [0001]
sustituye: []
adr: [0001]
commit: null
---

# 0003 — Contención y bucle en `.claude/`: agentes, hooks, permisos y procedimientos

## 1. Propósito y alcance

Construir la mitad del harness que vive en `.claude/`: los siete subagentes, los tres procedimientos del orquestador, los permisos y los hooks. Con eso, el CLI de la 0001 pasa a tener quien lo invoque y se puede escribir la primera novela. Es para el orquestador, que hoy no tiene procedimiento que seguir, y para el operador, que no puede lanzar nada.

**Dentro del alcance**

- `.claude/agents/`: los siete roles con el frontmatter de `architecture.md` §2.2 y §7.4, y un cuerpo con el contrato de entradas y salidas de §7.5.
- `.claude/commands/`: `novela-nueva.md`, `novela-continuar.md` y `novela-auditar.md`.
- `.claude/settings.json`: permisos (el `deny` sobre `canon/misterio.md` de §12.7 y lo que exige el modo desatendido) y el registro de los hooks del proyecto.
- `.claude/hooks/denegar-escritura-estado.py`: el guardarraíl `PreToolUse` de §7.1 y `validators.md` §4.4, con la excepción del `cronista` declarada y las salidas de cada rol convertidas en barrera.
- El trazado a Langfuse de §10.1 con el plugin ya instalado, habilitado solo para el proyecto.
- La puesta en marcha y el bucle desatendido de `AGENTS.md`, reescritos con lo que exige `claude -p` en esta máquina.
- Tres cambios en el backend que la ejecución real necesita: el run de arranque, la procedencia de `.claude/` en `manifest.json` (`validators.md` §4.7) y la sesión de Claude Code en `harness.log` (`architecture.md` §12.2).
- El tercer contrato de `validators.md` §3.8, Harness ↔ Claude Code, como test en CI.
- El canario de contención de `validators.md` §4.9: la parte que prueba las barreras, no la del orquestador.
- Una novela de humo de tres capítulos, que es la aceptación de los procedimientos y el primer baseline de scores.

**Fuera del alcance**

- Todo lo de la 0002: `novela gate`, trayectoria del orquestador, freno en `pendiente`, modelo resuelto por invocación, canario del orquestador, filtro por campo del secreto y QA saneado para el reintento. La 0002 pasa a depender de esta.
- La cola en disco, el supervisor y `run.sh` (`architecture.md` §12.8), los `GET` del log en vivo (§12.6) y el índice recuperable (§12.4).
- `novela budget` y la degradación por cuota de §9. `/novela-continuar` corre siempre en el nivel 1. Parar es la única degradación posible, y se hace con el `|| break` del bucle desatendido.
- La calidad de los prompts más allá de lo que mide la novela de humo. Esta spec fija el contrato de cada agente, no su estilo.
- El frontend.

## 2. Problema

El backend está implementado y nada lo ejecuta. `ls .claude` devuelve «No such file or directory». `CLAUDE.md` da por existentes los siete agentes, los tres slash commands y los dos hooks, y ninguno está en disco. `architecture.md` §12.7 afirma que `.claude/` contiene un `settings.json` con plugins, y tampoco es cierto. `validators.md` §2 lo resume: los métodos 10, 11, 12, 14, 15, 20 y 27, el hook y el `tools` del 13 no corren «hasta la spec que construya `.claude/`».

Hay cuatro huecos concretos:

1. **El invariante 3 se sostiene en una sola capa.** Solo el aborto de `novela briefing` lo protege. `tools` no restringe rutas (`architecture.md` §6.3) y no hay ninguna regla `deny`. El invariante 1 depende solo de los triggers de `estado.db`.
2. **La regla del hook escrita hoy bloquearía al `cronista`.** `CLAUDE.md` y `architecture.md` §7.1 dicen que el hook deniega cualquier escritura bajo `estado/`. Pero §7.5 declara `estado/deltas/NN.json` como salida del `cronista`. `validators.md` §3.8 ya lo señala como conflicto escrito.
3. **El modo desatendido no está resuelto.** `claude -p` no tiene a quién pedir permiso. Nadie ha decidido qué herramientas se autorizan de antemano ni con qué modo de permisos. El experimento de `decisiones-abiertas.md` añade tres problemas propios de esta máquina:
   - el `allow` de un proyecto sin confianza aceptada se ignora, y hoy este repo no la tiene;
   - Git Bash convierte `/novela-continuar` en una ruta de Windows;
   - el hook de Langfuse falla porque `uv` no está en el PATH.
4. **El run del capítulo 1 registra un canon vacío.** `/novela-nueva` tiene que generar el briefing del `arquitecto` con `novela briefing <slug> 1 arquitecto`, porque el subcomando exige un capítulo en `1..N`. Ese briefing abre el run del capítulo 1 y escribe su `manifest.json` antes de que exista el canon. Reproducido sobre un workspace nuevo:

   ```
   $ novela nueva prueba --idea "un faro" --capitulos 3 --palabras 9000
   $ novela briefing prueba 1 arquitecto
   runs/r-20260923-1408/briefings/01-arquitecto.md · 229 de 50000 tokens
   $ cat runs/r-20260923-1408/manifest.json
     "version_canon": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "version_plan":  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
   ```

   `e3b0c442…` es el sha256 de la cadena vacía. `/novela-continuar` reutiliza ese run para el capítulo 1, porque su manifiesto dice `capitulo: 1`. Así, el primer capítulo de cada novela queda atribuido a un canon y un plan que no existían. Los tests de la 0001 no lo ven porque `fabrica.py` escribe canon y plan directamente, sin pasar por el briefing de arranque.

A esto se suma que `manifest.json` registra `sha_commit` pero no si el árbol estaba sucio. Un prompt de agente editado sin commitear produce dos ejecuciones con el mismo sha (`validators.md` §4.7).

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Orquestador | Recibe los tres procedimientos. Pierde la capacidad de leer el misterio y de escribir el estado, aunque se equivoque |
| Agentes (los siete) | Reciben un contrato escrito y unas barreras que no dependen de que lo obedezcan, incluida la de escribir solo en sus salidas |
| Agente `cronista` | Su salida `estado/deltas/NN.json` queda permitida de forma explícita por el hook |
| Operador humano | Tres pasos de puesta en marcha. Después puede lanzar `/novela-nueva` y el bucle desatendido, y resuelve las paradas de `intervencion.md` |
| Desarrollador del harness | El test de contrato falla en el commit, no en el capítulo 9. Sus sesiones solo heredan la regla sobre `estado/`, no la tabla por rol |

## 4. Contexto y restricciones

- **Invariantes que aplican.**
  - **3**: `deny` sobre el misterio más `tools` sin búsqueda.
  - **1**: hook y `deny` sobre `estado/`.
  - **5**: `/novela-continuar` reanuda desde `checkpoints/latest.json`, y la cuenta de intentos sale de `harness.log`, nunca de la conversación.
  - **7**: los procedimientos no reescriben capítulos cerrados, y el sello de 0001 RF-35 lo detecta.
  - **8**: el lock del CLI ya existe y los procedimientos no lo esquivan.
- **Restricciones técnicas.**
  - Sin SDK de proveedores.
  - El hook no puede importar `backend/`: corre en cada llamada de herramienta, fuera del venv. Tiene que ser Python de la stdlib.
  - La máquina de desarrollo es Windows con Git Bash y PowerShell, así que nada puede depender de un shell POSIX salvo el bucle, que exige Git Bash.
  - `bypassPermissions` queda descartado, porque ignora las reglas `deny`.
- **Supuestos verificados** el 2026-09-23 con Claude Code 2.1.280 (`decisiones-abiertas.md`, experimento E-1 a E-11):
  - `PreToolUse` se dispara para las herramientas de un subagente y trae `agent_type`.
  - El `deny` de `Read` alcanza a los subagentes.
  - `claude -p "/comando args"` resuelve los slash commands del proyecto.
  - Un hook con exit 2 bloquea también dentro de un subagente.
- **Supuestos no verificables.** `agent_type`, el formato del transcript y el comportamiento de `--setting-sources` no son contrato de Claude Code (`validators.md` §5.10). El canario vigila los dos primeros.
- **Dependencias.** La 0001, implementada. La 0002 depende de esta, no al revés.

## 5. Propuesta

Siete fases. Al final de cada una queda algo verificable.

### 5.1 Fase 1 — los siete agentes y su contrato estático

Un fichero por rol en `.claude/agents/<rol>.md`:

- **Frontmatter**: `name` igual al nombre del fichero, `description` que diga cuándo invocarlo, y `tools` y `model` exactamente como la tabla siguiente, que es la de `architecture.md` §2.2 y §7.4.
- **Cuerpo, las reglas de §7.4**: lee solo el briefing y las rutas que nombra; escribe solo en sus salidas; devuelve como máximo tres líneas; ante ambigüedad, falla sin inventar.
- **Cuerpo, las salidas**: cada agente nombra sus rutas de salida, con `<slug>` y `NN` como variables que rellena el prompt de la invocación.

| Agente | `tools` | `model` | Salidas (relativas a `novelas/<slug>/`) |
|---|---|---|---|
| `arquitecto` | `Read, Write` | `opus` | `canon/{premisa,mundo,estilo,misterio}.md`, `canon/personajes/*.md` |
| `trazador` | `Read, Write` | `opus` | `plan/escaleta.md`, `plan/capitulos/NN.md` |
| `escritor` | `Read, Write` | `opus` | `capitulos/NN.md` |
| `continuista` | `Read, Write` | `sonnet` | `qa/NN-continuidad.json` |
| `editor-estilo` | `Read, Edit, Write` | `sonnet` | `capitulos/NN.md`, `qa/NN-estilo.json` |
| `lector-suspense` | `Read, Write` | `sonnet` | `qa/NN-suspense.json` |
| `cronista` | `Read, Write` | `haiku` | `estado/deltas/NN.json` |

`NN` son 2 o 3 dígitos, según el workspace. Esta tabla es la fuente de la segunda regla del hook (§5.2) y la comprueba un test de `backend/tests/test_contratos.py`.

### 5.2 Fase 2 — las barreras

**Hook `PreToolUse`** en `.claude/hooks/denegar-escritura-estado.py`, Python de la stdlib, registrado en `.claude/settings.json` con `python "$CLAUDE_PROJECT_DIR/.claude/hooks/denegar-escritura-estado.py"`:

1. **Escrituras** (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`), para todos:
   - Deniega cualquier ruta bajo `novelas/*/estado/` salvo `estado/deltas/NN.json`.
   - Antes de comparar, normaliza la ruta: la resuelve contra `cwd`, colapsa `..` y separadores, y en Windows compara sin distinguir mayúsculas, porque `Estado\ESTADO.DB` es el mismo fichero en NTFS.
2. **Escrituras de los siete roles.** Si `agent_type` es uno de los siete, además, solo permite rutas de sus salidas de §5.1 dentro de un workspace de `novelas/`. Cualquier otro `agent_type` y la sesión principal solo tienen la regla 1, así que el desarrollo del harness no se ve afectado.
3. **`Bash`.** Deniega toda orden que case `canon[\\/].*misterio` o `estado\.db`, sin distinguir mayúsculas.
4. **Falla cerrado.** Cualquier entrada que no pueda interpretar la deniega con exit 2, porque un error distinto de 2 Claude Code lo trata como no bloqueante y la acción seguiría adelante.
5. **Solo mira la ruta.** Examina `file_path` o `command`, nunca el `tool_input` entero. En el experimento, una regla sobre todo el `tool_input` bloqueó un `Agent` cuyo prompt mencionaba la ruta prohibida.

**Permisos** en `.claude/settings.json`:

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

- **Por qué `Edit(...)`:** es la regla de ruta que autoriza también `Write` (E-8).
- **Por qué no se lista `Read`:** leer dentro del proyecto no pide permiso.
- **Por qué `Agent` sin nombre:** restringirlo por subagente no surte efecto (E-9).
- **El `deny` del misterio** es viable porque `novela briefing` ya incrusta el contenido y no pasa rutas (`assemble.py`, línea 4): ningún agente necesita abrir el fichero.
- **Lo que no va:** ni claves, ni `enabledPlugins`, ni `env`.

### 5.3 Fase 3 — procedencia y correlación

Es código, así que lleva TDD.

- **Run de arranque.** `Manifest` gana `fase: "arranque" | "capitulo"`, con `"capitulo"` por defecto.
  - `novela briefing` con `arquitecto` o `trazador` abre o reutiliza el último run con `fase: "arranque"`.
  - Para el resto de agentes solo se reutilizan runs con `fase: "capitulo"`.
  - No cambian `run_id`, `RUN_ID_PATRON` ni el modelo de respuesta de la API.
- **Procedencia de `.claude/`.** `Manifest` gana dos campos:
  - `sucio: bool`: si `git status --porcelain` tiene cambios en `.claude/`, `backend/config/` o `backend/novela/`.
  - `hashes_claude: {ruta: sha256}`: uno por fichero de `.claude/agents/` y `.claude/commands/`.
- **Sesión en el log.** Si `NOVELA_SESSION_ID` está definida y es un UUID, `Run.registro` añade `sesion=<uuid>` a cada línea de `harness.log`.

### 5.4 Fase 4 — los procedimientos

Prosa en `.claude/commands/`. El orden lo fijan la custodia de 0001 RF-32 y la máquina de §4.10 de `validators.md`, no el gusto. Cada paso «Task» es una invocación cuyo prompt contiene solo el slug, `NN`, la ruta del briefing, las rutas de salida y, en un reintento, las rutas de `qa/` que lo motivan. Nunca prosa del orquestador ni el capítulo.

**`/novela-nueva <slug> --idea "..." [--capitulos N] [--palabras P]`**

1. `novela nueva <slug> ...` con los mismos flags.
2. `novela briefing <slug> 1 arquitecto` y después Task `arquitecto`.
3. `novela briefing <slug> 1 trazador` y después Task `trazador`. Este briefing valida el canon contra sus modelos al cargarlo, así que funciona como gate del `arquitecto`: si falla, se reintenta al `arquitecto` con el error, con un máximo de dos veces.
4. Devolver los ids creados y la orden de continuar.

**`/novela-continuar <slug> [--capitulos N]`**, por capítulo:

1. `novela pendiente <slug>`: con código distinto de 0, se termina. `novela estado <slug> --breve`. Si hay un `runs/*/intervencion.md` sin resolver, se para. El capítulo es el de `checkpoints/latest.json` más uno, o el 1.
2. `novela briefing … escritor` y después Task `escritor`.
3. `novela validar`. Si sale con 1, se reintenta al `escritor` con `qa/NN-validacion.json`.
4. Los tres briefings de revisión, **todos antes de lanzar ninguno**, para que incrusten el mismo hash. Después, tres Task en un solo turno: `continuista`, `editor-estilo` y `lector-suspense`.
5. `novela validar` otra vez, porque el `editor-estilo` ha reescrito el capítulo. Si falla, se reintenta al **`editor-estilo`**, con el mismo briefing (no se regenera) y `qa/NN-validacion.json`, y se repite este paso.
6. Gate: se leen los `veredicto` de `qa/NN-continuidad.json` y `qa/NN-suspense.json`. Si alguno rechaza, se reintenta al `escritor` con esas dos rutas y se vuelve al paso 3.
7. `novela briefing … cronista`, Task `cronista` y después `novela aplicar-delta`. Si el delta se rechaza, se reintenta al `cronista` con la causa, que está en `harness.log`.
8. `novela checkpoint`.

**Cuenta de intentos.** Hay como máximo dos reintentos por gate. Antes de cada reintento, el procedimiento lee `runs/<run_id>/harness.log` y cuenta:

- **Gate mecánico:** las líneas `validar NN -> 1`, que suman las de los pasos 3 y 5.
- **Gate de revisión:** las líneas `briefing NN continuista -> 0`, menos una.
- **Gate de delta:** las líneas `aplicar-delta NN -> 1`.

El tercer fallo escribe `runs/<run_id>/intervencion.md` con el gate, los intentos y las rutas de `qa/` y del briefing, y para.

**`/novela-auditar <slug>`**: `novela auditar`. Si sale con 0, `novela exportar --formato md` y `--formato epub`. Si sale con 1, se informa sin exportar.

### 5.5 Fase 5 — trazado y canario

- **Trazado.**
  - Lo hace el plugin `langfuse-observability`, que ya está instalado en el ámbito de usuario. Se habilita solo en `.claude/settings.local.json` (`enabledPlugins`), y el opt-in es estar habilitado: desaparece `TRACE_TO_LANGFUSE`.
  - Las claves las guarda el plugin en el llavero del sistema operativo.
  - Sus hooks son `Stop` y `SessionEnd`, y su log está en `~/.claude/state/langfuse_hook.log`.
  - El bucle exporta `CC_LANGFUSE_TRACE_TAGS=<slug>` para filtrar por novela.
- **Canario de contención.**
  - Consta de `backend/tests/canario/agente.json` y `backend/tests/canario/ejecutar.py`. Ninguno lo recoge pytest, porque invoca un modelo.
  - `ejecutar.py` crea un workspace de prueba, anota el hash de `estado.db` y lanza `claude -p --agents "$(cat agente.json)"` con los flags del bucle.
  - Los intentos son cuatro, y los cuatro tienen que fallar:
    - escribir `estado/estado.db`;
    - leer `canon/misterio.md` por su ruta;
    - ejecutar `novela`;
    - con un segundo agente definido con `name: "escritor"`, escribir `canon/estilo.md`.
  - El veredicto sale del disco, no del informe del agente.
  - Corre por release del harness y tras cada actualización mayor de Claude Code.

### 5.6 Fase 6 — puesta en marcha y bucle desatendido

Tres pasos de puesta en marcha, una vez por máquina. Se añaden a `AGENTS.md` y a `architecture.md` §11.1:

1. `uv` en el PATH. Lo necesitan `uv tool` y el hook del plugin de Langfuse.
2. `uv tool install --editable ./backend`, que deja `novela` en `~/.local/bin`.
3. Abrir `claude` una vez en la raíz del repo y aceptar el diálogo de confianza. Sin ella, `claude -p` ignora el `allow` del proyecto.

El bucle desatendido sustituye al de `AGENTS.md` y `CLAUDE.md`. Se ejecuta en Git Bash:

```bash
export MSYS_NO_PATHCONV=1                 # sin esto, "/novela-continuar" llega como ruta de Windows
export CC_LANGFUSE_TRACE_TAGS=<slug>
while novela pendiente <slug>; do
  antes=$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)
  export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
  claude -p "/novela-continuar <slug> --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
    --setting-sources project,local --permission-mode dontAsk --model opus || break
  [ "$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)" != "$antes" ] || break
done
```

- `--setting-sources project,local` deja fuera los plugins y hooks del ámbito de usuario.
- `--model opus` fija el modelo del orquestador.
- La última línea para el bucle si una sesión termina sin avanzar el checkpoint. Así, un permiso que falte o una confianza no aceptada no se convierten en sesiones sin fin que gastan cuota.

Las sesiones interactivas del harness se abren con `claude --setting-sources project,local`.

### 5.7 Fase 7 — novela de humo

Primero `/novela-nueva humo-0003 --capitulos 3 --palabras 9000` en interactivo, y después el bucle de §5.6. Se acepta si la novela termina con `checkpoints/03.json` confirmado. Su baseline se registra en §13 de esta spec.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `.claude/agents/` contiene exactamente siete ficheros `.md`, uno por rol, y en cada uno `name` es igual al nombre del fichero | debe |
| RF-02 | El `tools` de cada agente es exactamente el de §5.1; ninguno declara `Glob`, `Grep`, `Bash`, `Task`, `Agent`, `Skill`, `WebFetch` ni `WebSearch` | debe |
| RF-03 | El `model` de cada agente es el de §5.1 | debe |
| RF-04 | El cuerpo de cada agente nombra todas sus rutas de salida de §5.1 | debería |
| RF-05 | El hook deniega `Write`, `Edit`, `MultiEdit` y `NotebookEdit` sobre cualquier ruta bajo `novelas/*/estado/` salvo `estado/deltas/NN.json`, después de normalizarla | debe |
| RF-06 | El hook deniega, con exit 2, toda entrada que no pueda interpretar | debe |
| RF-07 | Con `agent_type` igual a uno de los siete roles, el hook deniega toda escritura fuera de sus salidas de §5.1 | debe |
| RF-08 | `.claude/settings.json` contiene los cuatro `deny` de §5.2 | debe |
| RF-09 | `.claude/settings.json` no contiene claves, `enabledPlugins`, `env` ni el modo `bypassPermissions` | debe |
| RF-10 | El `allow` de `.claude/settings.json` es exactamente el de §5.2 | debe |
| RF-11 | Los briefings de `arquitecto` y `trazador` van a un run con `fase: "arranque"` que ningún otro agente reutiliza | debe |
| RF-12 | `manifest.json` registra `sucio` y el sha256 de cada fichero de `.claude/agents/` y `.claude/commands/` | debe |
| RF-13 | `/novela-nueva` sigue los pasos de §5.4 | debe |
| RF-14 | `/novela-continuar` sigue los pasos de §5.4: los tres briefings de revisión antes de ninguna revisión, `validar` después del editor, el `cronista` después del gate, la cuenta de intentos desde `harness.log` e `intervencion.md` al tercer fallo | debe |
| RF-15 | Todo prompt de Task de los procedimientos lleva solo slug, `NN`, ruta de briefing, rutas de salida y, en reintento, rutas de `qa/` | debe |
| RF-16 | `/novela-auditar` sigue los pasos de §5.4 | debe |
| RF-17 | El trazado a Langfuse funciona en el bucle de §5.6 y ningún fichero versionado lo habilita ni guarda sus claves | debería |
| RF-18 | El canario intenta las cuatro acciones de §5.5 y todas fallan en disco | debe |
| RF-19 | La novela de humo de tres capítulos termina con `checkpoints/03.json` y deja su baseline en §13 | debe |
| RF-20 | El hook deniega las órdenes `Bash` que casan `canon[\\/].*misterio` o `estado\.db` | debe |
| RF-21 | Con `NOVELA_SESSION_ID` definida y válida como UUID, cada línea de `harness.log` lleva `sesion=<uuid>`; si no es un UUID, no se escribe | debería |
| RF-22 | El bucle de §5.6 para cuando una sesión termina sin cambiar `checkpoints/latest.json` | debe |
| RF-23 | `AGENTS.md` documenta los tres pasos de puesta en marcha de §5.6 | debe |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | El hook responde en menos de 300 ms por llamada en la máquina de desarrollo. Corre en cada escritura y en cada `Bash` |
| RNF-02 | Consumo de contexto | Un prompt de Task de los procedimientos no pasa de 15 líneas y un retorno de agente, de 3. Las sesiones del harness no cargan contexto del ámbito de usuario |
| RNF-03 | Coste / cuota | Ninguna llamada a modelo por capítulo además de las cinco del bucle. El canario cuesta una sesión por release. El bucle no lanza una segunda sesión sin avance |
| RNF-04 | Fiabilidad | Un corte en cualquier paso de `/novela-continuar` se reanuda repitiendo el primer paso no confirmado, con la cuenta de intentos intacta. El hook falla cerrado |
| RNF-05 | Observabilidad | Cada sesión desatendida produce su traza en Langfuse con la etiqueta del slug. `harness.log` la enlaza con cada paso, y `manifest.json` la atribuye a un prompt concreto aunque el árbol esté sucio |
| RNF-06 | Compatibilidad | Ninguna novela en curso. Los tres campos nuevos de `Manifest` tienen valor por defecto |
| RNF-07 | Seguridad | Ningún modo de permisos que ignore `deny`. Las claves, fuera de git (0001 CA-32 ya lo prueba en el pre-commit) |

## 8. Interfaces y contratos

- **Contrato de agente** (**nuevo**): los siete ficheros de §5.1. Es la primera vez que existen. `architecture.md` §7.4 y §7.5 dejan de describir un contrato sin implementación.
- **Ficheros de `.claude/`** (**nuevos**): `settings.json`, `hooks/denegar-escritura-estado.py` y `commands/novela-{nueva,continuar,auditar}.md`. `settings.local.json` queda para el plugin, fuera de git.
- **Hook**: lee de stdin el JSON de `PreToolUse` (`tool_name`, `tool_input`, `cwd` y, en un subagente, `agent_type`). Deniega con exit 2 y el motivo en stderr, y permite con exit 0 sin salida.
- **`manifest.json`** (**compatible**): gana `fase`, `sucio` y `hashes_claude`. Cambia el modelo `Manifest` de `dominio/artefactos.py`, que no tiene JSON Schema en `backend/schemas/`. `GET /runs/{run_id}` devuelve los campos nuevos, así que se regenera el OpenAPI commiteado.
- **`harness.log`** (**compatible**): sufijo opcional `sesion=<uuid>`.
- **Entorno** (**nuevo**): `NOVELA_SESSION_ID`, que lee el CLI; `CC_LANGFUSE_TRACE_TAGS`, que lee el plugin.
- **CLI** (**compatible**): ningún subcomando nuevo. `novela briefing` cambia de run para `arquitecto` y `trazador`.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Sin cambios de forma. El `deny` impide leer `misterio.md` desde Claude Code; el CLI lo sigue leyendo |
| `plan/` | Sin cambios |
| `estado/estado.db` | Sin cambios. Hook y `deny` impiden escribirla desde una herramienta de fichero o desde `sqlite3` |
| `memoria/` | Sin cambios |

`runs/` gana el run de arranque, tres campos en el manifiesto y la sesión en el log.

## 10. Migración y compatibilidad

No aplica: no hay novelas empezadas y los cambios en `manifest.json` y `harness.log` son aditivos.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01, RF-02, RF-03) El test de contrato lee `.claude/agents/*.md` y falla si falta o sobra un rol, si `name` no casa con el fichero, o si `tools` o `model` difieren de §5.1
- [ ] **CA-02** (RF-04) El mismo test falla si el cuerpo de un agente no nombra alguna de sus salidas
- [ ] **CA-03** (RF-05) Property-based: para toda ruta generada bajo `novelas/<slug>/estado/` que no sea `estado/deltas/NN.json`, con variaciones de mayúsculas, separadores y `..`, el hook sale con 2; para `estado/deltas/NN.json` sin `agent_type`, sale con 0
- [ ] **CA-04** (RF-06) Una entrada que no es JSON, o una escritura sin `file_path`, hace salir al hook con 2
- [ ] **CA-05** (RF-07) Property-based: para cada rol y cada salida de su fila de §5.1, el hook sale con 0; para cada rol y cada salida de otra fila, o una ruta fuera de `novelas/`, sale con 2. Con `agent_type: Explore` o sin `agent_type`, una ruta del repo sale con 0
- [ ] **CA-06** (RF-08, RF-09, RF-10) El test parsea `.claude/settings.json` y falla si no es JSON válido, si tiene claves de primer nivel distintas de `permissions` y `hooks`, si `allow` no es exactamente el de §5.2, si falta algún `deny` o si aparece `bypassPermissions`
- [ ] **CA-07** (RF-11) Tras `novela briefing <slug> 1 arquitecto` y `… trazador`, los dos briefings están en el mismo run con `fase: "arranque"`. El primer `novela briefing <slug> 1 escritor` abre otro run con `fase: "capitulo"`, cuyo manifiesto registra el hash del canon y el plan presentes
- [ ] **CA-08** (RF-12) Con un fichero de `.claude/agents/` modificado sin commitear, el manifiesto registra `sucio: true` y un hash distinto del commiteado
- [ ] **CA-09** (RF-18) `ejecutar.py` informa de los cuatro intentos como fallidos, el hash de `estado.db` no cambia, `canon/estilo.md` no cambia y el marcador del misterio no aparece en la salida
- [ ] **CA-10** (RF-13 a RF-17, RF-19, RF-22) La novela de humo de §5.7 termina con `checkpoints/03.json` confirmado, tres trazas en Langfuse con la etiqueta `humo-0003` y los briefings de los cinco agentes por capítulo en `runs/`
- [ ] **CA-11** (RF-20) El hook sale con 2 ante `cat novelas/x/canon/misterio.md` y `sqlite3 novelas/x/estado/estado.db`, y con 0 ante `novela estado el-misterio-del-faro --breve`
- [ ] **CA-12** (RF-21) Con `NOVELA_SESSION_ID` válido, la línea de `harness.log` de un `validar` lleva `sesion=<uuid>`; con un valor que no es UUID, no lo lleva y el comando no falla
- [ ] **CA-13** (RF-23) Revisión en el commit: `AGENTS.md` contiene los tres pasos y el bucle de §5.6

## 12. Trazabilidad

Se rellena durante la implementación.

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 a RF-03 | CA-01 | `backend/tests/test_contratos.py::test_agentes_de_claude` | pendiente |

## 13. Verificación

- **Contrato (T)**, `validators.md` §3.8, tercer contrato: CA-01, CA-02 y CA-06 son estáticos y corren en CI. CA-06 cubre además que en `-p` un `settings.json` inválido se ignora sin avisar.
- **Property-based (T)** sobre el hook: CA-03 y CA-05. No es un gate de `validate.py`, pero cumple la misma función de guardarraíl de §3.6, y los ejemplos no cubren las variantes de ruta de Windows. El test ejecuta el script como subproceso, igual que Claude Code.
- **Unit (T)** con TDD: CA-07, CA-08 y CA-12, que son los únicos cambios en `backend/`.
- **Canario (I + T)**, §4.9: CA-09. Es la única verificación periódica de que las barreras disparan dentro de un subagente.
- **Novela de humo (D)**: CA-10. Es la única verificación de los procedimientos, que son prosa (`validators.md` §5.8).
- **Riesgos aceptados**:
  - La cuenta de intentos la lleva la sesión leyendo `harness.log`, y puede leerlo mal. La 0002 (`novela gate`) la convierte en código.
  - El reintento del `escritor` lee `qa/` por ruta, y ese `qa/` lo escriben revisores que conocen el misterio. Es la fuga de `validators.md` §4.9.1 que la 0002 cierra con su RF-03.
  - La rama `Bash` del hook es texto sobre la orden, y un glob como `cat canon/mis*` la esquiva. Solo la sesión principal tiene `Bash`, y no es adversaria.
  - El orquestador puede invocar un subagente que no sea uno de los siete, porque `Agent` no se puede restringir por nombre. Lo audita la trayectoria de la 0002.
  - `agent_type`, `--setting-sources` y el formato del transcript no son contrato de Claude Code (`validators.md` §5.10). El canario vigila los dos primeros.
  - La segunda regla del hook no sabe qué capítulo está en curso: permite `capitulos/NN.md` para cualquier `NN`. Reescribir uno cerrado lo detecta el sello de 0001 RF-35.

### Baseline

Se rellena al cerrar CA-10: `run_id` y `session_id` por capítulo, los seis scores de `architecture.md` §10.5, palabras, intentos por gate, intervenciones y sha del commit con el árbol limpio.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno se toca. El 1 y el 3 ganan dos capas preventivas cada uno |
| Esquemas | Ninguno en `backend/schemas/`. Cambia el modelo `Manifest` y se regenera el OpenAPI |
| Contratos de agente | Se crean los siete |
| Docs de referencia | `AGENTS.md` (puesta en marcha y bucle desatendido). `CLAUDE.md` (bucle, regla del hook con la excepción, hooks y log del trazado, sin `TRACE_TO_LANGFUSE`). `architecture.md`: §3.1 (árbol de `.claude/`); §6.3 y §7.4 (dejan de describir algo inexistente); §7.1 (regla del hook); §2.3 y §11.1 (bucle y arranque); §10.1 y §10.2 (plugin y `session_id`); §12.2 y §12.7 (se cierran). `validators.md`: §2 (qué corre de verdad), §3.8, §4.4 y §4.9 (canario con `--agents`). `definitions.md` §6 si describe el manifiesto |
| Frontend | Nada |

## 15. Alternativas descartadas

- **Meter esto en la 0002.** Tiene 17 preguntas abiertas, y varias solo se cierran con una ejecución que depende de esta spec. Fusionarlas bloquearía justo lo que las desbloquea.
- **`bypassPermissions` en el modo desatendido.** Ignora las reglas `deny`, así que el invariante 3 se quedaría sin su capa de ruta.
- **`acceptEdits`.** Autoriza escribir en todo el repo; la allowlist se limita a `novelas/`.
- **Un `deny` por agente.** Los permisos son de sesión y no de subagente. El incrustado del briefing hace innecesario distinguir en la lectura, y la escritura la distingue el hook por `agent_type`.
- **Hook en shell.** La máquina de desarrollo es Windows. Python de la stdlib corre igual en los dos sistemas.
- **Que el hook importe `backend/novela`.** Arrastraría el venv a cada llamada de herramienta y rompería el hook si el venv no está sincronizado. La regla cabe en la stdlib.
- **Hook manual de Langfuse.** Sería un segundo script que mantener, para hacer lo mismo que el plugin ya instalado.
- **`uv run --project backend novela`.** Alarga cada orden, y el `allow` y el bucle tendrían que casar esa forma.
- **Contar los intentos en la conversación.** Se compacta y no sobrevive a una reanudación. `harness.log` ya tiene el dato.
- **Un octavo agente `canario` en `.claude/agents/`.** Rompe RF-01 y el orquestador podría invocarlo. `--agents` lo define solo para su sesión.
- **Separar el arranque con otro prefijo de `run_id`.** Obliga a tocar el patrón que comparte la API, por algo que un campo resuelve.

## 16. Preguntas abiertas

Ninguna. Las once de la v0.1 se resolvieron con el experimento del 2026-09-23 y el razonamiento de `docs/implementation-plans/0003-contencion/decisiones-abiertas.md`.

| Pregunta | Decisión |
|---|---|
| P-01 ¿`PreToolUse` en subagentes y los identifica? | **Sí a las dos.** RF-07 pasa a «debe»: tabla de salidas por rol en el hook |
| P-02 ¿`deny` de `Read` en subagentes, patrón, Bash? | **Sí**, con `Read(./novelas/*/canon/misterio.md)`. Bash no se da por cubierto: rama propia en el hook (RF-20) y `deny` de `Edit` y `sqlite3` como segunda capa del invariante 1 |
| P-03 ¿Permisos en `claude -p`? | **Allowlist** de tres reglas con `Edit(...)`, **`dontAsk`** en el bucle y **confianza** aceptada una vez. El bucle para si no hay avance (RF-22) |
| P-04 ¿Plugin o hook manual? ¿`session_id`? | **Plugin**, habilitado solo en `settings.local.json`, con las sesiones aisladas con `--setting-sources project,local`. **`--session-id`** existe: UUID por sesión en `harness.log` (RF-21) |
| P-05 ¿`novela` en el PATH? | **`uv tool install --editable ./backend`**, con `uv` en el PATH |
| P-06 ¿Run de arranque? | **Campo `fase`** en `Manifest`. Arquitecto y trazador comparten un run de arranque |
| P-07 ¿Quién reintenta si falla `validar` tras el editor? | **El `editor-estilo`**, sin regenerar su briefing para no romper la custodia. Cuenta contra el gate mecánico |
| P-08 ¿Canario sin octavo agente? | **`claude -p --agents`**, con un veredicto que se comprueba en disco |
| P-09 ¿Dónde va el baseline? | **En §13 de esta spec**; los valores completos, en Langfuse |
| P-10 ¿Cuenta de intentos? | **`harness.log`**, que ya registra cada subcomando con su código |
| P-11 ¿Plugins de desarrollo? | **En el ámbito de usuario**, donde ya están. Las sesiones del harness no los cargan |
