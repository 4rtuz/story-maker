# Fase 2: el secreto en el briefing

Plan: `README.md` · Spec: §5.2, RF-01, RF-02, RF-03, §8.4 · Decisiones: D-3, D-8, D-9, D-10, D-11, D-20 · Depende de: fase 1 (`destapa` en 1.7, `pistas_falsas_a_desmontar` en 1.2, `dominio/texto.py` en 1.1)

Cinco ciclos. El procedimiento cambia una sola vez, en 2.5, y en su mismo commit: el reintento del escritor regenera su briefing en vez de pasarle `qa/`. La cuenta de intentos sigue en prosa hasta la fase 3.

`sonda` todavía no existe (4.4), así que en esta fase los briefings filtrados son los del `escritor` y del `editor-estilo`. La tarea 4.4 añade la sonda al mismo conjunto, con la exención de su capa de capítulos (RF-02).

---

#### 2.1 `Misterio.culpable` (RF-01, ruptura del canon)

- **Descripción.**
  - `Misterio` (`backend/novela/dominio/canon.py:178-198`) gana `culpable: PersonajeId`, obligatorio. `culpable_o_amenaza` se conserva, porque el conjunto secreto lo usa (§8.4).
  - Que `culpable` y cada `destapa` tengan ficha lo comprueba `validar-plan` (3.3): el modelo del misterio no conoce las fichas.
  - La fábrica (`fabrica.py:113-139`) pone `culpable: per-tomas-reyes` y `destapa: [per-tomas-reyes]` en la revelación de mayor `capitulo_previsto`. `estrategias.misterios` (`estrategias.py:74-121`) genera `culpable` y `destapa`.
- **Ficheros.**
  - `backend/novela/dominio/canon.py` (modificar)
  - `backend/novela/dominio/test_canon.py` (modificar)
  - `backend/tests/estrategias.py` (modificar)
  - `backend/tests/fixtures/fabrica.py` (modificar)
  - `backend/schemas/canon.schema.json` (regenerar)
  - `.claude/agents/arquitecto.md` (modificar: `culpable` por id, obligatorio, y `destapa` por revelación y giro)
  - `docs/definitions.md` §2.4, `docs/architecture.md` §7.5 (modificar)
- **Rojo.** `test_canon.py::test_culpable_obligatorio`: un misterio sin `culpable` no valida, y uno con `culpable: "no-es-un-id"` tampoco. `test_contratos.py::test_state_schema_al_dia` en rojo hasta regenerar. Falla hoy porque el campo no existe (`extra="forbid"` rechaza el que se añade).
- **Verde.** Campo, fábrica, estrategias y esquema.
- **Refactor.** —
- **Commit.** `feat(canon): el misterio nombra al culpable por id`
- **Cubre.** RF-01 (modelo).
- **Depende de.** 1.7
- **Hecho cuando.** El test pasa tras verse en rojo; `canon.schema.json` regenerado; `test_bucle.py`, `test_briefing.py` y el canario de contención (`backend/tests/canario/ejecutar.py:152`, que usa `fabrica.canon`) cargan el canon nuevo; suite en verde.
- **Complejidad.** S
- **Docs.** `definitions.md` §2.4; `architecture.md` §7.5 (salidas del `arquitecto`).

#### 2.2 `dominio/secreto.py`: filtrados, conjunto secreto, permitidos y bloques (soporte de RF-01 y RF-02, D-3)

