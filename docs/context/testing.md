# How to test it

> Source: `docs/suspense-novel-harness.md` — §15 (15.1-15.2) (lines 1497-1589). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The two testing levels and why the POC must come before the real-chapter rehearsal.
- POC (15.1): 3 chapters of ~60 words, 13 numbered checks, what it validates and explicitly what it does not.
- The POC exit criterion: all thirteen checks pass and the whole run passes twice in a row unchanged.
- Rehearsal (15.2): 3 real chapters, 12 checks grouped by plan / text / state / loop / operation, plus probability recalibration.
- Load when running or extending the acceptance tests for a phase.

---

## 15. How to test it

There are **two levels of testing, in this order**. First the POC, which validates that the machine
works. Then the rehearsal with real chapters, which validates that what it writes can be read.
Skipping the first to get to the second is the classic mistake: you end up debugging the context
assembler at ten minutes per chapter.

### 15.1 POC — 3 chapters of 4 lines

Run with `perfil_activo: "poc"` in `config.json` (§6.0). Three chapters of about 60 words, two
scenes each, and **one act per chapter**, so that all three act gates fire across three chapters
instead of thirty.

**What it validates**: the machine. State, gates, resumption, delta application, ledger updates,
rolling-summary regeneration, attempt promotion, the patch loop, quota accounting, commits.

**What it does NOT validate, and worth being clear about so you draw no false conclusions**:
literary quality. At 60 words there is no pacing, no tension and no prose to judge, which is why the
profile lowers the threshold from 4.0 to 3.0. **Evaluator scores in POC mode are not a quality
signal**: their only job here is to push the machine down both branches of the loop. It also does
not validate the context budget of §7.4, which only comes under strain with real chapters.

Checks, all verifiable in minutes:

1. The outline has exactly 3 entries and no empty fields. Execution halts at `GATE_PLAN` and does
   not advance until you answer.
2. Chapter 1 comes out with 2 scenes, `<!-- ESCENA n -->` and `<!-- FIN -->` markers, between 30 and
   90 words, in third person past tense.
3. The draft appears in `novel/.attempts/01-i0.md` and **not** in `novel/chapters/`. Only on
   approval is it promoted.
4. On acceptance, `01-card.md` is created, `clues.md`, `timeline.md` and `character-state.md` are
   updated, and `rolling-summary.md` is regenerated.
5. There is one git commit per accepted chapter, and `.attempts/` never appears in history.
6. **Force a second iteration**: temporarily raise `umbral_media` to 5.0. `01-i1.md` must be
   generated, and the unflagged scenes must be byte-for-byte identical to those in `01-i0.md`.
7. **Force exhaustion**: with the threshold at 5.0, the chapter must be accepted using the
   highest-mean attempt and appear in `narrative-debt.md`.
8. Finishing chapter 1 triggers the Act Editor and halts execution at `GATE_ACT`. Same after 2 and
   3.
9. **Inject a contradiction** into chapter 3 by hand: change an object already established in
   chapter 1. The Continuity Editor must catch it and the patch must fix it.
10. **Leave a red herring undefused**: the audit before chapter 3 must halt execution rather than
    write it.
11. **Close Claude Code midway through chapter 2** and resume in a new session: it continues without
    duplicating work and with a correct quota counter.
12. In chapter 3, the Writer's context includes chapter 2 in full and chapter 1 as a card, not both
    in full. This is what proves the sliding window of §7.2 actually slides.
13. **Count the actual requests** in the OpenRouter dashboard and compare against §13.5.

**Exit criterion**: all thirteen points pass **and** the whole POC has run twice in a row without
changing anything. A POC that only works the first time has validated nothing.

### 15.2 Rehearsal with 3 real chapters

Only after the POC. Run with `perfil_activo: "completo"` and `capitulos.total` temporarily reduced
to 3. Here the text itself is judged.

**On the plan**
1. The outline has one entry per chapter, no empty fields and no "to be determined".
2. Every `real` clue in the premise appears in the ledger with an assigned resolution chapter, and
   every `red_herring` with an assigned defusing chapter.

**On the text**
3. All three chapters are in Spanish, third person limited, past tense, and none leaks into the
   interiority of a character who is not its POV character.
4. Length within 1,700-2,300 words, with scene markers and `<!-- FIN -->`.
5. All three end on a hook. Read only the endings: if any closes at rest, it fails.
6. All three beats of each outline entry actually occur in the text.

**On the state**
7. After the three chapters, `clues.md`, `timeline.md` and `character-state.md` reflect what was
   written. Verify by hand against the text: this is the most important point of the rehearsal,
   because an extractor that hallucinates poisons the remaining 27 chapters.
8. `rolling-summary.md` holds the full text of the last 2 and the card of the one before.

**On the loop**
9. Inject a contradiction by hand into chapter 3 and confirm the Continuity Editor catches it.
10. Force a bad chapter (drop `temperature` to 0 or mutilate the context) and confirm that it
    exhausts both iterations, that the best attempt is accepted, and that it appears in
    `narrative-debt.md`.

**On operation**
11. Close Claude Code midway through chapter 2 and resume in a new session: it must continue without
    duplicating work or corrupting state. Also verify the quota counter is correct.
12. **Count the actual requests for the 3 chapters in the OpenRouter dashboard** and compare against
    the forecast in §13.3 (~12 per chapter). An overshoot almost always means some subagent is using
    tools and burning turns. This is the check that decides whether the full novel takes nine days
    or twenty-five, so it is not optional.

**Recalibration**: record how many of the 3 chapters were approved first time and adjust the
probabilities in §13. If fewer than 1 in 3 are approved, the problem is almost always the outline
(vague beats) or the anchor passage, not the Writer.

