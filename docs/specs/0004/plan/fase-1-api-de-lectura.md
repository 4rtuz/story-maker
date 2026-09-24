# Fase 1: API de lectura

Plan: `README.md` · Spec: `docs/specs/0004/spec.md` §5 (RF-32 a RF-38), §8.3, §8.4 · Decisiones: D2, D4, D8, D17, D34, D48, D49, D53 · Depende de: nada; la spec está aceptada (D29)

Tres commits en el backend. Cada uno cierra con `uv run pytest`, `uv run mypy --strict .` y `uv run ruff check .` en verde desde `backend/`, y con `backend/api/openapi.json` regenerado con `REGENERAR=1 uv run pytest tests/test_contratos.py` (`backend/tests/test_contratos.py:141-149`). El diff del OpenAPI solo añade rutas y esquemas (RNF-18).

Ningún `GET` nuevo cambia un modelo existente, así que `backend/schemas/` no se regenera: `TramoDeLog` no es contrato de ningún agente (spec §8.3). Como todo modelo Pydantic nuevo, `TramoDeLog` lleva una línea en `docs/definitions.md`, en T-02 (D34).

---

#### T-01 `GET …/config`, `…/escaleta` y `…/checkpoint`

- Descripción: tres rutas nuevas en `backend/api/routers/novelas.py` con la dependencia `Workspace` (`novelas.py:14-23`) y los modelos de dominio tal cual: `Config`, `Escaleta` y `Checkpoint | None` (D4, PD4). `WorkspaceRepository.escaleta()` lee `plan/escaleta.md`, parte el frontmatter con `novela.dominio.frontmatter.partir` y valida con `Escaleta.model_validate(…, context={"num_capitulos": config().parametros_obra.num_capitulos})`, porque `modelo_de_md` (`workspace.py:117-123`) no pasa contexto. Si falta el fichero o no valida, `WorkspaceInvalido`, que `backend/api/main.py:24-28` convierte en 404. `…/checkpoint` reutiliza `ultimo_checkpoint()` (`workspace.py:102-104`).
- Orden TDD:
  1. Rojo: `test_config` (el cuerpo es igual a `Config` validado desde el `config.yaml`, valores por defecto incluidos, no al YAML literal; D53), `test_escaleta` y `test_checkpoint` en `backend/tests/test_api.py`, con el fixture `novelas` (`backend/conftest.py:80-91`) sobre `demo-24`, un workspace creado con `fabrica.cli(base, "nueva", …)` para «sin plan ni checkpoints», y el path traversal con los espías de `test_path_traversal` (`test_api.py:27-52`). Unitario de `escaleta()` en `backend/novela/plataforma/test_workspace.py` (existe): contexto aplicado, 404 si la curva no cuadra con `num_capitulos`.
  2. Verde: `escaleta()` y las tres rutas.
  3. Regenerar `openapi.json`; `test_openapi_al_dia` en verde.
- Archivos: `backend/api/routers/novelas.py` (modificar) · `backend/novela/plataforma/workspace.py` (modificar) · `backend/tests/test_api.py` (modificar) · `backend/novela/plataforma/test_workspace.py` (modificar) · `backend/api/openapi.json` (regenerar) · `docs/architecture.md` §11.1 (modificar)
- Cubre: RF-32, RF-33, RF-34, RF-45, RNF-18
- Criterios: CA-32, CA-33, CA-34
- Documentación: `docs/architecture.md` §11.1 (`:831-837`), con las tres rutas nuevas.
- Depende de: —
- Hecho cuando: `uv run pytest tests/test_api.py -k "config or escaleta or checkpoint"` pasa tras haberse visto en rojo; `GET /novelas/demo-24/escaleta` responde 200 con 24 valores en `curva_tension_objetivo` y el workspace sin plan responde 404; `GET /novelas/..%2F..%2Fetc/config` responde 422 sin que los espías registren rutas fuera de `backend/`; suite completa, `mypy --strict` y `ruff` en verde; `openapi.json` regenerado sin cambios en las cinco rutas de la 0001.
- Complejidad: M
- Riesgo: la validación de respuesta de FastAPI (`backend/.venv/Lib/site-packages/fastapi/routing.py:317`) podría volver a ejecutar el `model_validator` de `Escaleta` sin contexto. CA-33 lo detecta; ver README §8.

#### T-02 `TramoDeLog`, `GET …/runs` y `GET …/runs/{run_id}/log`

- Descripción:
  - En `backend/novela/dominio/artefactos.py`: `TOPE_TRAMO_BYTES = 65_536`, `TOPE_LECTURA_BYTES = 1_048_576`, `TramoDeLog(Modelo)` con `desde`, `hasta`, `tamano`, `modificado` y `lineas` (spec §8.3), y la función pura `cortar_tramo(ventana: bytes, desde: int, tope: int, *, en_limite: bool, hasta_el_final: bool) -> tuple[list[str], int]` (D17, D48, PD3):
    - si `desde` no es límite de línea, descarta hasta el primer `\n` inclusive;
    - corta en el último `\n` de los primeros `tope` bytes o, si no hay, en el primero de la ventana;
    - sin `\n`, sin líneas y con `hasta` = `desde` si la ventana llega al final, o `desde` + 1 MiB si no;
    - quita el `\n` final y el `\r` anterior; decodifica UTF-8 con sustitución.
  - En `backend/novela/plataforma/workspace.py`: `manifiestos()`, que lee `runs/*/manifest.json` con `leer_json(…, Manifest)` ordenados por `run_id`, y `tramo_de_log(run_id, desde)`, que hace `stat` (tamaño y `mtime` con zona), `seek(max(desde − 1, 0))` y lee como mucho `TOPE_LECTURA_BYTES` a partir de `desde`, más el byte anterior para `en_limite`, sin leer nunca desde el principio (D48).
  - En `backend/api/routers/novelas.py`: `GET SLUG + "/runs"` y `GET SLUG + "/runs/{run_id}/log"` con `run_id` en `Path(pattern=RUN_ID_PATRON)` y `desde` en `Query(default=0)`. Códigos: `desde < 0` o no entero → 422; `desde > tamano` → 416; run sin directorio → 404; run sin `harness.log` → 200 con `{"desde": d, "hasta": d, "tamano": 0, "modificado": null, "lineas": []}` para cualquier `d` ≥ 0 (RF-37, D48). El `GET …/runs/{run_id}` existente (`novelas.py:55-60`) no cambia.