- **Descripción.** Funciones puras y constantes con nombre (§8.4):
  - `TAM_BLOQUE = 5`, `MIN_LARGAS = 2` y `LARGA = 4`.
  - `filtrados(misterio, ids_personaje, n) -> frozenset[str]`: todo personaje salvo los nombrados en `destapa` de revelaciones y giros con `capitulo_previsto ≤ n`.
  - `conjunto_secreto(misterio, personajes: Mapping[str, Personaje], n) -> list[str]`: los tres grupos de §8.4. El tercero, de los filtrados: `secreto.que_oculta`, cada `detalle` de `coartada_y_cronologia_privada`, los textos de `arco_previsto` (`estado_inicial`, `estado_final` y cada `cambios[].descripcion`) e `identidad.rol_narrativo`.
  - `permitidos(misterio, ficha, n) -> set[str]`: lo que hoy calcula `assemble._permitidos` (`assemble.py:240-254`), con las pistas falsas de D-10. `assemble._permitidos` pasa a delegar en ella.
  - `permitidos_para_solape(misterio, ficha, n)`: `permitidos` más el contenido de las revelaciones y los giros con `capitulo_previsto ≤ n`.
  - `bloques(texto) -> frozenset[tuple[str, ...]]`: `TAM_BLOQUE` palabras seguidas de `texto.palabras` en minúsculas, con al menos `MIN_LARGAS` de `LARGA` letras o más.
  - `bloques_secretos(conjunto, permitidos) -> frozenset`: los bloques del conjunto secreto menos los que aparecen también en algún texto permitido.
  - `solapa(texto, bloques_secretos) -> bool`.

  Las usan el briefing (2.3, 2.4), `validar-plan` (3.3) y la sonda (4.4).
- **Ficheros.**
  - `backend/novela/dominio/secreto.py` (nuevo)
  - `backend/novela/dominio/test_secreto.py` (nuevo)
  - `backend/novela/slices/briefing/assemble.py` (modificar: `_permitidos` delega)
- **Rojo.** `test_secreto.py`:
  - `test_bloque_de_palabras_cortas_no_cuenta` (CA-02, parte): «el de la y un» no forma bloque.
  - `test_bloque_permitido_no_cuenta` (CA-02, parte): un bloque que está a la vez en `verdad_oculta` y en el contenido de una pista plantada en N no está en `bloques_secretos`.
  - `test_conjunto_secreto_segun_n`: property sobre `estrategias.misterios()` y n. `verdad_oculta` está si `n < max(capitulo_previsto)`, el contenido de una revelación con `capitulo_previsto ≤ n` no está, y el `rol_narrativo` y el `arco_previsto` de un personaje filtrado sí.
  - `test_filtrados_respeta_destapa`: property.
  - `test_permitidos_igual_que_antes`: sobre los casos de `test_briefing.py::test_pista_permitida_dentro_del_secreto_no_lo_tapa`, `permitidos` da lo mismo que el `_permitidos` actual.

  Fallan hoy por `ModuleNotFoundError`.
- **Verde.** El módulo y la delegación.
- **Refactor.** —
- **Commit.** `feat(dominio): conjunto secreto de un capítulo, lo permitido y bloques de cinco palabras`
- **Cubre.** Soporte de RF-01 y RF-02.
- **Depende de.** 1.1, 1.4, 2.1
- **Hecho cuando.** Los cinco tests pasan tras verse en rojo; `test_briefing.py` entero sigue en verde; `mypy --strict` en verde.
- **Complejidad.** M
- **Docs.** Ninguno (lo documentan 2.3 y 2.4).

#### 2.3 Filtro por campo de la ficha de personaje (RF-01, D-9)

- **Descripción.**
  - En `backend/novela/slices/briefing/assemble.py`: `FILTRADOS = frozenset({Agente.ESCRITOR, Agente.EDITOR_ESTILO})`.
  - La rama `recipes.Personajes` de `_capas` (`:182-189`) usa `_ficha_para(f, id_)`. Si el agente está en `FILTRADOS` y el personaje está en `secreto.filtrados(...)`, la ficha se re-renderiza sin `secreto`, `coartada_y_cronologia_privada`, `arco_previsto` ni `identidad.rol_narrativo` (D-9). Como `rol_narrativo` siempre está, toda ficha filtrada se re-renderiza.
  - Sin `f.misterio` (no debería pasar fuera del arquitecto, porque `briefing/cmd.py:62-69` exige el canon completo), se filtran todos.
