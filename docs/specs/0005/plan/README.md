# Plan de implementación: Construir la fase de brief de la novela de regalo

- Spec de origen: `docs/specs/0005/spec.md` (v2, estado `aceptada`) y `docs/specs/0005/decisions.md` (D1–D20) · Fecha: 2026-09-24 · Estado: Aceptado

> **Ubicación.** El plan vive en `docs/specs/0005/plan/`, junto a la spec, según la convención de `AGENTS.md` § Proceso: modificar documentación. Este `README.md` recoge el análisis, las decisiones, el testing, la trazabilidad, los riesgos y las preguntas; cada fase va en su propio fichero.

Correspondencia de requisitos: R1–R30 ≡ RF-01–RF-30 y R31–R42 ≡ RNF-01–RNF-12. En el plan se citan con su ID original. Las tareas se numeran T<fase>.<n> y llevan entre paréntesis la tarea de la spec §12 que implementan (T-01…T-12). Las decisiones de la spec (D1–D20) no se reabren. Las de este plan se numeran PD1, PD2…

## 1. Resumen

Se añade una fase previa a `novela nueva` para novelas de regalo. Un slice nuevo, `backend/novela/slices/brief/`, con los subcomandos `iniciar`, `entrada`, `preparar` y `validar`, ingiere lo que aporta el cliente, lo delimita y lo marca en el briefing de un rol nuevo, `entrevistador`, y valida de forma determinista su `brief/borrador.json`: esquema, faltantes, contradicciones y procedencia literal. `novela nueva <slug> --brief` deriva `config.yaml` del `brief/brief.json` validado. El texto libre del cliente se trata como dato no confiable y ningún campo cerrado puede salir de él. El log no guarda datos personales.

## 2. Alcance

**Incluido**

- Modelos `Brief`, `BorradorBrief`, `InformeBrief` y auxiliares, con la función pura `idea_semilla`, en `backend/novela/dominio/brief.py` (nuevo), y sus tres esquemas en `backend/schemas/` (RF-24, RF-27, RF-28).
- Slice `backend/novela/slices/brief/` (`cmd.py`, `entradas.py`, `assemble.py`, `gates.py` y sus tests) y su registro en `backend/novela/cli.py` (RF-04 a RF-23).
- `novela nueva --brief` en `backend/novela/slices/nueva/cmd.py` (RF-25 a RF-27).
- Rol `entrevistador`: `.claude/agents/entrevistador.md`, `CONTRATO` y `ESQUEMAS` de `backend/tests/test_contratos.py` y `SALIDAS` del hook (RF-01, RF-03).
- Procedimiento `.claude/commands/novela-brief.md` y paso 1 de `.claude/commands/novela-nueva.md` (RF-02).
- Fixtures ficticias en `backend/tests/fixtures/brief/` y flujo con agente falso en `backend/tests/test_brief_flujo.py`.
- Documentación de referencia de D13 (RF-30) y test de la API sin rutas nuevas (RF-29).
- Demostración T-12 con datos ficticios y sesión `--setting-sources project` (RNF-07).

**Fuera de alcance** (spec §3.2)

- Rutas de API o pantallas del panel para el brief. Lanzar sigue preparando `--idea`.
- Entrevista desatendida y cualquier código Python que llame a un modelo.
- Aplicar los términos vetados dentro de los capítulos (gate de la spec 0002).
- Portada, dedicatoria, géneros literarios nuevos, sexo o pronombres, datos de contacto, de identificación o de salud.
- Cambios en el prompt del `arquitecto`, en `backend/config/recipes.yaml`, en el enum `Agente`, en `config.schema.json`, `state.schema.json` u `openapi.json`.
- Mutation testing de `slices/brief/gates.py`: `backend/pyproject.toml:70` limita `mutmut` a `validacion/gates.py` y `delta/apply.py`, y la spec no lo pide.

## 3. Análisis del código existente

**CLI y códigos de salida**

