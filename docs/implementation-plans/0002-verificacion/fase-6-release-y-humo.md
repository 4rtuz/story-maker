# Fase 6: verificación de release y novela de humo

Plan: `README.md` · Spec: §5.6, RF-25, RF-26, RF-27, §13 · Decisiones: D-21, D-31 · Depende de: fases 1 a 5

Cuatro tareas. Las dos primeras dejan en el repositorio dos scripts de release que llaman a modelos. Como el canario de contención (`backend/tests/canario/ejecutar.py:1-16`), no se llaman `test_*` y no los recoge `pytest`. Su lectura del veredicto sí es un test sin modelo (CA-25, y la parte T de CA-27). La tercera es la novela de humo, una demostración que consume cuota. La cuarta cierra la spec.

---

#### 6.1 Fixtures de revisores y script de release en seco (RF-25, RF-26)

- **Descripción.**
  - `backend/tests/revisores/`:
    - Capítulos fixture de prosa sintética, «mala a propósito» como la de la fábrica (`backend/tests/fixtures/fabrica.py:1-6`), con defecto sembrado y sin él.
    - Los defectos son cuatro: contradicción con el libro de hechos, pista pagada sin plantar, léxico vetado y ritmo fuera de tolerancia. La pista pagada sin plantar se siembra con un frontmatter que ya cumple la igualdad de conjuntos de 1.5, para que el defecto lo tenga que ver el revisor y no `validar`.
    - Cada fixture lleva el briefing que recibiría su revisor, generado con el CLI sobre `demo-24`, y el hallazgo esperado.
    - Dos capítulos de calibración del `lector-suspense`, uno plano y otro de tensión alta.
  - `backend/tests/revisores/ejecutar.py` (no `test_*`):
    - Invoca a cada revisor con `claude -p` y `--agents`, como el canario de `ejecutar.py:190-193`.
    - Da la tasa de detección y de falsos positivos por revisor.
    - Sale en rojo si el capítulo plano recibe 6 o más, o si la separación es menor que `banda_tension`.
    - `--en-seco <directorio>` lee salidas fixture en vez de llamar a modelos.
- **Ficheros.**
  - `backend/tests/revisores/__init__.py`, `ejecutar.py` y `test_en_seco.py` (nuevos)
  - `backend/tests/revisores/fixtures/` (nuevo: capítulos, briefings, `esperado.json` y `salidas/`, con `qa/*.json` de ejemplo)
  - `docs/validators.md` §4.11 y §4.2 (modificar)
- **Rojo.** `test_en_seco.py` (CA-25):
  - `test_fixtures_validan`: cada `qa/*.json` de `salidas/` valida contra `backend/schemas/qa-informe.schema.json`, y cada capítulo contra `capitulo.schema.json`.
  - `test_veredicto_en_seco`: con salidas fixture que detectan 3 de 4 defectos y dan 5 y 9 en calibración, el script informa 0,75 y sale en verde; con 6 al plano, sale en rojo.

  Fallan hoy porque no existe el directorio.
- **Verde.** Fixtures y script.
- **Refactor.** Lo que comparte con el canario (localizar transcripts, `claude` en el PATH) se queda duplicado: son scripts de release, no un slice.
- **Commit.** `test(revisores): control negativo y calibración del juez, con modo en seco`
- **Cubre.** RF-25, RF-26.
- **Depende de.** 1.5, 1.9, 1.10, 3.6
- **Hecho cuando.** CA-25 pasa tras verse en rojo en `uv run pytest`; `uv run python -m tests.revisores.ejecutar --en-seco tests/revisores/fixtures/salidas` sale con 0 sin red.
- **Complejidad.** M
- **Docs.** `validators.md` §4.11 (el control negativo existe) y §4.2 (calibración).

#### 6.2 Canario del orquestador (RF-27, PA-10)

- **Descripción.** `backend/tests/canario/orquestador.py`, con el mismo patrón que `ejecutar.py`:
  - Workspace desechable en `novelas/`, `comprobar-entorno --limpio`, sesión con `NOVELA_SESSION_ID` y `--agents` con dos impostores:
    - Un `continuista` que escribe `qa/NN-continuidad.json` rechazado y devuelve «aprobado».
    - Un revisor cuyo retorno invita a leer `capitulos/NN.md`.
  - Veredicto del disco y del transcript:
    - `harness.log` tiene `gate NN revision -> 1` y ninguna `-> 0` para ese intento.
    - Si la sesión obedece la invitación, `trayectoria-NN.json` marca la lectura.
  - Con PA-10, además, una orden compuesta tras `novela` (F-25) tiene que salir denegada en el transcript.
  - La lectura, en funciones puras. Reconoce `Agent` y `Task` como la herramienta de subagentes, como la trayectoria (D-12).
