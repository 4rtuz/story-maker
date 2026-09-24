# Plan de implementación: Verificación a escala de novela: secreto, estado, estilo, tensión y orquestador

- Spec de origen: `docs/specs/0002-verificacion-a-escala-de-novela.md` (v0.3, `aceptada`, con las enmiendas de la revisión de validadores) · ADR: `docs/adr/0002-los-gates-los-decide-el-cli.md` · Fecha: 2026-09-24 · Estado: Borrador

> **Ubicación.** Se pidió este directorio y esta forma: `README.md` más un fichero por fase de la spec §5. Coincide con `AGENTS.md` § Proceso: modificar documentación (`docs/implementation-plans/NNNN-<slug>/`, «se borra al implementarla»). El plan de la 0003 (`b09f543:docs/implementation-plans/0003-contencion/`) no se pudo leer: el planificador no tiene Bash. La forma sigue la descripción de la petición y la del plan de la 0004, que sí está en el árbol.

Los requisitos se citan con los ids de la spec (RF-01…RF-30, RNF-01…RNF-07, CA-01…CA-30). Las tareas se numeran por fase (1.1, 1.2…). Las decisiones de este plan son D-1, D-2…, y las preguntas abiertas PA-1, PA-2…, para no confundirlas con las P-01…P-17 de la spec, que están cerradas.

| Fase | Fichero | Tareas |
|---|---|---|
| 1. Gates mecánicos sobre capítulo y delta | `fase-1-gates-mecanicos.md` | 1.1–1.11 |
| 2. El secreto en el briefing | `fase-2-secreto-en-el-briefing.md` | 2.1–2.5 |
| 3. El plan y los gates en código | `fase-3-plan-y-gates-en-codigo.md` | 3.1–3.9 |
| 4. Tensión y secreto a escala de acto | `fase-4-tension-y-secreto-por-acto.md` | 4.1–4.6 |
| 5. Trayectoria del orquestador | `fase-5-trayectoria.md` | 5.1–5.6 |
| 6. Verificación de release y novela de humo | `fase-6-release-y-humo.md` | 6.1–6.4 |

## 1. Resumen

La spec cierra cinco modos de fallo que hoy solo se descubren tarde: el secreto que llega parafraseado al `escritor`, el `cronista` que escribe en tablas append-only sin evidencia, la deriva de estilo sin medida, la tensión sin banda y un orquestador que cuenta los intentos a mano. El plan lo reparte en 41 tareas: 38 ciclos TDD cerrados y tres de documentación o demostración (5.6, 6.3 y 6.4). Construye gates puros en `backend/novela/`, cuatro subcomandos nuevos (`validar-plan`, `gate` con cinco tipos, `sonda`, `trayectoria`), un agente nuevo (`sonda`) y un hook `Stop`, y cambia los dos procedimientos una sola vez, en la fase 3. Ningún test llama a un modelo. Las dos piezas que sí llaman a modelos (script de revisores y canario del orquestador) quedan fuera de `pytest`, con un modo en seco probado.

## 2. Alcance

**Incluido** (spec §1 y §5)

- Fase 1: RF-05, RF-06, RF-07, RF-08, RF-09, RF-10, RF-11, RF-12 y RF-28, más `Revelacion.destapa` (D-2) y la capa `reparto` del `cronista`.
- Fase 2: RF-01, RF-02 y RF-03, más `Misterio.culpable`.
- Fase 3: RF-14, RF-16, RF-17, RF-19 y RF-29, con los cinco gates (`plan`, `mecanico`, `final`, `revision`, `delta`) y la reescritura de `/novela-continuar` y `/novela-nueva`.
- Fase 4: RF-04, RF-15, RF-18 y RF-30.
- Fase 5: RF-13, RF-20, RF-21, RF-22 y RF-24.
- Fase 6: RF-25, RF-26, RF-27 y la novela de humo `humo-0002`.
- Los nueve cambios de esquema de la spec §8.8, cada uno con su `REGENERAR=1 uv run pytest tests/test_contratos.py`, su `docs/definitions.md` y su test de contrato en el mismo commit.
- La documentación de referencia que cada tarea deja desfasada, en su mismo commit (§5.2 de este README).

**Fuera de alcance** (spec §1)

- RF-23 y `novela budget` (P-16), el índice recuperable, el solape de escenas en `linea_temporal` y el objeto sin paradero.
- El texto concreto de los prompts de agente: el plan dice qué contrato cambia y en qué commit, y lo valida `humo-0002` (tarea 6.3).
- El panel (`frontend/`) y la API: ningún endpoint nuevo. Solo se regenera `backend/api/openapi.json` porque cambia `FrontmatterCapitulo` (tarea 1.3).
- Migrar `humo-0003` (RNF-06).
- Reescribir capítulos cerrados: la política de cuota deja de hacerlo (RF-24), no se añade ningún mecanismo.

## 3. Análisis del código existente

Solo se cita lo que se ha leído. Los números de línea son del árbol de la rama `spec-0003` el 2026-09-24.

**Gates y validación**

- `backend/novela/slices/validacion/gates.py` es puro (docstring, `:1-5`). `Contexto` (`:19-26`) no lleva ni el estado de las pistas ni el canon de estilo. `_pistas` (`:58-69`) solo comprueba que lo del plan está en el frontmatter, no la igualdad. `_hilos` (`:72-82`) solo mira que un hilo cerrado estuviera abierto. `_ids` (`:85-99`) no conoce pistas falsas. Todo esto es lo que cambia en RF-05, RF-09 y RF-10.
- `backend/novela/slices/validacion/cmd.py:19-38` (`_contexto`) lee la ficha, el misterio y los hilos. `:51` registra `validar NN`, y esa línea es la que cuentan el procedimiento (`.claude/commands/novela-continuar.md:94-106`) y su tabla de reanudación (`:121-131`).
- `backend/pyproject.toml:66-75`: `mutmut` solo muta `gates.py` y `delta/apply.py`. RF-11, RF-14, RF-15 y RF-16 exigen mutación sobre módulos que no existen todavía (D-8).

**Delta y estado**

- `backend/novela/dominio/estado.py:70-75` (`EntradaTemporal`), `:87-92` (`EntradaConocimiento`) y `:115-119` (`Hecho`) son a la vez modelos del estado y del delta (`Delta`, `:159-178`). La spec quiere la obligatoriedad y el mínimo de 15 caracteres «en el contrato del delta, no en el del estado» (§5.1.3, RF-06), y en `humo-0003` una de sus 85 citas tiene menos: hacen falta tipos propios del delta para las cuatro colecciones, `libro_de_hechos` incluido (D-4).
- `backend/novela/slices/delta/violaciones.py:17-20` define `normalizar`, que RF-05 también necesita en `validacion/`. Ningún slice importa hoy de otro (búsqueda de `from novela.slices.` fuera de tests): baja a `dominio/` (D-3). `_citas` (`:67-78`) ya comprueba las citas presentes; `violaciones` (`:100-107`) es donde entran los invariantes y el control de resúmenes.
- `backend/novela/slices/delta/apply.py:41-62` y `backend/novela/slices/delta/cmd.py:124-128` usan `pistas_plantadas` y `pistas_pagadas` como listas de ids: rompen cuando pasan a ser `{id, cita}` (tarea 1.3).
- `backend/novela/slices/delta/cmd.py:100-101` antepone `custodia:` a cada causa de la custodia. Es la marca que el gate `delta` usa para intervenir sin reintento (spec §8.1).

**Briefing**

- `backend/novela/slices/briefing/assemble.py` es puro (`:1-6`). La capa `Personajes` (`:182-189`) incrusta el texto crudo de la ficha, con su frontmatter entero: es la vía de RF-01. `_pistas_del_capitulo` (`:152-162`) no conoce pistas falsas. `_permitidos` (`:240-254`) no admite su contenido, así que en cuanto el briefing las incluya el guardarraíl literal abortaría (D-10). `validar-plan` y el solape también necesitan `_permitidos` (§8.4), y hoy vive en el slice de briefing (D-3). `ensamblar` (`:344-368`) vigila el secreto antes de degradar (`:346-347`).
- `backend/novela/dominio/canon.py:66-71`: `Identidad.rol_narrativo` es obligatorio. Una ficha sin él ya no es un `Personaje` válido, así que la ficha filtrada se re-renderiza desde el diccionario y no desde el modelo (D-9).
- `backend/novela/slices/briefing/cmd.py:167` escribe siempre `NN-<agente>.md`; `:159-166` convierte `FugaDelSecreto` y `PresupuestoExcedido` en 1 y `FuenteAusente` en 4. `:140-141` abre el run de arranque para `arquitecto` y `trazador`.
- `backend/novela/slices/briefing/recipes.py:99-107` exige una receta por cada valor de `Agente`: añadir `sonda` al enum (`backend/novela/dominio/ids.py:47-54`) obliga a su receta en el mismo commit. La receta del `cronista` (`backend/config/recipes.yaml:58-63`) no trae canon: en `humo-0003` inventó escenarios y un personaje (tarea 1.7).
- `backend/tests/fixtures/golden/08-escritor.md` fija byte a byte el briefing del escritor (`backend/novela/slices/briefing/test_briefing.py:115-125`). Cambia en 1.3 (el capítulo 7 incrustado lleva el frontmatter nuevo) y en 2.3 (fichas filtradas).

**Run, log y códigos**

