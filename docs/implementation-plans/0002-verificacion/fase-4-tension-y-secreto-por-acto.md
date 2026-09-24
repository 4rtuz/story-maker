# Fase 4: tensión y secreto a escala de acto

Plan: `README.md` · Spec: §5.4, RF-04, RF-15, RF-18, RF-30, §8.1 (`sonda`), §8.6, §8.7 · Decisiones: D-6, D-7, D-8, D-14, D-15, D-16, D-20, D-21, D-22, D-26, D-30, D-31 · Depende de: fases 2 (filtro y solape) y 3 (código 5, `intervencion.py`, parser del log)

Seis ciclos. El agente `sonda` entra en dos pasos: primero la capa de capítulos del acto (4.3), probada con recetas de test, y después el agente, el enum, la receta real, el hook y los contratos, en un solo commit (4.4). `recipes.validar` exige una receta por agente (`backend/novela/slices/briefing/recipes.py:99-107`). La capa `reparto` ya existe desde 1.7. El procedimiento cambia en 4.6, con las sondas y la auditoría de acto en las posiciones de D-26.

---

#### 4.1 Carga de preguntas abiertas en `checkpoint` (RF-15, D-21, D-22)

- **Descripción.**
  - Nuevo `backend/novela/slices/checkpoint/carga.py`, puro:
    - `carga(estado, misterio, k) -> int`, para cualquier k ≤ N, derivable del estado actual:
      - hilos con `abierto_en ≤ k` y (`cerrado_en` nulo o `> k`);
      - pistas con `plantada_en ≤ k` y (`pagada_en` nulo o `> k`);
      - revelaciones y giros con `capitulo_previsto > k`.
    - `avisos(serie: Mapping[int, int], n, escaleta) -> list[str]`. Hay dos avisos:
      - Carga 0 con `n < puntos_de_giro.climax`.
      - `carga(N) < carga(N−1) < carga(N−2) < carga(N−3)`, con N−2, N−1 y N en el acto de `numero == 2` (RF-15). N−3 puede ser del acto 1.
  - `checkpoint/cmd.py` (`:105-117`) añade `carga_preguntas` a los scores y escribe cada aviso con `abierto.registrar` (D-22).
- **Ficheros.**
  - `backend/novela/slices/checkpoint/carga.py` (nuevo)
  - `backend/novela/slices/checkpoint/test_carga.py` (nuevo)
  - `backend/novela/slices/checkpoint/cmd.py` (modificar)
  - `backend/novela/slices/checkpoint/test_checkpoint.py` (modificar: siete nombres en `test_checkpoint_emite_los_seis_scores`, que se renombra)
  - `backend/tests/fixtures/humo0003.py` (modificar si hace falta)
  - `backend/pyproject.toml` (modificar: `carga.py` en `mutmut`)
  - `docs/architecture.md` §10.5, `docs/validators.md` §4.13 (modificar)
- **Rojo.** `test_carga.py`:
  - `test_carga_humo_0003` (CA-15): con el estado y el calendario transcritos en `humo0003.py` (hilos, pistas y revelaciones de `novelas/humo-0003/plan/escaleta.md`), `carga` da 12, 9 y 0 en los capítulos 1, 2 y 3, y `avisos` no devuelve nada. El clímax es el 3 y el acto 2 solo tiene el capítulo 2.
  - `test_tres_bajadas_en_acto_2`: una serie sintética con tres bajadas estrictas y N−2, N−1 y N en el acto 2 da un aviso. Con dos bajadas no lo da, con una igualdad en medio tampoco, y con N−2 en el acto 1 tampoco.
  - `test_cero_antes_del_climax`.

  Mutación sobre `<` frente a `≤`, en el clímax y en las bajadas, y sobre el número de bajadas. Fallan hoy por `ModuleNotFoundError`.
