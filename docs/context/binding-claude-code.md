# Binding: Claude Code over OpenRouter (Annex A)

> Source: `docs/suspense-novel-harness.md` — Annex A (A.1-A.6) (lines 1664-1846). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The only part of the spec that is rewritten if the runtime changes; everything in §1-17 is independent of it.
- Environment variables that route Claude Code to OpenRouter, and the three common causes of silent failure (A.1).
- The `.claude/` file layout and the subagent frontmatter template, with `tools: []` as the single most important line (A.2, A.3).
- The three model slots, the class-to-slot-to-identifier mapping, and the fallback chain (A.4).
- The orchestrating skill's pseudocode, step by step, and which steps must stay deterministic (A.5); the six ports as implemented here (A.6).
- Load when touching anything under `.claude/`, model routing, or the orchestration loop.

---

# Annex A — Runtime binding: Claude Code over OpenRouter

This annex is **the only part of the document that has to be rewritten if the runtime changes**.
Everything above it is independent of the runtime.

## A.1 Routing Claude Code to OpenRouter

Claude Code speaks Anthropic's Messages format. OpenRouter exposes a compatibility layer for that
format, so **no local gateway is needed**: no proxy, no Docker, no listening port. It is enough to
point Claude Code at the OpenRouter endpoint.

```bash
export OPENROUTER_API_KEY="<your OpenRouter key>"
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=""
```

Three details that are common causes of silent failure:

- `OPENROUTER_API_KEY` must be defined **before** `ANTHROPIC_AUTH_TOKEN`, or the expansion comes out
  empty and authentication falls back to a path that was not intended.
- `ANTHROPIC_API_KEY` must be an **empty string, not left undefined**. If left undefined, Claude
  Code may authenticate against Anthropic and the run will work without touching OpenRouter at all,
  which is the exact opposite of the requirement.
- Verify with `/status` inside Claude Code that routing points at OpenRouter, and cross-check
  against the OpenRouter activity dashboard. A session answering is not proof that it is routed.

These variables belong in `.claude/settings.local.json` or in the shell profile.
**`.claude/settings.local.json` must not be committed**: it holds the key.

## A.2 Binding file layout

```
.claude/
├── settings.local.json          # variables from A.1 — NOT version-controlled
├── agents/
│   ├── architect.md
│   ├── writer.md
│   ├── evaluator.md
│   ├── continuity.md
│   └── act-editor.md
└── skills/
    └── novel/
        └── SKILL.md             # orchestrating skill
```

Each file under `agents/` carries, as its body, the **literal system prompt** of the corresponding
agent from §5, copied unmodified. The annex does not rewrite the prompts: it references them.

## A.3 Defining a subagent

Template, with the Writer as the example. The other four are identical in shape and differ in name,
description, model class and body.

```markdown
---
name: writer
description: Writes the draft of one novel chapter from the assembled context it is given.
  Returns only the chapter text with scene markers.
tools: []
model: opus
---

<here goes, literal and complete, the system prompt from §5.2>
```

**`tools: []` is the single most important line in this annex.** A tool-less subagent resolves its
task in one turn and costs one request; one with `Read` and `Write` enters a tool loop and costs
between three and six. Under the 50-requests-per-day cap, that difference decides whether the novel
takes nine days or more than twenty (§13.3).

The trade-off is that **the orchestrator must pass it all the context in the prompt**, since the
subagent cannot read files. That is exactly what the assembler in §7 does, and it is why the 16k
token budget in §7.4 is a requirement and not a recommendation.

> `[OPEN: exact syntax]` Confirm against the installed version of Claude Code the exact way to
> declare a tool-less subagent: whether `tools: []` is valid syntax or whether the field must be
> omitted and restricted another way. The design intent — zero tools — does not change; only how it
> is written. Verifiable in a minute during phase F0.

## A.4 Model classes and identifiers

Claude Code does not allow an arbitrary identifier per subagent: it offers **three slots**, selected
by each agent's frontmatter with `model: opus | sonnet | haiku`, plus one slot specific to
subagents. Slots resolve to OpenRouter identifiers through environment variables.

```bash
export ANTHROPIC_DEFAULT_OPUS_MODEL="<id of the high-capability model>"
export ANTHROPIC_DEFAULT_SONNET_MODEL="<id of the balanced model>"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="<id of the fast model>"
export CLAUDE_CODE_SUBAGENT_MODEL="<default id for subagents>"
```

Mapping between the core's roles and the slots:

