# Context index — `docs/suspense-novel-harness.md`

Loadable slices of the English specification. **Read this table first and load only the files whose
"Load when" matches the task at hand. Never load `docs/suspense-novel-harness.md` whole.**

Rules for this set:

- The source file is read-only and unchanged. Every one of its sections lands in exactly one file
  below, with nothing duplicated and nothing dropped.
- Section numbers inside these files (`§7`, `Annex A`) are the *source's* numbering. The "Source"
  column maps them.
- Normative sentences, contracts, schemas, field names, figures and code blocks are copied
  literally. Only redundant prose was compressed.
- `conflicts.md` and `open-questions.md` are new: they record what the source contradicts or leaves
  undefined. Nothing was invented to fill a gap.
- Note `conflicts.md` C-07: the repository's canonical spec is the Spanish `harness-novela-suspense.md`
  with a `novela/` tree, so the `novel/` paths throughout this set are the translated spelling.

## Scope

- The routing table: every context file, its one-line scope, and the trigger for loading it.
- The rules this context set follows (one section per file, literal normative text, unresolved gaps kept unresolved).
- A "Common task → files" shortcut table for the seven recurring jobs.
- Load this first, always, and load nothing else until it tells you to.

## Files

| File | Scope (1 line) | Load when… |
|---|---|---|
| [overview.md](overview.md) | §1 + translator's note: what the system is and everything a run produces. | You need orientation, or you are deciding which other file to open. |
| [scope.md](scope.md) | §2: what v1 includes, what it excludes, the privacy limitation and the open stack risk. | Deciding whether something belongs in v1, or the OpenRouter/`:free` stack is in question. |
| [glossary.md](glossary.md) | §3: operational definitions of every narrative and system term. | A term in another file is unclear. |
| [architecture.md](architecture.md) | §4: full flow, the one-chapter cycle, and the core / port / binding layering. | Changing how phases fit together, or working near the core/binding boundary. |
| [agents-overview.md](agents-overview.md) | §5 preamble: conventions shared by the five agents, the no-tools rule, model classes. | Defining or auditing any subagent — read before the per-agent file. |
| [agent-architect.md](agent-architect.md) | §5.1: the Architect's parameters and literal system prompt. | Generating or revising anything under `novel/bible/`. |
| [agent-writer.md](agent-writer.md) | §5.2: the Writer's parameters, literal system prompt, output format and patch mode. | Drafting a chapter or applying a targeted patch. |
| [agent-evaluator.md](agent-evaluator.md) | §5.3: the Evaluator's parameters, literal system prompt and JSON schema. | Scoring a chapter or parsing an evaluation result. |
| [agent-continuity.md](agent-continuity.md) | §5.4: the Continuity Editor's parameters, literal system prompt and delta JSON schema. | Verifying a chapter or applying state deltas. |
| [agent-act-editor.md](agent-act-editor.md) | §5.5: the Act Editor's parameters, literal system prompt and report format. | An act closes. |
| [artifacts-tree.md](artifacts-tree.md) | §6 preamble: the complete `novel/` directory layout. | You need to know where a file lives — the cheapest load in the set. |
| [config-schema.md](config-schema.md) | §6.0: `config.json`, the profile merge, and the rule that the file beats the document. | Changing any threshold, length, count or budget. |
| [artifacts-bible.md](artifacts-bible.md) | §6.1-6.5: schemas for the five planning artifacts, immutable after Gate 1. | Generating or validating anything under `novel/bible/`. |
| [artifacts-state.md](artifacts-state.md) | §6.6-6.12: schemas for every artifact the run mutates while writing. | Applying deltas, regenerating the rolling summary, or logging narrative debt. |
| [context-assembly.md](context-assembly.md) | §7: who sees what, the decreasing-granularity window, clue filtering, the 16k budget. | Touching the context assembler or anything that decides what goes into a prompt. |
| [continuity-rules.md](continuity-rules.md) | §8: the clue life cycle, the five blocking rules, and when each verification runs. | Implementing the deterministic continuity checks or chasing a clue-state bug. |
| [evaluation-loop.md](evaluation-loop.md) | §9: rubric, acceptance condition, rewrite ceiling, exhaustion behaviour, patch verification. | Working on the accept/reject decision, the rewrite loop or patch application. |
| [state-machine.md](state-machine.md) | §10: every state and transition, the `state.json` schema, and the resumption rules. | Implementing persistence, resume, or a new transition. |
| [gates.md](gates.md) | §11: the three gates, the ad hoc block gate, their literal answer options, and the async channel. | Implementing or changing any point where the run stops and waits for a person. |
| [failure-modes.md](failure-modes.md) | §12: every anticipated failure, its detection and its exact response. | Adding error handling or diagnosing a run that stopped unexpectedly. |
| [cost-and-quota.md](cost-and-quota.md) | §13: logical calls, actual requests, the 2.5x binding factor, wall-clock time, POC cost. | Estimating a run, changing the binding, or explaining why the novel takes days. |
| [implementation-phases.md](implementation-phases.md) | §14 (**volatile**): phases F0-F6 with a verifiable done criterion each. | Planning what to build next or checking a phase's exit criterion. |
| [testing.md](testing.md) | §15: the 13 POC checks and the 12 rehearsal checks, with their exit criteria. | Running or extending the acceptance tests for a phase. |
| [decisions.md](decisions.md) | §16: the 15 decisions taken, the alternatives rejected, and why. | Before proposing a change to an architectural choice, so you do not re-litigate a closed one. |
| [unresolved-decisions.md](unresolved-decisions.md) | §17 (**volatile**): the spec's own `[OPEN: ...]` register, verbatim. | Starting any phase, or filling in a model identifier or environment variable. |
| [binding-claude-code.md](binding-claude-code.md) | Annex A: routing, `.claude/` layout, `tools: []`, model slots, the skill's pseudocode, the six ports as built. | Touching anything under `.claude/`, model routing, or the orchestration loop. |
| [port-contract.md](port-contract.md) | Annex B: the six ports, the five checks for a new binding, the unimplemented Python binding. | Writing a new binding, or auditing whether core logic has leaked into this one. |
| [conflicts.md](conflicts.md) | 8 contradictions in the source, both versions recorded, none resolved. | Before implementing anything one of the entries touches — short enough to read whole. |
| [open-questions.md](open-questions.md) | 15 gaps the source leaves undefined, with source references. | Before implementing a section, alongside that section's own file. |

## Common task → files

| Task | Load |
|---|---|
| Write the next chapter | `agents-overview.md`, `agent-writer.md`, `context-assembly.md`, `artifacts-bible.md` (outline entry) |
| Judge and accept a chapter | `agent-evaluator.md`, `agent-continuity.md`, `evaluation-loop.md`, `continuity-rules.md` |
| Apply state after acceptance | `artifacts-state.md`, `continuity-rules.md`, `state-machine.md` |
| Change a number | `config-schema.md`, then the file carrying the section that number appears in |
| Change the runtime | `port-contract.md`, `binding-claude-code.md`, `architecture.md` (§4.5), `cost-and-quota.md` (§13.3) |
| Close an act | `agent-act-editor.md`, `gates.md`, `artifacts-bible.md` (outline revision) |
| Debug a stopped run | `state-machine.md`, `failure-modes.md`, `cost-and-quota.md` |