- `backend/novela/plataforma/run.py:114-136`: `registro` escribe `<marca> [sesion=<uuid>] <orden> -> <código>[ · causas]`. `_run_id` (`:147-166`) reutiliza el run abierto solo si el capítulo no tiene checkpoint (`:158-162`); si lo tiene, crea uno nuevo desde el reloj. Un subcomando nuevo que llame a `run.abrir` sobre un capítulo cerrado crearía un run espurio (D-7).
- `backend/novela/plataforma/salida.py:18`: códigos 2, 3 y 4. No hay 5 (RF-29).
- `backend/novela/slices/estado/cmd.py:54-60`: `pendiente` solo mira el checkpoint.
- `backend/novela/slices/auditoria/cmd.py:15-36` no abre run y escribe `qa/auditoria.json`.
- `backend/novela/plataforma/langfuse.py:24-29`: `ScoreSink.emitir(slug, capitulo, run_id, scores)`. Id determinista por score (`:52`). `backend/novela/slices/checkpoint/test_checkpoint.py:78-101` prueba los scores sin red, parcheando `urllib.request.urlopen`: es el patrón de RNF-05.

**Harness de `.claude/`**

- `.claude/hooks/denegar-escritura-estado.py:22-35` (`SALIDAS`), `:36` (`ROLES`) y `:88-96` (regla 5: `ROLES | {"canario"}`). `backend/tests/test_hook.py:182-195` compara `SALIDAS` con `CONTRATO` sustituyendo `NN` por `07` y `*` por `x`: la salida de la sonda (`qa/NN-sonda-(briefing|texto)-[1-3].json`) no se puede escribir con esos dos comodines (D-15).
- `backend/tests/test_contratos.py:165-201` (`CONTRATO` y `ESQUEMAS`, siete roles), `:246-260` (`test_settings_de_claude` desempaqueta un único registro `PreToolUse`), y `backend/novela/plataforma/test_run.py:125-133` (asserta 7 ficheros de agente).
- `.claude/settings.json:11-23`: solo `PreToolUse`. El hook `Stop` del plugin de Langfuse vive en el ámbito del plugin (`CLAUDE.md` § Hooks).
- `.claude/commands/novela-continuar.md:15-23` (tabla de códigos sin 5), `:94-119` (cuenta de intentos y plantilla de `intervencion.md` en prosa) y `.claude/commands/novela-nueva.md:64-81` (gate del arquitecto con su propia cuenta y su propia intervención). CA-29 prohíbe que un procedimiento escriba `intervencion.md` para un gate de `novela gate`, y conserva las demás (D-28).

**API**

- `backend/api/routers/capitulos.py:18-21` devuelve `list[FrontmatterCapitulo]`: la ruptura de RF-05 cambia el OpenAPI (regenerar en 1.3) y hace que el índice de `humo-0003` responda 404. Ningún router lista briefings ni sirve `qa/`, así que los ficheros nuevos de `runs/` y `qa/` no rompen nada de la API.

**Fixtures y datos**

- `backend/tests/fixtures/fabrica.py` es el agente falso. Hoy no cumpliría la spec: el delta deja sin cita la segunda escena (`:365-370`) y `conocimiento_lector` (`:391`), el frontmatter usa ids sueltos (`:306-307`), el misterio no tiene `culpable` (`:113-139`) y la ficha que desmonta `pfa-001` no la declara. Cada tarea que cambia un contrato ajusta la fábrica en el mismo commit. Sus citas (`frase_de_hecho`, `frase_de_escena`, `Elena encontró la pista …`) pasan de 15 caracteres.
- `novelas/` está en `.gitignore`: `humo-0003` no existe en CI (D-20, PA-1). Lo que se ha leído de ella sin abrir capítulos ni misterio:
  - Las cargas 12, 9 y 0 de CA-15 salen de su escaleta (`novelas/humo-0003/plan/escaleta.md`: hilos por capítulo, pistas por acto y revelaciones rev-001 y rev-003 en el 2 y rev-002 en el 3).
  - Sus fichas no tienen `pistas_falsas_a_desmontar`, que es un campo nuevo. CA-14 completa esos campos desde la escaleta.
  - Los tres deltas usan ubicaciones que no son escenarios de `canon/mundo.md` (spec §8.3, invariante 3).
  - En `runs/r-20260924-1120/harness.log`, el capítulo 3 lo tocaron dos sesiones (líneas 1-6 y 7-18): una sesión reanudada no tiene el `briefing … escritor` en su transcript (D-12).
  - Sus dos `intervencion.md` tienen línea `resuelto:`.

## 4. Decisiones de diseño

Las que la spec no fija. Cada una, con la opción elegida y la descartada.

### D-1. Nombre del directorio
- Elegida: `docs/implementation-plans/0002-verificacion/`, como se pidió.
- Descartada: `0002-verificacion-a-escala-de-novela/`, el nombre que saldría de la ruta de la spec.
- Motivo: lo pide la petición y `AGENTS.md` solo exige `NNNN-<slug>/`.

### D-2. `destapa` entra en la fase 1 y `culpable` en la 2
- Elegida: `Revelacion.destapa: list[PersonajeId] = []` se añade en la tarea 1.7, que es cuando lo necesita la excepción del invariante 1 (§8.3). `Misterio.culpable` se queda en la 2.1.
- Descartada: implementar el invariante 1 sin excepción en la fase 1 y añadirla en la 2, con lo que la regla cambiaría de semántica entre fases.
- Motivo: `destapa` es compatible (lista vacía por defecto). `culpable` es la ruptura del canon y no hace falta hasta el filtro.

### D-3. Utilidades de texto y de secreto en `dominio/`
- Elegida:
  - `backend/novela/dominio/texto.py` (nuevo): `normalizar` (se mueve desde `violaciones.py:17-20`, y allí queda un reexport), `palabras`, `frases`, `candidatos_nombre_propio`, `ids_citados` y `MIN_CITA = 15`.
  - `backend/novela/dominio/secreto.py` (nuevo): `filtrados`, `conjunto_secreto`, `permitidos`, `bloques`, `solapa`, y las constantes `TAM_BLOQUE = 5`, `MIN_LARGAS = 2` y `LARGA = 4` (§8.4). `permitidos(misterio, ficha, n)` es el `_permitidos` de `assemble.py:240-254`, que pasa a delegar en él. Lo usan `briefing`, `validar-plan` y `sonda`.
- Descartada: importar `violaciones.normalizar` desde `validacion/gates.py`, o `assemble._permitidos` desde `validacion_plan/`.
- Motivo: `architecture.md` §3.0 no deja importar un slice desde otro: «o baja a `dominio/` porque es una regla del negocio, o a `plataforma/`».

### D-4. Tipos de entrada propios del delta, cuatro colecciones
- Elegida: `EntradaTemporalDelta`, `EntradaConocimientoDelta` y `HechoDelta` en `dominio/estado.py`.
  - `cita: str` obligatoria, con un validador que exige `len(normalizar(cita)) >= MIN_CITA`. El esquema lleva `minLength: 15` como aproximación; el validador manda.
  - Un método `al_estado()` devuelve la entrada del estado. `apply.aplicar` y `violaciones._reescrituras` convierten antes de comparar o de añadir.
  - `Hecho` también se separa: es el modelo de `Estado.libro_de_hechos`, y endurecerlo haría ilegible una base con citas cortas, como la de `humo-0003` (RNF-06).
- Descartadas: comprobar la cita en `violaciones` (la spec quiere la ruptura en `delta.schema.json`, §8.8), y una subclase de las entradas del estado. La igualdad de Pydantic v2 exige la misma clase, así que `_altas` (`apply.py:25-29`) duplicaría entradas al reanudar y `_reescrituras` (`violaciones.py:37-52`) daría «ya está con otro contenido» sobre la misma entrada.
- Motivo: la propiedad de idempotencia de `test_apply.py:26-36` tiene que seguir en verde, y `state.schema.json` no cambia (§8.8).

### D-5. `validar --final`: misma línea de log, informe con `final: true`
- Elegida:
  - `registro("validar", nn)` también con `--final`, y `final` como primer elemento del detalle (`validar 07 -> 0 · final`).
  - `InformeQA` gana `final: bool = False`, y `validar --final` escribe `final: true` en `qa/NN-validacion.json` (§8.1, §8.8).
  - El gate `final` trata un informe con `final: false` como ilegible, y por tanto como rechazado. El gate `mecanico` no mira el campo.
- Descartada: `validar 07 --final -> X` en el log.
- Motivo: en las fases 1 y 2 el procedimiento todavía cuenta `validar NN -> 1` en los pasos 3 y 5, y su tabla de reanudación busca la última línea `validar NN`. Con otra orden, el paso 5 dejaría de contar.

### D-6. Repetición, cuenta y formato de las líneas de `gate`, `sonda` y `trayectoria` (RNF-04, §8.1)
- Formato de la línea (`run.registro(*orden, entradas=…)`): el detalle lleva primero las causas y al final `entradas=<sha256>`.

  | Situación | Línea |
  |---|---|
  | Decisión normal | `gate 07 revision -> 1 · <causas>; entradas=<sha>` |
  | El gate interviene | `gate 07 revision -> 5 · intervención (<motivo>); entradas=<sha>` |
  | Intervención viva previa | `gate 07 revision -> 5 · intervención viva` |

  `<motivo>` es `agotamiento`, `custodia`, `tendencia_negativa` o, en `sonda`, `fuga` o `agotamiento`. Así se casan las dos subcadenas de §8.1 (`-> 5 · intervención` frente a `-> 5 · intervención viva`) sin ambigüedad: la cuenta se reinicia con `intervención (`, y `intervención viva` no reinicia.
