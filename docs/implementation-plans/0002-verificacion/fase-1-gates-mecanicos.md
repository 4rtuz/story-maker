# Fase 1: gates mecánicos sobre capítulo y delta

Plan: `README.md` · Spec: §5.1, RF-05 a RF-12, RF-28, §8.3, §8.5, §8.8 · Decisiones: D-2, D-3, D-4, D-5, D-8, D-10, D-16, D-25

Once ciclos cerrados. La fase no cambia el procedimiento, salvo el `--final` del paso 5 (1.9), que entra en el mismo commit que el flag. Tres rupturas de contrato: frontmatter (1.3), delta (1.6) y el `destapa` compatible del canon (1.7). Cada una lleva su prompt de agente en el mismo commit, para que el bucle no quede roto entre commits (README §6, regla 6).

Antes de cada commit, desde `backend/`: `uv run pytest`, `uv run mypy --strict .` y `uv run ruff check .`. En las tareas que tocan módulos mutados, además `uv run mutmut run`.

---

#### 1.1 `dominio/texto.py`: normalizar, palabras, frases, ids y nombres propios

- **Descripción.** Tarea de soporte (D-3). `normalizar` baja de `backend/novela/slices/delta/violaciones.py:17-20` a `dominio/`, y `violaciones.py` la reimporta, así que el comportamiento no cambia. Se añaden las funciones puras que usan RF-05, RF-06, RF-08 y RF-11:
  - `MIN_CITA = 15`: el mínimo de caracteres de una cita tras normalizar (RF-05, RF-06).
  - `palabras(texto) -> list[str]`: secuencias `\w+` tras NFC.
  - `frases(texto) -> list[str]`: segmentos terminados en `.`, `!`, `?` o `…`.
  - `ids_citados(texto) -> set[str]`: la unión de los patrones de `backend/novela/dominio/ids.py:13-22`, sin anclas.
  - `candidatos_nombre_propio(texto) -> set[str]`: palabras de tres letras o más que empiezan por mayúscula y no abren frase, tras `.`, `!`, `?`, `…` o `:`, ni el texto (§8.3).
- **Ficheros.**
  - `backend/novela/dominio/texto.py` (nuevo)
  - `backend/novela/dominio/test_texto.py` (nuevo)
  - `backend/novela/slices/delta/violaciones.py` (modificar: `from novela.dominio.texto import normalizar`)
- **Rojo.** `test_texto.py`:
  - `test_normalizar_es_la_de_0001`: la misma tabla de casos que ya cubre `test_violaciones.py::test_citas_property`, ahora contra `novela.dominio.texto.normalizar`.
  - `test_candidatos_tras_puntuacion_y_al_inicio`: «Ana vio a Luis. Luego: Marta» da `{"Luis"}`.
  - `test_ids_citados_cubre_todos_los_prefijos`: property, un id generado de cada prefijo dentro de un texto aparece en el conjunto.

  Falla hoy con `ModuleNotFoundError: novela.dominio.texto`.
- **Verde.** El módulo, con las expresiones de `ids.py` reutilizadas (sin copiar la regex), y el import en `violaciones.py`.
- **Refactor.** `violaciones._ESPACIOS` desaparece.
- **Commit.** `refactor(dominio): normalizar y utilidades de texto en dominio/texto.py`
- **Cubre.** Soporte de RF-05, RF-06, RF-08 y RF-11.
- **Depende de.** —
- **Hecho cuando.** `uv run pytest novela/dominio/test_texto.py novela/slices/delta` pasa tras verse en rojo, y ningún test existente cambia.
- **Complejidad.** S
- **Docs.** Ninguno.

#### 1.2 Ficha de plan: `pistas_falsas_a_desmontar` y `analepsis` (RF-28)

- **Descripción.**
  - `FichaCapitulo` (`backend/novela/dominio/plan.py:79-100`) gana `pistas_falsas_a_desmontar: list[PistaFalsaId] = []`.
  - `EscenaPlan` (`:61-76`) gana `analepsis: bool = False`.
  - Es compatible (§8.8).
  - La fábrica escribe `pistas_falsas_a_desmontar` solo en la ficha del capítulo que desmonta `pfa-001` (`cuando_se_desmonta = num_capitulos − 1`, `fabrica.py:130`), para no cambiar el golden del capítulo 8.
- **Ficheros.**
  - `backend/novela/dominio/plan.py` (modificar)
  - `backend/novela/dominio/test_plan.py` (modificar)
  - `backend/schemas/plan-capitulo.schema.json` (regenerar)
  - `backend/tests/fixtures/fabrica.py` (modificar `plan`)
  - `.claude/agents/trazador.md` (modificar: los dos campos y cuándo se usan)
  - `docs/definitions.md` §3 (modificar)
  - `docs/architecture.md` §7.5 (modificar)
