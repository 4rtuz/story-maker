# Fase 5: trayectoria del orquestador

Plan: `README.md` · Spec: §5.5, RF-13, RF-20, RF-21, RF-22, RF-24, §8.7, RNF-01, RNF-04, RNF-05, RNF-07 · Decisiones: D-6, D-7, D-12, D-13, D-14, D-21 · Depende de: fases 3 (gate, código 5, parser del log) y 4 (ocho agentes, sondas y auditoría de acto en el orden)

Seis ciclos. Los supuestos sobre el transcript y el hook `Stop` ya están verificados (spec §4, PA-3 del README): la entrada del `Stop`, la forma de un resultado de `Bash`, el nombre `Agent` de la herramienta de subagentes y las marcas de compactación. Se anotan en `validators.md` §5.10 en el commit de 5.1.

Ningún fixture de transcript lleva prosa: se construyen a mano con la forma de la spec §4 y textos de relleno (D-12), y usan `Agent`, que es el nombre de `humo-0003`. Los transcripts reales de `humo-0003` solo sirven para comprobar la forma, en local.

---

#### 5.1 Lector de transcript tolerante y tramos por capítulo (RF-20, RF-22, D-12)

- **Descripción.** Nuevo `backend/novela/slices/trayectoria/transcript.py`, puro:
  - Modelos `EntradaTranscript`, `Mensaje`, `Uso`, `ToolUse`, `ToolResult` y `ToolUseResult`, con `ConfigDict(extra="ignore", frozen=True)`. `toolUseResult` puede ser un objeto (con `agentType`, `resolvedModel`, `content`, `stdout`…) o una cadena `Error: Exit code N…` (PA-3).
  - `leer(lineas) -> Transcript`, que ignora y cuenta las líneas que no validan y agrupa por `message.id`, sin repetir el `usage`.
  - `ordenes(transcript) -> list[Orden]`: cada `Bash` que empieza por `novela`, con subcomando, slug, capítulo, flags, código (de `is_error` y `Exit code N`) y el `run_id` de su salida si es un `briefing`.
  - `invocaciones(transcript) -> list[Invocacion]`: cada `tool_use` de nombre `Agent` o `Task`, con su tipo (`input.subagent_type` o `toolUseResult.agentType`), la longitud del prompt, las líneas y los caracteres del retorno y `resolvedModel`.
  - `tramos(transcript) -> list[Tramo]`:
    - Las órdenes del arranque (`nueva`, `briefing … arquitecto|trazador`, `validar-plan` y `gate … plan`) no abren tramo.
    - El tramo de N empieza en la primera orden que nombra N y termina en la primera que nombra N+1, o al final.
    - Es «cerrado» si contiene su `checkpoint` en 0.
  - `compactaciones(transcript)`: las entradas `system` con `subtype: compact_boundary`.
- **Ficheros.**
  - `backend/novela/slices/trayectoria/__init__.py`, `transcript.py` y `test_transcript.py` (nuevos)
  - `backend/novela/slices/trayectoria/fixtures/limpio.jsonl`, `limpio-task.jsonl`, `repetido.jsonl`, `compactado.jsonl`, `reanudado.jsonl`, `arranque.jsonl` e `ilegible.jsonl` (nuevos, sin prosa)
  - `docs/validators.md` §5.10 (modificar: los supuestos de la spec §4)
- **Rojo.** `test_transcript.py`:
  - `test_message_id_repetido_cuenta_una_vez` (CA-22): dos líneas con el mismo `message.id` y el mismo `usage` suman una vez.
  - `test_tramos_de_una_sesion_limpia`: un tramo del 8, cerrado, que incluye las órdenes tras su `checkpoint`.
  - `test_tramo_reanudado_empieza_en_la_primera_orden`, con la forma del capítulo 3 de `humo-0003`, que empieza por `briefing 03 continuista`.
  - `test_sesion_de_arranque_no_tiene_tramo`.
  - `test_agent_y_task_se_leen_igual`.
  - `test_lineas_ilegibles_se_cuentan_y_no_rompen`.
  - `test_codigo_de_salida_de_bash`: el objeto con `stdout` da 0, y la cadena `Error: Exit code 5…` da 5.

  Fallan hoy por `ModuleNotFoundError`.
