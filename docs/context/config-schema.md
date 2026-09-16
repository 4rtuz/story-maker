# config.json

> Source: `docs/suspense-novel-harness.md` — §6.0 (lines 653-736). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The one file in `novel/` a human writes and the system only reads; every numeric parameter of the whole spec lives here.
- The governing rule: the document explains the numbers, `config.json` fixes them; if they disagree, the file wins.
- The `base` / `perfiles` deep-merge structure, group by group, and how each group maps to a section of the spec.
- Why model identifiers are deliberately absent, and what mutability is allowed (between chapters only).
- The shipped `poc` profile, verbatim. Load before changing any threshold, length, count or budget.

---

### 6.0 `config.json`

Authored by hand before the first run · Written by: **the person** · Read by: the runtime, on every
invocation · **Mutable, but only between chapters.** It is the only file in `novel/` that a human
writes and the system only reads.

**The rule that governs this whole document**: every numeric constant appearing in sections 1 to 17
— 30 chapters, 2,000 words, threshold 4.0, 2 rewrites, 16k tokens — is the default value of the
`completo` profile in this file. **The document explains the numbers; `config.json` fixes them.** If
the two disagree, the file wins and the document has an erratum.

Structure: a `base` section holding every value, and a `perfiles` object where each profile declares
**only what changes**. The active profile is **deep-merged** over `base`. This is what lets the POC
(§15.1) be another profile rather than another codebase.

Note: the shipped file uses Spanish key names, matching the Spanish document (see the translator's
note at the top). The structure below is annotated in English; the keys are the file's.

```json
{
  "version": 1,
  "perfil_activo": "poc",
  "base": {
    "obra":        { language, subgenre, point of view, tense,
                     max POV characters, max characters },
    "capitulos":   { total, target words, word tolerance,
                     min scenes, max scenes },
    "actos":       [ { number, from, to } ],
    "entrevista":  { rounds, max questions per round,
                     min options per question, max options per question },
    "evaluacion":  { scale max, mean threshold, blocking-criterion threshold,
                     blocking criteria, max rewrites, max patches per iteration,
                     behaviour on exhaustion, attempt-selection rule },
    "continuidad": { audit-before-chapter, max chapters a clue may go untouched,
                     five blocking-rule flags from §8.2 },
    "contexto":    { max token budget, tokens per word,
                     chapters kept in full, chapters kept as cards,
                     card word count, act-summary word count,
                     timeline days visible, trim order },
    "puertas":     { plan, act close, final, continuity block },
    "agentes":     { "<role>": { model class, temperature, max tokens, tools } },
    "ejecucion":   { chapters per invocation, commit per chapter,
                     quota: { daily limit, per-minute limit, stop if a chapter
                              does not fit },
                     retries: { max, backoff base seconds, backoff max seconds },
                     truncation: { max retries, word-target reduction,
                                   mandatory end marker },
                     malformed JSON: { max retries },
                     language drift: { max retries } },
    "rutas":       { root, bible, state, chapters, attempts,
                     reports, state file, author notes }
  },
  "perfiles": { "poc": { ...only what changes }, "completo": {} }
}
```

How the groups map to the rest of the document: `obra` and `capitulos` to §2 · `actos` to §3 ·
`entrevista` to §5.1 · `evaluacion` to §9 · `continuidad` to §8 · `contexto` to §7 · `puertas` to
§11 · `agentes` to §5 · `ejecucion` to §12 · `rutas` to this §6.

**What is deliberately NOT here**: the model identifiers. They live in environment variables (Annex
A.4) because they belong to the binding, not the core, and freezing them here would break the
portability of §4.5. `config.json` declares model *classes*; the binding resolves them.

**Mutability**: it can be edited between chapters and the run picks the change up on the next
invocation. Editing it mid-chapter-loop is unsupported and produces undefined behaviour. Changing
`capitulos.total` or `actos` once the novel has started invalidates the approved outline and
requires going back through Gate 1.

**Real example** (the `poc` profile, which ships active):

```json
"poc": {
  "capitulos": { "total": 3, "palabras_objetivo": 60, "tolerancia_palabras": 0.5,
                 "escenas_min": 2, "escenas_max": 2 },
  "actos": [ { "numero": 1, "desde": 1, "hasta": 1 },
             { "numero": 2, "desde": 2, "hasta": 2 },
             { "numero": 3, "desde": 3, "hasta": 3 } ],
  "entrevista":  { "rondas": 1 },
  "evaluacion":  { "umbral_media": 3.0, "umbral_criterio_bloqueante": 3 },
  "continuidad": { "auditoria_antes_de_capitulo": 3, "max_capitulos_pista_sin_tocar": 2 },
  "contexto":    { "capitulos_texto_integro": 1, "capitulos_ficha_completa": 1 }
}
```
