---
spec: NNNN
titulo: ""
estado: borrador          # borrador | aceptada | implementada | descartada
autor: ""
fecha: AAAA-MM-DD
version: 0.1              # sube al cambiar un requisito ya revisado
afecta: []                # backend | frontend | agentes | esquemas | docs
depende_de: []            # otras specs (NNNN) que deben estar implementadas antes
sustituye: []             # specs que esta deja obsoletas
adr: []                   # ADRs relacionados en docs/adr/
commit: null              # sha, al pasar a implementada
---

# NNNN — <título>

## 1. Propósito y alcance

Una frase: qué hace este cambio y para quién. Después, el alcance en dos listas.

**Dentro del alcance**

- ...

**Fuera del alcance**

- ... (lo que alguien podría asumir que entra y no entra; evita discusiones en revisión)

## 2. Problema

Qué no funciona o qué falta hoy. Sin solución todavía. Si no puedes escribir esto en tres frases, el problema no está claro y la spec es prematura.

Incluye la evidencia: el comando que falla, el capítulo que salió incoherente, la traza de Langfuse. Un problema sin evidencia es una preferencia.

## 3. Actores y partes implicadas

Quién usa o sufre este cambio. Solo los que aparecen en los requisitos.

| Actor | Interés en este cambio |
|---|---|
| Orquestador | |
| Agente `<rol>` | |
| Operador humano | |
| Frontend / API | |

## 4. Contexto y restricciones

- **Invariantes que aplican**: cuáles de los 8 de `AGENTS.md` condicionan la solución.
- **Restricciones técnicas**: Python 3.12, sin SDK de proveedores, API de solo lectura, escritura atómica, un proceso por workspace.
- **Supuestos**: lo que damos por cierto sin verificarlo. Si un supuesto cae, la spec se revisa.
- **Dependencias**: specs, ADRs o trabajo externo que deben existir antes.

## 5. Propuesta

Qué se va a hacer. Concreto: rutas de fichero, nombres de subcomando, forma del JSON, nombre de los campos nuevos.

Si el cambio tiene varias fases, numéralas y di qué queda utilizable al final de cada una.

## 6. Requisitos funcionales

Un identificador por requisito. Son la unidad de trazabilidad: cada uno se enlaza con al menos un criterio de aceptación y con el test que lo cubre.

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | El sistema debe ... | debe / debería / podría |
| RF-02 | | |

Redacta en voz activa y verificable: «el subcomando `novela X` escribe `<ruta>` con el campo `Y`», no «mejor gestión de Y».

## 7. Requisitos no funcionales

Solo los que este cambio pone en juego. Borra las filas que no apliquen; una tabla de relleno no informa.

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | ej. `novela validar` termina en < 2 s para un capítulo de 4.000 palabras |
| RNF-02 | Consumo de contexto | ej. el briefing de `<rol>` no supera N tokens |
| RNF-03 | Coste / cuota | ej. no añade llamadas a modelo por capítulo |
| RNF-04 | Fiabilidad | comportamiento ante fallo a mitad de escritura; qué deja el checkpoint |
| RNF-05 | Observabilidad | qué score o atributo nuevo aparece en la traza |
| RNF-06 | Compatibilidad | qué pasa con las novelas ya empezadas |
| RNF-07 | Seguridad | claves, rutas fuera del workspace, escritura desde la API |

## 8. Interfaces y contratos

Lo que otro componente puede depender de después de este cambio.

- **CLI**: firma exacta del subcomando, opciones, códigos de salida.
- **API**: método, ruta, modelo de respuesta (`backend/novela/dominio/`), status codes.
- **Esquemas**: ficheros de `backend/schemas/` que se crean o cambian, campo a campo.
- **Contrato de agente**: entradas del briefing, rutas de salida, `tools` permitidas.
- **Ficheros del workspace**: qué se escribe, dónde y en qué orden.

Marca cada uno como **nuevo**, **compatible** o **ruptura**. Una ruptura necesita la sección 10.

## 9. Datos y estado

Cómo afecta a las cuatro ramas de contexto. Una línea por rama, o «sin cambios».

| Rama | Cambio |
|---|---|
| `canon/` | |
| `plan/` | |
| `estado/state.json` | ¿campos nuevos? ¿los escribe `aplicar-delta`? |
| `memoria/` | ¿hay que poder reconstruirla? |

Recuerda: `libro_de_hechos` y `conocimiento` son append-only.

## 10. Migración y compatibilidad

Solo si hay novelas en curso o datos existentes. Qué pasa con ellas, si hace falta un subcomando de migración, y si se puede revertir sin perder trabajo.

Si no aplica: «No aplica: cambio aditivo, las novelas en curso siguen validando.»

## 11. Criterios de aceptación

Cada uno debe ser verificable ejecutando algo, y trazar a un requisito. Se convierten uno a uno en los tests del ciclo TDD; una spec sin criterios verificables no se acepta.

- [ ] **CA-01** (RF-01) `novela ...` con X devuelve Y
- [ ] **CA-02** (RF-02) El esquema Z rechaza un documento sin el campo W
- [ ] **CA-03** (RNF-01) ...

## 12. Trazabilidad

Se rellena durante la implementación. Sin esta tabla no se pasa a `implementada`.

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01 | `backend/tests/test_....py::test_...` | pendiente |

## 13. Verificación

Qué métodos de `docs/validators.md` cubren este cambio y cuáles no.

- Gates de `validate.py` o ramas de `delta.py` tocados → el test es **property-based**, no de ejemplo (`docs/validators.md` §3.6).
- Cambio de prompt de agente → no hay TDD: se valida con una novela de humo de 3 capítulos comparando scores. Di cuál es el baseline.
- **Riesgos aceptados**: lo que queda sin cubrir se nombra aquí; no se omite.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | ¿toca alguno de los 8 de `AGENTS.md`? Si sí, para y pregunta antes de seguir |
| Esquemas | ¿hay que regenerar `backend/schemas/` y actualizar `docs/definitions.md`? |
| Contratos de agente | ¿cambia el frontmatter, las `tools` o la receta de alguno? |
| Docs de referencia | qué secciones de `architecture.md` / `validators.md` quedan desfasadas |
| Frontend | ¿cambia algo que consuma el panel? |

## 15. Alternativas descartadas

Una línea por alternativa y por qué no. Si la decisión es cara de revertir, esto no va aquí: va en un ADR de `docs/adr/`.

## 16. Preguntas abiertas

Lo que bloquea pasar a `aceptada`. Cada una con responsable. Una spec no se acepta con preguntas abiertas: se resuelven en el fichero, no en la conversación.

- [ ] ... — <quién decide>