- **Rojo.** `test_plan.py::test_ficha_con_y_sin_campos_nuevos` (CA-28): una ficha sin los campos valida con sus defectos; con ellos, valida y los conserva; y las dos validan con `jsonschema` contra `backend/schemas/plan-capitulo.schema.json`. Falla hoy porque el modelo tiene `extra="forbid"` (`base.py:24`) y rechaza los campos. `test_contratos.py::test_state_schema_al_dia` pasa a rojo en cuanto cambia el modelo.
- **Verde.** Los dos campos, `REGENERAR=1 uv run pytest tests/test_contratos.py` y la fábrica.
- **Refactor.** —
- **Commit.** `feat(plan): la ficha declara las pistas falsas que desmonta y las escenas en analepsis`
- **Cubre.** RF-28.
- **Depende de.** —
- **Hecho cuando.** CA-28 pasa tras verse en rojo; `plan-capitulo.schema.json` regenerado; el golden `backend/tests/fixtures/golden/08-escritor.md` sin cambios; suite, `mypy` y `ruff` en verde.
- **Complejidad.** S
- **Docs.** `definitions.md` §3 y `architecture.md` §7.5, en este commit.

#### 1.3 Frontmatter con citas: pistas plantadas, pagadas y falsas desmontadas (RF-05)

- **Descripción.**
  - `FrontmatterCapitulo` (`backend/novela/dominio/artefactos.py:30-46`): `pistas_plantadas` y `pistas_pagadas` pasan a `list[PistaCitada]`, con `PistaCitada(Modelo): id: PistaId; cita: str`, y se añade `pistas_falsas_desmontadas: list[PistaFalsaCitada] = []`. La cita no lleva mínimo en el modelo: una cita corta tiene que llegar al gate para que su hallazgo la copie.
  - Nuevo gate `_citas` en `backend/novela/slices/validacion/gates.py`. Por cada entrada de las tres listas, un hallazgo `cita_de_pista` (D-16) si falta, si `len(normalizar(cita)) < MIN_CITA` o si `normalizar(cita)` no es subcadena de `normalizar(cuerpo)` (los dos lados normalizados, como 0001 RF-33). La `descripcion` del hallazgo copia la cita, porque el `editor-estilo` reintenta con su mismo briefing, que no trae las pistas, y solo así puede restaurar la frase que borró (RF-05).
  - Se adaptan los consumidores de ids: `gates._pistas` y `gates._ids` (`:58-99`), `apply._pistas` (`backend/novela/slices/delta/apply.py:41-62`, con `p.id`), `delta/cmd.py:124-128` y `backend/tests/estrategias.py::frontmatter_de`.
  - La fábrica (`fabrica.capitulo`, `:280-314`) escribe `{id, cita}` con la frase `Elena encontró la pista …` del cuerpo, de más de 15 caracteres, y, en el capítulo que desmonta `pfa-001`, una frase propia y su cita.
