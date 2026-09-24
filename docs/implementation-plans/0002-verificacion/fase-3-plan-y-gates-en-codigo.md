# Fase 3: el plan y los gates en código

Plan: `README.md` · Spec: §5.3, RF-14, RF-16, RF-17, RF-19, RF-29, §8.1, §8.2, RNF-04 · ADR 0002 · Decisiones: D-5, D-6, D-7, D-8, D-14, D-16, D-17, D-18, D-23, D-24, D-27, D-28, D-29, D-30 · Depende de: fases 1 y 2

Nueve ciclos. De 3.1 a 3.7 se construyen y prueban `validar-plan` y los cinco gates (`plan`, `mecanico`, `final`, `revision`, `delta`) sin que el procedimiento los llame: el bucle sigue como en la fase 2. En 3.8 cambian los dos procedimientos a la vez, en un solo commit. 3.9 lleva el model checking al gate real.

---

#### 3.1 Código 5 e `intervencion.md` escrita por el CLI (RF-29, D-14)

- **Descripción.**
  - `INTERVENCION = 5` en `backend/novela/plataforma/salida.py:18`, y en su docstring la fila «5 intervención escrita por el CLI».
  - Nuevo `backend/novela/plataforma/intervencion.py`:
    - `Bloque` (dataclass con `capitulo`, `gate`, `motivo`, `intentos`, `briefing`, `qa` y `causa`), con el formato de la plantilla que hoy está en prosa (`.claude/commands/novela-continuar.md:108-115`) más la línea `motivo:` (D-6).
    - `renderizar(bloque) -> str`, que es puro.
    - `escribir(ws, run, bloque)`: añade el bloque y reescribe con `ws.escribir`, de forma atómica.
    - `viva(texto) -> bool`, pura: después del último `# Intervención` no hay ninguna línea que empiece por `resuelto:`.
    - `vivas(ws) -> list[Path]`.
- **Ficheros.**
  - `backend/novela/plataforma/salida.py` (modificar)
  - `backend/novela/plataforma/intervencion.py` (nuevo)
  - `backend/novela/plataforma/test_intervencion.py` (nuevo)
  - `docs/architecture.md` §8 («Parada»), `docs/validators.md` §4.5, `docs/definitions.md` §6 (modificar)
- **Rojo.** `test_intervencion.py`:
  - `test_viva_y_resuelta`: un bloque sin `resuelto:` está vivo, y con `resuelto: x` no. Los dos ficheros de un bloque con la forma de los de `humo-0003` se leen como resueltos.
  - `test_segundo_bloque_tras_uno_resuelto_esta_vivo`.
  - `test_escritura_atomica_conserva_el_anterior`.

  Fallan hoy por `ModuleNotFoundError`.
- **Verde.** El módulo y la constante.
- **Refactor.** —
- **Commit.** `feat(plataforma): código 5 e intervencion.md con bloques, escrita por el CLI`
- **Cubre.** RF-29 (código y fichero).
- **Depende de.** —
- **Hecho cuando.** Los tres tests pasan tras verse en rojo; `salida.py` documenta el 5.
- **Complejidad.** S
- **Docs.** `architecture.md` §8 («Parada»: la escribe el CLI con formato fijo); `validators.md` §4.5 (el primer punto de parada lo escribe el CLI); `definitions.md` §6.

#### 3.2 Lectura de `harness.log`, `entradas=` y `run.existente` (soporte de RF-19 y RNF-04, D-6, D-7)

- **Descripción.** En `backend/novela/plataforma/run.py`:
  - `LineaLog` (dataclass con `marca`, `sesion`, `orden: tuple[str, ...]`, `codigo: str`, `causas: tuple[str, ...]` y `entradas: str | None`), con dos propiedades: `intervencion: str | None`, el motivo de una causa `intervención (<motivo>)`, y `intervencion_viva: bool`.
  - `parsear(linea) -> LineaLog | None`, pura. `Run.lineas() -> list[LineaLog]`.
  - `registro(*orden, entradas=None)`, que añade `entradas=<sha>` como **último** elemento del detalle (`:130-135`), tras las causas (D-6). Así, `-> 5 · intervención (…)` y `-> 5 · intervención viva` siguen siendo las subcadenas de §8.1.
  - `existente(ws, run_id) -> Run | None`, que no crea manifiesto.
  - Las líneas que ya escribe el CLI no cambian si `entradas` es `None`.
