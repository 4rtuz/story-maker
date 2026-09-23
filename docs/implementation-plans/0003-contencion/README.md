# Plan de implementación — spec 0003

Cómo se construye `.claude/` y cómo se cierran los cinco cambios de backend que pide la spec
`docs/specs/0003-contencion-y-bucle-en-claude.md`. La spec dice **qué** hay que hacer y cómo se
comprueba. Este plan dice **en qué orden**, qué test abre cada ciclo y dónde cae cada commit.

**Si el plan y la spec se contradicen, manda la spec.** Este directorio es ruta de ejecución, no
contrato. Cuando la spec pase a `implementada`, se borra entero, `decisiones-abiertas.md` incluido.

## Los siete documentos

| Fase | Fichero | Qué construye | Utilizable al terminar |
|---|---|---|---|
| 1 | [fase-1-agentes.md](fase-1-agentes.md) | `.claude/agents/` y el test de contrato CA-01/02 | Los siete roles existen, y CI detecta si derivan |
| 2 | [fase-2-barreras.md](fase-2-barreras.md) | hook `PreToolUse`, `.claude/settings.json` y sus tests | Los invariantes 1 y 3 tienen tres capas |
| 3 | [fase-3-procedencia.md](fase-3-procedencia.md) | `fase`, `sucio`, `hashes_claude`, `sesion=` y `novela comprobar-entorno` (TDD) | El capítulo 1 se atribuye a su canon real, y el entorno se comprueba antes de lanzar |
| 4 | [fase-4-procedimientos.md](fase-4-procedimientos.md) | los tres slash commands | El orquestador tiene procedimiento |
| 5 | [fase-5-trazado-y-canario.md](fase-5-trazado-y-canario.md) | plugin de Langfuse y canario de contención | Las barreras se prueban dentro de un subagente real |
| 6 | [fase-6-puesta-en-marcha.md](fase-6-puesta-en-marcha.md) | los tres pasos de máquina y el bucle desatendido | `claude -p` puede correr sin nadie delante |
| 7 | [fase-7-novela-de-humo.md](fase-7-novela-de-humo.md) | `humo-0003` y el baseline | La spec pasa a `implementada` |

Cada fase se lee sola. Este README es lo único que se lee siempre.

## Orden de ejecución: 1 → 2 → 3 → 4 → 6 → 5 → 7

La numeración es la de la spec §5, y se conserva para que los RF y CA casen. El orden de trabajo
cambia en un punto: **la fase 6 va antes que la 5**.

- El canario (fase 5) lanza `claude -p` con los flags del bucle. Sin la confianza aceptada
  (paso 3 de la fase 6), el `allow` del proyecto se ignora (E-6) y el `Agent` que invoca al
  canario se deniega. El canario fallaría por la razón equivocada y daría un verde falso.
- El hook del plugin de Langfuse necesita `uv` en el PATH (E-11), que es el paso 1 de la fase 6.

El **código** del canario se puede escribir antes, pero no ejecutarse.

Dependencias duras, las únicas que obligan a un orden:

| Fase | Necesita terminada | Por qué |
|---|---|---|
| 2 | 1 | La tabla de salidas del hook se contrasta con la de los agentes en el mismo test |
| 4 | 1 y 3 | Los procedimientos nombran a los agentes, y sin el run de arranque `/novela-nueva` rompe la atribución del capítulo 1 |
| 5 | 2 y 6 | El canario prueba las barreras, y necesita la máquina preparada |
| 7 | todas | Es la aceptación de todo lo anterior |

La 3 es independiente de la 1 y la 2. Si hay dos personas, una hace 1→2 y la otra la 3.

## Estado de partida

- `.claude/` no existe. `ls .claude` → «No such file or directory».
- `.gitignore` ya ignora `novelas/` y `.claude/settings.local.json`. No hay que tocarlo.
- El backend de la 0001 está entero en esta rama (`spec-0003`, que sale de `spec-backend`). Se
  tocan `novela/dominio/artefactos.py` (`Manifest`), `novela/plataforma/run.py`,
  `novela/slices/briefing/cmd.py`, `novela/cli.py` y `api/openapi.json`, que se regenera. Se crea
  un slice nuevo, `novela/slices/entorno/`.
- La spec está en `aceptada` (v0.3). La v0.3 incorporó los 16 fallos de `validators.md` §4.17
  que no tenían spec (su §16, «Enmiendas de la v0.3»). Este plan ya los incluye.
