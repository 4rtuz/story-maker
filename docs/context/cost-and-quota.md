# Cost, quota and wall-clock time

> Source: `docs/suspense-novel-harness.md` — §13 (13.1-13.5) (lines 1377-1479). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The stated assumptions behind every number here, including the first-pass approval probabilities to be recalibrated (13.1).
- Logical calls per chapter and per phase — runtime-agnostic, ~162 for the full novel (13.2).
- Actual OpenRouter requests under the Claude Code binding, the 2.5x conversion factor, ~410 total (13.3).
- Wall-clock time (~9 days) and the three levers that reduce it (13.4).
- The POC's request cost and why a single pass does not fit in one 50-request day (13.5).
- Load when estimating a run, changing the binding, or explaining why the novel takes days.

---

## 13. Cost and performance

This section has two levels. The first, **logical calls**, is part of the core and does not change
if the runtime changes. The second, **actual requests**, depends on the binding and must be redone
every time the runtime changes.

### 13.1 Stated assumptions

- 30 chapters, 2,000 words per chapter, 1.5 tokens per word.
- Probability of first-pass approval: **0.5**. With one rewrite: **0.4**. With two: **0.1**. These
  are starting estimates; they must be recalibrated after the 3-chapter rehearsal (§15).
- Continuity verification and state extraction go in **a single call** (§5.4).
- The rolling summary is regenerated **with no LLM call**.
- Quota: 50 requests/day, 20/minute. Monetary cost: **€0**, if the `:free` models turn out to be
  viable (§2, open risk).

### 13.2 Logical calls (runtime-agnostic)

| Path | Probability | Calls | Breakdown |
|---|--:|--:|---|
| Approved first time | 0.5 | 3 | writer + evaluator + continuity |
| One rewrite | 0.4 | 6 | 3 + patch + evaluator + continuity |
| Two rewrites | 0.1 | 9 | 3 + 2 × (patch + evaluator + continuity) |
| **Expected value per chapter** | | **4.8** | 0.5·3 + 0.4·6 + 0.1·9 |

| Phase | Logical calls |
|---|--:|
| Interview (3 rounds) | 3 |
| Premise + characters + voice | 3 |
| Outline (one per act) | 3 |
| Adjustments after Gate 1 | 3 |
| 30 chapters × 4.8 | 144 |
| Act Editor (3 acts, with margin) | 4 |
| Outline revisions at act gates | 2 |
| **Total** | **~162** |

### 13.3 Actual requests in the Claude Code binding

This is where the runtime change hurts, and it is worth saying plainly: **in Claude Code a logical
call does not cost one request.** The orchestrating session is itself an agent, and every turn of
its own — deciding what to do, invoking a subagent, processing what comes back, writing a file — is
a request against OpenRouter. A subagent is its own session with its own loop.

Conversion factors, with subagents that have **no tools** (Annex A.3):

| Item | Requests | Why |
|---|--:|---|
| One logical call to a subagent | 1 | With no tools, it resolves in one turn |
| Orchestrator turns per chapter | 6 to 8 | Read state, assemble context, dispatch three subagents, apply deltas, write card and summary, commit |
| **Cycle of a chapter approved first time** | **~10** | 3 subagents + ~7 orchestration turns |
| **Cycle with one rewrite** | **~15** | 6 subagents + ~9 turns |
| **Expected value per chapter** | **~12** | against 4.8 logical calls: **a factor of 2.5** |

| Phase | Actual requests |
|---|--:|
| Full planning (12 logical calls) | ~30 |
| 30 chapters × 12 | ~360 |
| Act editors and outline revisions | ~20 |
| **Total** | **~410** |

### 13.4 Wall-clock time

**410 / 50 ≈ 9 calendar days**, against 4 in the previous design. The novel has not changed; what
it costs to execute has. The three levers for bringing that number down, in order of effectiveness:

1. **Tool-less subagents** (already assumed by the design). Giving them `Read` and `Write` would
   multiply requests by two or three and push the novel past twenty days. It is the single
   highest-impact decision in the whole binding.
2. **Do not chain chapters within one session.** Besides protecting the context (§7.5), it avoids
   redundant orchestration turns.
3. **Load $10 of credit on OpenRouter**, which raises the cap from 50 to 1,000 requests a day and
   cuts wall-clock time from nine days to under one. It is by far the cheapest way to buy speed in
   this system, and worth bearing in mind before optimising anything else.

The 20 requests-per-minute limit is still not binding: what dominates is the latency of generating
long chapters.

### 13.5 Cost of the POC

The `poc` profile (§6.0, §15.1) does not make requests cheaper, only tokens: a 60-word chapter costs
the same orchestration turns as a 2,000-word one.

| Phase | Requests |
|---|--:|
| Reduced planning (1 interview round, 3 outline entries) | ~12 |
| 3 chapters × ~12 | ~36 |
| 3 act editors and 3 gates | ~10 |
| **Total per POC pass** | **~58** |

**And here is the practical problem**: under the 50-requests-per-day cap, **a single POC pass does
not fit in one day**, and the exit criterion in §15.1 requires two passes in a row. That means three
to four days just to validate the machine, before a single line of real novel is written.

A POC you can only run every other day is not a POC. **This is the moment where loading the $10 of
OpenRouter credit pays for itself** (see lever 3 in §13.4): it raises the cap to 1,000 requests a day
and turns the POC into something you run several times in an afternoon.

**Design consequence**: writing the novel takes several calendar days by construction, not through
inefficiency. That is why persistence and resumption (§10) are v1 requirements and not a later
improvement. Under the current binding that statement is more true than before, not less.

