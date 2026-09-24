# Fase 1: Dominio y contratos

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T1.1 · Depende de: nada; solo la aceptación de la spec (P1)

Reglas comunes: las de `README.md` §5.

## T1.1 (T-01) Modelos del brief, `idea_semilla` y esquemas
- Descripción: crear `dominio/brief.py` con `Ocasion`, `Genero = Subgenero`, `Tono`, `Extension` (con el objetivo 1.000/1.250/1.500), `Fuente`, `ValorTexto`, `ValorEdad`, `ValorCerrado[T]`, `Prohibidos`, `Destinatario` (versión borrador y estricta), `BorradorBrief`, `Brief`, `InicioBrief`, `EntradaMeta`, `Hallazgo` (con `tipo` y `codigo` como `Literal` cerrados de §8.3) e `InformeBrief` (validador: `valido` si y solo si `hallazgos` vacío), con los límites de §8.3 y patrones `[0-9]`. Función pura `idea_semilla(brief) -> str` con la plantilla de §8.4, en el orden del brief. Registrar los tres modelos en `esquemas.py` y regenerar. Crear las fixtures `brief-completo.json`, `borrador-completo.json` y `golden/idea-semilla.txt`. Añadir a `test_contratos.py` `test_brief_valida_contra_el_esquema` (CA-28), `test_fixtures_de_brief_sin_datos_personales` (RNF-05: correo, teléfono de 9 dígitos, DNI/NIE y nombres propios fuera de la lista ficticia) y un test de minimización que recorre `brief.schema.json` y comprueba que los únicos campos personales son `nombre`, `edad`, `rasgos` y `recuerdos` (RNF-06). Documentar en `docs/definitions.md` §1 y §6.
- Archivos: `backend/novela/dominio/brief.py` (nuevo) · `backend/novela/dominio/test_brief.py` (nuevo) · `backend/novela/dominio/esquemas.py` (modificar) · `backend/schemas/brief.schema.json`, `brief-borrador.schema.json`, `brief-informe.schema.json` (nuevos, generados) · `backend/tests/test_contratos.py` (modificar) · `backend/tests/fixtures/brief/brief-completo.json`, `borrador-completo.json`, `golden/idea-semilla.txt` (nuevos) · `docs/definitions.md` (modificar)
- Cubre: RF-24, RF-27, RF-28, RNF-05, RNF-06, RNF-09 (parcial)
- Depende de: —
- Hecho cuando: pasan `dominio/test_brief.py::test_brief_ata_entradas` (CA-24) y `::test_idea_semilla_determinista` (CA-27, igual byte a byte al golden y conserva el orden), `test_contratos.py::test_state_schema_al_dia` y `::test_brief_valida_contra_el_esquema` (CA-28), el test de RNF-05 y el de RNF-06; añadir un campo a `Brief` sin regenerar pone rojo `test_state_schema_al_dia`, y `config.schema.json` y `state.schema.json` no tienen diff.
- Complejidad: M
