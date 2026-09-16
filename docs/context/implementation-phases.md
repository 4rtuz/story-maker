# Phased implementation plan (volatile)

> Source: `docs/suspense-novel-harness.md` — §14 (lines 1482-1494). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- **Volatile**: this is a roadmap, not a contract. It changes as phases complete.
- Phases F0 to F6 with a verifiable "done" criterion for each.
- F0 (stack viability) blocks everything else; F5 closes on the POC passing twice in a row.
- Load when planning what to build next or checking whether a phase's exit criterion is met.

---

## 14. Phased implementation plan

| Phase | Contents | Verifiable "done" criterion |
|---|---|---|
| **F0 — Stack viability** | Point Claude Code at OpenRouter (Annex A.1) and test the candidate `:free` models. **Nothing else starts until this phase passes.** | A Claude Code session routed to OpenRouter answers correctly; `/status` confirms the routing. A tool-less test subagent returns valid JSON 10 times out of 10. The OpenRouter dashboard records the requests. On failure, apply one of the three ways out in §2 **before** going any further. |
| **F1 — Skeleton** | Structure of `.claude/agents/` and `.claude/skills/`, minimal orchestrating skill, atomic `state.json`, quota governor, status and resume commands. | Invoking the skill prints the current state. A test invocation increments `calls_today` in `state.json`. Closing Claude Code halfway and opening a new session resumes from persisted state. A simulated 429 produces a wait and a retry. |
| **F2 — Planning** | Architect subagent, 3-round interview, generation of the four artifacts, schema validators, Gate 1. | Starting from a 3-line idea, the four artifacts are produced, all four pass their schema validators, the outline has exactly 30 entries with no empty fields, and execution halts at `GATE_PLAN`. |
| **F3 — Writing** | Context assembler (§7), Writer subagent, truncation detection, scene-level recovery, commit per chapter. | `01-chapter.md` is generated at 1,700-2,300 words, with scene markers and `<!-- FIN -->`, in third person past tense. The assembler reports an input budget under 16k tokens. The cycle consumes ~10 requests, not ~25: if it consumes ~25, some subagent is using tools. |
| **F4 — Quality** | Evaluator and Continuity Editor subagents, delta application, targeted patch with hash verification, narrative debt, deterministic blocking rules. | With a contradiction injected by hand into a chapter (e.g. changing the colour of an already-established object), the Continuity Editor detects it and the patch fixes it within 2 iterations without altering the unflagged scenes. A deliberately bad chapter exhausts its iterations and appears in `narrative-debt.md`. |
| **F5 — Acts and closing** | Act Editor subagent, Gates 2 and 3, outline revision, final audit, `author-notes.md`. | **The POC in §15.1 passes in full, twice in a row.** This is the milestone that closes the first deliverable version: from here on, the machine is proven. |
| **F5b — Real rehearsal** | No new functionality: just switch `perfil_activo` to `completo`. | The real-chapter rehearsal in §15.2 passes in full, and the probabilities in §13.1 are recalibrated against observed data. |
| **F6 — Closing the port contract** | Verify that no core logic has leaked into the binding. | Each of the six functions in Annex B has exactly one implementation site in the binding. Searching the core artifacts for "Claude Code", "OpenRouter" and any model identifier: zero hits outside the annexes. |

