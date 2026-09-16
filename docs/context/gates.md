# Human control points

> Source: `docs/suspense-novel-harness.md` — §11 (lines 1307-1350). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- Gate 1 (plan approval): when it fires, what is printed, and the literal `approve` / `redo` / `edit` answers.
- Gate 2 (act close): fires after chapters 8, 22 and 30; the `continue` / `adjust` / `adjust : <instruction>` / `stop` answers.
- Gate 3 (final delivery) and the ad hoc block gate opened on a `BLOQUEO` verdict, with `force` / `rewrite` / `stop`.
- The asynchronous channel (`author-notes.md`) that corrects course without halting the run.
- Load when implementing or changing any point where the run stops and waits for a person.

---

## 11. Human control points

Three synchronous gates plus one asynchronous channel. Outside them, the system moves on its own.

### Gate 1 — Plan approval
**When**: after the four bible artifacts are generated. **Why here**: it is the only moment at which
a correction costs one call rather than thirty chapters.

The system prints the premise, the character list with each character's lie, the anchor passage and
the 30 outline entries in condensed form (title, POV character, hook), then asks literally:

> Do you approve the plan? Answer with one of these:
> - `approve` — state is initialised and chapter 1 begins.
> - `redo <artifact> : <instruction>` — only that artifact is regenerated.
> - `edit` — the run pauses so you can edit the files by hand; on resume they are validated against
>   their schemas.

### Gate 2 — Act close
**When**: after chapters 8, 22 and 30. The Act Editor's report and the state of the clue ledger are
shown.

> Act <N> report. Editor's recommendation: <...>
> - `continue` — proceed with the outline as it stands.
> - `adjust` — the Architect revises the outline for the remaining chapters, applying the report.
> - `adjust : <instruction>` — the same, plus your instruction.
> - `stop` — state is persisted and the process exits.

### Gate 3 — Final delivery
**When**: after chapter 30 and the audit in §8.3. The audit result, the full contents of
`narrative-debt.md` and the run statistics are shown.

### Block gate (ad hoc)
Opened only when the Continuity Editor returns `BLOQUEO`. The contradiction and its evidence are
shown:

> Irresolvable contradiction in chapter <N>: <...>
> - `force` — the chapter is accepted and the contradiction is logged as debt.
> - `rewrite : <instruction>` — it goes back to the Writer with your instruction.
> - `stop` — state is persisted and the process exits.

### Asynchronous channel
`novel/author-notes.md` is read at the start of every chapter. It lets you correct course without
halting the run or waiting for a gate.

