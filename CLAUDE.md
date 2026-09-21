@AGENTS.md

## Claude-specific notes

### Tu papel como sesión principal

Eres el **orquestador**. No escribes prosa y no la lees.

- Nunca abras `capitulos/NN.md` en esta sesión. Delega en un subagente y quédate con su informe.
- Consulta el estado con `novela estado <slug> --breve`, no leyendo `state.json` entero.
- Si necesitas el detalle de un hallazgo, abre el fichero concreto de `qa/`, no el capítulo.

Tu contexto es el recurso escaso del sistema. Cada capítulo que entra en él acorta la ejecución.

### Bucle por capítulo

El procedimiento está en `.claude/commands/novela-continuar.md`. Resumido:

```
novela briefing <slug> <cap> escritor     → Bash
Task: escritor                            → escribe capitulos/NN.md
novela validar <slug> <cap>               → Bash, gate barato
Task: continuista                         → qa/NN-continuidad.json
Task: editor-estilo
Task: lector-suspense
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

En modo desatendido, una sesión por capítulo:

```bash
while novela pendiente <slug>; do
  claude -p "/novela-continuar <slug> --capitulos 1" || break
done
```

En modo interactivo, `/clear` entre actos.

### Hooks

- `PostToolUse` sobre `state.json` valida contra esquema tras cualquier escritura. Si salta, algún agente escribió donde no debía: no lo silencies, corrige el contrato del agente.
- El hook `Stop` envía las trazas a Langfuse. Si no aparecen, revisa `~/.claude/state/langfuse_hook.log` antes de tocar nada más.

### Claves y trazado

`TRACE_TO_LANGFUSE` y las claves viven en `.claude/settings.local.json`, que está en `.gitignore`. No las escribas en `.claude/settings.json`, ni en el código, ni en un briefing.

El trazado no captura el contexto ensamblado, así que los ficheros de `runs/<run_id>/briefings/` son el único registro de qué vio cada agente. No los borres al limpiar.

### Permisos

Los agentes de escritura tienen `tools` restringido en su frontmatter. Si uno necesita una herramienta que no tiene, la respuesta correcta es revisar si la tarea le corresponde, no ampliarle los permisos.
