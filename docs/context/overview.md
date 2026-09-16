# Overview

> Source: `docs/suspense-novel-harness.md` — title block, translator's note, §1 (lines 1-41). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- What the system is: five LLM agents writing a 30-chapter Spanish psychological domestic suspense novel from a 2-3 sentence idea.
- The list of everything the run produces (manuscript, bible, state artifacts, cards, `state.json`).
- The translator's note: this English file is a translation; the novel itself stays Spanish; paths were translated too (`novel/` vs `novela/`).
- Load when you need orientation, or when deciding which other context file to open.

---

# Multi-agent harness for a suspense novel — Specification v1

> Single source of truth. Any implementation decision not covered here is flagged as
> `[OPEN: ...]` in section 17.

> **Translator's note.** This document is an English translation of
> `docs/harness-novela-suspense.md`. Both describe the same system. Three things to know before you
> build from this version:
> 1. **The novel itself is still written in Spanish.** That is a product decision, not a
>    translation artifact, and it is why the agent prompts below ask for Spanish output.
> 2. **The five system prompts have been translated.** Driving Spanish prose from English
>    instructions is viable and often improves instruction-following, but it raises the
>    language-drift risk documented in §12. If you hit drift on free models, take the system
>    prompts verbatim from the Spanish document instead; nothing else in the design changes.
> 3. **File paths and identifiers have been translated too** (`novel/` rather than `novela/`, and
>    so on). Pick one document as canonical for a given project so you do not end up maintaining
>    two directory trees.

---

## 1. Executive summary

The system orchestrates five LLM agents — reached through the OpenRouter API on its free tier — to
write a psychological domestic suspense novel of roughly 60,000 words across 30 chapters, starting
from a two- or three-sentence idea supplied by a person. The v1 orchestration runtime is **Claude
Code**, with a skill driving the cycle and one subagent per role, but the design does not depend on
that choice: sections 1 to 17 are runtime-agnostic and talk to the runtime through the six ports of
Annex B, so replacing it means writing a new annex (§4.5). The system
interviews that person to sharpen the idea, builds a story bible and a chapter-by-chapter outline,
and then writes the chapters in order; each chapter passes through a literary quality evaluator and
through a continuity editor that checks it against an accumulating record of facts, clues, timeline
and character state. A chapter is accepted only when it clears a numeric threshold; if it still
fails after two rewrites, the best attempt is accepted and its defects are logged as narrative
debt. The person intervenes at three approval gates only: after the plan, at the close of each act,
and when the novel is finished.

**It produces**: the manuscript (`novel/chapters/NN-chapter.md`, 30 files), the story bible
(premise, characters, voice and style, outline), the state artifacts that hold it together (rolling
summary, clue ledger, timeline, character state, narrative debt), one card per written chapter, and
an execution state file (`novel/state.json`) that allows the process to resume from any point.