- **Ficheros.**
  - `backend/novela/dominio/artefactos.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar: `cita_de_pista`)
  - `backend/novela/slices/validacion/gates.py` (modificar)
  - `backend/novela/slices/validacion/test_gates.py` (modificar)
  - `backend/novela/slices/delta/apply.py` (modificar)
  - `backend/novela/slices/delta/cmd.py` (modificar)
  - `backend/novela/slices/delta/test_apply.py` (modificar `test_pistas_derivadas_del_frontmatter`)
  - `backend/tests/estrategias.py` (modificar)
  - `backend/tests/fixtures/fabrica.py` (modificar)
  - `backend/tests/fixtures/golden/08-escritor.md` (regenerar: el capítulo 7 incrustado cambia de frontmatter)
  - `backend/schemas/capitulo.schema.json` y `qa-informe.schema.json` (regenerar)
  - `backend/api/openapi.json` (regenerar: `GET …/capitulos` devuelve `FrontmatterCapitulo`, `backend/api/routers/capitulos.py:18-21`)
  - `.claude/agents/escritor.md` (modificar: el frontmatter con `{id, cita}`, la cita de 15 caracteres o más y la pista falsa)
  - `.claude/agents/editor-estilo.md` (modificar: en reintento, restaura la frase que copia el hallazgo `cita_de_pista`)
  - `docs/architecture.md` §7.2, `docs/validators.md` §3.9.4 y §6, `docs/definitions.md` §6 (modificar)
- **Rojo.** `test_gates.py`:
  - `test_citas_de_pistas_property` (CA-05): sobre `capitulos_validos()` (la estrategia existente de `test_gates.py:91`, adaptada), en una entrada de cualquiera de las tres listas se quita la cita, se sustituye por un texto que no es subcadena del cuerpo normalizado o se recorta a menos de 15 caracteres normalizados. `gates.validar` devuelve al menos un `cita_de_pista`, y el capítulo intacto no devuelve ninguno. También pasa una cita que solo casa tras normalizar los dos lados (espacios y saltos distintos).
  - `test_hallazgo_copia_la_cita` (CA-05): la `descripcion` del hallazgo de una cita no literal contiene la cita.

  Falla hoy porque el modelo no tiene `cita` ni el gate existe: `FrontmatterCapitulo` rechaza `{id, cita}`, y el caso intacto sale con `frontmatter_invalido`.
- **Verde.** Modelo, gate `_citas` tras `_frontmatter`, adaptaciones de `.id` y fábrica. `REGENERAR=1` para los dos esquemas y para `openapi.json`, y `REGENERAR=1` en `test_golden_escritor`.
- **Refactor.** Las listas de ids que usan `_pistas`, `_ids` y `apply._pistas` salen de un helper `ids(lista)` en `artefactos.py`.
- **Commit.** `feat(validar): cada pista del frontmatter lleva la cita que la planta, la paga o la desmonta`
- **Cubre.** RF-05.
- **Depende de.** 1.1, 1.2
- **Hecho cuando.**
  - CA-05 pasa tras verse en rojo, también con `--hypothesis-profile=ci`.
  - `test_bucle.py::test_bucle_completo_con_agente_falso` en verde con la fábrica nueva.
  - El diff del golden solo toca el frontmatter del capítulo 7 incrustado.
  - `openapi.json` regenerado.
  - `mutmut` sin supervivientes nuevos en `gates.py`, incluida la comparación con `MIN_CITA`.
- **Complejidad.** M
- **Docs.** `architecture.md` §7.2; `validators.md` §3.9.4 (la cita ya existe) y §6, fila `novela validar <cap>`; `definitions.md` §6.

#### 1.4 El briefing del escritor trae las pistas falsas a desmontar (RF-05, D-10)

- **Descripción.**
  - `_pistas_del_capitulo` (`backend/novela/slices/briefing/assemble.py:152-162`) añade `- pfa-NNN · desmontar · <contenido>` por cada id de `ficha.pistas_falsas_a_desmontar`, y lanza `FuenteAusente` si el misterio no la tiene.
  - `_permitidos` (`:240-254`) admite ese contenido (D-10). En 2.4 pasa a `dominio/secreto.permitidos` (D-3).
- **Ficheros.**
  - `backend/novela/slices/briefing/assemble.py` (modificar)
  - `backend/novela/slices/briefing/test_briefing.py` (modificar)
  - `docs/architecture.md` §6.3 (modificar)
- **Rojo.** `test_briefing.py`:
  - `test_pistas_falsas_del_capitulo_en_el_briefing`: property sobre `estrategias.misterios()` con una ficha que desmonta una de sus pistas falsas. El cuerpo del briefing del escritor contiene su contenido tras «Pistas de este capítulo», y `ensamblar` no lanza `FugaDelSecreto`.
  - `test_pista_falsa_ajena_sigue_siendo_fuga`: el contenido de una pista falsa que la ficha no desmonta, inyectado en la ficha, sí la lanza.

  Falla hoy porque el contenido no se incluye y, si se inyecta, el guardarraíl aborta.
- **Verde.** Las dos funciones.
- **Refactor.** —
- **Commit.** `feat(briefing): el escritor recibe el contenido de las pistas falsas que desmonta su capítulo`
- **Cubre.** RF-05 (spec §5.1.1, segunda mitad).
- **Depende de.** 1.2
- **Hecho cuando.** Los dos tests pasan tras verse en rojo; `test_misterio_nunca_en_briefing` sigue en verde; el golden no cambia.
- **Complejidad.** S
- **Docs.** `architecture.md` §6.3.

#### 1.5 Igualdad de conjuntos con el plan y pista pagada ya plantada (RF-09)

- **Descripción.**
  - `gates._pistas` y `gates._hilos` (`gates.py:58-82`) se sustituyen por `_conjuntos(fm, ficha)`, que compara los cinco pares de §5.1.2 con `==` sobre conjuntos y emite un hallazgo `conjunto_distinto_del_plan` por par distinto, con la diferencia simétrica en `referencia`. También entra `_pagadas(fm, plantadas_antes)`, que da `pista_pagada_sin_plantar` si una pista pagada no está plantada antes ni en este capítulo.
  - `Contexto` (`:19-26`) gana `plantadas_antes: frozenset[str]`, que `validacion/cmd.py::_contexto` (`:19-38`) saca de `estado.pistas` con `plantada_en < capitulo`.
  - `hilo_cerrado_sin_abrir` se conserva como caso particular.
- **Ficheros.**
  - `backend/novela/slices/validacion/gates.py` (modificar)
  - `backend/novela/slices/validacion/cmd.py` (modificar)
  - `backend/novela/slices/validacion/test_gates.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar: dos tipos)
  - `backend/schemas/qa-informe.schema.json` (regenerar)
  - `backend/tests/test_humo_0003.py` (nuevo, marca `humo`, D-20)
  - `backend/pyproject.toml` (modificar: marca `humo` en `[tool.pytest.ini_options]`)
  - `docs/validators.md` §3.9.8 y §3.6, `docs/architecture.md` §8, `AGENTS.md` «CLI» (modificar)
