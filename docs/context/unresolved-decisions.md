# Unresolved decisions from the spec (volatile)

> Source: `docs/suspense-novel-harness.md` — §17 (lines 1629-1661). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- **Volatile**: the specification's own `[OPEN: ...]` register. Entries disappear as they are answered.
- `[OPEN: stack viability]` — blocking; nothing else starts until phase F0 answers it.
- `[OPEN: models]`, `[OPEN: training permissions]`, `[OPEN: title]`, `[OPEN: initial idea]`, `[OPEN: manuscript destination]`.
- Distinct from `open-questions.md`, which lists gaps found while restructuring the document rather than gaps the author already knew about.
- Load before starting any phase, and before filling in a model identifier or an environment variable.

---

## 17. Open questions

- **[OPEN: stack viability]** — *blocking; resolve before anything else.* It is unconfirmed that
  Claude Code routed to OpenRouter works with third-party `:free` models. OpenRouter guarantees its
  compatibility layer only with first-party Anthropic models (§2, open risk). Phase F0 in §14 exists
  precisely to answer this, and no other phase should begin before it. If the answer is no, one of
  the three ways out in §2 must be chosen, and that choice belongs to the author, not the
  implementer.

- **[OPEN: models]** Which specific `:free` model identifiers to use for each role. OpenRouter's
  free catalogue rotates frequently and cannot be pinned down from this document. The implementer
  must consult the current catalogue and fill in the environment variables in Annex A.4. Note the
  constraint the current binding imposes: Claude Code offers **three model slots** (the high,
  balanced and fast classes), not one per agent, so the five roles share at most three identifiers.
  Selection criteria: for the **Writer**, Spanish prose quality and a
  window of ≥ 32k; for **Evaluator** and **Continuity Editor**, reliability at emitting valid JSON,
  which matters more than literary ability; for the **Architect**, structured reasoning. Before the
  first launch, verify empirically that the Evaluator and Continuity Editor candidates return
  parseable JSON in 10 out of 10 attempts.

- **[OPEN: training permissions]** Confirm that the OpenRouter account has the permissions enabled
  that `:free` endpoints require, and consciously accept the implication described in §2.

- **[OPEN: title]** The novel's title is undecided. The Architect may propose one while generating
  the premise, but it is not specified as a mandatory field.

- **[OPEN: initial idea]** The two- or three-sentence starting idea has not been supplied yet. It is
  the only mandatory human input before Gate 1.

- **[OPEN: manuscript destination]** It has not been stated what happens to the 30 files at the end.
  v1 leaves them in `novel/chapters/`. If a single assembled file or an export is wanted, that is v2
  work and is out of scope today (§2).