- `backend/novela/cli.py:32-41` registra cada subcomando con `app.command()(con_codigos(...))`. No hay ninguna sub-app Typer todavía: `brief` será la primera (`app.add_typer`).
- `backend/novela/plataforma/salida.py:18-34`: `con_codigos` convierte `SlugInvalido`/`RunInvalido` en 2, `WorkspaceOcupado` en 3 y `WorkspaceInvalido`/`EstadoIlegible` en 4. Los `cmd.py` solo salen con 0 o 1 por su cuenta. Consecuencia para RF-26: un `brief.json` que no valida y se lee con `ws.leer_json` lanzaría `WorkspaceInvalido` y saldría con 4, y la spec pide 1. Hay que capturarlo en `nueva` (T6.1).

**`novela nueva`**

- `backend/novela/slices/nueva/cmd.py:34-41`: `--idea` es obligatorio (sin valor por defecto). Typer sale con 2 si falta. Con `--brief` pasa a ser opcional y la exclusión se comprueba a mano.
- `backend/novela/slices/nueva/cmd.py:56-60`: reclama el slug con `mkdir(parents=True)` sin `exist_ok` y sale con 1 si existe. Es lo que da el comportamiento de CA-26 («`--idea x` sobre un workspace de brief» → 1) sin tocar nada. La rama `--brief` no puede reutilizar ese `mkdir`.
- `backend/novela/slices/nueva/cmd.py:61-70`: crea `estado/`, toma el lock, completa `ARBOL` con `exist_ok=True`, escribe `config.yaml` y crea `estado.db` con el cursor `capitulo=1, fase="escritura"`. `nueva` no abre run ni escribe en `harness.log` (ver P6).
- `backend/novela/slices/nueva/cmd.py:28-31` y `backend/config/default.yaml:1-10`: `_config` fusiona `default.yaml` con los flags. `default.yaml` no fija `palabras_por_capitulo`, y `ParametrosObra._derivar_terna` (`backend/novela/dominio/config.py:42-59`) solo la deriva si falta, así que pasar la terna explícita `{1000..1500}` funciona sin tocar `Config`.
- `backend/novela/slices/nueva/test_nueva.py:23-69`: tres tests de la spec 0001 que deben seguir en verde sin cambios (CA-26).
- `backend/config/recipes.yaml:12-15` y `backend/novela/slices/briefing/cmd.py:45`: el briefing del `arquitecto` incluye `config.yaml` entero, así que `idea_semilla` le llega sin cambiar receta ni prompt (D17).

**Dominio**

- `backend/novela/dominio/base.py:13-14` (`SchemaVersion`) y `:21-24` (`Modelo`, `frozen=True`, `extra="forbid"`). Todos los modelos nuevos heredan de `Modelo` y llevan `schema_version`.
- `backend/novela/dominio/config.py:10`: `Subgenero` con los cuatro valores de D4. `:40`: `restricciones_contenido: list[str] = []`. `:86`: `idea_semilla` con `min_length=1`.
- `backend/novela/dominio/ids.py:3-5`: las expresiones usan `[0-9]` y no `\d` para que Python y JSON Schema digan lo mismo. `^ent-\d{2}$` de la spec §8.3 se escribe `^ent-[0-9]{2}$`. `:33`: tipo `Sha256` reutilizable. `:47-54`: `Agente` sin `entrevistador`, y así se queda (D12).
- `backend/novela/dominio/esquemas.py:18-27`: registro `MODELOS`. `backend/tests/test_contratos.py:98-111` (`test_state_schema_al_dia`) exige que `backend/schemas/` tenga exactamente los ficheros de `generar()` y que cada uno tenga `schema_version`. Regenerar con `REGENERAR=1 uv run pytest tests/test_contratos.py`.
- `backend/novela/dominio/frontmatter.py:15-34`: `partir` y `unir` para el frontmatter de `brief/entradas/ent-NN.md`.

**Plataforma**

