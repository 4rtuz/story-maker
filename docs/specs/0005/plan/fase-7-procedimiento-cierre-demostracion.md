# Fase 7: Procedimiento, cierre y demostración

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T7.1, T7.2, T7.3 · Depende de: fase 4, fase 5, fase 6

Reglas comunes: las de `README.md` §5.

Reparto de la documentación de D13 (PD6):

| Documento y sección | Qué cambia | Tarea |
|---|---|---|
| `docs/definitions.md` §1, §6 | Brief y sus campos; `brief/` | T1.1 |
| `docs/architecture.md` §4, §5, §8 · `AGENTS.md` § CLI | `brief/`, `ent-NN`, `novela brief iniciar|entrada` | T2.2 |
| `docs/architecture.md` §8 | `preparar` | T3.1 |
| `docs/architecture.md` §8 | `validar` | T4.3 |
| `docs/architecture.md` §2.2, §7.1, §7.4, §7.5 · `docs/definitions.md` §7 · `CLAUDE.md` § Subagentes, § Hooks · `AGENTS.md` § Qué es este proyecto | Rol `entrevistador`, sin número de roles | T5.1 |
| `docs/architecture.md` §8 · `AGENTS.md` § CLI | `novela nueva --brief` | T6.1 |
| `docs/architecture.md` §3.1, §8 · `docs/domain-knowledge.md` §1, §5 | Árbol del slice y comando `/novela-brief`; diagramas | T7.1 |
| `docs/validators.md` §2, §4.9, §5 | Datos personales, amenaza 2 con entrada del cliente, riesgos de la spec §11 | T7.2 |
| `docs/validators.md` §4.9 | Resultado de la demostración | T7.3 |

## T7.1 (T-10) Procedimiento `/novela-brief` y flujo con agente falso
- Descripción: `.claude/commands/novela-brief.md` con el formato de `.claude/commands/novela-nueva.md`: argumentos (`<slug> --ocasion <o>`), tabla de códigos, cada orden `novela` sola en su Bash, prompt de Task de §8.4, pasos de §8.5 (pedir al operador rutas de ficheros fuera del repositorio), decisión por la última línea del log (`brief validar -> 1 · agente:` reintenta, `· usuario:` pregunta al operador mostrando `brief/informe.json`), topes de 2 reintentos seguidos y 5 rondas contados en el log, `intervencion.md` y parada, y final con `/novela-nueva <slug> --brief`. Paso 1 y argumentos de `novela-nueva.md` con `--brief` como alternativa a `--idea`. `test_brief_flujo.py` recorre iniciar → entrada ×2 → preparar → agente falso → validar (`usuario:`) → entrada → preparar → validar (0) → `nueva --brief`, más una ejecución con `borrador-obediente.json`, y lee el `harness.log`. Documentar `docs/architecture.md` §3.1 y §8 y `docs/domain-knowledge.md` §1 y §5.
- Archivos: `.claude/commands/novela-brief.md` (nuevo) · `.claude/commands/novela-nueva.md` (modificar) · `backend/tests/test_brief_flujo.py` (nuevo) · `docs/architecture.md`, `docs/domain-knowledge.md` (modificar)
- Cubre: RF-02, RF-23 (flujo), RNF-01, RNF-04, RNF-10, RNF-12
- Depende de: T4.3, T5.1, T6.1
- Hecho cuando: pasan `test_brief_flujo.py::test_procedimiento_novela_brief` (CA-02: orden de las tres órdenes, `agente:` y `usuario:`, 2 y 5, `intervencion.md`, `/novela-nueva <slug> --brief`, sin `;`, `&&` ni `|` en órdenes `novela`) y `::test_flujo_completo` (CA-23: una línea por subcomando, prefijos esperados, ninguna aparición de los nombres ficticios, rasgos, citas ni términos vetados de las fixtures; ningún `brief.json` con citas en fragmentos marcados ni campos cerrados desde texto libre), y `test_contratos.py::test_sin_clientes_de_modelo` sigue en verde.
- Complejidad: M

## T7.2 (T-11) API sin rutas nuevas y cierre de la documentación
- Descripción: añadir `test_api.py::test_sin_rutas_de_brief` (ninguna ruta de la app contiene `brief`). Actualizar `docs/validators.md` §2, §4.9 (retirar la frase de `:295`, amenaza 2 con la entrada del cliente) y §5 (riesgos aceptados de la spec §11). Revisar todas las secciones de D13 contra el código final, sin «pendiente» ni «próximamente». Si P1 lo decide, trasladar o borrar el plan según el ciclo de vida de `AGENTS.md`.
- Archivos: `backend/tests/test_api.py` (modificar) · `docs/validators.md` (modificar)
- Cubre: RF-29, RF-30, RNF-09
- Depende de: T7.1
- Hecho cuando: pasan `test_contratos.py::test_openapi_al_dia` y `test_api.py::test_sin_rutas_de_brief` (CA-29); `git diff <commit anterior a T1.1> -- backend/api/openapi.json backend/schemas/config.schema.json backend/schemas/state.schema.json` está vacío (RNF-09); una búsqueda de `datos personales` en `docs/validators.md` ya no devuelve la frase de `:295`, y `rg -n "pendiente|próximamente"` no da resultados nuevos en las secciones de D13 (CA-30).
- Complejidad: S

## T7.3 (T-12) Demostración con datos ficticios
- Descripción: en una sesión del harness abierta con `NOVELA_SESSION_ID` exportada y `--setting-sources project` (sin `local`), ejecutar `/novela-brief` sobre un slug de prueba con `respuestas-completas.md` y `carta-inyectada.md`. Comprobar que el brief sale válido, que ningún campo cerrado procede de la carta y que en Langfuse no hay observaciones con el `session_id` de esa sesión (`GET /api/public/v2/observations` filtrando por `sessionId`, según `docs/architecture.md:783`). Anotar el resultado, sin nombres de personas, en `docs/validators.md` §4.9.
- Archivos: `docs/validators.md` (modificar)
- Cubre: RF-01 (comportamiento del prompt), RF-02 (procedimiento real), RNF-07
- Depende de: T7.2
- Hecho cuando: `novela brief validar` sale con 0 en la sesión, `brief/brief.json` no tiene `tono` ni otro campo cerrado con fuente `ent-02`, la consulta a Langfuse devuelve 0 observaciones para ese `session_id` y el resultado está anotado en §4.9.
- Complejidad: S