- **Verde.** El módulo y la cáscara.
- **Refactor.** —
- **Commit.** `feat(checkpoint): carga de preguntas abiertas como score y aviso de colapso`
- **Cubre.** RF-15, RNF-05 (`carga_preguntas`).
- **Depende de.** 3.2
- **Hecho cuando.** CA-15 pasa tras verse en rojo, en CI, sin `novelas/`; `mutmut` sin supervivientes en `carga.py`; el test de scores recibe siete nombres, con el `urlopen` parcheado (D-21).
- **Complejidad.** M
- **Docs.** `architecture.md` §10.5 (`carga_preguntas`); `validators.md` §4.13 (la carga se calcula en cada checkpoint, con la regla exacta).

#### 4.2 `novela auditar --acto K` (RF-18, D-7)

- **Descripción.**
  - `backend/novela/slices/auditoria/comprobaciones.py` gana `auditar_acto(estado, misterio, fichas, frontmatters, huellas, escaleta, banda, k) -> tuple[list[Hallazgo], dict[int, int | None]]`, pura, con las siete filas de §8.6 y los huecos de `tension_real` sin interpolar.
  - `auditoria/cmd.py::auditar` (`:15-36`) acepta `--acto K`:
    - Sale con 2 si el último capítulo del acto no tiene checkpoint.
    - Lee los frontmatters de los capítulos cerrados, que el CLI sí puede leer, y la `huella` de cada `qa/NN-validacion.json`.
    - Escribe `qa/acto-K.json`.
    - Con algún hallazgo de gravedad alta, escribe `intervencion.md` en el run del último capítulo del acto (`run.existente`, D-7) y sale con 5. Registra `auditar acto-K -> <código>` en ese run, con `intervención (auditoria)` si sale con 5.
    - Imprime como mucho 3 líneas.
  - Sin `--acto`, no cambia.
- **Ficheros.**
  - `backend/novela/slices/auditoria/comprobaciones.py` y `cmd.py` (modificar)
  - `backend/novela/slices/auditoria/test_auditoria.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar: tipos de D-16)
  - `backend/schemas/qa-informe.schema.json` (regenerar)
  - `AGENTS.md` «CLI», `docs/architecture.md` §8, `docs/validators.md` §4.13 y §6 (modificar)
- **Rojo.** `test_auditoria.py`:
  - `test_acto_con_hueco` (CA-18): sobre `demo-24` con un `tension_real` nulo en el capítulo 3, fabricado con un `qa/03-suspense.json` sin `tension` antes de su `aplicar-delta`, `--acto 1` reporta `hueco_de_tension` para el 3 y el valor del capítulo 3 en el informe es `null`.
  - `test_acto_pista_vencida_interviene` (CA-18): una pista con `capitulo_pagado` ya pasado sin pagar → 5 e `intervencion.md` viva.
  - `test_acto_sin_cerrar_uso_incorrecto` → 2.
  - `test_salida_en_tres_lineas`.

  Fallan hoy porque la opción no existe.
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(auditar): la auditoría de acto reporta lo que ya no puede cambiar y para si es grave`
- **Cubre.** RF-18, RF-29 (`auditar --acto`), RNF-02.
- **Depende de.** 3.1, 3.2, 3.3 (`banda_tension`)
- **Hecho cuando.** CA-18 pasa tras verse en rojo; `test_novela_terminada_limpia` y el resto de `test_auditoria.py`, sin cambios y en verde.
- **Complejidad.** M
- **Docs.** `AGENTS.md` «CLI» (`novela auditar <slug> [--acto K]`); `architecture.md` §8; `validators.md` §4.13 y §6, fila «Frontera de acto».

#### 4.3 Capa de la receta de la sonda: capítulos del acto (soporte de RF-04 y RF-30, D-15)

- **Descripción.**
  - `recipes.py` gana la capa `Capitulos(Modelo): capitulos: Literal["acto_en_curso"]`. La capa `reparto` ya existe desde la tarea 1.7, donde la usa el `cronista`.
  - `assemble.Fuentes` gana `capitulos_del_acto: Mapping[int, str]` (cuerpos sin frontmatter).
  - `_capas` la emite como `capitulos · acto en curso · NN`, una sección por capítulo, en orden.
  - `briefing/cmd.py::cargar_fuentes` (`:34-108`) lee los capítulos del acto de N (de `plan/escaleta.md`) hasta N.