- La sha es la de un JSON canónico (`sort_keys`, sin espacios) con el tipo, el capítulo y, por cada entrada, su ruta relativa, el sha256 de sus bytes y, si interviene en la ilegibilidad, su `st_mtime_ns`. También entran el cursor y las líneas del log que se consultan (gate `delta`) y los valores de la curva y de `tension_real` que usa (gate `revision`).
- Orden de evaluación del gate:
  1. Rango (D-7) → 2.
  2. Intervención viva en el run → 5, con la línea `intervención viva`.
  3. **Repetición**: si la **última línea** del `harness.log` del run es de este mismo gate, capítulo y tipo, y lleva la misma sha, sale con su código, imprime `gate NN <tipo>: repetido` y no escribe línea. Cualquier otra línea en medio (otra orden del CLI, un `briefing`, un `validar`) hace de la llamada un intento nuevo, aunque las entradas no hayan cambiado: un agente que no escribió nada gasta su intento.
  4. Evalúa, cuenta los `-> 1` posteriores a la última `-> 5 · intervención (` de ese gate y registra.
- `sonda`: no tiene repetición. Cada llamada con votos ausentes o inválidos escribe `sonda NN <tipo> -> 1` y cuenta (RNF-04). Lleva `entradas=` con la sha de los votos, y la usa solo para la autorización de D-30.
- `trayectoria`: repetición con la misma regla de la última línea (`trayectoria NN -> 0 · entradas=<sha del tramo>`). Además, solo escribe `intervencion.md` si la entrada de su sesión en `trayectoria-NN.json` cambia, para no duplicar bloques cuando otra línea se ha colado en medio.
- Descartadas: buscar la sha en cualquier línea anterior (la primera redacción del plan), porque dejaba a un agente que no escribe nada reintentar gratis; y un `gates.jsonl` (spec §15).

### D-7. Qué run abre cada subcomando nuevo y su rango

| Subcomando | Rango válido (si no, 2 sin abrir run) | Run |
|---|---|---|
| `validar-plan <slug>`, `gate <slug> 1 plan` | sin checkpoint, y `cap = 1` | `run.abrir(ws, 1, "arranque")`, que reutiliza el de `briefing … arquitecto` (`run.py:158-162`) |
| `gate <slug> <cap> mecanico\|final\|revision\|delta` | `cap = último checkpoint + 1` (ni cerrado ni por delante, §8.1 «Rango») | `run.abrir(ws, cap)` |
| `sonda <slug> <cap> briefing` | `cap = último checkpoint + 1` | `run.abrir(ws, cap)` |
| `sonda <slug> <cap> texto` | `cap = último checkpoint` (va tras el checkpoint, D-26) | `run.existente` del run de `checkpoints/NN.json` |
| `trayectoria` | — | Ninguno se abre: el run que nombran las salidas de `novela briefing` del tramo, o el más reciente con `manifest.json` de `(cap, "capitulo")`, con `run.existente`. Si no existe, no escribe |
| `auditar --acto K` | el último capítulo del acto tiene checkpoint | `run.existente` del run de su `checkpoints/NN.json` |

- Nueva función `run.existente(ws, run_id) -> Run | None`, que no crea manifiesto.
- Descartada: dejar que `run.abrir` cree lo que haga falta, como hacen hoy `validar` y `aplicar-delta`.

### D-8. Frontera pura / cáscara
Cada gate nuevo es una función pura que recibe datos ya leídos y devuelve hallazgos o una decisión, como `gates.py` y `violaciones.py`. La cáscara (`cmd.py`) lee, llama y escribe. Lo property-based y la mutación van contra lo puro:

| Pura (nuevo o ampliado) | Cáscara | Mutación |
|---|---|---|
| `slices/validacion/gates.py` (citas, conjuntos, léxico) y `slices/validacion/huella.py` | `slices/validacion/cmd.py` | sí (se añade `huella.py`) |
| `slices/delta/violaciones.py` (invariantes y resumen) | `slices/delta/cmd.py` | sí (se añade) |
| `slices/validacion_plan/comprobaciones.py` | `slices/validacion_plan/cmd.py` | sí |
| `slices/gate/decision.py` | `slices/gate/cmd.py` | sí |
| `slices/briefing/assemble.py`, `slices/briefing/reintento.py`, `slices/briefing/sonda.py` | `slices/briefing/cmd.py` | no (property-based) |
| `slices/checkpoint/carga.py` | `slices/checkpoint/cmd.py` | sí |
| `slices/auditoria/comprobaciones.py` (acto) | `slices/auditoria/cmd.py` | no |
| `slices/trayectoria/transcript.py` y `slices/trayectoria/comprobaciones.py` | `slices/trayectoria/cmd.py` | no |
| `dominio/texto.py`, `dominio/secreto.py`, `plataforma/intervencion.py` (el formato; la escritura es cáscara) | — | no |

`paths_to_mutate` y el `runner` de `backend/pyproject.toml:66-75` se amplían en la tarea que crea cada módulo.

### D-9. Orden dentro de `assemble.ensamblar` y ficha filtrada
- Elegido:
  1. El filtro de RF-01 actúa **al construir** la capa `Personajes` (`assemble.py:182-189`), para `escritor`, `editor-estilo` y `sonda`. Lo filtrado no llega a entrar.
  2. `_vigilar_el_secreto`, el guardarraíl literal de 0001, sin cambios de posición (`:347`).
  3. `_vigilar_el_solape` (RF-02), sobre las mismas secciones y antes de degradar. Lanza `SolapeConElSecreto`, subclase de `FugaDelSecreto`, así que `cmd.py:161` ya lo convierte en 1 sin fichero.
  4. Degradación.

  Primero el literal, porque sus mensajes y sus tests (`test_briefing.py:52-96`) no cambian. Los dos abortan antes de escribir. En el briefing de la `sonda`, ni 2 ni 3 miran las secciones de la capa `capitulos` (RF-02): es lo que la sonda mide.
- Ficha filtrada: los cuatro campos de RF-01 (`secreto`, `coartada_y_cronologia_privada`, `arco_previsto` e `identidad.rol_narrativo`).
  - Como `rol_narrativo` es obligatorio (`canon.py:66-71`), toda ficha de un personaje filtrado se re-renderiza: `frontmatter.unir(d, cuerpo)`, con `d = p.model_dump(mode="json", exclude={"secreto", "coartada_y_cronologia_privada", "arco_previsto"}, exclude_none=True)` sin `d["identidad"]["rol_narrativo"]`.
  - `cuerpo` sale de `frontmatter.partir(texto)[1]`, o es el texto entero si no tiene frontmatter (las fuentes de `backend/tests/fuentes.py` no lo llevan).
  - Un personaje destapado va con su texto crudo.
  - La prosa del cuerpo de la ficha no se filtra por campo: la cubre el solape.
- Descartadas: re-renderizar solo cuando «se quita algo», que ya no distingue nada porque `rol_narrativo` siempre está; y filtrar después de ensamblar, con lo que el secreto estaría un momento en memoria dentro del texto del briefing.

### D-10. `_permitidos` y las pistas falsas
- Elegida: `secreto.permitidos` (D-3) añade el `contenido` de las pistas falsas de `ficha.pistas_falsas_a_desmontar`. El briefing del escritor las trae en «Pistas de este capítulo» con la acción `desmontar`.
- Para el solape (§8.4), el conjunto de textos permitidos en N es `permitidos(misterio, ficha, n)` más el contenido de las revelaciones y los giros con `capitulo_previsto ≤ N`. Un bloque que aparece en alguno de ellos no cuenta.
- Descartada: admitir también las pistas falsas ya desmontadas en capítulos anteriores. Nada las incrusta.

### D-11. Briefing de reintento del escritor
- Detección: es reintento si en el run ya existe `briefings/NN-escritor.md`. `K = 2 + nº de NN-escritor-intento-*.md`, y el primer reintento es `-intento-2`.
- Qué entra: cada `qa/NN-*.json` de RF-03 solo si su `st_mtime_ns` es posterior al del último briefing del escritor del run. Así, el informe de continuidad de un ciclo anterior no vuelve en un reintento motivado por `validar`. `NN-escritor.md` no se toca (CA-03).
- Capa nueva `reintento: qa_saneado` en `recipes.py` y en la receta del escritor. Sin reintento, no emite nada.
- Qué no se rompe:
  - La custodia (`delta/cmd.py:27` y `:34-48`) solo mira los briefings de revisión y el del cronista.
  - `checkpoint` no mira briefings.
  - La tabla de reanudación («cualquier otro caso → paso 2») regenera el briefing y produce un `-intento-K`, lo que es correcto: el capítulo ya se intentó.
  - El hook no interviene, porque escribe el CLI.
  - La API no lista briefings.
  - La trayectoria (5.2) trata `NN-escritor-intento-K.md` como un briefing del escritor.
- Descartadas: `--reintento` en la orden (el procedimiento podría olvidarlo sin que nada lo viera) y sacar K del log (en la fase 2 todavía no hay líneas `gate`).

### D-12. `novela trayectoria` desde el hook `Stop`
- Entrada: sin `--transcript`, lee de stdin el JSON del hook y usa `transcript_path` y `session_id`. No usa `cwd` (§8.7): el workspace se resuelve con el slug de las órdenes y `WorkspaceRepository.resolver`, como cualquier otra orden (`NOVELAS_DIR` o `novelas/`).
- Clave de sesión: `NOVELA_SESSION_ID` del entorno del hook, que lo hereda de `claude`. Es el `sesion=` de `harness.log` y sobrevive a un `/clear`. El `session_id` del transcript se guarda como dato de la entrada.
- Slug, capítulo y run:
  - Salen de cada `tool_use` `Bash` cuyo `command` empieza por `novela <sub> <slug> <cap>`.
  - El `run_id`, de la salida del `novela briefing` (`runs/<run_id>/briefings/…`, `briefing/cmd.py:173-176`).
  - El código, de `is_error` y del prefijo `Exit code N` (PA-3).
  - Las órdenes del arranque (`nueva`, `briefing … arquitecto|trazador`, `validar-plan`, `gate … plan`) no forman tramo: las sesiones de `/novela-nueva` no tienen tramo (§8.7).