- **Rojo.**
  - `test_gates.py::test_conjuntos_iguales_property` (CA-09): sobre fichas y frontmatters generados iguales, se altera uno de los cinco conjuntos (añadir o quitar un id) o se paga una pista que no está en `plantadas_antes` ni en `pistas_plantadas`. Asserta rechazo, y que el caso sin alterar pasa. Falla hoy porque un id de más en el frontmatter no se detecta (`_pistas` solo mira lo que falta).
  - `test_humo_0003.py::test_frontmatters_cumplen_la_igualdad`: lee `novelas/humo-0003/capitulos/0N.md` y `plan/capitulos/0N.md`, reduce las pistas del frontmatter antiguo (ids sueltos) a conjuntos y aplica `_conjuntos` a los ids. Espera cero hallazgos. Salta si no existe el workspace.
- **Verde.** Las dos funciones y `plantadas_antes`.
- **Refactor.** `test_gates.py::test_gates_property` (`:91-111`) incorpora el defecto «conjunto».
- **Commit.** `feat(validar): frontmatter y ficha declaran los mismos conjuntos, y lo pagado ya está plantado`
- **Cubre.** RF-09.
- **Depende de.** 1.3
- **Hecho cuando.**
  - CA-09 pasa tras verse en rojo.
  - La mitad de humo pasa en local, lo que confirma la evidencia de P-17.
  - `mutmut` sobre `gates.py` sin supervivientes en `_conjuntos` ni `_pagadas`.
  - Suite en verde.
- **Complejidad.** M
- **Docs.** `validators.md` §3.9.8 («Cruce con el plan», estado real) y §3.6; `architecture.md` §8; `AGENTS.md` «CLI» (`validar`: «… pistas con cita e igualdad con el plan …»).

#### 1.6 Cita obligatoria de 15 caracteres o más en las cuatro colecciones del delta (RF-06, D-4)

- **Descripción.**
  - En `backend/novela/dominio/estado.py`: `EntradaTemporalDelta`, `EntradaConocimientoDelta` y `HechoDelta`, con `cita: str` obligatoria, un `field_validator` que exige `len(normalizar(cita)) >= MIN_CITA` (1.1) y `al_estado()`. El `Delta` (`:159-178`) usa esas en `linea_temporal`, `conocimiento`, `conocimiento_lector` y `libro_de_hechos`.
  - `EntradaTemporal`, `EntradaConocimiento` y `Hecho` (`:70-75`, `:87-92`, `:115-119`) del estado no cambian, porque `state.schema.json` no cambia (§8.8) y la base de `humo-0003` tiene una cita de menos de 15 caracteres (RF-06).
  - `apply.aplicar` (`apply.py:73-105`) y `violaciones._reescrituras` y `_citas` (`violaciones.py:37-78`) convierten con `al_estado()` antes de comparar o de añadir. `_citas` ya normaliza los dos lados (`:69-77`).
  - La fábrica añade la cita a la segunda escena (`fabrica.py:365-370`, `frase_de_escena(n, 2)`) y a `conocimiento_lector` (`:391`, `frase_de_hecho(n)`). `estrategias.deltas` genera citas con una estrategia `cita_larga` (una `frase` filtrada por `len(normalizar(x)) >= 15`).
- **Ficheros.**
  - `backend/novela/dominio/estado.py` (modificar)
  - `backend/novela/dominio/test_estado.py` (modificar)
  - `backend/novela/slices/delta/apply.py` (modificar)
  - `backend/novela/slices/delta/violaciones.py` (modificar)
  - `backend/novela/slices/delta/test_delta.py` (modificar)
  - `backend/tests/estrategias.py` (modificar)
  - `backend/tests/fixtures/fabrica.py` (modificar)
  - `backend/tests/test_humo_0003.py` (modificar)
  - `backend/schemas/delta.schema.json` (regenerar)
  - `.claude/agents/cronista.md` (modificar: cita obligatoria, de 15 caracteres o más, en las cuatro colecciones, sin exención)
  - `docs/definitions.md` §4, `docs/architecture.md` §7.6, `docs/validators.md` §3.9.8 (modificar)