- **Ficheros.**
  - `backend/novela/plataforma/run.py` (modificar)
  - `backend/novela/plataforma/test_run.py` (modificar)
- **Rojo.** `test_run.py`:
  - `test_parsear_ida_y_vuelta_property`: `parsear` de lo que escribe `registro` devuelve orden, código, sesión, causas y entradas, con y sin cada uno.
  - `test_intervencion_y_viva_se_distinguen`: `-> 5 · intervención (agotamiento); entradas=…` da el motivo `agotamiento`, y `-> 5 · intervención viva` da `intervencion_viva` sin motivo.
  - `test_lineas_sin_entradas_no_cambian`: la línea de `validar 08` es la misma que antes.
  - `test_existente_no_crea`.

  Fallan hoy porque no existen `parsear`, `lineas`, `existente` ni el parámetro.
- **Verde.** Lo descrito.
- **Refactor.** La construcción de la línea en `registro` y su lectura en `parsear` comparten las constantes del separador.
- **Commit.** `feat(run): harness.log se lee como datos y la línea puede llevar la sha de sus entradas`
- **Cubre.** Soporte de RF-19 y RNF-04.
- **Depende de.** —
- **Hecho cuando.** Los tests pasan tras verse en rojo; `test_validacion.py::test_sesion_en_el_log` y el resto de la suite, sin cambios y en verde.
- **Complejidad.** S
- **Docs.** Ninguno.

#### 3.3 `novela validar-plan` (RF-14, D-7, D-24)

- **Descripción.**
  - Slice nuevo `backend/novela/slices/validacion_plan/`.
    - `comprobaciones.py`, puro: `validar_plan(escaleta, fichas, misterio, personajes, escenarios, config) -> list[Hallazgo]`, con las seis comprobaciones de §8.2. La 5 usa `dominio.secreto` con la exención de lo permitido en N (2.2).
    - `cmd.py`: `validar_plan(slug)` exige que no haya checkpoint (si lo hay, sale con 2) y abre `run.abrir(ws, 1, "arranque")`. Lee canon, plan y config, escribe `qa/plan-validacion.json` (`agente: validar-plan`, `capitulo: 1`) y sale con 0 o 1. Imprime como mucho 3 líneas.
  - `ParametrosSistema` (`backend/novela/dominio/config.py:74-81`) gana `banda_tension: int = Field(default=2, ge=0)` y `max_capitulos_sin_subir: int = Field(default=3, ge=1)`, compatibles.
  - `Productor` y `TipoHallazgo` de `qa.py` ganan `validar-plan` y los tipos de D-16.
  - Registro en `backend/novela/cli.py:32-41` como `validar-plan`.