- **Ficheros.**
  - `backend/novela/slices/briefing/recipes.py` (modificar)
  - `backend/novela/slices/briefing/assemble.py` (modificar)
  - `backend/novela/slices/briefing/cmd.py` (modificar)
  - `backend/novela/slices/briefing/test_assemble.py` (modificar)
  - `backend/tests/fuentes.py` (modificar)
- **Rojo.** `test_assemble.py`:
  - `test_capitulos_del_acto_en_orden`: solo los del acto y hasta N.

  Falla hoy porque `Receta` rechaza las capas desconocidas (`test_recipes.py:9-24`).
- **Verde.** Capas y fuentes.
- **Refactor.** —
- **Commit.** `feat(briefing): capa de capítulos del acto`
- **Cubre.** Soporte de RF-04 y RF-30.
- **Depende de.** 2.5
- **Hecho cuando.** El test pasa tras verse en rojo; el golden no cambia.
- **Complejidad.** S
- **Docs.** Ninguno (lo documenta 4.4).

#### 4.4 Agente `sonda`: contrato, receta, hook y ocho roles (RF-30, RF-01, RF-02, D-9, D-15)

- **Descripción.**
  - `Agente.SONDA = "sonda"` en `backend/novela/dominio/ids.py:47-54`.
  - `.claude/agents/sonda.md` (`tools: Read, Write`, `model: sonnet`). Su contrato:
    - Lee solo su briefing, que es `NN-escritor.md` para la del briefing y `NN-sonda.md` para la del texto, y su esquema, `backend/schemas/sonda-voto.schema.json`.
    - Escribe `qa/NN-sonda-<tipo>-K.json`.
    - Devuelve una línea.
  - Receta `sonda` en `backend/config/recipes.yaml`, con dos capas y nada más: `presupuesto_tokens: 80000`, `capas: [capitulos: acto_en_curso, reparto: sin_rol]`, `excluir: [canon/misterio]`. Sin `canon/premisa` ni `canon/mundo`: `mundo` trae `quien_tiene_acceso`, que es material de trama (D-15).
  - `VotoSonda` (en `backend/novela/dominio/qa.py`) con los campos de §8.8, registrado en `backend/novela/dominio/esquemas.py:18-27` como `sonda-voto.schema.json`.
  - `assemble.FILTRADOS` gana `SONDA` (RF-01, RF-02). En el briefing de la sonda, `_vigilar_el_secreto` y `_vigilar_el_solape` se saltan las secciones de la capa `capitulos` (RF-02, D-9).
  - `novela briefing … sonda` sale con 2 (D-15).
  - Hook:
    - `SALIDAS["sonda"] = [rf"qa/{_NN}-sonda-(briefing|texto)-[1-3]\.json"]` en `.claude/hooks/denegar-escritura-estado.py:22-35`.
    - La regla 5 (`:88-96`) admite los ocho roles de `ROLES` más `canario`, sin cambiar el código.
  - `backend/config/default.yaml:13-20` gana `sonda: sonnet`.
- **Ficheros.**
  - `backend/novela/dominio/ids.py`, `qa.py` y `esquemas.py` (modificar)
  - `backend/schemas/sonda-voto.schema.json` (nuevo, generado)
  - `backend/config/recipes.yaml` y `backend/config/default.yaml` (modificar)
  - `backend/novela/slices/briefing/assemble.py` y `cmd.py` (modificar)
  - `backend/novela/slices/briefing/test_briefing.py` y `test_recipes.py` (modificar)
  - `.claude/agents/sonda.md` (nuevo)
  - `.claude/hooks/denegar-escritura-estado.py` (modificar)
  - `backend/tests/test_contratos.py` (modificar)
  - `backend/tests/test_hook.py` (modificar)
  - `backend/novela/plataforma/test_run.py` (modificar: `len(agentes) == 8`, `:132`)
  - `AGENTS.md` «Qué es este proyecto», `CLAUDE.md` «Subagentes» y «Hooks», `docs/architecture.md` §2.2, §6.2, §7.1, §7.4 y §7.5, `docs/validators.md` §3.8, §4.4 y §4.15, `docs/definitions.md` §7 (modificar)