- **Rojo.**
  - `test_estado.py::test_delta_sin_cita_no_valida_property` (CA-06, mitad del esquema): sobre `estrategias.deltas()`, en una entrada de cualquiera de las cuatro colecciones se quita la cita o se recorta a menos de 15 caracteres normalizados. `Delta.model_validate` lanza `ValidationError`; sin cita, además, el JSON resultante no valida con `jsonschema` contra `delta.schema.json`. Falla hoy porque `cita` es opcional en tres colecciones y no tiene mínimo en ninguna.
  - `test_delta.py::test_delta_sin_cita_deja_el_estado_igual`: por CLI sobre `demo-24`, un delta del capítulo 8 sin una cita, o con una de 10 caracteres en `libro_de_hechos`, sale con 1, y `estado --json` es idéntico antes y después.
  - `test_apply.py::test_idempotencia_property` y `test_violaciones.py::test_reaplicar_lo_mismo_no_es_duplicar` se ejecutan con los tipos nuevos y deben seguir en verde. Si no se convierte, fallan (D-4).
  - `test_humo_0003.py::test_estado_sigue_leyendose`: `novela estado humo-0003 --json` sobre una copia en `tmp_path` sale con 0 y valida contra `state.schema.json`.
- **Verde.** Tipos, conversión, fábrica y estrategias.
- **Refactor.** `estrategias.citas` (`:296-301`) sin los filtros `if e.cita`.
- **Commit.** `feat(delta): toda entrada del delta lleva una cita de 15 caracteres o más, en el contrato del delta`
- **Cubre.** RF-06, RNF-06.
- **Depende de.** 1.1
- **Hecho cuando.** CA-06 (las dos mitades de CI) pasa tras verse en rojo; la de humo, en local; la idempotencia sigue en verde; `delta.schema.json` regenerado; `state.schema.json` sin diff.
- **Complejidad.** M
- **Docs.** `definitions.md` §4 (delta); `architecture.md` §7.6; `validators.md` §3.9.8 («Qué entra ya» pasa a describir lo que hay).

#### 1.7 Invariantes narrativos del delta (RF-07, D-2)

- **Descripción.**
  - `Revelacion` (`backend/novela/dominio/canon.py:159-166`), y con ella `Giro`, gana `destapa: list[PersonajeId] = []`. Es compatible, D-2.
  - `violaciones.violaciones` (`violaciones.py:100-107`) recibe un `ContextoNarrativo` (dataclass congelado, puro) con:
    - `personajes_con_ficha`
    - `escenarios` (ids de `canon/mundo.md`)
    - `destapados_en_n` (unión de `destapa` de revelaciones y giros con `capitulo_previsto = N`)
    - `presentes_en_analepsis` (personajes de las escenas de la ficha con `analepsis: true`)
    - `pov` (de la ficha)
    - `punto_de_vista` (de `config.yaml`)
  - Añade `_invariantes(estado, delta, ctx)`, con las seis reglas de §8.3.
  - La cáscara (`delta/cmd.py::_derivados`, `:51-70`, o una función hermana) lee `canon/mundo.md`, `canon/personajes/*.md`, la ficha y `config.yaml`.
  - **El `cronista` tiene que poder cumplir los invariantes 3 y 4.** Hoy su receta (`backend/config/recipes.yaml:58-63`) solo trae estado y capítulo, y en `humo-0003` inventó escenarios (`esc-torre-faro`) y un personaje (`per-anselmo`) en los tres deltas. La receta gana `permanente: [canon/mundo]` y la capa `reparto: sin_rol`: un YAML con `id`, `nombre` y `alias` por ficha de personaje, sin `rol_narrativo`, `secreto` ni ningún otro campo (§8.9). La capa `Reparto` se crea aquí, en `recipes.py` y `assemble._capas`, y la fase 4 la reutiliza para la `sonda` (4.4).
- **Ficheros.**
  - `backend/novela/dominio/canon.py` (modificar)
  - `backend/novela/slices/delta/violaciones.py` (modificar)
  - `backend/novela/slices/delta/cmd.py` (modificar)
  - `backend/novela/slices/delta/test_invariantes.py` (nuevo)
  - `backend/novela/slices/briefing/recipes.py`, `assemble.py`, `test_assemble.py` y `backend/config/recipes.yaml` (modificar: capa `reparto` y receta del `cronista`)
  - `backend/tests/estrategias.py` (modificar: `destapa`)
  - `backend/schemas/canon.schema.json` (regenerar)
  - `backend/pyproject.toml` (modificar: `violaciones.py` y `test_invariantes.py` en `mutmut`)
  - `.claude/agents/cronista.md` (modificar: solo personajes con ficha y ubicaciones del canon, que ahora vienen en su briefing)
  - `.claude/agents/arquitecto.md` (modificar: `destapa`)
  - `docs/definitions.md` §2.4, `docs/architecture.md` §6.2, §7.5 y §7.6, `docs/validators.md` §3.9.8 y §5.13 (modificar)