- **Ficheros.**
  - `backend/novela/slices/validacion_plan/__init__.py`, `comprobaciones.py`, `cmd.py`, `test_comprobaciones.py` y `test_validacion_plan.py` (nuevos)
  - `backend/novela/dominio/config.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar)
  - `backend/novela/cli.py` (modificar)
  - `backend/schemas/config.schema.json` y `qa-informe.schema.json` (regenerar)
  - `backend/tests/fixtures/humo0003.py` (nuevo: el calendario de su escaleta, D-20)
  - `backend/tests/test_humo_0003.py` (modificar)
  - `backend/pyproject.toml` (modificar: `comprobaciones.py` del plan en `mutmut`)
  - `AGENTS.md` «CLI», `docs/architecture.md` §8, `docs/validators.md` §3.9.1 y §6, `docs/definitions.md` §1 y §8 (modificar)
- **Rojo.**
  - `test_comprobaciones.py::test_cada_comprobacion_rompe_property` (CA-14): parametrizado por las seis comprobaciones. Sobre un plan válido de la fábrica (`fabrica.plan` y `fabrica.canon` de `DEMO`), una mutación generada que rompe exactamente esa comprobación hace aparecer su tipo de hallazgo y ninguno de las otras cinco.
  - `test_comprobaciones.py::test_curva_casos_de_borde`: el punto medio igual al anterior, el siguiente es el clímax, `max_capitulos_sin_subir` exacto y uno más.
  - `test_humo_0003.py::test_plan_valida`: el plan de `humo-0003` en local, con `pistas_falsas_a_desmontar` completado en memoria desde su escaleta (pfa-002 en el 2 y pfa-001 en el 3) y con un misterio sintético de `humo0003.py`, sale sin hallazgos (CA-14).
  - `test_validacion_plan.py::test_codigos_y_salida`: 0 sin hallazgos, 1 con ellos, 2 con checkpoint, como mucho 3 líneas (RNF-02) y 24 fichas en menos de 5 s (RNF-01).

  Fallan hoy porque no existe el subcomando.
- **Verde.** El slice, los campos de config y el registro.
- **Refactor.** —
- **Commit.** `feat(validar-plan): el plan se verifica una vez, antes del capítulo 1`
- **Cubre.** RF-14, RNF-01 (`validar-plan`), RNF-02.
- **Depende de.** 2.2, 3.2
- **Hecho cuando.**
  - CA-14 pasa tras verse en rojo, y la mitad de humo en local.
  - `uv run mutmut run` sin supervivientes en las comparaciones de la curva.
  - Esquemas regenerados.
  - Si existe `frontend/src/shared/api/esquema.gen.ts` y la API sirve `Config` (spec 0004), se regeneran `openapi.json` y los tipos.
- **Complejidad.** L
- **Docs.** `AGENTS.md` «CLI» (`novela validar-plan <slug>`); `architecture.md` §8; `validators.md` §3.9.1 (estado real) y §6, fila «Tras el `trazador`»; `definitions.md` §1 (dos parámetros) y §8.

#### 3.4 `novela gate`: núcleo, y los gates `plan`, `mecanico`, `final` y `delta` (RF-19, D-5, D-6, D-7, D-23, D-29)

- **Descripción.**
  - Slice nuevo `backend/novela/slices/gate/`.
  - `decision.py`, puro:
    - `consumidos(lineas, nn, tipo) -> int`: cuenta las líneas `gate NN <tipo> -> 1` posteriores a la última `gate NN <tipo> -> 5 · intervención (…)`. La `intervención viva` no reinicia (§8.1). Una intervención resuelta concede así otros tres intentos. Cada gate cuenta aparte (D-29).
    - `repetido(lineas, nn, tipo, sha) -> int | None`: la decisión de la **última** línea del log, si es `gate NN <tipo>`, lleva esa sha y su código es 0 o 1. Cualquier otra línea al final da `None` (RNF-04).
    - `autorizadas(lineas, nn, tipo) -> frozenset[str]`: los motivos de las `intervención (…)` previas de ese gate que no son `agotamiento` ni `custodia` (D-30).
    - `evaluar_plan(informe)`, `evaluar_mecanico(informe)`, `evaluar_final(informe)` (con `final: false`, ilegible, D-5) y `evaluar_delta(cursor, ultima_aplicar_delta)`, que devuelven motivos, vacío si aprueba.
    - `decidir(motivos, consumidos, custodia) -> Decision`: 0 sin motivos; 5 con motivo `custodia` si la causa es `custodia:`; 5 con motivo `agotamiento` si hay dos consumidos; 1 en otro caso.
  - `cmd.py::gate(slug, capitulo, tipo)`, con `tipo: TipoGate` (`plan`, `mecanico`, `final`, `revision` y `delta`). `revision` sale provisionalmente con 2 hasta 3.5. En este orden (D-6):
    1. Rango (D-7): `plan` solo con `cap = 1` y sin checkpoint, en el run de arranque; los demás, solo con `cap = último checkpoint + 1`. Fuera de rango, 2 sin abrir run.
    2. Intervención viva en el run: 5 y la línea `gate NN <tipo> -> 5 · intervención viva`, sin evaluar.
    3. Sha de las entradas y `repetido`: repite el código sin escribir línea.
    4. Evalúa y decide, y registra `registro("gate", nn, tipo, entradas=sha)`, con `intervención (<motivo>)` como causa si sale con 5.
    5. Con 5, `intervencion.escribir`, con el motivo.

    Imprime como mucho 3 líneas.
  - Registro en `cli.py`.
- **Ficheros.**
  - `backend/novela/slices/gate/__init__.py`, `decision.py`, `cmd.py`, `test_decision.py` y `test_gate.py` (nuevos)
  - `backend/novela/cli.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar: `gate` en `Productor`)
  - `backend/schemas/qa-informe.schema.json` (regenerar)
  - `backend/tests/fixtures/fabrica.py` (modificar: `informe_validacion(n, rechazado, final)`, `delta_invalido`)
  - `backend/pyproject.toml` (modificar: `decision.py` en `mutmut`)
  - `AGENTS.md` «CLI», `docs/architecture.md` §2.1, `docs/validators.md` §4.4 y §4.10, `docs/definitions.md` §8 (modificar)