- **Verde.** El módulo.
- **Refactor.** —
- **Commit.** `feat(trayectoria): el transcript se lee con modelos tolerantes y se parte en tramos por capítulo`
- **Cubre.** RF-20 y RF-22 (lectura).
- **Depende de.** fase 4
- **Hecho cuando.** Los tests pasan tras verse en rojo; en local, los transcripts reales de las sesiones de capítulo de `humo-0003` (`~/.claude/projects/*/<sesión>.jsonl`) se leen sin líneas ilegibles de tipo `assistant` o `user`, y la suma de sus invocaciones `Agent` es la que dio la revisión de la spec (17).
- **Complejidad.** M
- **Docs.** `validators.md` §5.10.

#### 5.2 Comprobaciones de §8.7 y `trayectoria-NN.json` (RF-13, RF-20, RF-22, RF-24, RNF-07)

- **Descripción.**
  - `backend/novela/slices/trayectoria/comprobaciones.py`, puro: `comprobar(tramo, previos: Mapping[str, str], agentes_previos: frozenset[str], ultimo_de_acto: bool, slug) -> ResultadoTramo`, con:
    - **Orden**: cada invocación de subagente tiene antes su `briefing` en 0. Para la sonda del briefing, el del `escritor`; para la del texto, `sonda … texto` con 1. `validar` va antes de los revisores y `validar --final` después del editor, `gate … revision` antes del `cronista`, y `aplicar-delta` antes de `checkpoint`. Si `ultimo_de_acto`, tras el `checkpoint` van `sonda … texto` y `auditar --acto`.
    - **Lo que no deja artefacto**:
      - Un `Read`, `Bash` o `PowerShell` sobre `capitulos/`. Las demás lecturas de la sesión principal no cuentan.
      - Un `Write` o un `Edit` en el workspace, salvo `runs/*/intervencion.md`.
      - Una invocación de un tipo que no es de los ocho.
      - Un prompt de más de 2.000 caracteres.
      - Un retorno de más de 3 líneas no vacías o de más de 1.000 caracteres.
      - Un capítulo cerrado sin alguno de los cinco agentes del bucle (RF-24), sobre la unión con `agentes_previos` de otras sesiones.
    - **Contexto**: el máximo por mensaje distinto, con aviso por encima de 70.000; una compactación dentro del tramo es violación.
    - **Modelos** (RF-13): `message.model` del orquestador y `toolUseResult.resolvedModel` por agente. `previos` da, para el orquestador y para cada agente, el modelo de la trayectoria anterior más reciente en la que ese agente aparece. Si difiere, la violación es `modelo_cambiado`.
  - Modelo `Trayectoria` en `backend/novela/dominio/artefactos.py`: `capitulo`, `run_id`, `sesiones: dict[str, EntradaSesion]` (clave `NOVELA_SESSION_ID`, con el `session_id` del transcript como campo) y `violaciones`, solo con ids, nombres de herramienta, longitudes y cuentas (RNF-07). Se registra en `esquemas.py` como `trayectoria.schema.json`.
- **Ficheros.**
  - `backend/novela/slices/trayectoria/comprobaciones.py` y `test_comprobaciones.py` (nuevos)
  - `backend/novela/slices/trayectoria/fixtures/*.jsonl` (nuevos: uno por violación, con `Agent`)
  - `backend/novela/dominio/artefactos.py` y `esquemas.py` (modificar)
  - `backend/schemas/trayectoria.schema.json` (nuevo, generado)
  - `docs/validators.md` §4.16 y §4.13, `docs/definitions.md` §6 (modificar)
