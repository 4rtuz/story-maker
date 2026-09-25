# Guardrails

Dos piezas del policy engine que se aplican en código, no en el prompt: el guardrail de palabras prohibidas sobre cada capítulo y el log de auditoría de las denegaciones del hook `PreToolUse`.

## Palabras prohibidas

**Listas.** En la base de la novela (`estado/estado.db`), tabla `prohibidas(termino, nivel)`, en tres niveles:

| Nivel | Qué es | Cómo entra |
|---|---|---|
| `global` | Insultos y términos ofensivos | `backend/config/prohibidas-globales.txt`, versionado; se siembra en `novela nueva` y en la primera escritura de una base anterior |
| `cliente` | Lo que el cliente vetó en el brief | `brief.json` → `prohibidos.terminos` → `config.yaml` `restricciones_contenido`, cargado en `novela nueva --brief` |
| `novela` | Lo que surge después, para esa novela | `novela prohibidas añadir <slug> <término>…` |

`novela prohibidas listar <slug>` imprime `nivel<TAB>término`. Un término que ya está en un nivel anterior no se repite en el siguiente. Una base sin las tablas se lee del fichero global y del `config.yaml`, sin escribir.

**Normalización** (`backend/novela/dominio/prohibidas.py`). Por palabra completa: sin caja, sin tildes (la ñ se conserva: «año» no es «ano») y reducida a una raíz que iguala plural (`-s`, `-es`), género (`-o`/`-a`) y diminutivo (`-ito`, `-ita`, `-illo`, `-illa`). Una frase casa si sus raíces aparecen seguidas, aunque crucen un salto de línea. Es una heurística: dos palabras distintas con la misma raíz («bono», «bonito») casan. Por eso la lista global deja fuera las que tienen una forma inocente de otro género («zorra», «perra», «polla»).

**Dónde bloquea.** Es el validador `vp_prohibidas` de `novela validar`: un hallazgo `termino_prohibido` por término y forma, con `referencia` = nivel, `ubicacion` = `línea N, M` (del cuerpo, sin el frontmatter) y una descripción que nombra la forma y el término. `validar` sale con 1 y el bucle de `/novela-continuar` devuelve el capítulo al escritor (paso 3) o al editor (paso 5) con `reintento: qa/NN-validacion.json`, que es donde lee qué término y dónde. Con dos intentos consumidos, `intervencion.md` y para.

**Registro.** Cada coincidencia que rechaza un capítulo añade una fila a `auditoria_policy(id, momento, origen, decision, nivel, termino, capitulo, detalle)`, append-only por trigger como `libro_de_hechos`, y emite a Langfuse el score `guardrail_prohibidas` (número de coincidencias). En `checkpoint`, `vp_prohibidas` sale como score binario con los demás `vp_*`. Un capítulo limpio no escribe en la base: `validar` la abre en solo lectura.

**A mano.** `novela prohibidas comprobar <slug>` recorre `capitulos/*.md` de un workspace existente sin reescribirlos, imprime `NN línea L: «forma» es el término prohibido «término» (nivel)`, registra las coincidencias con `origen = comprobar` y sale con 1 si hay alguna. Toma el lock: con una generación en marcha sale con 3.

## Auditoría del hook

`.claude/hooks/denegar-escritura-estado.py` añade una línea JSON por denegación (`momento`, `decision`, `herramienta`, `agente`, `sesion`, `motivo`) a `novelas/<slug>/auditoria/policy.jsonl` si la ruta cae en un workspace que existe, y si no (una orden, una entrada ilegible) a `.claude/logs/policy.jsonl` de `CLAUDE_PROJECT_DIR`. No crea workspaces. Si no puede escribir, la decisión no cambia: el log nunca hace fallar al hook. `.claude/logs/` y `novelas/` están en `.gitignore`.

## Validadores y verificadores

| Validador | Qué comprueba | Puntos | Bloquea en | Tipos | Score y valor | Test |
|---|---|---|---|---|---|---|
| `vp_prohibidas` | Ningún término de los tres niveles, en ninguna variante simple, en el cuerpo del capítulo | `validar` | `validar` | `termino_prohibido` | binario en `checkpoint`; `guardrail_prohibidas` = coincidencias en `validar` | `validacion/test_gates.py::test_prohibidas_property` |

Verificación:

- `dominio/test_prohibidas.py`: variantes de caja, tilde, plural, género y diminutivo; palabra completa; frases; la ñ. Property-based.
- `validacion/test_gates.py::test_prohibidas_property`: cualquier nivel, en cualquier línea, deja un solo hallazgo con término, nivel y línea.
- `prohibidas/test_prohibidas.py`: de punta a punta con el CLI, un caso por nivel (global, cliente desde el brief, novela añadida), auditoría append-only, score, capítulo limpio sin tocar la base, y `comprobar` sin reescribir.
- `tests/test_hook.py`: el log del workspace, el del proyecto y un log que no se puede escribir.
- `tests/test_contratos.py::test_tabla_de_validadores`: la tabla de `docs/validators.md` §3.10, que también lleva esta fila, coincide con el catálogo.

---