| Role (§5) | Declared class | Slot | Identifier |
|---|---|---|---|
| Architect | high-capability | `opus` | `[OPEN: models]` |
| Writer | high-capability | `opus` | `[OPEN: models]` |
| Evaluator | balanced | `sonnet` | `[OPEN: models]` |
| Continuity Editor | balanced | `sonnet` | `[OPEN: models]` |
| Act Editor | high-capability | `opus` | `[OPEN: models]` |

The §5.2 requirement — that Writer and Evaluator not share a model — is met because they fall into
different slots. It would *not* be met if someone pointed all three slots at the same identifier,
which the configuration permits and which must be explicitly avoided.

**Limitation inherited from the binding**: Architect, Writer and Act Editor share a slot and
therefore an identifier. The core neither requires nor forbids this; it is a consequence of there
being only three slots. If separating them ever mattered, the binding would have to change.

The fallback chain of §12 is implemented by reassigning the relevant environment variable and
resuming: since state lives on disk and stores no identifiers (§10.1), switching model mid-novel
requires nothing else.

## A.5 The orchestrating skill

It lives in `.claude/skills/novel/SKILL.md` and is invoked from the main session. It is the only
component that launches subagents, because **a subagent cannot launch another**: the loop has to
live in the main session, and that is a runtime constraint, not a design preference.

Each invocation **writes exactly one chapter and stops** (§7.5). State lives in `novel/state.json`,
never in the conversation.

The body of the skill, in pseudocode. This is not code to copy: it is the order of operations the
skill must describe in prose for whichever agent executes it.

```
1.  state = read(novel/state.json)
2.  if state.state is a GATE_*: present the gate to the human (§11) and stop.
3.  if quota_exhausted(state): report and stop. Do not start a chapter that does not fit.
4.  N = state.current_chapter
5.  context = assemble_context(N)             # rules in §7; max budget 16k tokens
6.  draft = subagent("writer", context)
7.  save(novel/.attempts/NN-i0.md, draft)
8.  evaluation = subagent("evaluator",  draft + outline entry + voice-and-style)
    continuity = subagent("continuity", draft + filtered state)
9.  if both approve -> go to 13
10. if iterations remain:
        patches = merge(evaluation.patches, continuity.contradictions)
        draft = subagent("writer", draft + patches)
        verify_hashes_of_unpatched_scenes()          # §9.5
        go back to 8
11. if iterations exhausted:
        draft = best_attempt_by_mean()               # §9.4
        log in novel/state/narrative-debt.md
12. if continuity.verdict == "BLOQUEO": open the block gate (§11) and stop.
13. promote draft to novel/chapters/NN-chapter.md
14. apply continuity.deltas to clues, timeline, character-state
15. write novel/chapters/NN-card.md
16. regenerate novel/state/rolling-summary.md        # deterministic, no LLM
17. move applied notes in novel/author-notes.md
18. git commit -m "feat(novel): chapter NN — <title>"
19. state.current_chapter = N + 1; persist state.json
20. if N was an act boundary: run subagent("act-editor") and leave state at GATE_ACT
21. if N == 29: run the final audit of §8.3 before allowing chapter 30
```

Steps 5, 14, 16 and 21 are **deterministic and must not be delegated to a subagent**: they are file
manipulation and rule checking, not judgement. Delegating them would burn quota and add a source of
hallucination where there is none today.

## A.6 The six ports in this binding

| Port (Annex B) | Implementation in Claude Code |
|---|---|
| **P1 invoke** | The `Agent` tool over the subagents in `.claude/agents/`, tool-less |
| **P2 artifacts** | The orchestrating session's `Read` and `Write` tools |
| **P3 state** | `Write` over `novel/state.json`, full rewrite after every transition |
| **P4 human** | The Claude Code conversation itself: the skill presents the gate and ends its turn |
| **P5 version** | `Bash` with `git commit` |
| **P6 budget** | Counter in `state.json` plus the OpenRouter activity dashboard as a cross-check |

Port **P4 is the one that gains most from this runtime**: in a script you would have to build a
console dialogue, whereas here a gate is simply the end of a turn, with the human already present
and able to answer in natural language instead of with a fixed command.

Port **P6 is the one that fares worst**: the counter in `state.json` counts logical calls, but quota
is spent in requests, and the orchestrator has no direct visibility of how many requests its own
loop has consumed. That is why §15 requires cross-checking against the OpenRouter dashboard during
the 3-chapter rehearsal, rather than trusting the internal counter.