- `docs/definitions.md` no describe el manifiesto. La condición de la spec §14 («`definitions.md`
  §6 si describe el manifiesto») no se da, así que no se toca.
- El frontend está vacío. El OpenAPI regenerado no tiene consumidor que ajustar.

## Convenciones

Aplican a todas las fases. Escritas aquí una vez; las fases no las repiten.

**Dos tipos de trabajo, dos procesos (de `AGENTS.md`).**

| Qué | Proceso | Fases |
|---|---|---|
| Código: hook, `run.py`, `Manifest`, tests de contrato, canario | TDD: rojo visto, verde, refactor, `uv run pytest` + `mypy --strict` + `ruff` | 1 (test), 2, 3, 5 (canario) |
| Prosa: cuerpos de agente, slash commands, docs | Spec y novela de humo. **Sin TDD**: no es determinista | 1 (cuerpos), 4, 6, 7 |

Los tests de contrato de la fase 1 **sí** son TDD: verifican el frontmatter y la presencia de las
salidas, que son deterministas. Lo que no se prueba es el estilo del prompt.

**Un commit es un ciclo cerrado. No se commitea en rojo.** Cada tarea lleva su mensaje sugerido.

**Docs de referencia en el mismo commit que lo que los cambia.** La spec §14 enumera los
desfases. Este plan reparte cada uno en la tarea que lo provoca, no en un commit de limpieza al
final. La tabla de abajo es el índice.

**El prompt de un agente se cambia en su fichero y se commitea.** El sha es lo que atribuye un
cambio de calidad (`CLAUDE.md`). Desde la fase 3, además, `manifest.json` registra `sucio` y el
hash de cada fichero, así que una ejecución con el árbol sucio queda marcada.

**Ningún test llama a un modelo.** El canario (fase 5) sí lo hace, y por eso no se llama
`test_*` ni lo recoge pytest.

**Entorno de esta máquina** (memoria del proyecto): `uv` vive en
`AppData\Roaming\Python\Python312\Scripts` y no está en el PATH hasta la fase 6. Hasta entonces,
exportarlo antes de `uv` y antes de `git commit`, porque el pre-commit lo usa.

## Matriz RF → fase → tarea

| RF | Qué exige | Fase | Tarea |
|---|---|---|---|
| RF-01 | Siete ficheros, `name` = fichero | 1 | 1.1, 1.2 |
| RF-02 | `tools` exacto, sin herramientas prohibidas | 1 | 1.1, 1.2 |
| RF-03 | `model` exacto | 1 | 1.1, 1.2 |
| RF-04 | El cuerpo nombra sus salidas | 1 | 1.1, 1.2 |
| RF-05 | Hook: nada bajo `estado/` salvo `deltas/NN.json`, normalizado también a la Win32 | 2 | 2.2 |
| RF-06 | Hook: falla cerrado con exit 2 | 2 | 2.1 |
| RF-07 | Hook: cada rol solo en sus salidas | 2 | 2.3 |
| RF-08 | Los cuatro `deny` | 2 | 2.6 |
| RF-09 | Sin claves, `enabledPlugins`, `env` ni `bypassPermissions` | 2 | 2.6 |
| RF-10 | `allow` exacto | 2 | 2.6 |
| RF-11 | Run de arranque que nadie más reutiliza | 3 | 3.1 |
| RF-12 | `sucio` y `hashes_claude` en el manifiesto, con `CLAUDE.md` y `AGENTS.md` | 3 | 3.2 |
| RF-13 | `/novela-nueva` | 4 | 4.2 |
| RF-14 | `/novela-continuar` | 4 | 4.3 |
| RF-15 | Prompts de Task mínimos | 4 | 4.1 |
| RF-16 | `/novela-auditar` | 4 | 4.4 |
| RF-17 | Trazado en el bucle, sin nada versionado | 5 | 5.1 |
| RF-18 | Canario: cinco intentos que fallan, dos controles que pasan, veredicto en disco y transcript | 5 | 5.2, 5.3 |
| RF-19 | Novela de humo con `checkpoints/03.json` y baseline | 7 | 7.2, 7.4 |
| RF-20 | Hook: regla de órdenes para `Bash` y `PowerShell` | 2 | 2.4 |
| RF-21 | `sesion=<uuid>` en `harness.log`, sin alterar lo que se cuenta | 3 | 3.3 |
| RF-22 | El bucle para sin avance de checkpoint | 6 | 6.2, 6.3 |
| RF-23 | `AGENTS.md` documenta la puesta en marcha | 6 | 6.2 |
| RF-24 | Cada agente nombra su esquema, y el esquema existe | 1 | 1.1, 1.2 |
| RF-25 | Hook: la sesión principal solo escribe `intervencion.md` en `novelas/` | 2 | 2.3b |
| RF-26 | Hook: con `NOVELA_SESSION_ID`, solo los siete y `canario` | 2 | 2.4b |
| RF-27 | `NOVELA_RUN_ID` a un run de otro capítulo o fase aborta | 3 | 3.1 |
| RF-28 | `novela comprobar-entorno [--limpio]` | 3 | 3.4 |
| RF-29 | Tres reglas de lectura y tabla de códigos en los procedimientos | 4 | 4.2, 4.3 |
| RF-30 | El bucle comprueba el entorno; las sesiones interactivas llevan `NOVELA_SESSION_ID` | 6 | 6.2 |
| RF-31 | Ensayo de intervención y `/memory` en la novela de humo | 7 | 7.2, 7.3 |