- **Rojo.** `test_comprobaciones.py`:
  - `test_cada_violacion` (CA-20): parametrizado, un fixture por comprobación de §8.7 produce exactamente su violación, incluida la falta de `sonda … texto` o de `auditar --acto` tras el último capítulo de un acto.
  - `test_transcript_limpio`: ninguna. Con lecturas de `checkpoints/latest.json` y de `runs/*/intervencion.md`, y un `Write` de `runs/r-…/intervencion.md`, tampoco.
  - `test_agent_y_task_dan_la_misma_trayectoria` (CA-20).
  - `test_modelo_cambiado` (CA-13): dos transcripts de capítulos seguidos con distinto `resolvedModel` del escritor; la segunda trayectoria lo registra.
  - `test_modelo_contra_la_ultima_trayectoria_con_ese_agente` (RF-13): una `sonda` que aparece en el capítulo 1 y en el 4, con el mismo modelo, no da violación aunque no aparezca en el 2 ni en el 3; con otro modelo, sí.
  - `test_compactacion_en_tramo` (CA-22).
  - `test_capitulo_cerrado_sin_lector_suspense` (CA-24).
  - `test_reanudado_no_da_agente_ausente` (CA-20): la unión de dos sesiones.
  - `test_sin_texto` (RNF-07): el JSON serializado no contiene ninguno de los textos de relleno de los prompts ni de los retornos del fixture.

  Fallan hoy por `ModuleNotFoundError`.
- **Verde.** El módulo, el modelo y el esquema.
- **Refactor.** Los umbrales (70.000, 2.000, 1.000 y 3), como constantes de módulo, porque son provisionales (spec §13).
- **Commit.** `feat(trayectoria): comprobaciones de orden, contexto y modelos sobre el tramo de cada capítulo`
- **Cubre.** RF-13, RF-20, RF-22, RF-24 (test), RNF-07.
- **Depende de.** 5.1
- **Hecho cuando.** CA-13, CA-20 (mitad pura), CA-22 y CA-24 (test) pasan tras verse en rojo; `trayectoria.schema.json` commiteado.
- **Complejidad.** L
- **Docs.** `validators.md` §4.16 (estado real: «uno de los ocho», sin «nivel de degradación registrado») y §4.13 (el modelo resuelto lo registra la trayectoria y para vía intervención); `definitions.md` §6 (`trayectoria-NN.json`).

#### 5.3 `novela trayectoria [--transcript <ruta>]` (RF-20, RNF-01, RNF-04, RNF-05, D-6, D-12, D-21)

- **Descripción.** `backend/novela/slices/trayectoria/cmd.py::trayectoria`:
  - Sin `NOVELA_SESSION_ID`, sale con 0 sin leer nada.
  - Lee `transcript_path` y `session_id` de stdin (D-12), o usa `--transcript`. No usa `cwd`. Un stdin ilegible sale con 1, nunca con 2.
  - Por cada tramo:
    - Resuelve el workspace con `WorkspaceRepository.resolver(slug)` y toma `ws.bloquear()`. Ocupado → stderr y sigue.
    - Localiza el run con `run.existente` (D-7).
    - Construye `previos` recorriendo hacia atrás los `trayectoria-*.json` de los runs de los checkpoints anteriores, y `agentes_previos` de las otras sesiones de `trayectoria-NN.json`. `ultimo_de_acto` sale de `plan/escaleta.md`.
    - Repetición (D-6): si la última línea del log del run es `trayectoria NN` con la misma sha del tramo, no hace nada.
    - Si no, fusiona su entrada de sesión en `trayectoria-NN.json` (atómico) y registra `trayectoria NN -> 0 · entradas=<sha>`. Con violaciones, y solo si su entrada cambió, `intervencion.escribir`.
    - Emite `trayectoria` y `contexto_max` por el `ScoreSink` (D-21).
  - Todo error por tramo se captura y va a stderr.
  - Registro en `cli.py`, fuera de `con_codigos`, o con una envoltura que convierte cualquier excepción en 1 para que nunca salga con 2.
- **Ficheros.**
  - `backend/novela/slices/trayectoria/cmd.py` y `test_trayectoria.py` (nuevos)
  - `backend/novela/cli.py` (modificar)
  - `AGENTS.md` «CLI», `docs/architecture.md` §10.5, `docs/validators.md` §4.17 F-08, F-33 y F-53 (modificar)