- **Rojo.** `test_gate.py`, con el agente falso sobre `demo-24`, capítulo 8 (CA-19):
  - `test_ciclo_de_cada_gate`, parametrizado por `plan`, `mecanico`, `final` y `delta`: aprobado → 0; rechazado → 1, 1 y 5 a la tercera, con `intervencion.md` viva en el run.
  - `test_repeticion_sin_orden_en_medio`: dos llamadas seguidas con las mismas entradas dan el mismo código y dejan una sola línea `gate 08 mecanico -> 1`.
  - `test_orden_en_medio_cuenta_otro_intento`: rechazo, un `novela briefing … escritor` en medio sin que nadie reescriba el capítulo, y otra llamada con las mismas entradas: dos líneas `-> 1`, la segunda con la misma sha.
  - `test_intervencion_viva_no_reinicia`: con la viva, → 5 y una línea `-> 5 · intervención viva`. Tras resolverla, la cuenta sigue desde la última `intervención (agotamiento)`, no desde la viva.
  - `test_resuelta_concede_tres`: tras el 5, con `resuelto:` en `intervencion.md`, un rechazo → 1, otro → 1 y el tercero → 5.
  - `test_validacion_de_otro_capitulo_es_ilegible` (F-163): con el capítulo reescrito y sin `validar` después, el `capitulo_sha256` de `qa/NN-validacion.json` no casa con el disco → `mecanico` y `final` rechazan.
  - `test_mecanico_no_consume_final`: dos rechazos de `mecanico` y después un rechazo de `final` → 1, no 5 (D-29).
  - `test_final_exige_final_true`: un `qa/08-validacion.json` aprobado con `final: false` → 1 en el gate `final`.
  - `test_custodia_interviene_al_primero`: un `aplicar-delta` rechazado por custodia (capítulo reescrito tras el `cronista`, como en `test_bucle.py:141-147`) → `gate … delta` 5 al primer fallo. Resuelta, otro fallo de custodia vuelve a dar 5 (D-30).
  - `test_rango`: `gate demo-24 7 mecanico` (cerrado) y `gate demo-24 9 mecanico` (por delante) → 2 sin crear run.
  - `test_delta_sin_aplicar_delta`: → 2 (D-23).
  - `test_salida_en_tres_lineas` (RNF-02).
  - `test_decision.py::test_decidir_property` y `::test_consumidos_property`: tabla de verdad de `decidir`, y `consumidos` sobre secuencias de líneas generadas, con mutación.

  Fallan hoy porque no existe el subcomando.
- **Verde.** El slice y la fábrica.
- **Refactor.** La construcción de las entradas de la sha, una función por tipo en `cmd.py`.
- **Commit.** `feat(gate): novela gate decide y cuenta los intentos de los gates de plan, mecánico, final y delta`
- **Cubre.** RF-19, RF-29, RNF-02, RNF-04.
- **Depende de.** 1.9, 3.1, 3.2, 3.3
- **Hecho cuando.** Los tests de CA-19 para los cuatro tipos pasan tras verse en rojo; `mutmut` sin supervivientes en `decision.py`; el `harness.log` de los tests solo tiene líneas `gate` con `entradas=` al final del detalle, salvo las de `intervención viva`.
- **Complejidad.** L
- **Docs.** `AGENTS.md` «CLI» (`novela gate <slug> <cap> <plan|mecanico|final|revision|delta>`); `architecture.md` §2.1 (tabla «Gates»: «Quién lo evalúa» pasa a ser `novela gate`, con los cinco; «Quién orquesta» deja de atribuir el juicio a la sesión); `validators.md` §4.4 (fila de `novela gate`: cuenta en `harness.log` y no toca `cursor.intento`) y §4.10; `definitions.md` §8.