Los 19 criterios de aceptación van nombrados en la tarea que los cierra.

## Docs de referencia: qué tarea toca qué

La lista de la spec §14, repartida. Cada línea va en el commit de su tarea.

| Documento y sección | Cambio | Tarea |
|---|---|---|
| `architecture.md` §3.1 | Árbol de `.claude/`: `agents/`, `commands/`, `hooks/`, `settings.json` | 1.3 (agents), 2.7 (hooks, settings), 4.5 (commands) |
| `architecture.md` §3.1, línea del `manifest.json` | Quitar «sesión de Claude Code»: la sesión va al log, no al manifiesto | 3.3 |
| `architecture.md` §6.3, §7.4 | Revisar que no describan un contrato sin fichero | 1.3 |
| `architecture.md` §7.5 | Entradas: el esquema de salida de cada agente (ver fase 1, «hueco») | 1.3 |
| `architecture.md` §7.1 | Regla del hook con la excepción del `cronista` | 2.7 |
| `architecture.md` §12.7 | Se cierra: el `deny` existe | 2.7 |
| `architecture.md` §12.2 | Se cierra: `sesion=` en `harness.log` | 3.3 |
| `architecture.md` §10.1, §10.2 | Plugin, sin `TRACE_TO_LANGFUSE`; `session_id` fijado desde fuera | 5.1 |
| `architecture.md` §2.3, §11.1 | Bucle nuevo y puesta en marcha | 6.2 |
| `architecture.md` §8 y `AGENTS.md` «CLI» | `novela comprobar-entorno [--limpio]`, una línea | 3.4 |
| `validators.md` §2 | Qué corre de verdad: se actualiza en cada fase que enciende un método | 1.3, 2.7, 5.4, 7.5 |
| `validators.md` §3.8 | Tercer contrato, Harness ↔ Claude Code, ya en CI | 2.7 |
| `validators.md` §4.17 | Cada fila F-NN marcada `0003` pasa a `activo` en el commit que la cierra. Las `propuesto` no se implementan sin enmendar antes la spec | la tarea de su CA |
| `validators.md` §4.4 | Guardarraíl real: hook + `deny` | 2.7 |
| `validators.md` §4.9 | Canario con `--agents` | 5.4 |
| `CLAUDE.md` «Hooks» | Regla del hook con la excepción; trazado por plugin (`Stop` y `SessionEnd`) | 2.7, 5.1 |
| `CLAUDE.md` «Claves y trazado» | Sin `TRACE_TO_LANGFUSE` | 5.1 |
| `CLAUDE.md` «Bucle por capítulo» | Segundo `validar` tras el editor; `cronista` después del gate | 4.5 |
| `CLAUDE.md` y `AGENTS.md`, bucle desatendido | El de la spec §5.6 | 6.2 |
| `AGENTS.md` «Puesta en marcha» | Los tres pasos | 6.2 |

`CLAUDE.md` y `AGENTS.md` se cargan en cada sesión y en cada subagente. Cada edición **sustituye**
texto; ninguna añade una sección nueva salvo los tres pasos de puesta en marcha, que la spec exige
(RF-23).

