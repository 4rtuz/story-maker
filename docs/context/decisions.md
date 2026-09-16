# Decisions taken and alternatives rejected

> Source: `docs/suspense-novel-harness.md` — §16 (lines 1592-1626). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- Fifteen numbered decisions with the option chosen and the options rejected, each with its reason.
- Marks which four were the author's own and which eleven were applied by default.
- Covers runtime, runtime isolation, orchestration shape, POC-first, config externalisation, tool-less subagents, quota, length, agent count, POV, subgenre, outline shape, state record, two evaluators, models, rubric, exhaustion, correction, human control, granularity.
- Lists the additions that were not in the original diagram.
- Load before proposing a change to an architectural choice, so you do not re-litigate a closed decision.

---

## 16. Decisions taken and alternatives rejected

The first four were decided by the author. The remaining eleven were applied by default, taking the
recommended option, following the author's instruction to resolve unanswered questions that way.

| # | Decision | Chosen | Rejected, and why |
|---|---|---|---|
| 1 | Runtime | **Claude Code: orchestrating skill + one subagent per role, with inference routed to OpenRouter** · *external requirement imposed on the author* | Python script with no framework: this was the previous decision and remains technically superior in quota consumption (a factor of 2.5, §13.3), but it is not available. It is documented as an alternative binding in Annex B.3 in case the requirement is lifted. LangGraph and n8n: rejected before, unchanged. |
| 1b | Runtime isolation | **Agnostic core (§1-17) + binding annex (A) + port contract (B)** · *author's decision* | Writing for Claude Code with a migration note: easier to read today, but the runtime has already changed once in this document's lifetime and the next change would force a full review. Documenting both bindings in full now: the unused one ages without anyone noticing. |
| 1c | Shape of the orchestration | **Orchestrating skill, one chapter per invocation** · *author's decision* | A skill that runs a whole act: early drift propagates across many chapters before you see it, and it also breaks the orchestrating session's context budget (§7.5). Separate per-phase slash commands: they leave state and transitions in the human's hands, which is precisely what the state machine exists to avoid. |
| 1e | First deliverable | **A POC of 3 four-line chapters before the novel** · *author's decision* | Going straight to real chapters: every debug cycle would cost minutes of generation and dozens of requests, and the failures being hunted — state, deltas, attempt promotion, gates — do not depend on text length. The POC exposes them in minutes. |
| 1f | System parameters | **Externalised in `config.json` with mergeable profiles** | Constants in code: would force touching the implementation to switch from POC to full novel, which is exactly what turns a POC into a throwaway prototype. One file per profile: they drift apart as soon as a shared value changes. |
| 1d | Subagent tools | **None: the orchestrator does all I/O** | Giving them `Read` and `Write`: would keep the orchestrating session lighter, but multiplies actual requests by two or three and takes the novel from nine days to over twenty. With quota as the scarce resource, the orchestrating session is protected by limiting work to one chapter per invocation, not by handing out tools. |
| 2 | Quota | **50 req/day** · *author's decision* | — A fact, not a preference. It conditions the whole document. |
| 3 | Length | **30 × 2,000 ≈ 60,000** · *author's decision* | 40 × 2,500: more drift and ~270 calls. 15 × 2,500: would not have exercised the long-stretch problem. |
| 4 | Agents | **5** · *author's decision* | 3 (the original diagram): the Writer would be its own continuity editor, which is the root failure. 7: Test-reader and final style editor do not fit in 50 req/day. |
| 5 | POV and tense | Third limited, 2-3 POV characters, past | First person present: harder to withhold information legitimately, and more fragile against voice drift between models. |
| 6 | Subgenre | Psychological domestic thriller | Police procedural: demands technical detail that free models invent. Conspiracy/action: depends on scale and choreography, their weak points. |
| 7 | Outline | **Single file, 30 entries, 3 act headings** | Three separate files: this was one of the two readings of the original diagram; it describes the shape of the story but not what happens in chapter 17, which is what the Writer needs. One file per act: fragments without gaining anything, since the Writer only loads its own entry ±1. |
| 8 | State record | Chapter card + rolling summary + clues + timeline + character state | A single cumulative summary: grows without structure and loses precisely what needs verifying. Re-reading previous chapters: overflows both context and quota. |
| 9 | Evaluation | **Two evaluators**: quality (subjective) and continuity (objective) | One with a mixed rubric: when "is it well written?" is mixed with "is it true?", the model systematically sacrifices the second. |
| 10 | Models | Different model for Writer than for Evaluator/Continuity | Same model: tends to validate its own text. On the free tier, diversity costs nothing. |
| 11 | Rubric and threshold | 6 criteria × 1-5; mean ≥ 4.0 with 2 blocking ≥ 4; max 2 rewrites | Threshold 4.5 and 4 iterations: free models oscillate without converging and the quota cost is prohibitive. Binary verdict: makes it impossible to pick the best attempt when iterations run out. |
| 12 | On exhausting iterations | Accept the best attempt + narrative debt + continue | Halt and ask: turns a 4-day autonomous run into an interactive session. Silently lowering the threshold: you lose the record of what went wrong. |
| 13 | Correction | Targeted patch by scene, with hash verification | Full rewrite: twice the tokens and regression over text that was already fine. Letting the Evaluator correct: mixes the roles of judge and author, and the voice drifts. |
| 14 | Human control | 3 gates + asynchronous channel | Chapter by chapter: 30 interruptions, incompatible with "minimal human intervention". Zero intervention: an outline error surfaces at chapter 30. |
| 15 | Granularity | Full chapter in one call; scenes only as recovery | Always scene by scene: triples the quota, which is the scarce resource. No truncation control: would put cut-off chapters into the corpus, which then contaminate the context of every chapter that follows. |

### Additions that were not in the original diagram

`state/clues.md`, `state/timeline.md`, `state/character-state.md`, `state/narrative-debt.md`,
`bible/voice-and-style.md`, `bible/outline.md`, the per-chapter cards, `state.json`,
`author-notes.md`, the quota governor, the model fallback chain, and the pre-chapter-30 audit. All
of them are integrated into the flow in §4, not bolted on.