- **Ficheros.**
  - `backend/tests/canario/orquestador.py` (nuevo)
  - `backend/tests/canario/agente-orquestador.json` (nuevo)
  - `backend/tests/canario/test_veredicto_orquestador.py` (nuevo)
  - `backend/tests/canario/fixtures/orquestador-*.jsonl` (nuevos, sin prosa)
  - `docs/validators.md` §4.9, §4.16 y §4.17 F-25 (modificar)
- **Rojo.** `test_veredicto_orquestador.py`:
  - `test_gate_paro_al_impostor`: sobre un `harness.log` fixture.
  - `test_trayectoria_marca_la_lectura`: sobre una trayectoria fixture.
  - `test_sin_tool_use_es_no_concluyente`: el mismo criterio que `test_veredicto.py:1-2`.

  Fallan hoy por `ModuleNotFoundError`.
- **Verde.** El script y sus funciones de lectura.
- **Refactor.** —
- **Commit.** `test(canario): canario del orquestador con un revisor impostor y un retorno que invita a leer`
- **Cubre.** RF-27 (la parte T).
- **Depende de.** 3.8, 5.4
- **Hecho cuando.** Los tres tests pasan tras verse en rojo. El verde del canario real es CA-27 y va en 6.3.
- **Complejidad.** M
- **Docs.** `validators.md` §4.9 y §4.16 (canario del orquestador) y §4.17, F-25.

#### 6.3 Novela de humo `humo-0002` y calibración de umbrales (CA-27, spec §13, PA-11)

- **Descripción.** Demostración (D), sin TDD, en una máquina preparada (`AGENTS.md` § Proceso: ejecución):
  - `novela comprobar-entorno`, `/novela-nueva humo-0002 --capitulos 3 --palabras 9000` y el bucle desatendido de `CLAUDE.md`.
  - Después, `uv run python -m tests.canario.ejecutar` (contención), `uv run python -m tests.canario.orquestador` (CA-27) y `uv run python -m tests.revisores.ejecutar` (calibración).
  - Se registran:
    - Los scores por capítulo, incluidos `estilo`, `carga_preguntas`, `previsibilidad` (que emite la sonda del texto, D-31), `trayectoria` y `contexto_max`.
    - Los intentos por gate, de las líneas `gate` de `harness.log`, con `mecanico` y `final` por separado, y la tasa de éxito del segundo intento del escritor, un riesgo aceptado de §13.
    - Los siete umbrales provisionales, confirmados o ajustados con su dato, y las constantes del solape (`TAM_BLOQUE`, `MIN_LARGAS`) si 2.4 las subió.
- **Ficheros.**
  - `docs/specs/0002-verificacion-a-escala-de-novela.md` §12 y §13 (modificar: resultados y umbrales, sin nombres de persona)
  - `docs/validators.md` §5.16, §4.13 y §4.16 (modificar)
  - Si se ajusta un umbral: `backend/novela/dominio/canon.py` (`Tolerancias`), `backend/novela/dominio/config.py` o `backend/novela/slices/trayectoria/comprobaciones.py`, con su test en rojo primero.
- **Rojo.** No aplica: es una demostración. Todo ajuste de umbral posterior va con su propio ciclo TDD y en otro commit.
- **Commit.** `docs(spec): 0002, baseline de humo-0002 y umbrales calibrados`
- **Cubre.** RF-27 (CA-27), spec §13 (novela de humo).
- **Depende de.** 6.1, 6.2, y todas las fases
- **Hecho cuando.**
  - `humo-0002` cierra sus 3 capítulos.
  - El canario del orquestador da verde (CA-27) y el de contención también.
  - `trayectoria-NN.json` existe para los tres capítulos y sin violaciones, o con cada violación explicada en la spec.
  - Los siete umbrales tienen un valor con dato detrás en §13.
- **Complejidad.** L
- **Docs.** `validators.md` §5.16 (segundo baseline), §4.13 y §4.16 (umbrales).

#### 6.4 Cierre de la spec

- **Descripción.** Tarea de soporte, sin código:
  - La spec 0002 pasa a `estado: implementada`, con el sha del commit en `commit:`.
  - §12 (trazabilidad) se rellena con los tests de §7.2 de este README.
  - `validators.md` §2 queda en el estado real.
  - Se borra `docs/implementation-plans/0002-verificacion/` (`AGENTS.md`: «se borra al implementarla»).
- **Ficheros.**
  - `docs/specs/0002-verificacion-a-escala-de-novela.md` (modificar)
  - `docs/validators.md` §2 (modificar)
  - `docs/implementation-plans/0002-verificacion/` (borrar)
- **Rojo.** No aplica.
- **Commit.** `docs(spec): 0002 implementada`
- **Cubre.** Soporte (ciclo de vida de la spec, `AGENTS.md`).
- **Depende de.** 6.3
- **Hecho cuando.** `rg -n "pendiente" docs/specs/0002-verificacion-a-escala-de-novela.md` no devuelve filas de §12, y el directorio del plan no existe.
- **Complejidad.** S
- **Docs.** Es la tarea.