#### 3.5 Gate `revision`: veredictos e ilegibilidad (RF-19, D-17)

- **Descripción.**
  - `decision.evaluar_revision(continuidad: Leido, suspense: Leido) -> list[Hallazgo]`, donde `Leido` es `InformeQA` o `Ilegible(motivo)`.
  - La cáscara marca ilegible un informe que no existe, que no valida contra `InformeQA` o cuyo `st_mtime_ns` es anterior al de `runs/<run>/briefings/NN-<agente>.md`. Un `qa/NN-suspense.json` sin `puntuaciones.tension` también es ilegible (§8.1). La falta de `gancho` se añade en 3.7, cuando existe el campo.
  - `rechazado` o ilegible → motivo; `aprobado_con_reservas` aprueba.
  - Escribe `qa/NN-gate-revision.json` (`agente: gate`) con sus hallazgos (`informe_ilegible`).
- **Ficheros.**
  - `backend/novela/slices/gate/decision.py` y `cmd.py` (modificar)
  - `backend/novela/slices/gate/test_gate.py` y `test_decision.py` (modificar)
  - `backend/novela/dominio/qa.py` (modificar)
  - `backend/schemas/qa-informe.schema.json` (regenerar)
  - `docs/validators.md` §4.17 F-06, `docs/definitions.md` §6 (modificar)
