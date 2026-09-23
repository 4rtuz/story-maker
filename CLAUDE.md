@AGENTS.md

## Claude-specific notes

### Tu papel como sesión principal

Eres el **orquestador**. No escribes prosa y no la lees.

- Nunca abras `capitulos/NN.md` en esta sesión. Delega en un subagente y quédate con su informe.
- Consulta el estado con `novela estado <slug> --breve`, no volcando `estado.db` entero con `--json`.
- Si necesitas el detalle de un hallazgo, abre el fichero concreto de `qa/`, no el capítulo.

Tu contexto es el recurso escaso del sistema. Cada capítulo que entra en él acorta la ejecución.

### Bucle por capítulo

El procedimiento está en `.claude/commands/novela-continuar.md`. Resumido:

```
novela briefing <slug> <cap> escritor     → Bash
Task: escritor                            → escribe capitulos/NN.md
novela validar <slug> <cap>               → Bash, gate barato
novela briefing … × 3, después 3 Task     → continuista, editor-estilo, lector-suspense en un turno
novela validar <slug> <cap>               → otra vez: el editor reescribió el capítulo
gate: veredicto de qa/NN-continuidad y qa/NN-suspense
Task: cronista                            → delta de estado
novela aplicar-delta <slug> <cap>         → Bash
novela checkpoint <slug> <cap>            → Bash
```

Genera siempre el briefing **antes** de delegar. Un subagente invocado sin briefing no tiene forma de saber qué contexto le corresponde y explorará el workspace por su cuenta.

Ejecuta `novela validar` antes de los agentes de revisión. Si falla, reintenta con el escritor pasándole únicamente el informe de QA: nunca un "está mal" genérico y nunca el capítulo entero de vuelta.

Máximo dos reintentos por gate. Al tercero, escribe `runs/<run_id>/intervencion.md` y para.

### Subagentes

Están en `.claude/agents/`, uno por rol. Invócalos con Task por su nombre exacto; no improvises roles nuevos ni hagas tú el trabajo de uno de ellos «para ahorrar una llamada».

El campo `model` del frontmatter ya está fijado por rol (opus para `arquitecto`, `trazador` y `escritor`; sonnet para los de revisión; haiku para `cronista`). No lo cambies sobre la marcha.

Si modificas el prompt de un agente, hazlo en su fichero y commitea: el sha del commit es lo que permite atribuir un cambio de calidad en las trazas.

### Slash commands

```
/novela-nueva <slug> --idea "..." --capitulos 24 --palabras 80000
/novela-continuar <slug> [--capitulos N]
/novela-auditar <slug>
```

En modo desatendido, una sesión por capítulo, en Git Bash:

```bash
export MSYS_NO_PATHCONV=1                 # sin esto, "/novela-continuar" llega como ruta de Windows
export CC_LANGFUSE_TRACE_TAGS=<slug>
novela comprobar-entorno || exit 1
while novela pendiente <slug>; do
  antes=$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)
  export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
  claude -p "/novela-continuar <slug> --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
    --setting-sources project,local --permission-mode dontAsk --model opus || break
  [ "$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)" != "$antes" ] || break
done
```

En modo interactivo, `/clear` entre actos, en una sesión del harness abierta así (las de desarrollo no exportan la variable):

```bash
export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
claude --session-id "$NOVELA_SESSION_ID" --setting-sources project,local --model opus
```

### Hooks

- `PreToolUse` deniega cualquier escritura bajo `estado/` salvo `estado/deltas/NN.json`, a cada rol fuera de sus salidas, a la sesión principal en el workspace salvo `intervencion.md`, y en el bucle, cualquier subagente que no sea de los siete. Si salta, algún agente intentó escribir donde no debía: no lo silencies, corrige el contrato del agente.
- El trazado a Langfuse lo hacen los hooks `Stop` y `SessionEnd` del plugin `langfuse-observability`. Si no aparecen trazas, revisa `~/.claude/state/langfuse_hook.log` antes de tocar nada más.

### Claves y trazado

El plugin se habilita solo en `.claude/settings.local.json` (`enabledPlugins`, nada más), que está en `.gitignore`; el opt-in es tenerlo habilitado, y sus claves las guarda él en el llavero del sistema. Los scores de `novela checkpoint` leen `TRACE_TO_LANGFUSE` y las claves del entorno o de `.env` en la raíz, que git ignora. No las escribas en `.claude/settings.json`, ni en el código, ni en un briefing.

El trazado no captura el contexto ensamblado, así que los ficheros de `runs/<run_id>/briefings/` son el único registro de qué vio cada agente. No los borres al limpiar.

### Permisos

Los agentes de escritura tienen `tools` restringido en su frontmatter. Si uno necesita una herramienta que no tiene, la respuesta correcta es revisar si la tarea le corresponde, no ampliarle los permisos.

`tools` restringe capacidad y descubrimiento, no rutas: sin `Glob` ni `Grep` un agente solo alcanza lo que su briefing le nombra. Si lo que falta es una ruta, se arregla en la receta.

Los plugins y skills del repositorio son para desarrollar el harness. Ningún agente lleva `Skill`.
