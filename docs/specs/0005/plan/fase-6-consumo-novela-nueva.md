# Fase 6: Consumo por `novela nueva`

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T6.1 · Depende de: fase 1, fase 4

Reglas comunes: las de `README.md` §5.

## T6.1 (T-09) `novela nueva --brief`
- Descripción: implementar PD5. `--idea` pasa a `str | None = None` y `--brief` es un flag booleano. Sin `--brief`, el camino actual no cambia. Con `--brief`: exclusiones (2), precondiciones (1), lectura de `brief.json` con `WorkspaceInvalido` convertido en 1, configuración con `num_capitulos: 10`, terna `{objetivo, 1000, 1500}`, `longitud_total_palabras = 10 × objetivo`, `subgenero = genero`, `restricciones_contenido = prohibidos.terminos` e `idea_semilla(brief)`, y creación del árbol y de `estado.db`. Mensajes de error sin valores del brief (PD3). Documentar `--brief` en `docs/architecture.md` §8 y `AGENTS.md` § CLI.
- Archivos: `backend/novela/slices/nueva/cmd.py` (modificar) · `backend/novela/slices/nueva/test_nueva.py` (modificar: solo tests nuevos) · `docs/architecture.md`, `AGENTS.md` (modificar)
- Cubre: RF-25, RF-26, RF-27 (integración), RNF-09 (parcial)
- Depende de: T1.1, T4.3
- Hecho cuando: pasan `test_nueva.py::test_nueva_desde_brief` (CA-25, con `GET /novelas` listando el slug vía `TestClient`) y `::test_brief_excluyente` (CA-26: 2, 2, 1, 1 y 1, sin `config.yaml` ni `estado.db`); los tres tests existentes de `test_nueva.py` pasan sin editarse (`git diff` de esas funciones vacío), y `config.schema.json` no cambia.
- Complejidad: M
