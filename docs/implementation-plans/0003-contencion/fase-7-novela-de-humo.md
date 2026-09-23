# Fase 7 — Novela de humo

**Objetivo.** Aceptar los procedimientos con una ejecución real, dejar el primer baseline de
scores, y cerrar la spec.

**Al terminar existe**: `novelas/humo-0003/` con `checkpoints/03.json`; el baseline en la spec
§13; la spec en `implementada`; este directorio, borrado.

**Cierra**: RF-19, RF-31, y la aceptación de RF-13 a RF-17, RF-22 y RF-30. CA-10, CA-19.

Requiere todas las fases. Es la única verificación de los procedimientos, que son prosa
(`validators.md` §5.8).

---

## 7.1 — Antes de lanzar

- Árbol limpio y commiteado. El baseline registra el sha, y un sha con el árbol sucio no atribuye
  nada. El manifiesto de cada run lo confirma con `sucio: false`.
- El canario de la fase 5 en verde **con este mismo sha** de `.claude/`. Si algo de `.claude/`
  cambió después, repite el canario.
- `novela comprobar-entorno --limpio` sale con 0 en Git Bash, y `uv --version` responde.
- Las claves de los scores en `.env`, con `TRACE_TO_LANGFUSE=true`, y las tareas 3.5 y 3.6
  hechas. Con eso, `comprobar-entorno` en 0 garantiza que `.env` está ignorado y que no falta
  ninguna clave. Sin ello, el baseline se queda sin sus seis scores (F-54).

---

## 7.2 — Ejecución

1. **Arranque, en interactivo**, con la forma de sesión del harness de la fase 6 (RF-30):

   ```bash
   export CC_LANGFUSE_TRACE_TAGS=humo-0003
   export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
   claude --session-id "$NOVELA_SESSION_ID" --setting-sources project,local --model opus
   > /memory
   > /novela-nueva humo-0003 --idea "<idea>" --capitulos 3 --palabras 9000
   ```

   **`/memory` primero** (CA-19): anota qué memorias lista. Si aparece la de usuario
   (`~/.claude/CLAUDE.md`), `--setting-sources` no la excluye. Va a la spec §13 como riesgo, con
   el contenido que cargaba; esta spec no lo mitiga.

   La idea se escoge antes y se escribe en el baseline. Al terminar: `/exit`, no `/clear`: la
   sesión siguiente es otra.

2. **Ensayo de intervención** (CA-19), antes del bucle:

   ```bash
   printf '# Intervención — ensayo\n\ngate: ensayo\n' > novelas/humo-0003/runs/<run de arranque>/intervencion.md
   ls -R novelas/humo-0003/runs > /tmp/runs-antes
   export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
   claude -p "/novela-continuar humo-0003 --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
     --setting-sources project,local --permission-mode dontAsk --model opus
   ls -R novelas/humo-0003/runs | diff /tmp/runs-antes -
   ```

   El `diff` tiene que salir vacío: la sesión paró en el paso 1 sin crear ningún run ni briefing.
   Su traza en Langfuse no tiene ninguna invocación de subagente. Después:
   `echo 'resuelto: ensayo' >> …/intervencion.md`.

   El fichero se escribe desde la shell, no desde Claude: la regla 3 del hook permitiría
   `intervencion.md`, pero el ensayo no debe depender de ninguna sesión.

3. **Bucle, en Git Bash**, el de `AGENTS.md` (fase 6) con `<slug> = humo-0003`.

4. **Si para**:
   - con `intervencion.md` → léelo; es una decisión humana. Si el defecto es de un prompt, se
     corrige en `.claude/agents/<rol>.md` y **se commitea antes de relanzar** (`CLAUDE.md`: el
     sha atribuye el cambio). Después, `resuelto: <sha>` en el `intervencion.md` y se relanza el
     bucle, que reanuda desde el checkpoint;
   - por el freno (sin avance y sin `intervencion.md`) → la sesión terminó sin hacer nada. Mira su
     traza en Langfuse y el `harness.log` del run abierto antes que nada. Las causas típicas son un
     permiso que falta, o que el orquestador no encontró el comando;
   - por `|| break` → `claude` salió con error. Su salida está en la terminal;
   - por `comprobar-entorno` → no se llegó a lanzar ninguna sesión. El hallazgo está en pantalla;
   - sin `intervencion.md` y con el CLI roto (regla de lectura 1) → la última línea de
     `harness.log` no es un `-> 1`. Es un defecto del harness, no de un agente.

   Cada parada y su causa van al baseline. Son datos, no ruido: la 0002 las necesita.