- Subagentes: se aceptan `Agent` y `Task` como nombre de la herramienta (en `humo-0003` es `Agent`, 17 usos), y el tipo sale de `input.subagent_type` o de `toolUseResult.agentType`. Los fixtures usan `Agent`, y uno repite con `Task`.
- Tramo:
  - Empieza en la primera orden `novela` de la sesión que nombra el capítulo N, porque una sesión reanudada no empieza por el `briefing … escritor`.
  - Termina en la primera orden que nombra N+1, o al final del transcript. Así caben las órdenes que §8.7 exige tras el checkpoint del último capítulo de un acto (`sonda … texto` y `auditar --acto`).
  - Es «cerrado» si contiene su `checkpoint` en 0. Uno abierto se evalúa con lo que no deja artefacto, el contexto y la compactación, pero no con RF-24.
- Lecturas: solo un `Read`, `Bash` o `PowerShell` sobre `capitulos/` es violación. El resto de lecturas de la sesión principal (`checkpoints/latest.json`, la búsqueda de `intervencion.md`) son del procedimiento. Un `Write` o un `Edit` de `runs/*/intervencion.md` tampoco es violación (D-28).
- `trayectoria-NN.json` acumula una entrada por sesión (`sesiones: {<NOVELA_SESSION_ID>: …}`), reescrita de forma atómica. RF-24 mira la unión de agentes de todas las sesiones del capítulo.
- Lock: se toma con `ws.bloquear()` (timeout 0, `plataforma/lock.py:18-28`). Si está ocupado, no escribe, lo dice en stderr y sale con 0. El freno lo pone `pendiente` (D-13).
- Códigos: nunca sale con 2 desde el hook. Un stdin ilegible sale con 1, y todo error por tramo se captura y va a stderr. En un hook `Stop`, un 2 bloquea el fin del turno.
- Idempotencia: la de D-6.
- Modelos tolerantes: los del transcript viven en `slices/trayectoria/transcript.py` con `ConfigDict(extra="ignore", frozen=True)`, no en `dominio/`. Cubren `toolUseResult` (objeto o cadena de error), `compact_boundary`, `isCompactSummary` y el `message.id` repetido. Una línea que no casa se cuenta como `lineas_ilegibles` y se ignora.
- Fixtures de transcript sin prosa: `backend/novela/slices/trayectoria/fixtures/*.jsonl`, construidos a mano con la forma de la spec §4 y textos de relleno.
- Sin `NOVELA_SESSION_ID`: sale con 0 sin leer nada (RF-20).

### D-13. Orden de las comprobaciones de `pendiente`
1. Hay una intervención viva en cualquier run → 5.
2. La novela está terminada → 1.
3. Al último capítulo cerrado le falta `trayectoria-NN.json`, o el fichero no tiene la entrada de la sesión que lo cerró, y esa sesión no es `NOVELA_SESSION_ID` → 5. La sesión que cerró sale de la línea `checkpoint NN -> 0` del run del checkpoint. Si la línea no lleva `sesion=` (fábrica, tests, sesiones de desarrollo), no se exige.
4. En otro caso → 0.

- Descartado: exigir la trayectoria también a una novela terminada. `humo-0003`, cerrada antes de la fase 5, pararía para siempre.

### D-14. `intervencion.md` con bloques
- Elegida: `backend/novela/plataforma/intervencion.py` (nuevo) es la única implementación del CLI. `escribir(run, bloque)` añade un bloque que empieza por `# Intervención — capítulo NN` y reescribe el fichero entero de forma atómica. `viva(ruta)` es verdadero si, después del último encabezado `# Intervención`, no hay ninguna línea que empiece por `resuelto:`. `vivas(ws)` recorre `runs/*/intervencion.md`.
- Descartada: sobrescribir el fichero, que borraría una intervención resuelta del mismo run.
- Motivo: los ficheros de un solo bloque, como los dos de `humo-0003`, se siguen leyendo igual.

### D-15. Agente `sonda`
- `novela sonda` vive en `slices/briefing/` (`sonda.py`, puro, y la orden en `cmd.py`), como `estado` y `pendiente` comparten `slices/estado/cmd.py`. La sonda del texto tiene que escribir un briefing, y un slice no importa otro.
- `novela briefing <slug> <cap> sonda` sale con 2: la sonda del briefing lee `NN-escritor.md` y la del texto la genera `novela sonda … texto`, que es lo que exige el orden de §8.7.
- Receta `sonda` (`presupuesto_tokens: 80000`, `excluir: [canon/misterio]`) con solo dos capas:
  - `capitulos: acto_en_curso`, nueva (4.3): el texto de los capítulos del acto de N hasta N, sin frontmatter.
  - `reparto: sin_rol`, de la tarea 1.7: id, nombre y alias de cada ficha.
  - Sin `canon/premisa` ni `canon/mundo`: `mundo` trae `quien_tiene_acceso`, que es material de trama.
- Guardarraíles: en el briefing de la sonda, la capa `capitulos` no la miran ni el solape ni el guardarraíl literal (RF-02). Solo queda `reparto` sometido a los dos. Un aborto al generar `NN-sonda.md`, que solo puede venir de `reparto` o de un `PresupuestoExcedido`, sale con 5 e intervención: es un canon contradictorio o un acto que no cabe, y los dos necesitan decisión humana.
- Votos (§8.1):
  - Un voto es inválido si no valida contra `VotoSonda` o si su `st_mtime_ns` es anterior al del briefing que juzga (`NN-escritor.md` o `NN-sonda.md`). Un voto inválido cuenta como ausente.
  - La moda de los tres es el `culpable_id` con dos o más votos, y sin ella no hay acierto.
  - La mediana de `confianza` se calcula sobre los votos que forman la moda.
- En el contrato de `test_contratos.py`, las salidas se escriben con un comodín `K` (`qa/NN-sonda-briefing-K.json` y `qa/NN-sonda-texto-K.json`). `_instancia` y `test_salidas_casan_el_contrato` de `test_hook.py` lo sustituyen por 1–3.

### D-16. Tipos de hallazgo nuevos
Se añaden a `TipoHallazgo` (`qa.py:17-43`):
- `validar`: `cita_de_pista` (ausente, de menos de 15 caracteres o no literal; la `descripcion` copia la cita, RF-05), `conjunto_distinto_del_plan`, `pista_pagada_sin_plantar`, `lexico_vetado`.
- `validar-plan`: `fair_play_del_plan`, `orden_de_pistas`, `hilo_mal_formado`, `solape_con_el_secreto`, `curva_mal_formada`, y se reutiliza `id_inexistente`.
- `gate`: `tension_fuera_de_banda`, `tendencia_negativa`, `gancho_fuera_de_plan`, `informe_ilegible`.
- `sonda`: `fuga_del_secreto`, `pista_sin_efecto`, `voto_ausente`.
- `auditar --acto`: `pista_vencida`, `hilo_vencido`, `hueco_de_tension`, `deriva_de_estilo`, y se reutilizan `revelacion_sin_pista`, `pista_falsa_sin_desmontar` y `tension_fuera_de_banda`.

La spec solo nombra `gancho_fuera_de_plan` y `pista_sin_efecto` (PA-6).

### D-17. Qué tensión mira el gate `revision`
- La de N sale de `qa/NN-suspense.json` `puntuaciones.tension`, redondeada como en `delta/cmd.py:55-57`, porque `tension_real[N]` todavía no existe (lo escribe `aplicar-delta`, después). Un `qa/NN-suspense.json` sin `puntuaciones.tension` es ilegible, y por tanto rechazado (§8.1).
- N−1 y N−2 salen de `estado.tension_real`. La tendencia exige que los tres tengan valor (CA-16).

### D-18. Última escena del gancho (RF-17)
- Del briefing `NN-lector-suspense.md` del run se toma la sección `## objetivo · capítulo NN`. Es la última capa de su receta (`backend/config/recipes.yaml:51-56`), y un test lo fija. Se quita el frontmatter del capítulo incrustado, y la última escena empieza tras la última línea cuyo `strip()` es igual a `convenciones_formato.separador_escena`, `* * *` por defecto. La fábrica usa `***` (`fabrica.py:175`).
- La comparación es `normalizar(cita) in normalizar(escena)`. Sin `gancho`, el informe es ilegible (§8.1).

### D-19. `GanchoFinal` baja a `dominio/base.py`
- `plan.py:16-18` lo reexporta. Lo necesita `qa.Gancho`, y las ramas de `dominio/` no se importan entre sí (`base.py:16`).

### D-20. Tests sobre `humo-0003`
- Elegida: los criterios que citan `humo-0003` (CA-06, CA-08, CA-09 y CA-14) y la medida de falsos positivos del solape (2.4) tienen su mitad de humo en `backend/tests/test_humo_0003.py` (nuevo), con la marca `humo` y `pytest.skip` si no existe `RAIZ_REPO/novelas/humo-0003`. Se ejecutan en local antes del commit de su tarea, y el «Hecho cuando» lo exige.
- Los tests que leen `canon/misterio.md` (2.4) no imprimen nunca su texto: los mensajes de fallo solo dan la capa, el fichero y el número de bloques.
- CA-15 no depende del workspace: `backend/tests/fixtures/humo0003.py` (nuevo) transcribe de su escaleta solo ids y números de capítulo (hilos, pistas, revelaciones y curva). Corre en CI.
- La mitad de CI de cada criterio es sintética y property-based.
- Descartadas: versionar una copia de `novelas/humo-0003/` (ver PA-1) y dejar la mitad de humo sin automatizar.