## Decisiones que toma este plan

La spec v0.2 no decía nada sobre estos puntos. Las marcadas con **(spec)** subieron a la v0.3 y
ya son contrato; el resto sigue siendo decisión de implementación, barata de revertir.

| # | Decisión | Motivo | Tarea |
|---|---|---|---|
| D-1 **(spec)** | El cuerpo de cada agente nombra la ruta de su esquema de salida en `backend/schemas/` | El briefing no incrusta esquemas (`assemble.py` no los toca), y la salida estructurada se exige «JSON válido contra su esquema». Leer dentro del proyecto no pide permiso | 1.2 |
| D-2 | La tabla de salidas por rol vive literal en el hook y en el test de contrato, y el test compara las dos | El hook no puede importar `backend/` (spec §4). Una copia vigilada por un test es más barata que generar código | 2.3 |
| D-3 | El hook compara rutas siempre sin distinguir mayúsculas, también en Linux | Denegar de más en Linux es inocuo. Una sola rama en vez de dos, y la propiedad de CA-03 no depende del sistema | 2.2 |
| D-4 | El hook lee `notebook_path` para `NotebookEdit` | `NotebookEdit` no trae `file_path`; sin esto, RF-06 lo denegaría siempre, y RF-05 lo nombra | 2.1 |
| D-5 **(spec)** | `sesion=<uuid>` va justo después de la marca de tiempo | No choca con las causas, que van al final tras `·`, y no altera las subcadenas `validar NN -> 1` que cuenta el procedimiento | 3.3 |
| D-6 **(spec)** | Sin git disponible, `sucio` es `true` | Conservador: un manifiesto que no puede probar que el árbol estaba limpio no lo afirma | 3.2 |
| D-7 | `/novela-continuar` sin `--capitulos` hace un capítulo | Es el modo desatendido y el que menos cuesta si falla. En interactivo se pasa `N` a mano | 4.3 |
| D-8 | Reanudación por tres marcas de disco, y si no, desde el `escritor` | Ver fase 4, tarea 4.3 | 4.3 |
| D-9 **(spec)** | Un `intervencion.md` está resuelto cuando tiene una línea `resuelto: <sha o motivo>` | La spec manda parar ante uno «sin resolver» y no dice cómo se resuelve. Borrarlo perdería el registro | 4.3, 7.2 |

## Riesgos que la implementación va a encontrar

1. **El hook falla abierto si `python` no resuelve.** Claude Code trata un código distinto de 2
   como no bloqueante, y «command not found» no es 2. En esta máquina `python3` es el alias de la
   Microsoft Store (E-11). El hook se registra con `python`. `novela comprobar-entorno` lo
   comprueba antes de cada bucle y del canario, y el primer intento del canario lo detectaría.
2. **`--setting-sources project,local` y un plugin instalado en el ámbito de usuario.** El plugin
   está instalado en `~/.claude/plugins`, pero se habilita en `settings.local.json`. Nadie ha
   comprobado que se cargue con `user` fuera de las fuentes. Es la primera comprobación de la
   tarea 5.1; si falla, se para y se enmienda la spec (RF-17 es «debería»).
3. **`--agents` y un nombre de agente del proyecto.** Si no sustituye al `escritor` del proyecto,
   el cuarto intento del canario lo haría el `escritor` real. La tarea 5.2 lo detecta con un
   nonce y lo anota en la spec (`decisiones-abiertas.md`, P-08).
4. **La regla 5 del hook depende de que el hook herede el entorno de `claude`.** Nadie lo ha
   comprobado. Si no lo hereda, la regla no se activa nunca y CA-15 (que fija el entorno del
   subproceso) pasa igual. Lo detecta el quinto intento del canario (tarea 5.3); si falla por
   eso, se anota en la spec y la regla se reformula antes de aceptar CA-09.
5. **`--setting-sources project,local` puede no excluir la memoria de usuario.** Lo comprueba
   `/memory` en la novela de humo (CA-19). No se mitiga en esta spec.

## Qué queda fuera

De la spec §1, y no se toca en ninguna fase: todo lo de la 0002 (`novela gate`, trayectoria,
canario del orquestador, QA saneado), la cola en disco y `run.sh`, los `GET` del log en vivo, el
índice recuperable, `novela budget` y la degradación por cuota, la calidad de los prompts más allá
de la novela de humo, y el frontend.