- **Rojo.**
  - `test_contratos.py::test_agentes_de_claude` (CA-30): `CONTRATO` (`:165-189`) gana `"sonda": (["Read", "Write"], "sonnet", ["qa/NN-sonda-briefing-K.json", "qa/NN-sonda-texto-K.json"])`, y `ESQUEMAS` gana su esquema. Falla porque falta el fichero de agente.
  - `test_hook.py::test_salidas_casan_el_contrato` y `::test_salidas_por_rol`: `_instancia` (`:138-142`) y la sustitución de `:191` cambian `K` por un dígito de 1 a 3. Fallan porque el hook no tiene `sonda`.
  - `test_hook.py::test_subagentes` (`:241-255`), con dos filas nuevas: `(SESION, "Agent", "sonda", 0)` y `(SESION, "Agent", "juez", 2)`, un noveno nombre (CA-30).
  - `test_briefing.py::test_filtro_por_campo_property` y `::test_solape_property`, extendidos a `Agente.SONDA`, sobre la capa `reparto`.
  - `test_briefing.py::test_capitulos_de_la_sonda_no_se_miran` (CA-02): un capítulo del acto con un bloque del conjunto secreto y un fragmento literal de `verdad_oculta` se ensambla en el briefing de la sonda. La misma inyección en la capa `reparto` lanza `SolapeConElSecreto`.
  - `test_briefing.py::test_receta_de_la_sonda_sin_canon`: el briefing de la sonda no contiene `canon/premisa` ni `canon/mundo` ni ningún `quien_tiene_acceso`.
  - `test_briefing.py::test_briefing_de_sonda_es_uso_incorrecto` → 2.
- **Verde.** Todo lo descrito, con `REGENERAR=1 uv run pytest tests/test_contratos.py`.
- **Refactor.** —
- **Commit.** `feat(agentes): octavo rol, la sonda ciega del secreto`
- **Cubre.** RF-30, RF-01 y RF-02 (sonda).
- **Depende de.** 1.7, 4.3
- **Hecho cuando.** CA-30 y la parte de la sonda de CA-01 y CA-02 pasan tras verse en rojo; `test_recipes.py::test_receta_valida` en verde con ocho recetas; `sonda-voto.schema.json` commiteado (`test_state_schema_al_dia` exige el conjunto exacto de ficheros, `test_contratos.py:69-70`); `rg -n "siete" AGENTS.md CLAUDE.md docs/architecture.md docs/validators.md` no devuelve menciones al número de roles.
- **Complejidad.** L
- **Docs.** `AGENTS.md` (ocho roles, con `sonda`); `CLAUDE.md` «Subagentes» (sonnet también para `sonda`) y «Hooks» (de los ocho); `architecture.md` §2.2 (tabla), §6.2 (receta `sonda`), §7.1 (regla 5), §7.4 y §7.5; `validators.md` §3.8 (ocho ficheros), §4.4 (fila de la regla 5: ocho) y §4.15 («sin herramientas» pasa a `Read, Write`, con el briefing en disco); `definitions.md` §7.

#### 4.5 `novela sonda <slug> <cap> <briefing|texto>` (RF-04, D-6, D-7, D-15, D-30, D-31)