### D-21. Scores nuevos y cómo se prueban sin red (RF-12, RF-15, RNF-05)

| Emite | Score | Valor |
|---|---|---|
| `checkpoint` | `estilo` | fracción de rasgos medidos dentro de tolerancia en `huella` de `qa/NN-validacion.json` (sustituye al veredicto de `qa/NN-estilo.json`) |
| `checkpoint` | `carga_preguntas` | la cuenta en bruto (entero como `float`) |
| `sonda … texto` (D-31) | `previsibilidad` | la fracción de votos válidos que aciertan el culpable (PA-7), con el capítulo y el `run_id` de N |
| `trayectoria` | `trayectoria` | 1 sin violaciones y 0 con alguna, por cada tramo cerrado, con el `run_id` del tramo |
| `trayectoria` | `contexto_max` | el máximo de tokens de contexto del tramo |

- Todos por `langfuse.desde_entorno(langfuse.entorno_efectivo(run.RAIZ_REPO))`, como `checkpoint/cmd.py:113`. Se prueban parcheando `urllib.request.urlopen`, como `test_checkpoint.py:78-101`, y con `SinkNulo` por defecto gracias a `_sin_claves_reales` (`backend/conftest.py:23-32`).

### D-22. Aviso de carga en `harness.log`
- Una línea propia, con `Run.registrar` y no con `registro`: `<marca> [sesion=…] aviso NN carga_preguntas · <motivo>`. No contiene ` -> `, así que ningún recuento de `<orden> NN -> X` la ve.

### D-23. Gate `delta` sin línea de `aplicar-delta`
- Sale con 2 (uso incorrecto). El procedimiento llamó al gate sin aplicar el delta.

### D-24. `validar-plan` escribe un `InformeQA`
- `qa/plan-validacion.json` con `capitulo: 1` y `agente: validar-plan`.

### D-25. Huella
- La lista fija de palabras funcionales es una constante de `huella.py`: unas 50 palabras frecuentes del español. Con `idioma` distinto de `es`, `delta_burrows` no se mide.
- Palabras: secuencias `\w+` tras NFC. Se excluyen las líneas que empiezan por `#` y las de separador.
- `delta_burrows_canon` (contra `parrafos_canonicos` de 1.000 palabras o más) se registra sin tolerancia y no cuenta como rasgo medido del score (PA-8).

### D-26. Posición de las sondas y de la auditoría de acto en el bucle
- La sonda del briefing va después del primer `novela briefing … escritor` del capítulo y antes de su `Task`.
- La sonda del texto va después del `checkpoint` de N, cuando N es el último capítulo de un acto o N = R − 1 (§8.7).
- `auditar --acto K` va después de la sonda del texto del último capítulo del acto K.

### D-27. Reintento del trazador
- Con el gate `plan` en 1, el `trazador` se reinvoca con su mismo briefing y `reintento: qa/plan-validacion.json` en el prompt. El trazador ve el misterio, así que ese informe no necesita sanearse.

### D-28. Quién escribe `intervencion.md`
- Elegida: desde la tarea 3.8, los procedimientos no la escriben para los gates que decide `novela gate` (`plan`, `mecanico`, `final`, `revision`, `delta`), ni para `sonda` ni `auditar --acto`: un 5 significa que ya la escribió el CLI. La siguen escribiendo para las paradas que ningún subcomando decide: el código 4, un 1 de `briefing` o de `checkpoint`, y el gate del `arquitecto` en `/novela-nueva`.
- Descartada: que no la escriban nunca. Una parada del arranque o un workspace inválido quedarían sin rastro en disco, y `pendiente` no las vería, porque solo mira `intervencion.md`.
- La regla 3 del hook sigue permitiendo `intervencion.md` a la sesión principal, y la trayectoria no cuenta ese `Write` como violación (spec §8.7).

### D-29. Cada gate cuenta aparte
- `consumidos(lineas, nn, tipo)` filtra por las tres partes de la orden (`gate`, `NN`, `<tipo>`). `mecanico` y `final` tienen líneas distintas, así que los fallos del `escritor` y los del `editor-estilo` no se suman (§8.1). La reanudación distingue `gate NN mecanico -> 0` de `gate NN final -> 0` (3.8).
- Descartada: una cuenta común de «gate mecánico» para los pasos 3 y 5, que es lo que hacía la prosa de la 0003 (`novela-continuar.md:101`).

### D-30. Qué autoriza una intervención resuelta
- Elegida: autorizan la causa en ese capítulo solo `tendencia_negativa` (gate `revision`) y `fuga` (sonda).
  - El gate, antes de intervenir por `tendencia_negativa`, busca en el run una línea `gate NN revision -> 5 · intervención (tendencia_negativa)`. Si la hay, y no hay intervención viva (se comprobó antes, D-6), la causa está autorizada: sigue evaluando la banda y el gancho, que pueden dar 1.
  - La sonda, con una fuga previa resuelta cuya `entradas=` es la sha de los mismos votos, sale con 0. Si el operador regeneró el briefing, los votos quedan anteriores a él y son inválidos (D-15), así que la sonda vuelve a pedir votos.
  - `agotamiento` nunca autoriza nada: reinicia la cuenta (D-6).
  - `custodia` tampoco: es una precondición sobre datos, y si la cadena sigue rota el gate vuelve a intervenir.
- Descartada: que cualquier intervención resuelta autorice su causa, `custodia` incluida, con lo que un capítulo reescrito tras el `cronista` pasaría al reintento.

### D-31. La sonda del texto va tras el checkpoint y emite `previsibilidad`
- Elegida: como §8.7 pone `sonda … texto` después del `checkpoint`, la orden trabaja sobre el run cerrado de N (D-7) y es ella quien emite `previsibilidad` por el `ScoreSink`, con el mismo id determinista (`<slug>-<run_id>-NN-previsibilidad`, `langfuse.py:52`) que tendría si la emitiera `checkpoint`.
- Descartada: que `checkpoint` la emita, porque la sonda del texto todavía no ha corrido cuando `checkpoint` se ejecuta (PA-13, resuelta).

## 5. Fases y tareas

### 5.1 Orden de ejecución y por qué

```
Fase 1 ──► Fase 2 ──► Fase 3 ──► Fase 4 ──► Fase 5 ──► Fase 6
 (gates)   (secreto)  (gate +    (acto +    (trayec-   (release,
                      procedim.)  sonda)     toria)     humo-0002)
```

- **1 antes que todo.** Es el cambio de contrato de más superficie (frontmatter, delta y canon de estilo) y el que más toca la fábrica. Todo lo posterior escribe fixtures con el contrato nuevo. No cambia el procedimiento, salvo el `--final` del paso 5 (1.9), que entra en el mismo commit que el flag, así que el bucle no queda nunca roto.
- **2 antes que 3.** El briefing de reintento (2.5) cambia los pasos 3 y 6 del procedimiento en su mismo commit, sin tocar la cuenta de intentos. La fase 3 reescribe entonces un procedimiento que ya no tiene la línea `reintento:` del escritor. Además, `culpable` (2.1) y `dominio/secreto.py` (2.2) los necesita `validar-plan` (3.3).
- **3 cambia el procedimiento una sola vez** (3.8), después de que existan y estén probados `validar-plan` y los cinco gates (3.3–3.7). Hasta 3.8, los subcomandos existen y nadie los llama, y el bucle sigue como en la fase 2.
- **4 después de 3.** La sonda y la auditoría de acto emiten el código 5 (3.1), escriben intervenciones con el mismo módulo y usan el formato de línea de D-6. La sonda usa el filtro y el solape de la fase 2.
- **5 después de 4.** Las comprobaciones de orden de §8.7 incluyen `gate`, `validar --final`, las dos sondas y `auditar --acto`, y la regla de «uno de los ocho» necesita el octavo agente.
- **6 al final.** Mide todo lo anterior con modelos reales.

Dentro de cada fase, el orden de las tareas es el de su fichero: cada una depende de las anteriores que lista en «Depende de».

### 5.2 Reparto de la documentación de referencia

Va en el mismo commit que el código (`AGENTS.md` § Proceso: modificar documentación). Solo se describe lo que ya existe tras el commit.

