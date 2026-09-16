# Bible artifact schemas

> Source: `docs/suspense-novel-harness.md` — §6.1-6.5 (lines 738-882). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- Markdown schemas for the five planning artifacts, all immutable after Gate 1 except the outline.
- `interview.md`, `premise.md` (≤600 words), `characters.md` (max 8), `voice-and-style.md` (anchor passage).
- `outline.md`: 30 entries under three act headings, with the per-chapter field list including `Pistas relevantes en contexto`.
- Who writes and who reads each file, and each one's mutability.
- Load when generating, validating or revising anything under `novel/bible/`.

---

### 6.1 `bible/interview.md`

Created when the 3 interview rounds finish · Written by: the runtime (from the Architect and the
author) · Read by: the Architect · **Immutable** after Gate 1.

```markdown
# Entrevista de partida

## Idea original
<verbatim, exactly as the author gave it>

## Ronda 1
### P1. <question>
- (A) <option>
- (B) <option>
**Respuesta:** <A|B|free text>
...

## Decisiones no consultadas
<list of decisions the Architect made on its own, and why>
```

### 6.2 `bible/premise.md`

Created during planning · Written by: the Architect · Read by: Writer, Evaluator, Act Editor ·
**Immutable** after Gate 1. Target: ≤ 600 words.

```markdown
# Premisa

## Logline
<one sentence, maximum 40 words>

## Situación de partida
<one paragraph>

## El secreto
<what has actually happened; the truth the reader does not know>

## La revelación
<what is revealed, in which chapter, and to whom>

## Pistas que sostienen la revelación
<at least 3, each with the chapter where it is planted>

## Apuesta temática
<one sentence: what the book is about underneath the plot>

## Final
<one paragraph: how it ends, including the fate of each main character>
```

**Example (fragment):**
```markdown
## Logline
Cuando su marido reaparece tras nueve días desaparecido sin recordar nada, una restauradora de
muebles empieza a sospechar que el hombre que ha vuelto no es exactamente el que se fue.
```

### 6.3 `bible/characters.md`

Written by: the Architect · Read by: Writer, Evaluator, Continuity Editor · **Immutable** after
Gate 1 (the changing *state* lives in `state/character-state.md`). Maximum 8 characters.

```markdown
# Personajes

## <Full name>
- **Rol:** protagonista | antagonista | secundario | figurante recurrente
- **Focalizador:** sí | no
- **Edad y ocupación:**
- **Deseo consciente:** <what they want and believe they want>
- **Necesidad inconsciente:** <what they actually need>
- **Miente sobre:** <what they hide, from whom, and why>
- **Rasgo físico distintivo:** <exactly one, memorable, reusable>
- **Tic verbal o de conducta:** <exactly one>
- **Arco:** <from X to Y, in one sentence>
- **Relaciones:** <name: nature of the bond>
```

### 6.4 `bible/voice-and-style.md`

Written by: the Architect · Read by: the Writer (on **every** call) and the Evaluator ·
**Immutable**. This is the anchor against voice drift, especially when the fallback chain switches
models midway through the novel.

```markdown
# Voz y estilo

## Parámetros fijos
- Persona y tiempo: tercera limitada, pasado
- Focalizadores: <list>
- Longitud media de frase: <corta | media | variada con dominio de la corta>
- Densidad de diálogo: <alta | media | baja>

## Reglas positivas
<5 to 8 actionable rules>

## Reglas negativas
<5 to 8 explicit prohibitions, with examples of what must not be written>

## Pasaje ancla
<200 words of sample prose, written by the Architect, that fix the register>
```

### 6.5 `bible/outline.md`

Written by: the Architect · Read by: the Writer (its own entry ±1 only), Evaluator, Act Editor ·
**Mutable, but only by the Architect and only for chapters not yet written**; every revision appends
a line to `## Cambios`. **This file resolves the ambiguity in the original diagram**: there are not
three files for beginning, middle and end; there is one, with three act headings.

```markdown
# Escaleta

## Acto 1 — Capítulos 1-8

### Capítulo 1
- **Título provisional:**
- **Focalizador:**
- **Día de ficción:** <integer, 0 = start>
- **Localización:**
- **Beats:**
  1. <...>
  2. <...>
  3. <...>
- **Pistas a plantar:** <ids, or "ninguna">
- **Pistas a reforzar:** <ids, or "ninguna">
- **Pistas a resolver:** <ids, or "ninguna">
- **Pistas relevantes en contexto:** <ids the Writer must keep in mind without touching them>
- **Empieza en:** <concrete situation>
- **Termina en:** <the hook>

## Acto 2 — Capítulos 9-22
...

## Acto 3 — Capítulos 23-30
...

## Cambios
- <date> · ch. <N> · <what changed> · <reason>
```

The **Pistas relevantes en contexto** field is the key to §7: it lets the runtime inject five clues
instead of fifty.