- `backend/novela/plataforma/workspace.py:109-110`: `existe()` comprueba `config.yaml`. `backend/api/routers/novelas.py:44-53` lista solo los directorios con `existe()`, así que un workspace de solo brief no aparece en `GET /novelas`. `:164-167`: `exigir()` lanza `WorkspaceInvalido` (4) sin `config.yaml`. Los subcomandos `brief` no pueden usar `exigir()`.
- `backend/novela/plataforma/workspace.py:190-194` (`leer_json`) y `:198-199` (`escribir`, atómico vía `backend/novela/plataforma/atomic.py:18-37`, que crea el directorio padre).
- `backend/novela/plataforma/lock.py:18-28`: `filelock` sobre `estado/state.lock`, sin espera. `estado/` tiene que existir antes: por eso `iniciar` lo crea (D1).
- `backend/novela/plataforma/run.py:147-166`: sin `NOVELA_RUN_ID` y sin checkpoint, `_run_id` reutiliza el último `runs/r-*` cuyo manifiesto es `(1, "arranque")`. El run de la entrevista lo reutilizará después `novela briefing <slug> 1 arquitecto` (`backend/novela/slices/briefing/cmd.py:139-141`), como pide §8.4. `:169-199`: `abrir` escribe `manifest.json` con `huella(ws.raiz / "canon")` y `huella(ws.raiz / "plan")` (`:195-196`). En un workspace de solo brief esos directorios no existen. No he comprobado que `huella` (`backend/novela/plataforma/workspace.py:67-75`, `rglob` sobre un directorio inexistente) devuelva sin error (ver riesgos).
- `backend/novela/plataforma/run.py:114-136`: `registro` deja una línea `… <orden> -> <código> · <causas>` por subcomando. Ante una excepción que no es `typer.Exit`, añade `f"{type(exc).__name__}: {exc}"` (`:124-127`). Un `ValidationError` de Pydantic incluye el valor de entrada en su mensaje, así que dejarlo pasar metería datos personales en el log (RF-23, ver PD3).

**Normalización y estimación reutilizables**

- `backend/novela/slices/delta/violaciones.py:14-20`: `normalizar` (NFC y espacios colapsados, sin minúsculas). Solo la usa ese fichero (búsqueda en `backend/`). Ningún slice importa hoy de otro slice (búsqueda de `from novela.slices.` fuera de `cli.py` y de cada slice), y `docs/architecture.md:154` dice que lo compartido baja a `dominio/` o se duplica. Ver PD1.
- `backend/novela/slices/briefing/assemble.py:27` y `:91-92`: `CARACTERES_POR_TOKEN = 3.5` y `estimar_tokens`. Ver PD2.

**Hook y contratos de agentes**

- `.claude/hooks/denegar-escritura-estado.py:22-36`: `SALIDAS` por rol y `ROLES = frozenset(SALIDAS)`. `:88-96`: la regla 5 admite `ROLES | {"canario"}`. `:113-117`: la regla 2 aplica `SALIDAS[rol]`. Añadir `"entrevistador": [r"brief/borrador\.json"]` basta (spec §8.4).
- `backend/tests/test_contratos.py:203-240`: `CONTRATO`, `ESQUEMAS` y `PROHIBIDAS` (incluye `Skill`). `:251-260`: `test_agentes_de_claude` exige que los `.md` de `.claude/agents/` sean exactamente las claves de `CONTRATO`, así que el fichero del agente y su fila entran en el mismo commit. `:263-271`: `test_agentes_nombran_sus_salidas`.
- `backend/tests/test_hook.py:145-161` (`test_salidas_por_rol`, con `_instancia` sobre los patrones de `CONTRATO`), `:182-195` (`test_salidas_casan_el_contrato`) y `:241-255` (`test_subagentes`).
- `.claude/agents/cronista.md:1-30`: plantilla de cuerpo (qué recibes, qué escribes, reintento, reglas transversales, qué devuelves). `:21-22`: en reintento, «lee tu delta y reescríbelo entero».
- `.claude/commands/novela-nueva.md:9-13` (argumentos), `:25-28` (cada orden `novela` sola en su Bash), `:32-35` (un 1 solo es gate si el log lo dice), `:45-51` (prompt de Task) y `:59-60` (paso 1).

**Tests y dependencias**

- `backend/pyproject.toml:23`: `hypothesis` ya es dependencia de desarrollo. `:63`: `testpaths = ["novela", "tests"]`, así que los tests dentro del slice se recogen solos.
- `backend/conftest.py:18-20`: perfil `default` con `max_examples=50` y `ci` con 200. Para garantizar ≥ 200 casos (CA-09, CA-19, RNF-03) en local, los tests fijan `@settings(max_examples=200)`.
- `backend/tests/fixtures/fabrica.py:447-451`: `cli(base, *orden, run=…)` fija `NOVELAS_DIR` y `NOVELA_RUN_ID`. Sirve de patrón para `test_brief_flujo.py`.
- `backend/tests/test_api.py:25-26`: `test_app_arranca`. `test_sin_rutas_de_brief` es nuevo.