- **Descripción.**
  - `backend/novela/slices/briefing/sonda.py`, puro:
    - `R(misterio)`: el menor `capitulo_previsto` de las revelaciones y giros que nombran al `culpable` en `destapa`, o el mayor de todos si ninguno lo nombra.
    - `toca(tipo, n, escaleta, ficha, misterio) -> bool`, con la cadencia de §8.1.
    - `validos(votos, mtime_briefing) -> list[VotoSonda]`: descarta los que no validan y los que tienen un `st_mtime_ns` anterior al del briefing que juzgan.
    - `moda(votos) -> str | None`: el `culpable_id` con dos o más votos, o `None`.
    - `decidir(votos, culpable, tipo, n, r, autorizada: bool) -> Decision`:
      - Acierto: la moda es el `culpable` y la mediana de `confianza` de los votos que forman la moda es ≥ 0,5. Sin moda, no hay acierto.
      - Fuga (acierto en la del briefing, o en la del texto con N < R − 1) → 5, salvo que esté autorizada (D-30), y entonces 0.
      - En N = R − 1, no acertar da `pista_sin_efecto` con 0.
      - Con menos de tres votos válidos → 1.
    - `consumidos` como en el gate: los `sonda NN <tipo> -> 1` posteriores a la última `-> 5 · intervención (` de esa sonda. Con dos, el siguiente voto ausente o inválido → 5 con motivo `agotamiento`.
  - La orden `sonda` en `briefing/cmd.py`:
    - Rango (D-7): `briefing` con `cap = último checkpoint + 1`, sobre `run.abrir`; `texto` con `cap = último checkpoint`, sobre `run.existente` del run de su checkpoint. Fuera de rango, 2.
    - Fuera de la cadencia, 0 sin leer votos.
    - Para `texto`, si no hay votos válidos, escribe antes `NN-sonda.md` con la receta `sonda` en el run cerrado. Un aborto del ensamblado (solo `reparto` o presupuesto) → 5 (D-15).
    - Lee `qa/NN-sonda-<tipo>-{1,2,3}.json` y aplica `validos`.
    - Sin repetición (RNF-04): cada llamada registra `sonda NN <tipo> -> <código> · <causas>; entradas=<sha de los votos>`, y un voto ausente siempre cuenta. La sha sirve para la autorización: una línea previa `-> 5 · intervención (fuga)` con la misma sha, sin intervención viva, autoriza esos votos.
    - Escribe `qa/NN-sonda-<tipo>.json` (`agente: sonda`).
    - Con 5, `intervencion.md`.
    - La del texto emite `previsibilidad` por el `ScoreSink`, con el capítulo N y su `run_id` (D-31).
    - Imprime como mucho 3 líneas.
  - Registro en `cli.py`.
- **Ficheros.**
  - `backend/novela/slices/briefing/sonda.py` (nuevo)
  - `backend/novela/slices/briefing/test_sonda.py` (nuevo)
  - `backend/novela/slices/briefing/cmd.py` (modificar)
  - `backend/novela/cli.py` (modificar)
  - `backend/novela/slices/briefing/fixtures/votos/*.json` (nuevo: votos sin prosa)
  - `backend/novela/dominio/qa.py` (modificar: `sonda` en `Productor`)
  - `backend/schemas/qa-informe.schema.json` (regenerar)
  - `AGENTS.md` «CLI», `docs/architecture.md` §8 y §10.5, `docs/validators.md` §4.15 y §5.12, `docs/definitions.md` §6 (modificar)