| Tarea | `docs/architecture.md` | `docs/validators.md` | `docs/definitions.md` | `AGENTS.md` / `CLAUDE.md` |
|---|---|---|---|---|
| 1.2 | §7.5 (salidas del trazador) | — | §3 (`pistas_falsas_a_desmontar`, `analepsis`) | — |
| 1.3 | §7.2 (frontmatter con citas de 15 caracteres o más) | §3.9.4 al estado real; §6, fila `validar` | §6 (frontmatter) | — |
| 1.4 | §6.3 (pistas falsas permitidas) | — | — | — |
| 1.5 | §8 (qué comprueba `validar`) | §3.9.8, cruce con el plan; §3.6, tabla de propiedades | — | `AGENTS.md` «CLI», línea de `validar` |
| 1.6 | §7.6 (cita obligatoria, mínimo 15) | §3.9.8 | §4 (delta) | — |
| 1.7 | §6.2 (receta del `cronista` con `canon/mundo` y `reparto`); §7.5 (entradas del `cronista`); §7.6 | §3.9.8 (invariantes); §5.13 | §4 (`destapa`) y §2.4 | — |
| 1.8 | §6.4 (memoria validada) | §3.9.11 | — | — |
| 1.9 | §8 (`validar --final`, `final: true`) | §3.9.9 (léxico) | §2.5 (`lexico_vetado`); QA (`final`) | `AGENTS.md` «CLI»; `CLAUDE.md` «Bucle por capítulo» (`validar --final`) |
| 1.10 | §7.3 (`huella`) | §3.9.9 (huella); §3.7 (módulos mutados) | §2.5 (`ritmo.tolerancias`) | — |
| 1.11 | §10.5 (`estilo` desde la huella) | — | — | — |
| 2.1 | §7.5 (salidas del arquitecto) | — | §2.4 (`culpable`) | — |
| 2.3 | §6.3 (filtro de los cuatro campos) | §4.4, fila del filtro por campo (cuatro campos); §4.9 (riesgo de 0003 §13 cerrado); §6, fila «Cada briefing» | — | — |
| 2.4 | §6.3 (solape, permitidos, constantes) | §4.4, fila del solape (conjunto de §8.4 y exención de lo permitido) | — | — |
| 2.5 | §2.1, párrafo «Reintentos»; §4 (`NN-escritor-intento-K.md`); §6.2 (capa `reintento`) | §4.4, fila del reintento; §4.6 («Reflection»: el escritor recibe su briefing de intento) | §6 (briefing de intento) | `CLAUDE.md` «Bucle por capítulo» (reintento con su briefing, no con el QA) |
| 3.1 | §8, «Parada» (código 5) | §4.5 (quién escribe la intervención) | §6 (`intervencion.md` con bloques) | — |
| 3.3 | §8 (`validar-plan`) | §3.9.1 al estado real; §6, fila «Tras el trazador» | §1 (`banda_tension`, `max_capitulos_sin_subir`); §8 | `AGENTS.md` «CLI» |
| 3.4 | §2.1, tabla «Gates» (cinco gates) y «Quién orquesta» | §4.4, fila de `novela gate` («incrementa `cursor.intento`» deja de ser cierto: cuenta en `harness.log`); §4.10 | §8 (protocolo) | `AGENTS.md` «CLI» (`gate` con cinco tipos) |
| 3.5 | — | §4.17, F-06 | §6 (`NN-gate-revision.json`) | — |
| 3.6 | — | §4.13 (banda y tendencia; la tendencia resuelta autoriza) | — | — |
| 3.7 | §7.3 (`gancho`) | §3.9.10; §6, fila `validar` (el gancho pasa al gate) | — | — |
| 3.8 | §2.1, §8 | §4.17, F-31 y F-35 | — | `CLAUDE.md` «Bucle por capítulo» y «Máximo dos reintentos…» |
| 3.9 | — | §4.10 (el model checking llama al gate real) | — | — |
| 4.1 | §10.5 (`carga_preguntas`) | §4.13 | — | — |
| 4.2 | §8 (`auditar --acto`) | §4.13; §6, fila «Frontera de acto» | — | `AGENTS.md` «CLI» |
| 4.4 | §2.2 (tabla de modelos); §6.2 (receta `sonda`); §7.4; §7.5; §7.1 (regla 5 del hook, ocho roles) | §3.8 (ocho ficheros); §4.4, fila de la regla 5 (ocho); §4.15 («sin herramientas» pasa a `Read, Write`) | §7 (agentes) | `AGENTS.md` «Qué es este proyecto» (ocho roles); `CLAUDE.md` «Subagentes» y «Hooks» (ocho) |
| 4.5 | §8 (`sonda`); §10.5 (`previsibilidad`, D-31) | §4.15 (`culpable` en vez de `culpable_o_amenaza`, votos, moda); §5.12 | §6 (votos y `NN-sonda-<tipo>.json`) | `AGENTS.md` «CLI» |
| 4.6 | — | §4.2 (el lector-suspense no puntúa la previsibilidad) | — | `CLAUDE.md` «Bucle por capítulo» (sondas y auditoría de acto) |
| 5.2 | — | §4.16 al estado real («uno de los siete» → ocho; sin «nivel de degradación registrado»); §4.13 (modelo resuelto: lo registra la trayectoria) | §6 (`trayectoria-NN.json`) | — |
| 5.3 | §10.5 (`trayectoria`, `contexto_max`) | §4.17, F-08, F-33 y F-53 | — | `AGENTS.md` «CLI» |
| 5.4 | §10.1 (dos hooks `Stop`) | §6, fila «Fin de sesión» | — | `CLAUDE.md` «Hooks» |
| 5.5 | §2.3 (`pendiente` con 5) | §4.4, filas de `pendiente` (código 5; la trayectoria ausente con sesión distinta); §4.17, F-34; §6, fila `pendiente` | — | `AGENTS.md` «CLI» (`pendiente`) |
| 5.6 | §9 sin niveles 2 a 4 ni `novela budget` (CA-24) | §3.9.7 (cita de los niveles 2 y 4); §4.4, fila de `novela budget` (fuera); §4.12 (el ensayo de niveles de cuota desaparece; queda la reanudación); §4.13 (huecos «por nivel 3») | — | — |
| 6.1 | — | §4.11; §4.2 (calibración) | — | — |
| 6.2 | — | §4.9 y §4.16 (canario del orquestador); §4.17, F-25 | — | — |
| 6.3 | — | §5.16; umbrales calibrados en §4.13 y §4.16 | — | — |

`validators.md` §2 (tabla resumen) se actualiza en la tarea que cambia el estado de cada método. `docs/domain-knowledge.md` no se toca: la spec no lo cita (§14).

## 6. Estrategia de testing

| Fase | Property-based (Hypothesis) | Ejemplo e integración | Mutación | Contrato |
|---|---|---|---|---|
| 1 | citas de pistas (CA-05), cita obligatoria de 15 o más (CA-06), un test por invariante (CA-07), igualdad de conjuntos (CA-09), léxico vetado (CA-10) | huella sobre ritmo conocido (CA-11), resúmenes (CA-08), `calcular_scores` (CA-12), `validar` < 2 s (RNF-01), humo marcado (D-20) | `gates.py`, `apply.py`, `violaciones.py`, `huella.py` | `capitulo`, `delta`, `canon` (léxico, tolerancias) y `plan-capitulo` (CA-28); OpenAPI |
| 2 | filtro de los cuatro campos (CA-01), solape con exención de lo permitido (CA-02), reintento saneado (CA-03) | golden regenerado, `NN-escritor.md` con el mismo sha, capa < 3.000 tokens (RNF-02), falsos positivos del solape en `humo-0003` (local) | — | `canon` (`culpable`) |
| 3 | banda y tendencia (CA-16), las seis de `validar-plan` (CA-14) | ciclo de los cinco gates con el agente falso (CA-19): repetición por última línea, cuenta aparte, intervención viva, reinicio y autorización; gancho (CA-17); salida ≤ 3 líneas (RNF-02); `validar-plan` < 5 s (RNF-01); procedimientos (CA-29) | `decision.py`, `comprobaciones.py` del plan | `config`, `qa-informe`; model checking con el gate real (§13) |
| 4 | — | carga sobre el calendario de `humo-0003` (CA-15), auditoría de acto (CA-18), votos fixture con moda, mediana y antigüedad (CA-04), cadencia | `carga.py` | ocho agentes, hook y regla 5 (CA-30); `sonda-voto` |
| 5 | — | transcripts fixture por comprobación, con `Agent` y `Task` (CA-13, CA-20, CA-22, CA-24), `pendiente` (CA-21), 10 MB < 5 s (RNF-01), sin texto (RNF-07), scores sin red (RNF-05) | — | `trayectoria`; `settings.json` con `Stop` |
| 6 | — | modo en seco de revisores y calibración (CA-25) | — | fixtures contra sus esquemas |

Casos límite que el plan cubre explícitamente:

- Repetir un gate sin nada en medio (misma decisión, sin línea) y con otra orden en medio (intento nuevo) (3.4).
- Intervención viva, que no reinicia la cuenta, y resuelta, que la reinicia (3.4).
- Rechazos de `mecanico` que no consumen intentos de `final` (3.4).
- Informe de revisor más antiguo que su briefing, y suspense sin `tension` o sin `gancho` (3.5, 3.7).
- Tendencia negativa resuelta, que no vuelve a intervenir (3.6).
- Hueco en `tension_real` en medio de la tendencia (3.6) y en la auditoría de acto (4.2).
- Separador de escena ausente, con el capítulo entero como una sola escena (3.7).
- Voto más antiguo que su briefing, votos sin moda y fuga resuelta con los mismos votos (4.5).
- Tramo reanudado por otra sesión, y `Agent` frente a `Task` (5.2).
- `message.id` repetido (5.1).
- Lock ocupado en el hook (5.3).
- `novela` fuera del PATH, que falla cerrado (5.5).
- Intervención con dos bloques (3.1).
- `humo-0003` tras las rupturas (§7.4).

Reglas comunes de cada tarea con código:

1. Primero el test, y verlo en rojo. El rojo se anota en el cuerpo del commit.
2. Después el mínimo verde, y el refactor con la suite en verde.
3. Antes de commitear, desde `backend/`: `uv run pytest`, `uv run mypy --strict .` y `uv run ruff check .`. En las tareas que tocan módulos mutados, además `uv run mutmut run` sin supervivientes nuevos.
4. Cada modelo Pydantic cambiado va con `REGENERAR=1 uv run pytest tests/test_contratos.py`, `docs/definitions.md` y el test de contrato, en el mismo commit.
5. Si cambia `FrontmatterCapitulo`, `Estado` o `Manifest`, se regenera `backend/api/openapi.json` en el mismo commit.
6. Los cambios de prompt de agente no tienen TDD. Van en el commit del contrato que los exige, para que el bucle no quede roto, y se validan en 6.3.

## 7. Matriz de trazabilidad

### 7.1 Requisito → tarea