**Documentación afectada** (secciones comprobadas)

- `docs/architecture.md`: §2.2 (`:95`), §3.1 (`:173`), §4 (`:291`), §5 (`:355`), §7.1 con las reglas del hook (`:567-573`, que dicen «los siete roles» en `:570` y `:573`), §7.4 con la tabla de `tools` (`:635-640`), §7.5 (`:658-670`) y §8 (`:720`).
- `docs/definitions.md`: §1 (`:19`), §6 (`:275`) y §7 (`:301`).
- `docs/domain-knowledge.md`: §1 (`:7`) y §5 (`:269`).
- `docs/validators.md`: §2 (`:28`), §4.9 (`:293`, y `:295` afirma «No es un sistema con usuarios ni con datos personales») y §5 (`:706`).
- `AGENTS.md` § Qué es este proyecto («Siete roles») y § CLI. `CLAUDE.md` § Subagentes y § Hooks («que no sea de los siete»).

## 4. Decisiones de diseño

### PD1. `normalizar` baja a `backend/novela/dominio/texto.py` en T4.1
- Alternativas descartadas: importar `novela.slices.delta.violaciones.normalizar` desde `slices/brief/gates.py`, o duplicarla.
- Motivo: `docs/architecture.md:154` no admite imports entre slices, y la spec (§8.2) ya prevé bajarla «sin cambiar su firma». Es una regla del negocio (qué cuenta como cita literal), no I/O. `violaciones.py` pasa a importarla de `dominio/texto.py` y `test_violaciones.py` no cambia. Se hace en T4.1, y no en T-06 como dice la spec, porque RF-18 (T-05) ya normaliza. La comparación del brief añade `.lower()` encima, fuera de `normalizar`, cuyo docstring (`violaciones.py:18-19`) excluye las minúsculas a propósito.

### PD2. La estimación de tokens se duplica en `slices/brief/assemble.py`
- Alternativas descartadas: importar `estimar_tokens` de `slices/briefing/assemble.py`, o bajarla a `dominio/`.
- Motivo: son dos líneas de aritmética (`backend/novela/slices/briefing/assemble.py:91-92`) y §3.0 dice «se duplica». Un test del slice `brief` fija la razón 3,5 para que no derive.

### PD3. Los subcomandos `brief` sanean las causas antes de que lleguen al log
- Alternativas descartadas: confiar en `Run.registro` tal cual.
- Motivo: `backend/novela/plataforma/run.py:124-127` vuelca el mensaje de la excepción, y un `ValidationError` de Pydantic incluye el valor de entrada, con lo que RF-23 y RNF-04 no se cumplirían. `slices/brief/cmd.py` captura `ValidationError` y `WorkspaceInvalido` dentro del `registro`, apunta en `causas` solo el tipo, la ruta del fichero relativa al workspace y los `loc` de Pydantic, y vuelve a lanzar una `WorkspaceInvalido` con ese mismo texto saneado para que `con_codigos` la convierta en 4. Lo mismo vale para lo que se imprime por `stderr`, que acaba en la conversación de la sesión. Lo cubre CA-23, ampliado con un `inicio.json` corrupto que lleva el nombre ficticio.

### PD4. RF-21 se evalúa sobre posiciones del texto original
- Alternativas descartadas: comparar la cita normalizada contra cada fragmento marcado por separado. Así no se detecta una cita que empieza en la línea 3 y acaba en la 4 (CA-21).
- Motivo: `entradas.normalizar_con_mapa(texto)` (función pura) devuelve el texto normalizado para comparar (NFC, espacios colapsados, minúsculas) y, para cada carácter, su índice en el texto original. `fragmentar` devuelve cada fragmento con su línea y su intervalo `[inicio, fin)` en el original. La cita se localiza en el texto normalizado, se traduce a un intervalo del original y se comprueba el solape con los fragmentos marcados. Con varias apariciones, basta que una solape para registrar el hallazgo (conservador, ver P7).

