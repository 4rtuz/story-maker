# Fase 3: Briefing del entrevistador

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T3.1 · Depende de: fase 2

Reglas comunes: las de `README.md` §5.

## T3.1 (T-04) `assemble.py` y `preparar`
- Descripción: `assemble.py` puro: recibe ocasión, entradas (meta y texto), borrador e informe anteriores (texto o `None`), `run_id` y límites, y devuelve el briefing con las secciones de §8.4 en su orden (ocasión, vocabularios de `Genero`, `Tono` y `Extension` sacados de los `Literal` de T1.1, límites de §8.3, reglas de procedencia, fragmentos marcados como `ent-NN: líneas a, b` fuera de todo bloque, borrador anterior, informe anterior y entradas delimitadas por id) y su estimación de tokens (PD2). Lanza `PresupuestoExcedido` si pasa de 40.000 y `MarcaEnTexto` (RF-10) con el id de la entrada. `cmd.py preparar`: comprueba que el brief está abierto, sale con 1 sin entradas, con 1 si `MarcaEnTexto` o `PresupuestoExcedido`, busca el último `brief-RR-entrevistador.md` del run y, si es idéntico byte a byte, imprime su ruta sin escribir (RF-13); si no, escribe `brief-(RR+1)`. Imprime `<ruta> · <n> tokens`. Crear el workspace sintético `brief-golden` y el golden.
- Archivos: `backend/novela/slices/brief/assemble.py` (nuevo) · `backend/novela/slices/brief/test_assemble.py` (nuevo) · `backend/novela/slices/brief/cmd.py` (modificar) · `backend/novela/slices/brief/test_cmd.py` (modificar) · `backend/tests/fixtures/brief/golden/brief-01-entrevistador.md` (nuevo) · `docs/architecture.md` §8 (modificar: `preparar`)
- Cubre: RF-08, RF-10 (CLI), RF-11 (briefing), RF-12, RF-13, RNF-11, RNF-12 (parcial)
- Depende de: T2.2
- Hecho cuando: pasan `test_assemble.py::test_briefing_golden` (CA-08, igual byte a byte con `NOVELA_RUN_ID` fijo), `test_cmd.py::test_preparar_sin_entradas` (CA-08, 1), un test de CLI de CA-10 (1, el motivo nombra el id y no hay briefing), la parte de briefing de CA-11 (`ent-02: líneas 4, 7` fuera de bloque y el texto de esas líneas una sola vez), `test_assemble.py::test_presupuesto` (CA-12) y `test_cmd.py::test_preparar_idempotente` (CA-13).
- Complejidad: M