- **Rojo.** `test_trayectoria.py`:
  - `test_sin_sesion_no_escribe` (CA-20): sin la variable, el workspace queda con la misma huella.
  - `test_escribe_trayectoria_e_intervencion`: sobre `demo-24` y un transcript fixture que nombra `demo-24 8` con una lectura de `capitulos/`, crea `runs/<run>/trayectoria-08.json`, con la clave `NOVELA_SESSION_ID` y el `session_id` del transcript como dato, e `intervencion.md` viva.
  - `test_repetido_no_escribe_otra_linea` (RNF-04), y `test_otra_linea_en_medio_no_duplica_la_intervencion`.
  - `test_no_usa_cwd`: con un `cwd` falso en stdin, resuelve el workspace por el slug.
  - `test_stdin_ilegible_sale_con_1`.
  - `test_lock_ocupado_sale_con_0_sin_escribir`, con `lock_ajeno` de `backend/conftest.py:45-65`.
  - `test_scores_sin_red` (RNF-05), con `urlopen` parcheado: `trayectoria` y `contexto_max`.
  - `test_diez_megas_en_menos_de_5_s` (RNF-01), con un transcript sintético de 10 MB generado en `tmp_path`.
  - `test_sin_texto_de_prompt_ni_retorno` (CA-20, RNF-07).

  Fallan hoy porque no existe la orden.
- **Verde.** La orden.
- **Refactor.** —
- **Commit.** `feat(trayectoria): novela trayectoria audita la sesión y escribe su veredicto en runs/`
- **Cubre.** RF-20, RF-13 (registro), RNF-01, RNF-04, RNF-05, RNF-07.
- **Depende de.** 5.2, 3.1, 3.2
- **Hecho cuando.** Los tests pasan tras verse en rojo; `uv run novela trayectoria < /dev/null` con `NOVELA_SESSION_ID` definida sale con 1, no con 2.
- **Complejidad.** L
- **Docs.** `AGENTS.md` «CLI» (`novela trayectoria [--transcript <ruta>]`); `architecture.md` §10.5 (scores `trayectoria` y `contexto_max`); `validators.md` §4.17, F-08, F-33 y F-53 (activos: auditoría de trayectoria).

#### 5.4 Hook `Stop` en `.claude/settings.json` (RF-20)

- **Descripción.**
  - `.claude/settings.json` gana `hooks.Stop: [{"hooks": [{"type": "command", "command": "novela trayectoria"}]}]`. La entrada que recibe es la de la spec §4.
  - `test_settings_de_claude` (`backend/tests/test_contratos.py:246-260`) desempaqueta `PreToolUse` y además exige el registro `Stop` con esa orden.
  - `comprobar-entorno` ya comprueba que `novela` arranca (`backend/novela/slices/entorno/cmd.py:1-2`).
- **Ficheros.**
  - `.claude/settings.json` (modificar)
  - `backend/tests/test_contratos.py` (modificar)
  - `CLAUDE.md` «Hooks», `docs/architecture.md` §10.1, `docs/validators.md` §6 (modificar)
- **Rojo.** `test_contratos.py::test_settings_de_claude`, ampliado: `settings["hooks"]["Stop"]` existe, lleva una sola orden y empieza por `novela trayectoria`. Falla hoy porque la clave no existe.
- **Verde.** El registro.
- **Refactor.** —
- **Commit.** `feat(hooks): el hook Stop audita la trayectoria al final de cada turno`
- **Cubre.** RF-20.
- **Depende de.** 5.3
- **Hecho cuando.** El test pasa tras verse en rojo. En una sesión desechable del harness con `NOVELA_SESSION_ID`, un turno sin órdenes `novela` no deja nada en `novelas/`, y `~/.claude/state/langfuse_hook.log` sigue recibiendo sus trazas.
- **Complejidad.** S
- **Docs.** `CLAUDE.md` «Hooks» (un `Stop` propio además del de Langfuse); `architecture.md` §10.1; `validators.md` §6, fila «Fin de sesión, hook `Stop`».

#### 5.5 Freno en `pendiente` (RF-21, D-13)

- **Descripción.**
  - `backend/novela/slices/estado/cmd.py::pendiente` (`:54-60`) aplica D-13, en este orden:
    - `intervencion.vivas(ws)` → 5.
    - Novela terminada → 1.
    - La trayectoria del último cerrado ausente, o sin la entrada de la sesión que lo cerró, y esa sesión es distinta de `NOVELA_SESSION_ID` → 5. La sesión que lo cerró sale de la línea `checkpoint NN -> 0` del run del checkpoint, con `run.parsear`.
  - Sigue sin tomar el lock ni escribir, como dice su docstring (`:1`).
  - El paso 1 de `/novela-continuar` deja de buscar a mano `intervencion.md`: lo hace `pendiente`. La regla de lectura 3 se conserva para el operador.