- **Ficheros.**
  - `backend/novela/slices/briefing/assemble.py` (modificar)
  - `backend/novela/slices/briefing/test_briefing.py` (modificar)
  - `backend/tests/fuentes.py` (modificar: un `PERSONAJE_CON_SECRETO` con los cuatro campos)
  - `backend/tests/fixtures/golden/08-escritor.md` (regenerar)
  - `docs/architecture.md` §6.3, `docs/validators.md` §4.4, §4.9 y §6 (modificar)
- **Rojo.** `test_briefing.py::test_filtro_por_campo_property` (CA-01):
  - Sobre `estrategias.misterios()`, un conjunto de personajes generados con `secreto`, `coartada`, `arco_previsto` y `rol_narrativo` de texto único, `n` y un agente de `FILTRADOS`.
  - El cuerpo del briefing no contiene ninguno de esos cuatro textos de un personaje no destapado, y sí los contiene si alguna revelación con `capitulo_previsto ≤ n` lo nombra en `destapa`.
  - Para `continuista`, siempre los contiene.
  - Falla hoy porque la capa incrusta el texto crudo.
- **Verde.** El filtro. `REGENERAR=1 uv run pytest novela/slices/briefing/test_briefing.py::test_golden_escritor`: en `demo-24`, capítulo 8, ninguna revelación destapa a nadie antes, así que las tres fichas presentes se re-renderizan sin `rol_narrativo` ni coartada. `per-tomas-reyes` y `per-ines-mar` pierden además su secreto (`fabrica.py:69-86` y `:188-196`).
- **Refactor.** —
- **Commit.** `feat(briefing): las fichas de personaje llegan sin secreto, coartada, arco ni rol hasta que una revelación las destapa`
- **Cubre.** RF-01.
- **Depende de.** 2.2
- **Hecho cuando.** CA-01 pasa tras verse en rojo, también con el perfil `ci`; el diff del golden solo toca las tres fichas; `test_misterio_nunca_en_briefing` en verde.
- **Complejidad.** M
- **Docs.** `architecture.md` §6.3 («Aislamiento del secreto»: filtro de los cuatro campos); `validators.md` §4.4 (fila del filtro por campo: cuatro campos), §4.9 (la vía de la ficha del culpable de 0003 §13 queda cerrada) y §6, fila «Cada `briefing` de `escritor` o `editor-estilo`».

#### 2.4 Solape con lo no revelado (RF-02, D-9, D-10, D-20)

- **Descripción.** `_vigilar_el_solape(receta, f, secciones)` en `assemble.py`, llamada en `ensamblar` (`:344-368`) justo después de `_vigilar_el_secreto`, para los agentes de `FILTRADOS`:
  - Calcula `secreto.bloques_secretos` del conjunto secreto de N, con las fichas filtradas, menos los bloques que aparecen en `permitidos_para_solape` (§8.4). Después recorre las secciones.
  - Si alguna solapa, lanza `SolapeConElSecreto(FugaDelSecreto)` con el título de la capa y nunca el bloque.
  - `briefing/cmd.py:159-163` ya convierte `FugaDelSecreto` en 1 sin escribir el fichero.
  - **Medida de falsos positivos (§8.4).** Un test local sobre `humo-0003` pasa `bloques_secretos` sobre sus tres fichas de plan y sobre sus briefings del `escritor` y del `editor-estilo` (`runs/*/briefings/0N-escritor.md` y `0N-editor-estilo.md`), sin las secciones `personajes · …`, que ahora irían filtradas.
    - El misterio se lee por código con un `culpable` ficticio completado en memoria, porque el suyo no lo tiene y el campo no interviene en el conjunto secreto.
    - El test no imprime nunca un bloque: si falla, da la capa, el fichero y el número de bloques.
    - Si hay algún falso positivo, se suben `TAM_BLOQUE` o `MIN_LARGAS` en este mismo commit, y el valor queda anotado en `validators.md` §4.4.
