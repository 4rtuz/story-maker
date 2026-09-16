# Context assembly

> Source: `docs/suspense-novel-harness.md` — §7 (7.1-7.5) (lines 1012-1102). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The matrix of what each of the five agents sees, block by block (7.1).
- The decreasing-granularity window: full text, then card, then one line, then one paragraph per act (7.2).
- Clue filtering: the Writer gets only its own entry's clue ids; the Continuity Editor gets every unresolved clue (7.3).
- The worst-case token budget at chapter 30, the 16,000-token design target and the trim order when it is exceeded (7.4).
- The orchestrating session's own context budget and the "one invocation = one chapter" rule (7.5).
- Load before touching the context assembler or anything that decides what goes into a prompt.


> SUPERSEDED BY: `config-schema.md` (§6.0), group `contexto` — the budget and window sizes here (16,000 tokens, 1.5 tokens/word, N-1/N-2 in full, N-3..N-6 as cards) are the `completo` defaults; `poc` overrides `capitulos_texto_integro` and `capitulos_ficha_completa` to 1.
---

## 7. Context management

### 7.1 What each agent sees

| Block | Architect | Writer | Evaluator | Continuity | Act Editor |
|---|:--:|:--:|:--:|:--:|:--:|
| System prompt | ✓ | ✓ | ✓ | ✓ | ✓ |
| `premise.md` | ✓ | ✓ | — | — | ✓ |
| `characters.md` | ✓ | present only | — | present only | — |
| `voice-and-style.md` | ✓ | ✓ | ✓ | — | — |
| `outline.md` | ✓ (full) | entry N ±1 | entry N | entry N | full act |
| Full text of ch. N-1, N-2 | — | ✓ | — | ✓ (N only) | — |
| Cards of ch. N-6..N-3 | — | ✓ | — | ✓ | full act |
| Rolling summary | ✓ | ✓ | — | ✓ | — |
| `clues.md` | ✓ (full) | filtered | — | filtered | ✓ (full) |
| `timeline.md` | — | last 7 days | — | ✓ | ✓ |
| `character-state.md` | — | present only | — | ✓ | — |
| `author-notes.md` | ✓ | ✓ | — | — | ✓ |
| The chapter under judgement | — | — | ✓ | ✓ | — |

**Permanent** for the Writer: system prompt, premise, voice and style. **Rotating**: everything
else, reassembled by the runtime for every chapter.

### 7.2 Decreasing-granularity strategy

The memory of what has been written degrades with distance; it is not truncated:

| Distance from the current chapter | What the Writer receives |
|---|---|
| N-1, N-2 | Full text |
| N-3 to N-6 | Full card (120 words) |
| N-7 and earlier within the current act | First sentence of the card |
| Acts already closed | One 150-word paragraph per act |

### 7.3 Clue filtering

The Writer **never** receives the full ledger. It receives only the clues whose ids appear in the
*Pistas a plantar / reforzar / resolver / relevantes en contexto* fields of its own outline entry.
In practice that is between 4 and 8 out of a total that will eventually approach 40. This is what
stops the context from growing with the chapter number. The Continuity Editor, by contrast, receives
every clue whose state is neither RESUELTA nor DESACTIVADA, because its job is precisely to catch
what the Writer did not have in front of it.

### 7.4 Token budget at chapter 30

Estimated at 1.5 tokens per Spanish word. This is the worst case of the entire run.

| Block | Tokens |
|---|--:|
| Writer system prompt | 900 |
| `premise.md` | 400 |
| `characters.md`, filtered to the 4 present | 900 |
| `voice-and-style.md` including the anchor passage | 700 |
| Outline, entries 29-31 | 600 |
| Filtered clues (6 of ~40) | 400 |
| State of the 4 characters present | 500 |
| Timeline, last 7 story days | 300 |
| Chapters 28 and 29 in full | 6,000 |
| Cards for chapters 24-27 | 720 |
| One line per chapter from 23 onward in the act | 200 |
| Summaries of acts 1 and 2 | 450 |
| `author-notes.md` | 200 |
| **Total input** | **~12,270** |
| Output (2,000 words) | ~3,000 |
| **Window required** | **~15,300** |

**Verifiable design target: the Writer's input never exceeds 16,000 tokens, at chapter 3 or at
chapter 30.** The practical consequence is that the system runs on any `:free` model with a 32k
window, not only on the large-window ones — which matters a great deal, because the free model
catalogue rotates and no single model can be depended upon. The runtime must check this budget
before every call and, if it is exceeded, trim in this order: timeline → old cards → full text of
N-2.

### 7.5 The orchestrator's context

With a conversational-agent runtime — Claude Code today, perhaps something else tomorrow — there is
a second window to watch besides the Writer's: **the orchestrating session's own**, which
accumulates everything that passes through it. Because the subagents have no tools, the orchestrator
reads the files and passes their contents along, so chapter text crosses its context twice: once
outbound and once inbound.

Per chapter that comes to roughly 12k tokens of assembled input plus about 3k of draft, plus the
Evaluator's and Continuity Editor's reports: on the order of **35k session tokens per chapter**,
counting a full cycle with one patch. Perfectly manageable for one chapter and plainly unmanageable
for thirty in a row.

Hence the operating rule: **one invocation of the orchestrating skill writes exactly one chapter and
then stops**. State lives in `state.json`, not in the conversation, so the next session starts
clean. This rule is what keeps §7.4 sufficient: without it, the Writer's 16k budget would be
correctly computed and the system would still blow up on the other side.