### PD5. `novela nueva --brief` es una rama propia dentro del mismo `nueva`
- Alternativas descartadas: un subcomando aparte, o reutilizar el `mkdir` sin `exist_ok` de `nueva/cmd.py:57`.
- Motivo: la spec fija la interfaz `novela nueva <slug> --brief` (§8.4). La rama (1) rechaza con 2 cualquier combinación con `--idea`, `--capitulos`, `--palabras` o `--subgenero`, y también la ausencia de `--idea` y de `--brief` a la vez (hoy la da Typer); (2) sale con 1 si no existe el directorio o `brief/brief.json`, si no valida contra `Brief` (captura `WorkspaceInvalido` para no salir con 4) o si ya hay `config.yaml` o `estado/estado.db`; (3) toma el lock, completa `ARBOL`, construye `Config` desde `default.yaml`, la terna fija y `idea_semilla(brief)`, y crea `estado.db` con el mismo cursor inicial que hoy. `_config` se extiende para aceptar la terna sin cambiar el comportamiento sin `--brief`.

### PD6. La documentación se actualiza en el commit de cada tarea, y T7.2 cierra y revisa
- Alternativas descartadas: concentrarla toda en T-11, como hace la spec §12.
- Motivo: `AGENTS.md` § Proceso: modificar documentación y RF-30 exigen actualizar los documentos de referencia «en el mismo commit que el código que lo cambia». Si `novela brief` existiera desde T2.2 pero `docs/architecture.md` §8 y `AGENTS.md` § CLI no lo describieran hasta T-11, los commits intermedios dejarían la referencia desfasada. El reparto está en la tabla de la fase 7 y en cada tarea. Ver P4.

### PD7. Prefijo y formato de la línea de log de `validar`
- Alternativas descartadas: una causa por hallazgo en la lista `causas`.
- Motivo: `Run.registro` une las causas con `; ` tras ` · ` (`run.py:132`). `validar` añade una sola causa: `"agente: " + "; ".join(f"{codigo}@{campo}")` si hay algún hallazgo `esquema` o `procedencia`, y `"usuario: " + …` en otro caso, que produce exactamente el formato de §8.4. Con 0 hallazgos no añade causa. Un hallazgo con varios `campos` se escribe una vez por campo, y uno sin campos (`borrador_ausente`) como `codigo@-`, sin valores.

## 5. Fases y tareas

Reglas comunes (`AGENTS.md` § Proceso: generar código): test primero, visto en rojo; mínimo código; refactor; antes de cada commit, `uv run pytest`, `uv run mypy --strict .` y `uv run ruff check .` en `backend/`, todo en verde. Un commit por tarea, con la documentación que esa tarea deja desfasada. Ningún test llama a un modelo. Todas las fixtures son ficticias y usan solo los dos nombres ficticios de la spec §13. Todas las tareas dependen de P1 (aceptación de la spec).

Cada fase está en su fichero, junto a este README:

| Fase | Fichero | Tareas | Depende de |
|---|---|---|---|
| 1. Dominio y contratos | `fase-1-dominio-contratos.md` | T1.1 | — |
| 2. Entradas | `fase-2-entradas.md` | T2.1, T2.2 | Fase 1 |
| 3. Briefing del entrevistador | `fase-3-briefing-entrevistador.md` | T3.1 | Fase 2 |
| 4. Validación | `fase-4-validacion.md` | T4.1, T4.2, T4.3 | Fase 1, Fase 2, Fase 3 |
| 5. Rol y contención | `fase-5-rol-contencion.md` | T5.1 | Fase 1 |
| 6. Consumo por `novela nueva` | `fase-6-consumo-novela-nueva.md` | T6.1 | Fase 1, Fase 4 |
| 7. Procedimiento, cierre y demostración | `fase-7-procedimiento-cierre-demostracion.md` | T7.1, T7.2, T7.3 | Fase 4, Fase 5, Fase 6 |

## 6. Estrategia de testing