- **Rojo.** `test_invariantes.py`, un test property-based por invariante (CA-07), cada uno con un delta que lo viola, que debe rechazarse con su causa, y uno que lo respeta, que debe aplicarse:
  - `test_invariante_1_muerto_no_resucita`, con la excepción de `destapa` en N.
  - `test_invariante_2_muerto_no_aprende`, con la excepción de `analepsis`.
  - `test_invariante_3_ubicaciones_del_canon`
  - `test_invariante_4_personajes_del_canon`, con las cinco posiciones de §8.3.
  - `test_invariante_5_hilos`
  - `test_invariante_6_punto_de_vista`, con `multiple` y `narrador_no_fiable` exentos.

  Y en `test_assemble.py`, `test_briefing_del_cronista_trae_ids_del_canon`: el briefing del `cronista` contiene cada id de escenario de `mundo` y cada id de personaje con ficha, y no contiene `rol_narrativo`, ni texto de `secreto`, ni de `coartada_y_cronologia_privada`.

  Fallan hoy porque `violaciones` no recibe contexto ni tiene la regla, y la receta del `cronista` no tiene canon.
- **Verde.** `destapa`, contexto, invariantes, capa `reparto` y receta.
- **Refactor.** Las cinco posiciones de personaje del invariante 4 salen de un solo generador de ids.
- **Commit.** `feat(delta): aplicar-delta rechaza deltas que violan los invariantes narrativos`
- **Cubre.** RF-07, y RF-01 en parte (`destapa`).
- **Depende de.** 1.2, 1.6
- **Hecho cuando.**
  - Los siete tests pasan tras verse en rojo, también con el perfil `ci`.
  - `test_bucle.py` en verde: la fábrica ya cumple los seis invariantes (escenarios de `mundo`, personajes con ficha, todos vivos, POV `per-elena-vidal` con su conocimiento en el del lector).
  - El briefing del `cronista` cabe en su presupuesto (`recipes.yaml:59`, 70.000) sobre `demo-24`.
  - `mutmut` sin supervivientes en `_invariantes`.
- **Complejidad.** L
- **Docs.** `definitions.md` §2.4 (`destapa`); `architecture.md` §6.2 (receta del `cronista`), §7.5 (entradas del `cronista`) y §7.6; `validators.md` §3.9.8 (invariantes al estado real) y §5.13.

#### 1.8 Resúmenes acotados (RF-08)

- **Descripción.** `violaciones._resumen(delta, cuerpo, ids_validos, nombres_canon)`:
  - Sobre `linea`, `parrafo` y cada valor de `escena`, todo id de `texto.ids_citados` tiene que estar en `ids_validos` (los del delta, los de la ficha y los del canon).
  - Todo candidato de `texto.candidatos_nombre_propio` tiene que estar en `texto.palabras(cuerpo)` o en `nombres_canon` (palabras de `nombre` y `alias` de las fichas y de `nombre` de escenarios e instituciones).
  - La cáscara pasa los dos conjuntos. Va antes de renderizar la memoria (`delta/cmd.py:120-123`).
- **Ficheros.**
  - `backend/novela/slices/delta/violaciones.py` (modificar)
  - `backend/novela/slices/delta/cmd.py` (modificar)
  - `backend/novela/slices/delta/test_violaciones.py` (modificar)
  - `backend/tests/test_humo_0003.py` (modificar)
  - `docs/validators.md` §3.9.11, `docs/architecture.md` §6.4 (modificar)
- **Rojo.**
  - `test_violaciones.py::test_resumen_nombres_e_ids` (CA-08): un resumen con «… y habló con Ramiro.», donde Ramiro no aparece en el cuerpo ni en el canon, se rechaza. «Ramiro habló.», al principio de la frase, se acepta. Un `obj-099` inexistente se rechaza.
  - `test_humo_0003.py::test_resumenes_se_aceptan`: con el delta, el cuerpo y el canon de `humo-0003` en local, `_resumen` no devuelve nada en los tres capítulos. Lee el cuerpo por código, no por la sesión.

  Falla hoy porque la función no existe.