- **Ficheros.**
  - `backend/novela/slices/estado/cmd.py` (modificar)
  - `backend/novela/slices/estado/test_estado.py` (modificar)
  - `.claude/commands/novela-continuar.md` (modificar el paso 1)
  - `AGENTS.md` «CLI», `docs/architecture.md` §2.3, `docs/validators.md` §4.4, §4.17 F-34 y §6 (modificar)
- **Rojo.** `test_estado.py`:
  - `test_pendiente_intervencion_viva` (CA-21): con un `intervencion.md` sin `resuelto:` → 5, y con `resuelto:` → 0.
  - `test_pendiente_trayectoria_ausente` (CA-21): con el último cerrado sin trayectoria y cerrado por la sesión `A` → 5 con `NOVELA_SESSION_ID=B` y 0 con `A`.
  - `test_pendiente_sin_sesion_en_el_log`: exento.
  - `test_pendiente_codigos` (`:42-48`), sin cambios.

  Fallan hoy porque `pendiente` solo mira el checkpoint.
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(pendiente): el bucle para con una intervención viva o sin la trayectoria del último capítulo`
- **Cubre.** RF-21, RF-29 (`pendiente`).
- **Depende de.** 5.3, 3.1
- **Hecho cuando.** CA-21 pasa tras verse en rojo; `test_bucle.py::test_bucle_completo_con_agente_falso` sigue esperando 1 (terminada) sin salida; sobre `humo-0003`, en local, `novela pendiente humo-0003` sale con 1 (README §7.4).
- **Complejidad.** M
- **Docs.** `AGENTS.md` «CLI» (`novela pendiente <slug>`: 0 quedan, 1 terminada, 5 intervención); `architecture.md` §2.3 (el `while` para también con 5); `validators.md` §4.4 (las dos filas de `pendiente`: el código es 5, y la trayectoria ausente solo cuenta con otra sesión), §4.17, F-34 (activo: `pendiente`) y §6, fila `novela pendiente`.

#### 5.6 Política de cuota sin niveles que toquen capítulos cerrados (RF-24)

- **Descripción.**
  - `docs/architecture.md` §9 (`:746-762`) pierde `novela budget` (`:752`) y los niveles 2 a 4 (`:757-759`). Queda «parada limpia en checkpoint» como única política, y la frase de que `continuista` y `cronista` no se degradan se amplía a los cinco agentes del bucle.
  - `docs/validators.md`:
    - §3.9.7 deja de describir los niveles 2 y 4 como vigentes.
    - §4.4 pierde la fila de `novela budget` («fija el nivel de degradación y lo escribe en el manifiesto»).
    - §4.12 pierde el ensayo de degradación por cuota y se queda con el de reanudación.
    - §4.13 pierde «por nivel 3» en la frase de los huecos de `tension_real`: un hueco ya solo viene de un `qa/NN-suspense.json` ilegible.
  - El test de RF-24 ya está en 5.2.
- **Ficheros.**
  - `docs/architecture.md` y `docs/validators.md` (modificar)
- **Rojo.** No aplica: es documentación. CA-24 lo cierra la revisión del commit, y su test (`test_capitulo_cerrado_sin_lector_suspense`) ya está en verde desde 5.2.
- **Verde.** El texto.
- **Commit.** `docs(arquitectura): sin novela budget, la única política de cuota es parar en un checkpoint`
- **Cubre.** RF-24.
- **Depende de.** 5.2
- **Hecho cuando.** `rg -n "novela budget|en lote|fronteras de acto y capítulos con revelación|nivel 3" docs/architecture.md docs/validators.md` no devuelve nada vigente en §9 ni en `validators.md` §3.9.7, §4.4, §4.12 y §4.13, y la revisión del PR lo confirma (CA-24).
- **Complejidad.** S
- **Docs.** Es la tarea.
