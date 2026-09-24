# Fase 4: Validación

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T4.1, T4.2, T4.3 · Depende de: fase 1, fase 2, fase 3

Reglas comunes: las de `README.md` §5.

## T4.1 (T-05) Gates de esquema, faltantes y contradicciones
- Descripción: bajar `normalizar` a `dominio/texto.py` (PD1). `gates.py` puro: `esquema(datos_json) -> (BorradorBrief | None, hallazgos)` (`borrador_ausente` o `esquema_invalido` con la ruta de cada `loc`, truncada al campo del borrador, ver P11), `faltantes(borrador)` (cada obligatorio a `null`, y `rasgos` o `recuerdos` vacíos; `prohibidos` con `terminos: []` no es faltante) y `contradicciones(borrador)` (C-01 y C-02 solo si `edad` y el otro campo existen; C-03 con coincidencia de palabra completa sobre texto normalizado y en minúsculas). Fixtures `borrador-sin-edad.json` y `borrador-contradictorio.json`.
- Archivos: `backend/novela/dominio/texto.py` (nuevo) · `backend/novela/slices/delta/violaciones.py` (modificar: importa `normalizar`) · `backend/novela/slices/brief/gates.py` (nuevo) · `backend/novela/slices/brief/test_gates.py` (nuevo) · `backend/tests/fixtures/brief/borrador-sin-edad.json`, `borrador-contradictorio.json` (nuevos)
- Cubre: RF-15, RF-16, RF-17, RF-18
- Depende de: T1.1
- Hecho cuando: pasan `test_gates.py::test_esquema` (CA-15, sin hallazgos de otro tipo), `::test_faltantes` (CA-16, exactamente tres `falta_campo`), `::test_contradiccion_edad_genero_tono` (CA-17, con los casos de 12 años y de `domestic_suspense`/`tierno`) y `::test_prohibido_en_texto` (CA-18, «hospitalario» no casa), y `slices/delta/test_violaciones.py` sigue en verde sin cambios.
- Complejidad: M

## T4.2 (T-06) Gate de procedencia
- Descripción: `gates.procedencia(borrador, entradas, marcados)`: para cada `fuente`, que la entrada existe (`entrada_inexistente`) y que la cita, normalizada y en minúsculas, es subcadena de su texto (`cita_no_literal`); para `nombre`, cada rasgo y cada término vetado, que el valor es subcadena de su cita (`valor_fuera_de_cita`); que `nombre`, `edad`, `genero`, `tono`, `extension` y `prohibidos` citan una entrada `respuesta` (`campo_cerrado_desde_texto_libre`); y que ninguna cita solapa un fragmento marcado (`cita_en_fragmento_marcado`, PD4). Fixtures `borrador-limpio.json` y `borrador-obediente.json`.
- Archivos: `backend/novela/slices/brief/gates.py` (modificar) · `backend/novela/slices/brief/test_gates.py` (modificar) · `backend/tests/fixtures/brief/borrador-limpio.json`, `borrador-obediente.json` (nuevos)
- Cubre: RF-19, RF-20, RF-21, RNF-01, RNF-02
- Depende de: T2.1, T4.1
- Hecho cuando: pasan `test_gates.py::test_procedencia_literal` (CA-19, tres códigos con sus rutas), `::test_procedencia_property` (CA-19, Hypothesis con `max_examples=200`: espacios insertados y NFC↔NFD sin hallazgos), `::test_inyeccion_no_altera_brief` (CA-20, a nivel de gates: con `borrador-obediente.json` salen `campo_cerrado_desde_texto_libre` en `tono` y `cita_en_fragmento_marcado` en el recuerdo) y `::test_cita_en_fragmento_marcado` (CA-21, líneas 3-4 sí, solo línea 3 no).
- Complejidad: L

## T4.3 (T-07) `validar`: informe, `brief.json`, custodia y log
- Descripción: `cmd.py validar`: brief abierto (RF-07), lock, run. Custodia: por cada entrada, si el sha256 del cuerpo no coincide con su frontmatter, `WorkspaceInvalido` con el id (4) sin escribir el informe (RF-22). Carga del borrador en crudo (`json.loads`, no `leer_json`, para que un borrador inválido sea hallazgo y no 4), gates en orden (esquema → si falla, nada más; si no, faltantes, contradicciones y procedencia), escritura atómica de `informe.json` con las `preguntas` del borrador y, sin hallazgos, construcción y escritura de `brief.json` con `ocasion` de `inicio.json` y `entradas` (RF-24). Línea de log con PD7 y causas saneadas (PD3). Medir RNF-08. Documentar `validar` en `docs/architecture.md` §8.
- Archivos: `backend/novela/slices/brief/cmd.py` (modificar) · `backend/novela/slices/brief/test_cmd.py` (modificar) · `docs/architecture.md` (modificar)
- Cubre: RF-07 (preparar y validar), RF-14, RF-22, RF-23, RF-24 (escritura), RNF-04, RNF-08, RNF-12 (parcial)
- Depende de: T3.1, T4.2
- Hecho cuando: pasan `test_cmd.py::test_validar_escribe_brief` (CA-14: 0, `valido: true`, `brief.json` valida contra el esquema; con `borrador-sin-edad.json`, 1, y un `brief.json` anterior igual byte a byte), `::test_brief_cerrado` completo (CA-07, las tres órdenes y la huella de `brief/` igual), `::test_entrada_manipulada` (CA-22: 4, nombra `ent-01`, sin `informe.json`), `::test_log_sin_valores` (CA-23 a nivel de slice, incluido el `inicio.json` corrupto de PD3) y un test de rendimiento con 20 entradas de 20.000 caracteres por debajo de 2 s con `time.perf_counter` (RNF-08).
- Complejidad: M