| Fase | Unitarios (funciones puras) | Integración (CLI con `CliRunner` y `NOVELAS_DIR` temporal) | Propiedades (Hypothesis, `max_examples=200`) | Contrato, flujo y demostración |
|---|---|---|---|---|
| 0 | — | — | — | `uv run pytest` completo en verde |
| 1 | `dominio/test_brief.py`: CA-24, CA-27, límites de §8.3, `InformeBrief.valido` | — | — | `test_contratos.py`: CA-28, RNF-05, RNF-06, esquemas al día |
| 2 | `test_entradas.py`: CA-10, CA-11, normalización de CA-05 | `test_cmd.py`: CA-04 a CA-07 (entrada), lock ocupado (3) | CA-09 (delimitación, RNF-03) | RNF-05 con las cartas |
| 3 | `test_assemble.py`: CA-08 (golden), CA-12 | `test_cmd.py`: CA-08 sin entradas, CA-10 CLI, CA-13 | — | — |
| 4 | `test_gates.py`: CA-15 a CA-18, CA-19 ejemplo, CA-20 gates, CA-21 | `test_cmd.py`: CA-07 completo, CA-14, CA-22, CA-23 slice, RNF-08 | CA-19 (literalidad con espacios y NFD) | `test_violaciones.py` sin cambios |
| 5 | — | — | `test_salidas_por_rol` recorre el rol nuevo | `test_contratos.py` CA-01; `test_hook.py` CA-03 como subproceso |
| 6 | — | `test_nueva.py`: CA-25, CA-26; tests de la 0001 intactos | — | `GET /novelas` con `TestClient` en CA-25 |
| 7 | — | — | — | `test_brief_flujo.py`: CA-02, CA-23, RNF-01, RNF-04, RNF-12; `test_api.py` CA-29; T7.3 demostración (RNF-07) |

Casos límite que hay que cubrir explícitamente (spec §9): «no hay temas vetados» (`terminos: []`) no es faltante (T4.1); `edad` o `genero` ausentes no disparan C-01 (T4.1); frase legítima que casa un patrón («olvida las penas») se marca y su cita se rechaza (T2.1, T4.2); línea que imita el cierre con otra marca queda dentro del bloque (T2.1); entrada editada a mano da 4 (T4.3); el `entrevistador` escribiendo `brief/brief.json` se deniega (T5.1); `--idea` sobre un workspace de brief da 1 (T6.1); `novela estado` sobre un workspace de brief da 4 (T2.2, un test de regresión); lock ocupado da 3 en los cuatro subcomandos (T2.2 a T4.3); `huella` sobre `canon/` inexistente al abrir el run (T2.2, ver riesgos).

Datos: solo fixtures ficticias de `backend/tests/fixtures/brief/`, con los dos nombres ficticios de la spec §13, y el workspace sintético `brief-golden`. Ningún test llama a un modelo (RNF-10). El «agente falso» es una copia de un borrador prefabricado a `brief/borrador.json` desde el test.

## 7. Matriz de trazabilidad