| Requisito | Descripción breve | Tareas |
|---|---|---|
| RF-01 | Filtro de cuatro campos; `culpable` y `destapa` | 1.7 (`destapa`), 2.1, 2.2, 2.3, 4.4 (sonda) |
| RF-02 | Solape con el conjunto secreto, salvo lo permitido; capa de capítulos de la sonda exenta | 2.2, 2.4, 4.4 (sonda) |
| RF-03 | Briefing de reintento con QA saneado | 2.5 |
| RF-04 | `novela sonda`, cadencia, votos y autorización | 4.5, 4.6 |
| RF-05 | Pistas y pistas falsas con cita de 15 o más | 1.1, 1.3, 1.4 |
| RF-06 | Cita obligatoria de 15 o más en las cuatro colecciones del delta | 1.6 |
| RF-07 | Invariantes narrativos | 1.7 |
| RF-08 | Resúmenes acotados | 1.1, 1.8 |
| RF-09 | Igualdad de conjuntos con el plan | 1.5 |
| RF-10 | Léxico vetado en `validar --final` | 1.9 |
| RF-11 | Huella en `qa/NN-validacion.json` | 1.10 |
| RF-12 | Score `estilo` desde la huella | 1.11 |
| RF-13 | Modelo resuelto frente a la trayectoria anterior en la que aparece | 5.2, 5.3 |
| RF-14 | `novela validar-plan` | 3.3, 3.8 |
| RF-15 | Carga de preguntas abiertas | 4.1 |
| RF-16 | Banda y tendencia | 3.6 |
| RF-17 | Gancho con cita | 3.7, 3.8 |
| RF-18 | `auditar --acto` | 4.2, 4.6 |
| RF-19 | `novela gate`, cinco tipos | 1.9 (`final: true`), 3.2, 3.4, 3.5, 3.8, 3.9 |
| RF-20 | `novela trayectoria` desde `Stop` | 5.1, 5.2, 5.3, 5.4 |
| RF-21 | Freno en `pendiente` | 5.5 |
| RF-22 | Contexto y compactación | 5.1, 5.2 |
| RF-23 | Fuera de esta spec | — |
| RF-24 | Política de cuota sin tocar capítulos cerrados | 5.2 (test), 5.6 (doc) |
| RF-25 | Control negativo de revisores | 6.1 |
| RF-26 | Calibración del juez | 6.1 |
| RF-27 | Canario del orquestador | 6.2, 6.3 |
| RF-28 | `pistas_falsas_a_desmontar` y `analepsis` | 1.2 |
| RF-29 | Código 5 | 3.1, 3.4, 3.8, 4.2, 4.5, 5.5 |
| RF-30 | Agente `sonda` | 4.4 |
| RNF-01 | Rendimiento de `validar`, `validar-plan` y `trayectoria` | 1.10, 3.3, 5.3 |
| RNF-02 | Capa `reintento` < 3.000 tokens; salidas ≤ 3 líneas | 2.5, 3.3, 3.4, 4.2, 4.5 |
| RNF-03 | Cero llamadas a modelo | todas; `test_sin_clientes_de_modelo` (`test_contratos.py:108-125`) sigue en verde |
| RNF-04 | Repetición por la última línea; `sonda` cuenta siempre | 3.2, 3.4, 4.5, 5.3 |
| RNF-05 | Scores nuevos | 1.11, 4.1, 4.5 (`previsibilidad`, D-31), 5.3 |
| RNF-06 | `humo-0003` se sigue leyendo | 1.6, §7.4 |
| RNF-07 | Trayectoria sin texto | 5.2, 5.3 |

Tareas de soporte, sin requisito propio: 1.1 (`dominio/texto.py`), 2.2 (`dominio/secreto.py`), 3.2 (parser del log), 4.3 (capa de capítulos del acto), 6.4 (cierre de la spec).

### 7.2 Criterio → test (rutas propuestas)

| CA | Test | Tarea |
|---|---|---|
| CA-01 | `backend/novela/slices/briefing/test_briefing.py::test_filtro_por_campo_property` (cuatro campos) | 2.3 (sonda: 4.4) |
| CA-02 | `backend/novela/slices/briefing/test_briefing.py::test_solape_property` · `::test_bloque_permitido_no_cuenta` · `backend/novela/dominio/test_secreto.py::test_bloque_de_palabras_cortas_no_cuenta` · `backend/novela/slices/briefing/test_briefing.py::test_capitulos_de_la_sonda_no_se_miran` | 2.2, 2.4 (sonda: 4.4) |
| CA-03 | `backend/novela/slices/briefing/test_reintento.py::test_capa_reintento_saneada_property` · `::test_briefing_original_intacto` | 2.5 |
| CA-04 | `backend/novela/slices/briefing/test_sonda.py::test_decision_con_votos_fixture` · `::test_mediana_de_los_votos_de_la_moda` · `::test_tercer_voto_ausente_interviene` · `::test_voto_mas_antiguo_que_su_briefing_es_ausente` · `::test_texto_en_r_menos_1_sin_acierto` · `::test_fuera_de_cadencia_no_lee_votos` · `::test_fuga_resuelta_mismos_votos` | 4.5 |
| CA-05 | `backend/novela/slices/validacion/test_gates.py::test_citas_de_pistas_property` · `::test_hallazgo_copia_la_cita` | 1.3 |
| CA-06 | `backend/novela/dominio/test_estado.py::test_delta_sin_cita_no_valida_property` · `backend/novela/slices/delta/test_delta.py::test_delta_sin_cita_deja_el_estado_igual` · `backend/tests/test_humo_0003.py::test_estado_sigue_leyendose` | 1.6 |
| CA-07 | `backend/novela/slices/delta/test_invariantes.py::test_invariante_1_muerto_no_resucita` … `::test_invariante_6_punto_de_vista` | 1.7 |
| CA-08 | `backend/novela/slices/delta/test_violaciones.py::test_resumen_nombres_e_ids` · `backend/tests/test_humo_0003.py::test_resumenes_se_aceptan` | 1.8 |
| CA-09 | `backend/novela/slices/validacion/test_gates.py::test_conjuntos_iguales_property` · `backend/tests/test_humo_0003.py::test_frontmatters_cumplen_la_igualdad` | 1.5 |
| CA-10 | `backend/novela/slices/validacion/test_gates.py::test_lexico_vetado_property` | 1.9 |
| CA-11 | `backend/novela/slices/validacion/test_huella.py::test_ritmo_conocido` · `::test_huella_no_cambia_el_veredicto` + `mutmut` sobre `huella.py` | 1.10 |
| CA-12 | `backend/novela/slices/checkpoint/test_checkpoint.py::test_estilo_desde_la_huella` | 1.11 |
| CA-13 | `backend/novela/slices/trayectoria/test_comprobaciones.py::test_modelo_cambiado` · `::test_modelo_contra_la_ultima_trayectoria_con_ese_agente` | 5.2 |
| CA-14 | `backend/novela/slices/validacion_plan/test_comprobaciones.py::test_cada_comprobacion_rompe_property` · `backend/tests/test_humo_0003.py::test_plan_valida` + `mutmut` sobre la curva | 3.3 |
| CA-15 | `backend/novela/slices/checkpoint/test_carga.py::test_carga_humo_0003` · `::test_tres_bajadas_en_acto_2` + `mutmut` | 4.1 |
| CA-16 | `backend/novela/slices/gate/test_decision.py::test_banda_y_tendencia_property` + `mutmut` | 3.6 |
| CA-17 | `backend/novela/slices/gate/test_decision.py::test_gancho` · `backend/novela/slices/gate/test_gate.py::test_gancho_fuera_de_plan_en_el_informe` | 3.7 |
| CA-18 | `backend/novela/slices/auditoria/test_auditoria.py::test_acto_con_hueco` · `::test_acto_pista_vencida_interviene` | 4.2 |
| CA-19 | `backend/novela/slices/gate/test_gate.py::test_ciclo_de_cada_gate` (cinco tipos) · `::test_repeticion_sin_orden_en_medio` · `::test_orden_en_medio_cuenta_otro_intento` · `::test_intervencion_viva_no_reinicia` · `::test_resuelta_concede_tres` · `::test_mecanico_no_consume_final` · `::test_informe_mas_antiguo_que_su_briefing` · `::test_custodia_interviene_al_primero` · `::test_tendencia_resuelta_no_vuelve_a_intervenir` · `backend/tests/test_bucle.py::test_la_maquina_con_el_gate_real` | 3.4, 3.5, 3.6, 3.9 |
| CA-20 | `backend/novela/slices/trayectoria/test_comprobaciones.py::test_cada_violacion` · `::test_transcript_limpio` · `::test_agent_y_task_dan_la_misma_trayectoria` · `::test_reanudado_no_da_agente_ausente` · `backend/novela/slices/trayectoria/test_trayectoria.py::test_sin_sesion_no_escribe` · `::test_sin_texto_de_prompt_ni_retorno` | 5.2, 5.3 |
| CA-21 | `backend/novela/slices/estado/test_estado.py::test_pendiente_intervencion_viva` · `::test_pendiente_trayectoria_ausente` | 5.5 |
| CA-22 | `backend/novela/slices/trayectoria/test_comprobaciones.py::test_compactacion_en_tramo` · `backend/novela/slices/trayectoria/test_transcript.py::test_message_id_repetido_cuenta_una_vez` | 5.1, 5.2 |
| CA-24 | `backend/novela/slices/trayectoria/test_comprobaciones.py::test_capitulo_cerrado_sin_lector_suspense` + revisión del commit de 5.6 | 5.2, 5.6 |
| CA-25 | `backend/tests/revisores/test_en_seco.py::test_fixtures_validan` · `::test_veredicto_en_seco` | 6.1 |
| CA-27 | Demostración (D): `uv run python -m tests.canario.orquestador` en `humo-0002`; la lectura del veredicto, en `backend/tests/canario/test_veredicto_orquestador.py` | 6.2, 6.3 |
| CA-28 | `backend/novela/dominio/test_plan.py::test_ficha_con_y_sin_campos_nuevos` | 1.2 |
| CA-29 | `backend/tests/test_contratos.py::test_procedimientos_y_codigo_5` | 3.8 |
| CA-30 | `backend/tests/test_contratos.py::test_agentes_de_claude` (ocho) · `backend/tests/test_hook.py::test_subagentes` (noveno nombre) · `::test_salidas_casan_el_contrato` | 4.4 |