- Orden TDD:
  1. Rojo, propiedad: `backend/novela/dominio/test_artefactos.py::test_cortar_tramo_property` con Hypothesis (perfiles de `backend/conftest.py:18-20`): líneas UTF-8 con multibyte, líneas vacías, líneas con `\r\n` y líneas mayores que el tope, tope ≥ 1 y un `desde` inicial arbitrario, también a mitad de línea y con un carácter multibyte partido en el tope; encadenado desde ese `desde` con cada `hasta` hasta un tramo sin líneas; concatenación igual a las líneas completas, sin `\r\n` ni `\n`, que empiezan en el primer límite de línea igual o posterior al `desde` inicial; `desde ≤ hasta ≤ tamano`; `hasta` siempre en un límite de línea; ninguna línea con `\n`; bytes ≤ tope salvo tramo de una sola línea mayor (CA-36). Un caso fijo aparte: una línea de más de 1 MiB da un tramo sin líneas con `hasta` = `desde` + 1 MiB, y el siguiente empieza en la línea posterior.
  2. Rojo, integración en `backend/tests/test_api.py`: `test_runs` (orden por `run_id`, un `Manifest` por fichero; CA-35), `test_log_encadenado`, `test_log_codigos` (422 con `desde=-1` y con `desde=abc`, 416, 404, 200 vacío con `desde=0` y 200 vacío con `desde=5` y `hasta` 5, en ese orden, con un run fabricado a mano con `manifest.json` y sin `harness.log`, porque `run.abrir` siempre deja log tras el primer paso, `run.py:169-199`; `desde` igual al tamaño da 200 sin líneas; y `…/runs/..%2F..%2Fconfig.yaml/log` que no responde 200 ni abre ficheros fuera de `backend/`; CA-37), y `test_log_rendimiento` (log de 1 MiB en `tmp_path`, `desde=0` en < 200 ms con `TestClient`, bytes ≤ 65 536; y con un espía de lectura, ≤ 1 MiB más un byte leídos por petición, también con `desde` cerca del final de un log de 8 MiB; RNF-17). Casos de enrutado de la spec §9: `…/runs`, `…/runs/{run_id}` y `…/runs/{run_id}/log` llegan cada uno a su endpoint.
  3. Verde: modelo, función, repositorio y rutas.
  4. Regenerar `openapi.json`.
- Archivos: `backend/novela/dominio/artefactos.py` (modificar) · `backend/novela/dominio/test_artefactos.py` (nuevo) · `backend/novela/plataforma/workspace.py` (modificar) · `backend/novela/plataforma/test_workspace.py` (modificar) · `backend/api/routers/novelas.py` (modificar) · `backend/tests/test_api.py` (modificar) · `backend/api/openapi.json` (regenerar) · `docs/architecture.md` §11.1 y §12.6 (modificar) · `docs/definitions.md` (modificar)
- Cubre: RF-35, RF-36, RF-37, RF-45, RNF-17, RNF-18
- Criterios: CA-35, CA-36, CA-37
- Documentación: `docs/architecture.md` §11.1 con las dos rutas y §12.6 (`:873`) cerrada, como están cerrados §12.2 y §12.7 («Cerrado (spec 0004): …»); y una línea con `TramoDeLog` en `docs/definitions.md` (D34).
- Depende de: T-01 (mismo router y mismo `openapi.json`)
- Hecho cuando: la propiedad de CA-36 y los tests de CA-35, CA-37 y RNF-17 pasan tras verse en rojo, también con `--hypothesis-profile=ci`; `test_cinco_get_en_solo_lectura` sigue sin cambios y en verde; suite completa, `mypy --strict` y `ruff` en verde; `openapi.json` regenerado.
- Complejidad: L

#### T-03 Los diez `GET` en solo lectura

- Descripción: `test_get_del_panel_en_solo_lectura` en `backend/tests/test_api.py` con el fixture `solo_lectura` (`test_api.py:55-72`): recorre los diez `GET` de la spec §8.4 con parámetros que responden 200, pide cada una de esas rutas con `POST`, `PUT`, `PATCH` y `DELETE` y espera 405, y comprueba que el OpenAPI no tiene operaciones distintas de `get`. Los `HEAD` y `OPTIONS` automáticos de Starlette y del CORS no cuentan (D49). `test_cinco_get_en_solo_lectura` (`:75-107`) no se toca. Es una tarea de verificación: si el test pasa a la primera, se comprueba que no es decorativo introduciendo una escritura temporal en un endpoint (sin commitearla) y viéndolo en rojo.
- Archivos: `backend/tests/test_api.py` (modificar)
- Cubre: RF-38, RNF-18
- Criterios: CA-38
- Documentación: ninguna (la regla de solo lectura ya está en `docs/architecture.md` §11.1).
- Depende de: T-01, T-02
- Hecho cuando: el test pasa y se ha visto en rojo con la escritura inyectada; `git diff` de `backend/api/openapi.json` desde antes de T-01 solo añade rutas y esquemas (revisión en el PR); suite completa, `mypy --strict` y `ruff` en verde.
- Complejidad: S
