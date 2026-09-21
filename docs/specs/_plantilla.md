---
spec: NNNN
titulo: ""
estado: borrador          # borrador | aceptada | implementada | descartada
autor: ""
fecha: AAAA-MM-DD
afecta: []                # backend | frontend | agentes | esquemas | docs
commit: null              # sha, al pasar a implementada
---

# NNNN — <título>

## Problema

Qué no funciona o qué falta hoy. Sin solución todavía. Si no puedes escribir esto en tres frases, el problema no está claro y la spec es prematura.

## Propuesta

Qué se va a hacer. Concreto: rutas de fichero, nombres de subcomando, forma del JSON.

## Criterios de aceptación

Cada uno debe ser verificable ejecutando algo. Se convierten uno a uno en los tests del ciclo TDD; una spec sin criterios verificables no se acepta.

- [ ] `novela ...` con X devuelve Y
- [ ] El esquema Z rechaza un documento sin el campo W
- [ ] ...

## Impacto

| Área | Cambio |
|---|---|
| Invariantes | ¿toca alguno de los 8 de AGENTS.md? Si sí, para y pregunta antes de seguir |
| Esquemas | ¿hay que regenerar `backend/schemas/` y actualizar `docs/definitions.md`? |
| Contratos de agente | ¿cambia el frontmatter, las `tools` o la receta de alguno? |
| Docs de referencia | qué secciones de `architecture.md` / `validators.md` quedan desfasadas |

## Verificación

Qué métodos de `docs/validators.md` cubren este cambio, y qué queda sin cubrir. Lo no cubierto se nombra aquí; no se omite.

## Alternativas descartadas

Una línea por alternativa y por qué no. Si la decisión es cara de revertir, esto no va aquí: va en un ADR de `docs/adr/`.