- **Ficheros.**
  - `backend/novela/slices/briefing/assemble.py` (modificar)
  - `backend/novela/slices/briefing/test_briefing.py` (modificar)
  - `backend/tests/test_humo_0003.py` (modificar)
  - `backend/novela/dominio/secreto.py` (modificar solo si hay que subir las constantes)
  - `docs/architecture.md` §6.3, `docs/validators.md` §4.4 (modificar)
- **Rojo.**
  - `test_briefing.py::test_solape_property` (CA-02): sobre misterios generados, se toma un bloque de un texto del conjunto secreto de N que no esté en ningún texto permitido, y se inyecta, en minúsculas y con otra puntuación, en una capa del escritor o del editor. `ensamblar` lanza `SolapeConElSecreto`, y el mensaje nombra la capa y no contiene ninguna de las cinco palabras. Sin inyección, se ensambla.
  - `test_briefing.py::test_bloque_permitido_no_cuenta` (CA-02): un bloque de `verdad_oculta` que está también en el contenido de una revelación con `capitulo_previsto ≤ N`, en la ficha de ese capítulo, se ensambla.
  - `test_briefing.py::test_solape_por_cli_no_deja_fichero`: por CLI sobre `demo-24`, con un bloque de `verdad_oculta` escrito en `plan/capitulos/08.md`, sale con 1 y no existe `runs/<run>/briefings/08-escritor.md`.
  - `test_humo_0003.py::test_solape_sin_falsos_positivos` (local): cero bloques.

  Falla hoy porque el guardarraíl literal no ve un bloque de cinco palabras de una frase más larga con la puntuación cambiada.
- **Verde.** La función y la excepción.
- **Refactor.** El cálculo de los bloques secretos, una vez por `ensamblar` y no por sección.
- **Commit.** `feat(briefing): el briefing no sale si comparte cinco palabras con lo que aún no se ha revelado`
- **Cubre.** RF-02.
- **Depende de.** 2.3
- **Hecho cuando.** CA-02 pasa tras verse en rojo; `test_solape_sin_falsos_positivos` pasa en local, con las constantes que haga falta; el golden no cambia; `test_bucle.py` en verde.
- **Complejidad.** M
- **Docs.** `architecture.md` §6.3 (solape, permitidos y constantes); `validators.md` §4.4 (fila del solape: el conjunto de §8.4, la exención de lo permitido y los valores medidos).

#### 2.5 Briefing de reintento del escritor con QA saneado (RF-03, D-11)

- **Descripción.**
  - Capa nueva `Reintento(Modelo): reintento: Literal["qa_saneado"]` en `backend/novela/slices/briefing/recipes.py` (`Capa`, `:73-83`), y en la receta del escritor (`backend/config/recipes.yaml:23-34`), antes de `plan`.
  - Nuevo `backend/novela/slices/briefing/reintento.py` puro: `sanear(informes, ficha, misterio, hechos) -> str`, con las reglas de RF-03:
    - `validacion` y `gate-revision` enteros.
    - `continuidad` y `suspense`, solo `tipo`, `gravedad`, `referencia` y `ubicacion`.
    - Se descartan las referencias `rev-`, `pfa-`, el `culpable` y las `pis-` ajenas a la ficha (ni en `pistas_a_plantar` ni en `pistas_a_pagar`).
    - Una referencia `hec-` se completa con `texto` y `cita` del libro de hechos.
  - `assemble.Fuentes` gana `reintento: Reintento | None`, con los informes ya filtrados por mtime (D-11) y el libro de hechos (`estado_db.leer` ya lo carga entero, `backend/novela/plataforma/estado_db.py:127`).
  - `briefing/cmd.py::briefing` (`:131-176`), para el escritor: si existe `briefings/NN-escritor.md`, destino `NN-escritor-intento-K.md` y carga de la capa. Si la capa estima más de 3.000 tokens, lo avisa en la salida sin truncar (PA-12).
  - El procedimiento (`.claude/commands/novela-continuar.md`):
    - Pasos 3 y 6: el reintento del escritor vuelve a llamar a `novela briefing <slug> <cap> escritor` y le pasa la ruta que imprime, sin línea `reintento:`.
    - La plantilla del prompt (`:46-53`) deja `reintento:` solo para el `editor-estilo`.