- **Rojo.**
  - `test_gate.py::test_informe_mas_antiguo_que_su_briefing` (CA-19): con `os.utime`, un `qa/08-continuidad.json` aprobado y anterior a `08-continuista.md` → 1, con `informe_ilegible` en `qa/08-gate-revision.json`.
  - `test_suspense_sin_tension_es_ilegible` → 1.
  - `test_ciclo_de_cada_gate`, ampliado a `revision`.
  - `test_json_invalido_es_ilegible`.
  - `test_reservas_aprueba`.

  Falla hoy porque `revision` sale con 2 (3.4).
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(gate): el gate de revisión rechaza un informe ilegible o más viejo que su briefing`
- **Cubre.** RF-19.
- **Depende de.** 3.4
- **Hecho cuando.** Los tests pasan tras verse en rojo; F-06 de `validators.md` pasa a «activo: `novela gate`».
- **Complejidad.** M
- **Docs.** `validators.md` §4.17, F-06; `definitions.md` §6 (`NN-gate-revision.json`).

#### 3.6 Banda y tendencia de tensión (RF-16, D-17, D-30)

- **Descripción.**
  - `decision.banda(tension_n, objetivo_n, banda) -> Hallazgo | None`, con `tension_fuera_de_banda` si `|t − o| > banda`.
  - `decision.tendencia(desviaciones: Sequence[int | None]) -> bool`: verdadera si las tres últimas tienen valor y son negativas. Un hueco la anula.
  - La cáscara:
    - Toma la tensión de N de `qa/NN-suspense.json` (D-17).
    - Toma N−1 y N−2 de `estado.tension_real`.
    - Toma los objetivos de `plan/escaleta.md`, validada con `context={"num_capitulos": …}` (`backend/novela/dominio/plan.py:37-58`).
    - Toma `banda_tension` de la config.
  - La tendencia sale con 5 y motivo `tendencia_negativa`, sin mirar los intentos, con `tendencia_negativa` en el informe y en la intervención. Si el motivo ya está en `autorizadas` (una intervención previa por tendencia, resuelta), no vuelve a intervenir por él y el gate sigue con la banda y el gancho (§8.1, D-30). La banda es un motivo más, que se cuenta.
- **Ficheros.**
  - `backend/novela/slices/gate/decision.py` y `cmd.py` (modificar)
  - `backend/novela/slices/gate/test_decision.py` y `test_gate.py` (modificar)
  - `docs/validators.md` §4.13 (modificar)
- **Rojo.**
  - `test_decision.py::test_banda_y_tendencia_property` (CA-16), con `banda_tension = 2`:
    - Una desviación de 3 da 1.
    - Una de −2, con las dos anteriores negativas, da 5.
    - Con un `None` entre ellas, no hay tendencia.
    - Una property sobre desviaciones generadas contrasta `banda` con `abs(d) > banda`.
  - `test_gate.py::test_tendencia_resuelta_no_vuelve_a_intervenir` (CA-19): 5 por tendencia, `resuelto:` y otra llamada con la misma tendencia → 0 si la banda y el gancho están bien, y 1 si la desviación supera la banda.

  Mutación sobre `>` frente a `>=` y sobre el número de capítulos de la tendencia. Falla hoy porque las funciones no existen.
- **Verde.** Lo descrito.
- **Refactor.** —
- **Commit.** `feat(gate): la tensión fuera de banda se reintenta y la caída sostenida va a intervención`
- **Cubre.** RF-16, RF-19 (autorización).
- **Depende de.** 3.5
- **Hecho cuando.** CA-16 y el caso de autorización de CA-19 pasan tras verse en rojo; `mutmut` mata los mutantes de la banda; la fábrica, cuya tensión es igual a la curva (`fabrica.py:228` y `:326`), sigue aprobando.
- **Complejidad.** M
- **Docs.** `validators.md` §4.13 («El gate de tensión necesita una banda…» pasa a describir lo que hay, con la autorización tras resolver).

#### 3.7 Gancho con cita (RF-17, D-18, D-19)

- **Descripción.**
  - `GanchoFinal` baja a `backend/novela/dominio/base.py`, y `plan.py:16-18` la reexporta.
  - `InformeQA` gana `gancho: Gancho | None = None`, con `Gancho(Modelo): tipo: GanchoFinal; cita: str`.
  - `decision.ultima_escena(texto_briefing, nn, separador) -> str` y `decision.evaluar_gancho(gancho, escena, esperado) -> Leido | Hallazgo | None`. Sin `gancho` (§8.1) o con una cita que no es subcadena normalizada, el informe es ilegible. Con otro tipo, `gancho_fuera_de_plan`.
  - La cáscara lee `NN-lector-suspense.md` del run y `canon/estilo.md` `convenciones_formato.separador_escena`, con `* * *` por defecto.
  - La fábrica escribe `gancho: {tipo: GANCHOS[n % 5], cita: frase_de_escena(n, 2)}` (`fabrica.py:24` y `:276-277`).
- **Ficheros.**
  - `backend/novela/dominio/base.py`, `plan.py` y `qa.py` (modificar)
  - `backend/novela/slices/gate/decision.py` y `cmd.py` (modificar)
  - `backend/novela/slices/gate/test_decision.py` y `test_gate.py` (modificar)
  - `backend/novela/slices/briefing/test_recipes.py` (modificar: `objetivo` es la última capa del `lector-suspense`)
  - `backend/tests/fixtures/fabrica.py` (modificar `informes`)
  - `backend/schemas/qa-informe.schema.json` (regenerar)
  - `.claude/agents/lector-suspense.md` (modificar: devuelve `gancho: {tipo, cita}`, con la cita copiada de la última escena, y `puntuaciones.tension` siempre)
  - `docs/architecture.md` §7.3, `docs/validators.md` §3.9.10 y §6 (modificar)
- **Rojo.**
  - `test_decision.py::test_gancho` (CA-17):
    - Con la cita en la última escena y el tipo de la ficha, aprueba.
    - Con una cita de otra escena, ilegible.
    - Sin `gancho`, ilegible.
    - Con otro tipo, `gancho_fuera_de_plan`.
    - Con `***` y con `* * *` como separador.
    - Sin separador, el capítulo entero es la última escena.
  - `test_gate.py::test_gancho_fuera_de_plan_en_el_informe`: por CLI → 1, con el hallazgo en `qa/08-gate-revision.json`.

  Fallan hoy porque `InformeQA` rechaza `gancho` (`extra="forbid"`).
- **Verde.** Modelos, funciones y fábrica.
- **Refactor.** —
- **Commit.** `feat(gate): el lector-suspense cita el gancho y el gate lo contrasta con la ficha`
- **Cubre.** RF-17.
- **Depende de.** 3.5
- **Hecho cuando.** CA-17 pasa tras verse en rojo; `qa-informe.schema.json` regenerado; `test_bucle.py` en verde con el gancho de la fábrica.
- **Complejidad.** M
- **Docs.** `architecture.md` §7.3 (`gancho`); `validators.md` §3.9.10 y §6, fila `validar` (el gancho sale de esa fila: lo comprueba el gate).

#### 3.8 Los procedimientos obedecen al gate (RF-19, RF-29, RF-14, D-27, D-28, D-29)

- **Descripción.** Cambio de procedimiento, sin TDD en el texto y con un test de contrato. Va en un solo commit.
  - `.claude/commands/novela-continuar.md`:
    - La tabla de códigos (`:15-23`) gana el 5, «para sin escribir nada: la intervención ya la escribió el CLI». El 4 y el 1 de `briefing` y de `checkpoint` siguen escribiendo `intervencion.md` con `gate: workspace`, porque ningún subcomando la escribe por ellos (D-28).
    - Regla de lectura 1: se aplica al gate. Un 1 de `novela gate` solo es un rechazo si la última línea del log contiene `gate NN <tipo> -> 1`. Si no, el CLI está roto.
    - Paso 3: tras `validar` (0 o 1), `novela gate <slug> <cap> mecanico`. Con 1, reintento del `escritor` con su briefing de intento (2.5).
    - Paso 5: tras `validar --final` (0 o 1), `novela gate <slug> <cap> final`. Con 1, reintento del `editor-estilo` con su mismo briefing y `reintento: qa/NN-validacion.json`.
    - Paso 6: `gate … revision`. Con 1, reintento del `escritor`.
    - Paso 7: tras `aplicar-delta` (0 o 1), `gate … delta`. Con 1, reintento del `cronista` con su `causa:`.
    - En cada caso, 0 avanza y 5 para. Cada gate cuenta aparte (D-29).
    - Se borran «Cuenta de intentos» (`:94-119`) y la plantilla de `intervencion.md` de los gates.
    - La tabla de reanudación (`:121-131`) pasa a leer líneas `gate`:
      - `gate NN delta -> 0` → paso 8.
      - `gate NN revision -> 0` → paso 7.
      - `gate NN revision -> 1` → paso 2, reintento. Cierra F-31: no se vuelve a revisar un capítulo rechazado.
      - `gate NN final -> 0` → paso 6.
      - `gate NN final -> 1` → paso 5, reintento del `editor-estilo`.
      - La última `gate NN mecanico` en 0, sin `briefing NN continuista` después → paso 4.
      - `gate NN mecanico -> 1` → paso 2, reintento.
  - `.claude/commands/novela-nueva.md`: tras el `Task` del `trazador`, `novela validar-plan <slug>` y después `novela gate <slug> 1 plan`. Con 1, `trazador` con su mismo briefing y `reintento: qa/plan-validacion.json` (D-27). El gate del `arquitecto` conserva su cuenta en prosa y su `intervencion.md` (D-28): no es un gate de `novela gate`.
  - `.claude/agents/trazador.md`: la cláusula de reintento.
  - `CLAUDE.md` «Bucle por capítulo»: las líneas `novela gate`, con `final` tras el segundo `validar`. «Máximo dos reintentos por gate. Al tercero, escribe `runs/<run_id>/intervencion.md` y para» pasa a «el gate cuenta los intentos y sale con 5; para sin escribir nada».
- **Ficheros.**
  - `.claude/commands/novela-continuar.md`, `.claude/commands/novela-nueva.md` y `.claude/agents/trazador.md` (modificar)
  - `backend/tests/test_contratos.py` (modificar)
  - `CLAUDE.md`, `docs/architecture.md` §2.1 y §8, `docs/validators.md` §4.17 F-31 y F-35 (modificar)
- **Rojo.** `test_contratos.py::test_procedimientos_y_codigo_5` (CA-29):
  - Los dos procedimientos contienen una fila `| 5 |` en su tabla de códigos.
  - `/novela-continuar` nombra `novela gate` con los cuatro tipos del bucle (`mecanico`, `final`, `revision`, `delta`), y `/novela-nueva` con `plan` y `validar-plan`.
  - En `/novela-continuar`, la única instrucción de escribir `intervencion.md` es la de la fila del 4 (y del 1 de `briefing` y `checkpoint`), con `gate: workspace`. No hay ninguna en los pasos 3, 5, 6 y 7, que decide `novela gate`. En `/novela-nueva`, las del gate del `arquitecto` y la del 4 se conservan.
  - La tabla de reanudación nombra `gate NN mecanico -> 0` y `gate NN final -> 0` en filas distintas.

  Falla hoy porque la tabla no tiene el 5 y `novela-continuar.md:105-106` manda escribir `intervencion.md` al agotar cualquier gate.
- **Verde.** Los textos.
- **Refactor.** —
- **Commit.** `feat(comandos): el orquestador obedece a novela gate y deja de contar intentos`
- **Cubre.** RF-19, RF-29, RF-14 (uso en `/novela-nueva`), RF-17 (el procedimiento ya no juzga veredictos).
- **Depende de.** 3.3, 3.4, 3.5, 3.6, 3.7
- **Hecho cuando.** CA-29 pasa tras verse en rojo; `test_hook.py::test_sesion_principal` sigue en verde, porque la regla 3 no cambia (D-28); una lectura del diff confirma que ningún paso depende ya de contar líneas en prosa, salvo el gate del `arquitecto`.
- **Complejidad.** M
- **Docs.** `CLAUDE.md` «Bucle por capítulo»; `architecture.md` §2.1 («Reintentos» y «Estado del bucle») y §8; `validators.md` §4.17, F-31 (activo: `novela gate`) y F-35 (tabla nueva).

#### 3.9 Model checking con el gate real (spec §13)

- **Descripción.** `backend/tests/test_bucle.py`:
  - `SECUENCIA` (`:25-36`) incluye los gates. `_siguientes` (`:68-84`) modela `gate mecanico`, `gate final`, `gate revision` y `gate delta` en lugar de `GATES` (`:48`), cada uno con su cuenta (D-29). `final` reintenta al `editor-estilo` y no vuelve al `escritor`.
  - Nuevo `test_la_maquina_con_el_gate_real`: por cada camino de la enumeración hasta un final (checkpoint o parada), lo reproduce con el CLI real sobre una copia de `demo-24` capítulo 8 y la fábrica (aprobado o rechazado según el camino). Comprueba que el código de cada `novela gate` es el que prevé la máquina y que el tercer rechazo de un gate deja `intervencion.md`.
- **Ficheros.**
  - `backend/tests/test_bucle.py` (modificar)
  - `backend/tests/fixtures/fabrica.py` (modificar: agentes falsos que rechazan)
  - `docs/validators.md` §4.10 (modificar)
- **Rojo.** El test nuevo, antes de adaptar la máquina: la enumeración actual no tiene pasos de gate y el CLI da 1 donde la máquina esperaba un «falla» sin código. Se ve en rojo con la máquina vieja.
- **Verde.** La máquina con los gates.
- **Refactor.** Los caminos se deduplican por la secuencia de decisiones, para que el test no pase de decenas de ejecuciones del CLI.
- **Commit.** `test(bucle): el model checking recorre los caminos contra novela gate`
- **Cubre.** RF-19 (CA-19, «con el agente falso»).
- **Depende de.** 3.8
- **Hecho cuando.** El test pasa tras verse en rojo, en menos de 60 s en la máquina de desarrollo; `test_maquina_del_bucle_y_sus_invariantes` sigue en verde con la máquina nueva, con el invariante 4 por gate («no hay un cuarto intento de ningún gate»).
- **Complejidad.** L
- **Docs.** `validators.md` §4.10 (el model checking llama al gate real; los intentos se cuentan por gate).