La spec no tiene CA-23 ni CA-26: RF-23 sale y RF-26 lo cubre CA-25.

### 7.3 Tareas por fase

| Fase | Tareas | Nº |
|---|---|---|
| 1 | 1.1 – 1.11 | 11 |
| 2 | 2.1 – 2.5 | 5 |
| 3 | 3.1 – 3.9 | 9 |
| 4 | 4.1 – 4.6 | 6 |
| 5 | 5.1 – 5.6 | 6 |
| 6 | 6.1 – 6.4 | 4 |

### 7.4 `humo-0003` tras las rupturas (RNF-06)

| Orden sobre `humo-0003` | Tras la fase | Resultado | Motivo |
|---|---|---|---|
| `novela estado --breve`, `--json` | todas | funciona | `Estado` no cambia (§8.8, `state.schema.json` «sin cambios»); D-4 deja la cita obligatoria y el mínimo de 15 solo en el delta |
| `novela pendiente` | todas | 1 (terminada) | D-13: la terminada se decide antes que la trayectoria ausente, y sus dos intervenciones están resueltas |
| `GET /novelas/humo-0003/estado`, `…/runs/{id}`, `…/capitulos/{n}` | todas | 200 | no validan el frontmatter |
| `GET …/capitulos` (índice) | 1.3 | 404 | `FrontmatterCapitulo` nuevo (`capitulos.py:18-21` → `WorkspaceInvalido` → 404 por `api/main.py:24-28`) |
| `novela exportar` | 1.3 | 4 | `export/cmd.py:30` valida el frontmatter |
| `novela validar`, `aplicar-delta` | 1.3, 1.6 | hallazgos o 1 | frontmatter y delta nuevos |
| `novela briefing`, `novela auditar` | 2.1 | 4 | `Misterio` sin `culpable` |

Tests que la usan, solo lectura y solo en local (D-20): `backend/tests/test_humo_0003.py` (CA-06, CA-08, CA-09, CA-14 y la medida del solape de 2.4). Ninguno escribe: todos leen sobre una copia en `tmp_path` o con los modelos, sin `run.abrir`. El de 2.4 completa en memoria un `culpable` ficticio para validar el misterio, porque el suyo no lo tiene, y ese campo no interviene en el conjunto secreto (§8.4).

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| La spec en el árbol tiene cambios sin commitear (`git status`: `M docs/specs/0002-…`) y el plan se basa en esa copia | M | M | Commitear la v0.3 enmendada antes de 1.1; si cambia un CA, se revisa la tarea que lo cierra |
| Un cambio de contrato de agente en un commit distinto del de su modelo deja el bucle roto | M | A | Regla 6 de §6: el prompt va en el commit del modelo (1.3, 1.6, 1.7, 1.9, 2.1, 2.5, 3.7, 4.4, 4.6) |
| La igualdad de Pydantic entre clases distintas rompe la idempotencia del delta | A si no se atiende | A | D-4 y la propiedad de `test_apply.py:26-36` en el mismo commit |
| El solape (5 palabras) da falsos positivos sobre un canon real que repite frases entre pistas y revelaciones | M | M | Exención de lo permitido (D-10); constantes con nombre y medida sobre `humo-0003` en 2.4; `humo-0002` lo mide |
| La sonda del texto recibe capítulos que el filtro no mira, y un capítulo que revela antes de tiempo solo lo ve la propia sonda | M | M | Es lo que la sonda mide (RF-02); el acierto antes de tiempo sale con 5 |
| Exit 2 de `trayectoria` en un hook `Stop` impide terminar el turno | M | A | D-12: nunca 2 desde el hook; test que invoca la orden con stdin ilegible y asserta 1 |
| En una sesión interactiva, un turno que acaba entre el `checkpoint` del último capítulo de un acto y su `sonda … texto` da una violación de orden | B | M | El bucle hace el capítulo en un solo turno; si el turno acaba ahí, es una parada real del procedimiento y merece intervención |
| La forma del resultado de `Bash` y el nombre `Agent` no son contrato (§5.10) | M | A | Se aceptan `Agent` y `Task`; si cambian, no hay trayectoria y `pendiente` para (falla cerrado, D-13) |
| `novela` no está en el PATH del hook (Windows, Device Guard: la memoria del proyecto dice que hay que usar el `novela.exe` de `backend\.venv`) | M | M | Falla cerrado vía `pendiente`; `comprobar-entorno` ya comprueba que `novela` arranca (`entorno/cmd.py:1-2`) |
| El recuento por mtime (ilegibilidad, votos y QA del reintento) depende del reloj del sistema de ficheros | B | M | Riesgo aceptado en la spec §13 (§5.18); se usa `st_mtime_ns` y se prueba con `os.utime` explícito |
| `run.abrir` crea un run espurio si un subcomando nuevo se llama fuera de rango | M | M | D-7: salida 2 antes de abrir |
| Mutación más lenta al ampliar `paths_to_mutate` | A | B | Un `runner` por módulo con solo sus tests (patrón de `pyproject.toml:73`) |
| Si se implementa antes la spec 0004 (T-01 sirve `Config`), `banda_tension` cambia su OpenAPI y `frontend/src/shared/api/esquema.gen.ts` | M | B | En 3.3, regenerar `openapi.json` y, si existe, `esquema.gen.ts` (regla 5 del plan de la 0004) |
| El repositorio contiene instrucciones dirigidas a agentes (`CLAUDE.md` «Tu papel como sesión principal», procedimientos) | B | B | Se trataron como contexto; ninguna cambia el plan |
| Un umbral provisional (los siete de §13) para el bucle en falso en `humo-0002` | M | M | Tarea 6.3: se calibran y se registran; la huella no es gate |

## 9. Preguntas abiertas

Ninguna. Las doce de la primera redacción del plan y la que abrieron las enmiendas de la spec (PA-13) se cerraron el 2026-09-24.

| ID | Resolución | Dónde queda |
|----|------------|-------------|
| PA-1 | Se acepta el supuesto: las mitades de `humo-0003` de CA-06, CA-08, CA-09 y CA-14 llevan la marca `humo`, se saltan en CI y corren en local. No se versiona ningún extracto de `novelas/`. CA-14 completa `pistas_falsas_a_desmontar` en memoria y usa un misterio sintético; la spec ya lo dice así | D-20; spec CA-14 |
| PA-2 | **Cambia el supuesto.** Una intervención resuelta concede otros tres intentos: `consumidos` cuenta solo las líneas `-> 1` posteriores a la última `-> 5 · intervención (` del mismo gate. La `intervención viva` no reinicia | Spec §8.1; D-6; tarea 3.4 |
| PA-3 | **Verificada**, no bloquea. La entrada del hook `Stop` trae `session_id`, `transcript_path` y `hook_event_name`: es lo que lee `langfuse_hook.py` del plugin, que trazó cada sesión de `humo-0003`. En el transcript de la sesión `34d4bf3c`, un `Bash` con código distinto de 0 da `is_error: true` y un texto que empieza por `Exit code N`, y `toolUseResult` es entonces una cadena `Error: Exit code N…`. Con 0, `toolUseResult` es un objeto con `stdout`, y el de `novela briefing` trae `runs/<run_id>/briefings/…`. Que un 2 en `Stop` bloquee el fin del turno es la semántica documentada de Claude Code, y D-12 nunca sale con 2 | Spec §4; fase 5 |
| PA-4 | **Cambia el supuesto.** Los procedimientos siguen escribiendo `intervencion.md` para las paradas que el CLI no decide | D-28; spec CA-29; tarea 3.8 |
| PA-5 | Es lo esperado: el invariante 3 se implementa tal cual. La spec recoge ya la evidencia (§2 y §8.3) | Tarea 1.7 |
| PA-6 | Se aceptan los nombres de D-16. Entran en `qa-informe.schema.json` en el commit de su tarea, y renombrarlos después es una ruptura | D-16 |
| PA-7 | `previsibilidad` es la fracción de votos válidos de la sonda del texto que aciertan el culpable, de 0 a 1. Más alto es más previsible | D-21 |
| PA-8 | `delta_burrows_canon` se registra sin tolerancia y no cuenta para `estilo` | D-25 |
| PA-9 | La unión de las entradas por sesión de `trayectoria-NN.json`, con clave `NOVELA_SESSION_ID` | D-12 |
| PA-10 | La orden compuesta tras `novela` (F-25) entra como tercera comprobación del canario del orquestador, sin CA propio | Tarea 6.2 |
| PA-11 | Lanza `humo-0002` el operador, con el bucle desatendido de `AGENTS.md`. Los resultados y los umbrales calibrados van a la spec §13, en un apartado «Baseline» como el de la 0003, y a `validators.md` | Tarea 6.3 |
| PA-12 | Test sobre un fixture realista, y un aviso en la salida de `briefing` si la capa `reintento` pasa de 3.000 tokens. Nunca se trunca | Tarea 2.5 |
| PA-13 | **Resuelta.** Se acepta D-31: `previsibilidad` la emite `novela sonda … texto`, que corre tras el `checkpoint`. La spec corrige RNF-05 | D-31; spec RNF-05 |
