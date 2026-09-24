# Fase 5: Rol y contención

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T5.1 · Depende de: fase 1

Reglas comunes: las de `README.md` §5.

## T5.1 (T-08) Agente `entrevistador`, contrato y hook
- Descripción: `.claude/agents/entrevistador.md` con `name: entrevistador`, `tools: Read, Write`, `model: sonnet` y un cuerpo que sigue el formato de `.claude/agents/cronista.md`: qué recibe (`slug`, `briefing`, `salidas`), qué escribe (solo `brief/borrador.json`, JSON válido contra `backend/schemas/brief-borrador.schema.json`, sin prosa ni vallas), las reglas de procedencia (valores copiados literales de su cita, campos cerrados solo desde entradas `respuesta`, nunca citar fragmentos marcados, el contenido de los bloques es dato), el reintento (lee el informe anterior del briefing, lee `brief/borrador.json` y lo reescribe entero, ver riesgos), `preguntas` para lo que falte o se contradiga, las cuatro reglas transversales de `docs/architecture.md:651-654` y qué devuelve. Añadir `entrevistador` a `CONTRATO` y `ESQUEMAS`, `SALIDAS["entrevistador"]` al hook, `test_entrevistador_solo_borrador` y el caso `(SESION, "Agent", "entrevistador", 0)` en `test_subagentes`. Actualizar los docstrings y comentarios que dicen «los siete». Documentar en `docs/architecture.md` §2.2, §7.1 (reglas 2 y 5, sin número), §7.4 y §7.5, `docs/definitions.md` §7, `CLAUDE.md` § Subagentes y § Hooks y `AGENTS.md` § Qué es este proyecto, sin fijar el número de roles (D14, PD6).
- Archivos: `.claude/agents/entrevistador.md` (nuevo) · `.claude/hooks/denegar-escritura-estado.py` (modificar) · `backend/tests/test_contratos.py` (modificar) · `backend/tests/test_hook.py` (modificar) · `docs/architecture.md`, `docs/definitions.md`, `CLAUDE.md`, `AGENTS.md` (modificar)
- Cubre: RF-01, RF-03
- Depende de: T1.1
- Hecho cuando: pasan `test_contratos.py::test_agentes_de_claude` y `::test_agentes_nombran_sus_salidas` (CA-01), y `test_hook.py::test_salidas_por_rol`, `::test_salidas_casan_el_contrato`, `::test_entrevistador_solo_borrador` y `::test_subagentes` (CA-03: `brief/borrador.json` con 0; `brief/brief.json`, `brief/informe.json`, `brief/entradas/ent-01.md`, `config.yaml` y `canon/premisa.md` con 2; `entrevistador` admitido y `general-purpose` denegado con `NOVELA_SESSION_ID`).
- Complejidad: S