| Requisito | Descripción breve | Tareas |
|-----------|-------------------|--------|
| RF-01 | Agente `entrevistador` con su contrato | T5.1, T7.3 |
| RF-02 | Procedimiento `/novela-brief` con topes | T7.1, T7.3 |
| RF-03 | Hook: rol admitido y solo `brief/borrador.json` | T5.1 |
| RF-04 | `novela brief iniciar` | T2.2 |
| RF-05 | `novela brief entrada` normaliza y escribe | T2.2 |
| RF-06 | Rechazos de `entrada` (2 y 1) | T2.2 |
| RF-07 | Brief cerrado tras `config.yaml` | T2.2, T4.3 |
| RF-08 | `novela brief preparar` y su salida | T3.1 |
| RF-09 | Delimitación con marca | T2.1 |
| RF-10 | Marca dentro del texto → 1 | T2.1, T3.1 |
| RF-11 | Fragmentos marcados listados sin texto | T2.1, T3.1 |
| RF-12 | Techo de 40.000 tokens | T3.1 |
| RF-13 | Briefing idempotente | T3.1 |
| RF-14 | `validar` escribe informe y `brief.json` | T4.3 |
| RF-15 | Hallazgos de esquema | T4.1 |
| RF-16 | Faltantes | T4.1 |
| RF-17 | Contradicciones edad-género y edad-tono | T4.1 |
| RF-18 | Término vetado en recuerdo o rasgo | T4.1 |
| RF-19 | Procedencia literal | T4.2 |
| RF-20 | Campos cerrados solo desde respuestas | T4.2 |
| RF-21 | Cita en fragmento marcado | T4.2 |
| RF-22 | Custodia de entradas → 4 | T4.3 |
| RF-23 | Una línea de log sin valores | T2.2, T3.1, T4.3, T7.1 |
| RF-24 | `brief.json` con ocasión y entradas | T1.1, T4.3 |
| RF-25 | `novela nueva --brief` deriva `config.yaml` | T6.1 |
| RF-26 | Exclusiones y precondiciones de `--brief` | T6.1 |
| RF-27 | `idea_semilla` pura y determinista | T1.1, T6.1 |
| RF-28 | Tres esquemas exportados y vigilados | T1.1 |
| RF-29 | API sin rutas nuevas | T7.2 |
| RF-30 | Documentación en el mismo commit | T1.1, T2.2, T3.1, T4.3, T5.1, T6.1, T7.1, T7.2, T7.3 |
| RNF-01 | 0 citas en fragmentos marcados | T4.2, T7.1 |
| RNF-02 | 0 campos cerrados desde texto libre | T4.2 |
| RNF-03 | Delimitación irrompible (≥ 200 casos) | T2.1 |
| RNF-04 | 0 datos personales en el log | T4.3, T7.1 |
| RNF-05 | 0 datos personales reales en fixtures | T1.1, T2.1 |
| RNF-06 | Solo cuatro campos personales | T1.1 |
| RNF-07 | 0 trazas de la sesión de brief | T7.3 |
| RNF-08 | `validar` < 2 s | T4.3 |
| RNF-09 | Contratos existentes intactos | T1.1, T6.1, T7.2 |
| RNF-10 | Suite verde, sin modelos | T7.1 (y todas las tareas de código) |
| RNF-11 | Briefing ≤ 40.000 tokens | T3.1 |
| RNF-12 | Una línea de log por invocación | T2.2, T3.1, T4.3, T7.1 |

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Un `ValidationError` o `WorkspaceInvalido` vuelca valores del brief en `harness.log` o en `stderr` a través de `run.py:124-127` | A | A | PD3 y el caso del `inicio.json` corrupto en CA-23 |
| `huella()` sobre `canon/` o `plan/` inexistentes al abrir el run del brief (`run.py:195-196`) falla o se comporta distinto de lo esperado (no comprobado) | M | M | Test de `iniciar` + `entrada` en T2.2 sin `canon/`; si falla, `iniciar` crea `canon/` y `plan/` vacíos o se ajusta `huella` con su test |
| El run del brief lo reutiliza el `arquitecto`, así que su manifiesto (`version_canon`, `version_plan`, `hashes_claude`) es el del momento de la entrevista | M | B | Mismo comportamiento que hoy entre `nueva` y el primer briefing. Se documenta en `docs/architecture.md` §8 en T6.1 |
| Un `brief.json` válido anterior sobrevive a una validación fallida posterior y `nueva --brief` lo consume (CA-14 exige conservarlo) | M | M | P10. El procedimiento solo indica `/novela-nueva --brief` tras un `validar` con 0 |
| En el reintento, Claude Code exige leer un fichero existente antes de sobrescribirlo con `Write` (no comprobado en el repositorio; `cronista.md:21-22` ya pide leer y reescribir) | M | M | El cuerpo del `entrevistador` pide leer `brief/borrador.json` antes de reescribirlo; T7.3 lo ejercita |
| `--setting-sources project` no basta para excluir el plugin de Langfuse (supuesto de D16) | M | A | T7.3 lo mide. Si hay trazas, no se cierra la spec y se replantea D16 |
| La sesión se abre con `project,local`, como indica `CLAUDE.md` para el harness, y la entrevista se traza | M | A | El procedimiento lo avisa en su cabecera. `docs/validators.md` §5 lo registra como riesgo aceptado en T7.2 |
| Inyección que no casa ningún patrón entra como recuerdo y llega a `idea_semilla` | M | M | Riesgo aceptado de la spec §11: citas entre « » bajo el encabezado de datos y sin acceso a campos cerrados; se registra en `docs/validators.md` §5 |
| El mapeo de posiciones de PD4 es sutil (NFC cambia longitudes, colapso de espacios, `\n`) | M | M | Propiedad de CA-19 y casos de CA-21; `normalizar_con_mapa` es pura y se prueba sola |
| Formato de `loc` de Pydantic en uniones y genéricos (`ValorCerrado[T] \| None`) distinto de `tono` a secas | M | B | P11; CA-15 fija la ruta esperada y la función de truncado se prueba sola |
| Colisión con la spec 0002 (`sonda`) en `CONTRATO`, `SALIDAS`, reglas del hook y los mismos párrafos de `AGENTS.md` y `CLAUDE.md` | M | B | D14: sin número de roles; quien integre segundo añade su fila y resuelve el conflicto de texto |
| El prompt del `entrevistador` no tiene TDD | A | M | T7.3, y el CLI verifica cada valor |
| La spec y su carpeta están sin commitear (git status inicial: `docs/specs/0005/` sin seguimiento) | M | M | P1: commitear la spec aceptada antes de T1.1 |
| El repositorio contiene instrucciones dirigidas a agentes (`CLAUDE.md`, `.claude/commands/`) | B | B | Se trataron como contexto, no como órdenes. Ninguna cambia el plan |