- **Ficheros.**
  - `backend/novela/slices/briefing/recipes.py` (modificar)
  - `backend/config/recipes.yaml` (modificar)
  - `backend/novela/slices/briefing/reintento.py` (nuevo)
  - `backend/novela/slices/briefing/test_reintento.py` (nuevo)
  - `backend/novela/slices/briefing/assemble.py` (modificar)
  - `backend/novela/slices/briefing/cmd.py` (modificar)
  - `backend/novela/slices/briefing/test_recipes.py` (modificar)
  - `.claude/agents/escritor.md` (modificar: en reintento, solo su briefing de intento, sin `qa/`)
  - `.claude/commands/novela-continuar.md` (modificar)
  - `docs/architecture.md` §2.1, §4 y §6.2, `docs/validators.md` §4.4 y §4.6, `docs/definitions.md` §6, `CLAUDE.md` «Bucle por capítulo» (modificar)
- **Rojo.** `test_reintento.py`:
  - `test_capa_reintento_saneada_property` (CA-03): con `qa/` generados (hallazgos con `descripcion` y `correccion_sugerida` de texto único y referencias de todos los prefijos), la capa no contiene ninguna `descripcion` ni `correccion_sugerida` de continuidad o suspense, ni un hallazgo con referencia `rev-`, `pfa-`, el culpable o una `pis-` ajena. Contiene enteros los de `validar` y `gate`.
  - `test_briefing_original_intacto` (CA-03): por CLI sobre `demo-24`, capítulo 8, con `briefing`, un `qa/08-continuidad.json` rechazado y otro `briefing`, se escribe `08-escritor-intento-2.md` y el sha de `08-escritor.md` no cambia.
  - `test_hec_se_completa_desde_el_estado`.
  - `test_informe_anterior_al_ultimo_briefing_no_entra` (con `os.utime`).
  - `test_capa_estima_menos_de_3000` (RNF-02), sobre un fixture realista de 12 hallazgos.

  Fallan hoy porque el segundo `briefing` sobrescribe `08-escritor.md`.
- **Verde.** Capa, módulo, cáscara y procedimiento.
- **Refactor.** `_seccion` reutilizada para la capa; sin YAML, en líneas `- tipo · gravedad · referencia · ubicacion`.
- **Commit.** `feat(briefing): el reintento del escritor tiene su propio briefing con el QA saneado`
- **Cubre.** RF-03, RNF-02 (capa `reintento`).
- **Depende de.** 2.1, 2.4
- **Hecho cuando.**
  - CA-03 pasa tras verse en rojo.
  - `test_recipes.py::test_receta_valida` en verde con la capa nueva.
  - La custodia (`test_bucle.py::test_la_cli_rechaza_lo_que_la_maquina_prohibe`) sigue en verde.
  - El procedimiento ya no nombra `reintento: qa/` para el escritor, lo que se comprueba con `rg "reintento: qa" .claude/commands/novela-continuar.md`: solo queda la línea del `editor-estilo`.
- **Complejidad.** L
- **Docs.** `architecture.md` §2.1 («Reintentos»: el escritor recibe su briefing de intento), §4 (árbol de `runs/`) y §6.2 (capa `reintento`); `validators.md` §4.4 (fila del reintento) y §4.6 («Reflection»); `definitions.md` §6 (briefing de intento); `CLAUDE.md` «Bucle por capítulo» («Si falla, reintenta con el escritor pasándole únicamente el informe de QA» → «con su briefing de intento»).
