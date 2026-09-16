# Conflicts in the source specification

> Contradictions found in `docs/suspense-novel-harness.md` while splitting it into this context set.
> **Nothing has been resolved here.** Both versions are recorded with their source reference, and the
> original text is left untouched in whichever destination file carries it. Resolving any of these is
> an author decision.

## Scope

- Every place where two parts of the source say incompatible things.
- Each entry gives both versions verbatim-in-substance, with heading and line reference.
- Each entry names the destination files that now carry the two sides, so you can load both.
- Load before implementing anything one of these entries touches; it is short enough to read whole.

---

## C-01 · The active profile contradicts the stated scope

| | Version |
|---|---|
| **A** | "Novel in **Spanish**, 30 chapters, target of 2,000 words per chapter (tolerance ±15%)." — §2 *In scope for v1*, line 48 |
| **B** | "**Real example** (the `poc` profile, which ships active)": `"capitulos": { "total": 3, "palabras_objetivo": 60, ... }` — §6.0, lines 722-736 |

§6.0 states the arbitration rule itself ("the file wins and the document has an erratum", line 662),
so this is arguably self-resolving — but §2 is written as a scope commitment, not as a default, and
the two are read by different audiences. Carried by `scope.md` and `config-schema.md`.

## C-02 · The Evaluator's system prompt hard-codes a threshold that `config.json` owns

| | Version |
|---|---|
| **A** | "VERDICT RULE: `APROBADO` only if media >= 4.0 AND tension >= 4 AND escaleta >= 4. ... Compute the mean yourself and apply the rule yourself; do not delegate it." — §5.3 system prompt, lines 485-487 |
| **B** | "every numeric constant appearing in sections 1 to 17 — 30 chapters, 2,000 words, threshold 4.0, 2 rewrites, 16k tokens — is the default value of the `completo` profile in this file" — §6.0, lines 659-662; the `poc` profile sets `"umbral_media": 3.0`, line 732 |

Annex B.2 point 2 forbids modifying a system prompt to suit a binding or profile ("If a binding
needs to add instructions to a prompt, those go in the invocation prompt", lines 1874-1877), so
under the `poc` profile the Evaluator's own prompt is guaranteed to disagree with the configured
threshold. Carried by `agent-evaluator.md`, `evaluation-loop.md`, `config-schema.md`,
`port-contract.md`.

## C-03 · When the final audit runs, relative to chapter 30

| | Version |
|---|---|
| **A** | "Before writing chapter 30 \| **Final audit**: no `real` clue unresolved, no `red_herring` undefused" — §8.3 table, line 1145; reinforced by Annex A.5 step 21, "if N == 29: run the final audit of §8.3 before allowing chapter 30", line 1820 |
| **B** | State machine: `GATE_ACT --> FINAL_AUDIT: end of act 3` then `FINAL_AUDIT --> GATE_FINAL` — §10, lines 1231-1232; and §11 Gate 3, "**When**: after chapter 30 and the audit in §8.3", line 1335 |

In A the audit gates the writing of chapter 30; in B it runs after chapter 30 is already written.
Carried by `continuity-rules.md`, `state-machine.md`, `gates.md`, `binding-claude-code.md`.

## C-04 · What `rolling-summary.md` contains for chapters N-1 and N-2

| | Version |
|---|---|
| **A** | "## Capítulos N-2 y N-1 — `<full text is injected directly; it is not copied here>`" — §6.9 schema, lines 954-955 |
| **B** | "`rolling-summary.md` holds the full text of the last 2 and the card of the one before." — §15.2 rehearsal check 8, line 1570 |

A says the full text is deliberately *not* stored in the file; B makes storing it an acceptance
check. Carried by `artifacts-state.md` and `testing.md`.

## C-05 · Whether the Evaluator receives the previous chapter's card

| | Version |
|---|---|
| **A** | "**Inputs**: the chapter, its outline entry, `voice-and-style.md`, the previous chapter's card." — §5.3, line 428 |
| **B** | §7.1 context matrix, row "Cards of ch. N-6..N-3" (line 1024): the Evaluator column is `—`; its only `✓` rows are system prompt, `voice-and-style.md`, outline entry N and the chapter under judgement — lines 1014-1029 |

Carried by `agent-evaluator.md` and `context-assembly.md`.

## C-06 · The "full tree" of §6 omits directories the spec requires

| | Version |
|---|---|
| **A** | "Full tree. All paths are relative to the repository root." — §6 preamble, line 622; the tree lists `bible/`, `state/`, `chapters/`, `reports/`, `config.json`, `state.json`, `author-notes.md` — lines 624-647 |
| **B** | "Intermediate drafts live in `novel/.attempts/` (git-ignored) until one is accepted" — §10.2, line 1300; also §4.2, §9.4, §15.1 checks 3 and 6 |

`novel/.attempts/` is required by the state machine and by three POC checks but does not appear in
the tree that calls itself full. The same tree shows only `reports/act-1.md` (line 646) while §11 fires Gate 2
three times. Carried by `artifacts-tree.md`, `state-machine.md`, `testing.md`.

## C-07 · Which directory tree is canonical

| | Version |
|---|---|
| **A** | "File paths and identifiers have been translated too (`novel/` rather than `novela/`, and so on). Pick one document as canonical for a given project so you do not end up maintaining two directory trees." — translator's note, lines 14-17 |
| **B** | Every path in §6, §10, §15 and Annex A uses `novel/`; the Markdown schemas inside those files keep Spanish headings and field names "because they are the literal shape of files the Spanish-writing agents produce and consume" — §6 preamble, lines 649-651 |

The document does not itself say which of the two documents is canonical; it only says to choose.
The repository's `CLAUDE.md` answers this outside the spec (`docs/harness-novela-suspense.md` is
canonical, `novela/`), which means **every path in this context set is the non-canonical spelling**.
Carried by `overview.md` and `artifacts-tree.md`.

## C-08 · The daily cap that every estimate depends on

| | Version |
|---|---|
| **A** | "designed to run under a cap of **50 requests per day**" — §2, line 66; `"daily_limit": 50` in `state.json`, §10.1 line 1266 |
| **B** | "**Load $10 of credit on OpenRouter**, which raises the cap from 50 to 1,000 requests a day" — §13.4 lever 3, line 1447; §13.5 makes it close to mandatory for the POC ("A POC you can only run every other day is not a POC") |

Not a logical contradiction, but §2 presents 50/day as a fixed constraint ("A fact, not a
preference. It conditions the whole document." — §16 decision 2, line 1605) while §13 treats it as a
$10 decision. Every wall-clock figure in the spec depends on which reading holds. Carried by
`scope.md`, `cost-and-quota.md`, `decisions.md`.
