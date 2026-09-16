# Evaluation loop

> Source: `docs/suspense-novel-harness.md` — §9 (9.1-9.5) (lines 1153-1204). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The six-criterion rubric, its 1-5 scale, and which two criteria are blocking (9.1).
- The exact acceptance condition combining the Evaluator's scores and the Continuity Editor's verdict (9.2).
- The 2-rewrite ceiling and the reasoning behind it (9.3).
- What happens when iterations are exhausted: best attempt by mean, narrative debt, continue; and the BLOQUEO exception (9.4).
- How a targeted patch is applied and verified by per-scene hash (9.5).
- Load when working on the accept/reject decision, the rewrite loop or patch application.


> SUPERSEDED BY: `config-schema.md` (§6.0), group `evaluacion` — the threshold 4.0, the blocking threshold 4 and the 2-rewrite ceiling are the `completo` defaults; `poc` sets `umbral_media` 3.0 and `umbral_criterio_bloqueante` 3. See `conflicts.md` C-02: the Evaluator's own system prompt hard-codes 4.0.
---

## 9. Evaluation loop

### 9.1 Rubric

Six criteria, integer scale 1-5, defined in the Evaluator's system prompt (§5.3). Two are
**blocking**: `tension` and `escaleta`.

| Score | Meaning |
|---|---|
| 1 | Unacceptable |
| 2 | Poor |
| 3 | Adequate but improvable |
| 4 | Good, publishable |
| 5 | Excellent |

### 9.2 Acceptance condition

A chapter is accepted if and only if **both** conditions hold:

```
Evaluator:  media >= 4.0  AND  tension >= 4  AND  escaleta >= 4
Continuity: veredicto == "OK"
```

### 9.3 Maximum iterations

**2 rewrites.** The reasoning: two passes capture nearly all the real improvement; from the third
onward free models tend to oscillate between versions without converging, and each pass costs three
calls (patch + re-evaluation + re-verification) out of a budget of 50 per day.

### 9.4 Behaviour when they are exhausted

1. The attempt with the **highest mean** is selected, not necessarily the last one; a rewrite can
   make a chapter worse.
2. That attempt is accepted and committed.
3. An entry is appended to `state/narrative-debt.md` with the failed criterion, the problem, and the
   correction that was proposed and not applied.
4. Execution **continues**. The system never halts because one isolated chapter is not good enough.

The exception: if the Continuity Editor returns `BLOQUEO` — a contradiction that would require
touching already-accepted chapters — this rule does not apply. State is persisted, an ad hoc human
gate is opened, and execution halts.

### 9.5 Applying the patch

The Writer receives the full chapter plus a `PARCHES SOLICITADOS` block that merges the Evaluator's
patches and the Continuity Editor's contradictions, grouped by scene. It returns the complete
chapter with the unflagged scenes copied over literally. The runtime **verifies** that the unflagged
scenes have not changed, by comparing hashes; if the model altered them, the originals are restored
and only the patched scenes are kept. This check is cheap and prevents silent regression, which is
the characteristic failure of rewrite loops.