---

## 7.3 — Comprobación (CA-10)

Todo en disco o en Langfuse, nada en la conversación:

| Comprobación | Dónde |
|---|---|
| `checkpoints/03.json` existe y `novela pendiente humo-0003` sale con 1 | disco |
| Tres runs de capítulo, cada uno con los briefings de los cinco agentes (`escritor`, `continuista`, `editor-estilo`, `lector-suspense`, `cronista`) | `runs/*/briefings/` |
| Un run de arranque, `fase: "arranque"`, con `01-arquitecto.md` y `01-trazador.md` | `runs/*/manifest.json` |
| El manifiesto del capítulo 1 **no** registra `e3b0c442…` como `version_canon` | `runs/*/manifest.json` |
| Cada línea de `harness.log`, también la del run de arranque, lleva `sesion=` | `runs/*/harness.log` |
| Una traza con la etiqueta `humo-0003` por sesión (arranque, ensayo y tres del bucle), con los `session_id` de `harness.log` | Langfuse |
| Todos los manifiestos con `sucio: false` y `hashes_claude` con `CLAUDE.md` y `AGENTS.md` | `runs/*/manifest.json` |
| Ninguna traza del bucle invoca un subagente fuera de los siete | Langfuse |
| Nada escrito fuera de las salidas de cada rol | `git status` limpio fuera de `novelas/` |

Y `/novela-auditar humo-0003`, que cierra RF-16: con 0 exporta md y epub; con 1 los hallazgos
van al baseline.

---

## 7.4 — Baseline

Rellena la subsección «Baseline» de la spec §13. Los valores completos quedan en Langfuse; la
spec guarda el resumen y cómo encontrarlo (P-09):

| Campo | De dónde |
|---|---|
| Idea, sha del commit (árbol limpio), versión de Claude Code | 7.1 |
| `run_id` y `session_id` por capítulo | `runs/*/manifest.json`, `harness.log` |
| Los seis scores de `architecture.md` §10.5 por capítulo | Langfuse (los emite `ScoreSink`) |
| Palabras por capítulo | frontmatter de `capitulos/NN.md`, o `qa/NN-validacion.json` (no abras el capítulo desde la sesión principal) |
| Intentos por gate | cuenta de `harness.log`, con las tres reglas de la fase 4 |
| Intervenciones y paradas del freno, con su causa | 7.2 |
| Número de ejecuciones: 1. No sirve para aceptar cambios de prompt hasta tener varias (spec §5.7, `validators.md` §5.16) | — |
| Resultado de `/memory` y del ensayo de intervención | 7.2 |

**Commit**: `docs(spec): baseline de la novela de humo de la 0003`

---

## 7.5 — Cierre de la spec

Un solo commit, que es el que queda como `commit:` en el frontmatter de la spec:

- Spec 0003: `estado: implementada`, `commit: <sha>`, la tabla de trazabilidad de §12 completa
  (los 19 CA con su test o su evidencia) y los criterios de §11 marcados.
- Lo que la ejecución haya descubierto y la spec no decía, anotado en la spec (§13, riesgos). En
  particular, el resultado de los riesgos 2 a 5 del README: el plugin con `--setting-sources`,
  `--agents`, la herencia del entorno en el hook y la memoria de usuario.
- `validators.md` §4.17: toda fila marcada `0003` está en `activo`, o dice por qué no.
- `validators.md` §2: la foto final de qué corre. Los métodos 10, 11, 12, 14, 15, 20 y 27 que
  cita la spec §2: cada uno pasa a correr o dice por qué sigue sin hacerlo (la mayoría esperan a
  la 0002).
- **Borrar `docs/implementation-plans/0003-contencion/`**, `decisiones-abiertas.md` incluido. El
  porqué queda en el historial, como el de la 0001 (`AGENTS.md`: «se borra al implementarla»).
- La spec 0002 ya dice que depende de esta. No se toca.

**Commit**: `docs(spec): 0003 implementada`

`novelas/humo-0003/` no se versiona (está en `.gitignore`) y **no se borra**: sus briefings son el
único registro de qué vio cada agente (`CLAUDE.md`, «Claves y trazado»), y el baseline remite a
ellos.