- **Rojo.** `test_sonda.py` (CA-04), con votos fixture:
  - `test_decision_con_votos_fixture`: moda correcta y mediana 0,5 en la sonda del briefing → 5 e `intervencion.md`; mediana 0,4 → 0; tres votos distintos (sin moda) → 0.
  - `test_mediana_de_los_votos_de_la_moda`: dos votos al culpable con 0,4 y 0,6, y un tercero a otro con 0,1 → 5 (mediana de la moda 0,5, aunque la de los tres sea 0,4). Dos al culpable con 0,3 y 0,6, y un tercero a otro con 0,9 → 0 (mediana de la moda 0,45, aunque la de los tres sea 0,6).
  - `test_tercer_voto_ausente_interviene`: un voto ausente → 1, 1 y 5; la misma llamada repetida sin cambios también cuenta (RNF-04).
  - `test_voto_mas_antiguo_que_su_briefing_es_ausente`: con `os.utime`, tres votos válidos pero anteriores a `NN-escritor.md` → 1.
  - `test_texto_en_r_menos_1_sin_acierto`: → 0, con `pista_sin_efecto` en `qa/NN-sonda-texto.json`.
  - `test_fuera_de_cadencia_no_lee_votos`: → 0. Se comprueba con un voto ilegible presente que no provoca error.
  - `test_fuga_resuelta_mismos_votos`: 5, `resuelto:` y otra llamada con los mismos votos → 0. Con los votos reescritos → 5.
  - `test_texto_sobre_capitulo_cerrado`: `texto` con `cap = último checkpoint` escribe `NN-sonda.md` en el run del checkpoint; con `cap` abierto → 2.
  - `test_previsibilidad_desde_la_sonda` (RNF-05): con dos de tres votos que aciertan, emite `previsibilidad == 2/3` con el `urlopen` parcheado.

  Fallan hoy porque no existe la orden.
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(sonda): novela sonda compara tres votos ciegos con el culpable`
- **Cubre.** RF-04, RF-29 (`sonda`), RNF-02, RNF-04, RNF-05 (`previsibilidad`).
- **Depende de.** 4.4, 3.1, 3.2
- **Hecho cuando.** CA-04 pasa tras verse en rojo; ninguna ruta de la orden llama a un modelo (`test_sin_clientes_de_modelo` en verde).
- **Complejidad.** L
- **Docs.** `AGENTS.md` «CLI» (`novela sonda <slug> <cap> <briefing|texto>`); `architecture.md` §8 y §10.5 (`previsibilidad`, D-31); `validators.md` §4.15 (la sonda compara con `culpable`, no con `culpable_o_amenaza`; moda y mediana de la moda; votos más viejos que su briefing) y §5.12; `definitions.md` §6.

#### 4.6 Sondas y auditoría de acto en el bucle; el `lector-suspense` deja la previsibilidad (RF-04, RF-18, D-26)

- **Descripción.**
  - `.claude/commands/novela-continuar.md`:
    - Tras el primer `novela briefing … escritor` del capítulo, `novela sonda <slug> <cap> briefing`. Con 1, tres `Task sonda` en un turno con el briefing del escritor y `salidas: qa/NN-sonda-briefing-{1,2,3}.json`, y otra vez `novela sonda`. Con 5, para.
    - Tras `novela checkpoint`, `novela sonda <slug> <cap> texto`. Con 1, tres `Task sonda` con la ruta que imprime y otra vez `novela sonda`. Con 5, para.
    - Tras la sonda del texto del último capítulo de un acto, `novela auditar <slug> --acto K`. Con 5, para.
  - `.claude/agents/lector-suspense.md`: sin `previsibilidad` en `puntuaciones` ni en sus `tipo`.
  - `CLAUDE.md` «Bucle por capítulo», con las dos sondas y la auditoría de acto.
- **Ficheros.**
  - `.claude/commands/novela-continuar.md` (modificar)
  - `.claude/agents/lector-suspense.md` (modificar)
  - `backend/tests/test_contratos.py` (modificar)
  - `CLAUDE.md`, `docs/validators.md` §4.2 (modificar)
- **Rojo.**
  - `test_contratos.py::test_procedimientos_y_codigo_5`, ampliado: `/novela-continuar` nombra `novela sonda` con los dos tipos y `novela auditar` con `--acto`, y la sonda del texto y la auditoría van después de `novela checkpoint`.
  - `test_contratos.py::test_lector_sin_previsibilidad`: el cuerpo de `lector-suspense.md` no la nombra.

  Fallan hoy porque no hay pasos.
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(comandos): sondas ciegas y auditoría de acto en el bucle; la previsibilidad la da la sonda`
- **Cubre.** RF-04 y RF-18 (en el bucle).
- **Depende de.** 4.1, 4.2, 4.5
- **Hecho cuando.** Los dos tests pasan tras verse en rojo; `Puntuacion` (`qa.py:45`) conserva `previsibilidad`, porque los `qa/` de `humo-0003` la traen y deben seguir validando.
- **Complejidad.** M
- **Docs.** `CLAUDE.md` «Bucle por capítulo»; `validators.md` §4.2 (el `lector-suspense` ya no juzga la previsibilidad).