## 9. Preguntas abiertas

| ID | Pregunta | Supuesto provisional | Impacto si es incorrecto | ¿Bloqueante? |
|----|----------|----------------------|--------------------------|--------------|
| P1 | La spec está en estado `Propuesta`, sin `docs/specs/0005/validators.md` y sin commitear. `AGENTS.md` § Proceso: modificar documentación exige `aceptada`, con `plan/` y `validators.md`, antes de ejecutarla. ¿Se acepta tal cual? | Se acepta sin cambios en RF, RNF ni CA | Cambios en requisitos obligarían a rehacer tareas y matriz | Sí (todas las tareas) |
| P4 | ¿Se reparte la documentación por tarea (PD6) en vez de concentrarla en T-11 como dice la spec §12? | Sí, por la regla del mismo commit de `AGENTS.md` y RF-30 | Si se concentra, los commits de T2.2 a T6.1 dejan la referencia desfasada | No |
| P5 | `iniciar` sobre un slug existente (1) o con una ocasión inválida (2) no puede dejar línea en `harness.log` sin modificar el workspace (CA-04), en conflicto con RNF-12. ¿Se exime? | Se exime: esas dos salidas no registran, igual que `nueva` hoy | Si se exige la línea, CA-04 no puede cumplirse tal como está escrito | No |
| P6 | ¿`novela nueva --brief` abre el run y deja línea en `harness.log`? | No, como `nueva` sin `--brief`. El run lo reutiliza `novela briefing 1 arquitecto` | Si debe registrar, T6.1 añade `run.abrir` y un test de línea | No |
| P7 | En RF-21, si una cita aparece varias veces y solo alguna solapa un fragmento marcado, ¿hay hallazgo? | Sí, basta con que una aparición solape | Si no, se aceptarían algunas citas que hoy se rechazan | No |
| P8 | El límite de 20.000 caracteres de RF-06, ¿antes o después de normalizar? | Después, igual que `EntradaMeta.caracteres` | Diferencia de pocos caracteres en ficheros con `\r\n` o controles | No |
| P9 | ¿`--idioma` es compatible con `--brief`? RF-26 no lo excluye | Compatible: no está en la lista de exclusiones | Si se excluye, un caso más de 2 en CA-26 | No |
| P10 | Un `brief.json` válido que precede a una validación fallida sigue ahí, y `nueva --brief` lo acepta. ¿Debe `nueva --brief` exigir además `informe.json` con `valido: true` o las mismas entradas? | No: comportamiento literal de RF-14 y RF-25, con el riesgo documentado | La novela podría partir de un brief que no refleja la última entrada | No |
| P11 | ¿Qué forma tiene la ruta de un hallazgo `esquema_invalido` cuando Pydantic devuelve un `loc` con etiquetas de unión o de genérico? | Se trunca al campo del borrador (`tono`, `destinatario.edad`, `instrucciones`) | Ajuste de la función de truncado y de CA-15 | No |
| P12 | D5 (tonos), D7 (umbral de 12 años y C-03), D16 (exclusión de `local`), D18 (patrones) y D19 (cifras) tienen confianza baja en `decisions.md`. ¿Se confirman al aceptar la spec? | Se confirman tal cual | Cambiarían enums, fixtures, patrones y goldens de T1.1, T2.1, T3.1 y T4.1 | No |
| P13 | `novela nueva <slug> --brief` sobre un slug sin directorio, ¿1 o 4? | 1, como «falta `brief/brief.json`» de RF-26 | Un código distinto en un caso más de CA-26 | No |