- **Verde.** La función y su cáscara.
- **Refactor.** —
- **Commit.** `feat(delta): el resumen solo nombra ids y personas que estén en el capítulo o en el canon`
- **Cubre.** RF-08.
- **Depende de.** 1.1, 1.7
- **Hecho cuando.** CA-08 pasa tras verse en rojo; la mitad de humo pasa en local (0 falsos positivos, como §8.3); la fábrica no dispara (`Elena`, `Tomás` e `Inés` son nombres del canon).
- **Complejidad.** M
- **Docs.** `validators.md` §3.9.11; `architecture.md` §6.4.

#### 1.9 Léxico vetado en `validar --final` (RF-10, D-5)

- **Descripción.**
  - `Estilo` (`canon.py:213-220`) gana `lexico_vetado: list[str] = []`.
  - `InformeQA` (`qa.py:57-65`) gana `final: bool = False` (§8.8), que el gate `final` de la fase 3 exige a `true` (§8.1).
  - `gates.validar` gana `final: bool` y `lexico: Sequence[str]`. Con `final`, añade `_lexico(cuerpo, lexico)`: `re.search(r"(?<!\w)" + re.escape(normalizar(e)) + r"(?!\w)", normalizar(cuerpo), re.IGNORECASE)`, con un hallazgo `lexico_vetado` por entrada presente.
  - `validacion/cmd.py::validar` (`:41-84`) acepta `--final`, lee `canon/estilo.md`, escribe `final: true` en `qa/NN-validacion.json` y registra `validar NN` con `final` en el detalle (D-5).
  - El paso 5 de `.claude/commands/novela-continuar.md` (`:80-82`) pasa a `novela validar <slug> <cap> --final`.
- **Ficheros.**
  - `backend/novela/dominio/canon.py` (modificar)
  - `backend/novela/slices/validacion/gates.py` (modificar)
  - `backend/novela/slices/validacion/cmd.py` (modificar)
  - `backend/novela/slices/validacion/test_gates.py` (modificar)
  - `backend/novela/slices/validacion/test_validacion.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar)
  - `backend/tests/estrategias.py` (modificar `estilos`)
  - `backend/schemas/canon.schema.json` y `qa-informe.schema.json` (regenerar)
  - `.claude/commands/novela-continuar.md` (modificar paso 5)
  - `.claude/agents/arquitecto.md` (modificar: `lexico_vetado`)
  - `.claude/agents/editor-estilo.md` (modificar: el léxico vetado se comprueba tras su reescritura)
  - `docs/definitions.md` §2.5 y QA, `docs/architecture.md` §8, `docs/validators.md` §3.9.9, `AGENTS.md` «CLI», `CLAUDE.md` «Bucle por capítulo» (modificar)
- **Rojo.**
  - `test_gates.py::test_lexico_vetado_property` (CA-10): una entrada del léxico, insertada en el cuerpo con mayúsculas aleatorias, da `lexico_vetado` con `final=True` y nada con `final=False`. Insertada solo dentro de otra palabra (prefijo y sufijo alfabéticos), no rechaza.
  - `test_validacion.py::test_final_en_el_log_y_en_el_informe`: `validar … --final` escribe una línea que contiene `validar 08 -> 0` y termina en `· final`, y `qa/08-validacion.json` lleva `final: true`. Sin `--final`, `final: false`.

  Falla hoy porque no hay flag ni campos.
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(validar): --final rechaza el léxico vetado del canon tras el editor-estilo`
- **Cubre.** RF-10, y RF-19 en parte (`final: true` que lee el gate `final`).
- **Depende de.** 1.3
- **Hecho cuando.** CA-10 pasa tras verse en rojo; la tabla de reanudación del procedimiento sigue casando la línea (`validar NN -> 0`); `mutmut` sobre `gates.py` sin supervivientes en `_lexico`.
- **Complejidad.** M
- **Docs.** `definitions.md` §2.5 y QA (`final`); `architecture.md` §8; `validators.md` §3.9.9; `AGENTS.md` «CLI» (`novela validar <slug> <cap> [--final]`); `CLAUDE.md` «Bucle por capítulo» (el segundo `validar` lleva `--final`).

#### 1.10 Huella estilométrica en `qa/NN-validacion.json` (RF-11, D-25)

- **Descripción.**
  - `Ritmo` (`canon.py:204-210`) gana `tolerancias: Tolerancias = Tolerancias()`, con `longitud_media_frase = 0.25` (relativa), `proporcion_dialogo = 0.10` (absoluta) y `delta_burrows = 0.9`.
  - `InformeQA` (`qa.py:57-65`) gana `huella: Huella | None = None`, con los cuatro rasgos de §8.5, `delta_burrows_canon`, `medidos` y `fuera_de_tolerancia`.
  - Nuevo `backend/novela/slices/validacion/huella.py` puro: `calcular(cuerpo, ritmo, separador, referencia: list[str] | None, canon: list[str]) -> Huella`. La referencia son las escenas de los capítulos 1 a 3, desde el capítulo 4, y se descartan las palabras de desviación nula.
  - `validacion/cmd.py` lee los capítulos 1–3 para N ≥ 4 y escribe `huella` en el informe **sin** convertirla en hallazgo.
- **Ficheros.**
  - `backend/novela/dominio/canon.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar)
  - `backend/novela/slices/validacion/huella.py` (nuevo)
  - `backend/novela/slices/validacion/test_huella.py` (nuevo)
  - `backend/novela/slices/validacion/cmd.py` (modificar)
  - `backend/novela/slices/validacion/test_validacion.py` (modificar `test_rendimiento`)
  - `backend/schemas/canon.schema.json` y `qa-informe.schema.json` (regenerar)
  - `backend/pyproject.toml` (modificar: `huella.py` en `paths_to_mutate` y `test_huella.py` en el `runner`)
  - `docs/definitions.md` §2.5, `docs/architecture.md` §7.3, `docs/validators.md` §3.9.9 y §3.7 (modificar)
- **Rojo.** `test_huella.py`:
  - `test_ritmo_conocido` (CA-11): texto fixture de 10 frases de 8 palabras y 2 líneas de diálogo de 10 palabras. Da una media de 8, una dispersión de 0 y una proporción de diálogo de 20 sobre 100. Con referencia 15, `longitud_media_frase` está fuera y `proporcion_dialogo` dentro.
  - `test_burrows_desde_el_4`: sin referencia, `delta_burrows` es `None` y no cuenta como medido.
  - `test_huella_no_cambia_el_veredicto`: por CLI sobre `demo-24` capítulo 8, con un ritmo que la fábrica incumple, el informe sigue `aprobado`, `hallazgos` está vacío y `huella.fuera_de_tolerancia` no.
  - `test_validacion.py::test_rendimiento` (RNF-01): un capítulo de 4.000 palabras se valida en menos de 2 s con huella y `--final`.

  Fallan hoy porque no existe el módulo ni el campo.
- **Verde.** Módulo, campos y cáscara.
- **Refactor.** La lista de palabras funcionales como `frozenset` constante.
- **Commit.** `feat(validar): huella estilométrica en el informe de validación, como señal y no como gate`
- **Cubre.** RF-11, RNF-01 (`validar`).
- **Depende de.** 1.1, 1.9
- **Hecho cuando.** CA-11 pasa tras verse en rojo; `uv run mutmut run` no deja supervivientes en las comparaciones con la tolerancia de `huella.py`; RNF-01 en verde.
- **Complejidad.** L
- **Docs.** `definitions.md` §2.5 (`ritmo.tolerancias`) y la sección de QA; `architecture.md` §7.3; `validators.md` §3.9.9 y §3.7 (módulos mutados).

#### 1.11 Score `estilo` desde la huella (RF-12)

- **Descripción.**
  - `checkpoint/cmd.py::calcular_scores` (`:29-52`) sustituye el parámetro `estilo: InformeQA | None` por `huella: Huella | None`, de `qa/NN-validacion.json`. `estilo = (medidos − fuera) / medidos` si hay rasgos medidos.
  - `checkpoint` deja de leer `qa/NN-estilo.json` (`:109`).
- **Ficheros.**
  - `backend/novela/slices/checkpoint/cmd.py` (modificar)
  - `backend/novela/slices/checkpoint/test_checkpoint.py` (modificar)
  - `docs/architecture.md` §10.5 (modificar)
- **Rojo.** `test_checkpoint.py::test_estilo_desde_la_huella` (CA-12):
  - `calcular_scores` con una huella de dos rasgos medidos y uno fuera da `estilo == 0.5`.
  - Por CLI, con `qa/08-estilo.json` borrado, `checkpoint` sigue emitiendo `estilo`, sin error. Se verifica con el `urlopen` parcheado de `test_checkpoint.py:92-96`.

  Falla hoy porque la firma espera un `InformeQA` y lee `qa/NN-estilo.json`.
- **Verde.** Cambio de firma y lectura.
- **Refactor.** —
- **Commit.** `feat(checkpoint): el score estilo sale de la huella y no del veredicto del editor`
- **Cubre.** RF-12, RNF-05 (`estilo`).
- **Depende de.** 1.10
- **Hecho cuando.** CA-12 pasa tras verse en rojo; `test_checkpoint_emite_los_seis_scores` sigue con los seis nombres.
- **Complejidad.** S
- **Docs.** `architecture.md` §10.5 («`estilo` es la fracción de rasgos de la huella en tolerancia»).
