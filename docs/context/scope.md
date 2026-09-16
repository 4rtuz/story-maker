# Scope and non-scope

> Source: `docs/suspense-novel-harness.md` — §2 (lines 44-109). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- What v1 includes: 30 chapters, subgenre, POV, runtime, POC-first, config-driven parameters, 50 req/day cap, git.
- The explicit out-of-scope table (test-reader, style editor, scene-by-scene default, GUI, gateway, other bindings, EPUB, multi-language, rewriting accepted chapters).
- The accepted privacy limitation of OpenRouter `:free` endpoints (training on inputs).
- The open risk of the stack ("Claude Code + OpenRouter + free models" is unsupported) and the three ways out.
- Load when deciding whether a feature belongs in v1, or when the stack itself is in question.


> SUPERSEDED BY: `config-schema.md` (§6.0) — the numeric constants in this section (30 chapters, 2,000 words, ±15%, 50 req/day) are the defaults of the `completo` profile. The shipped active profile is `poc`. Where document and file disagree, the file wins.
---

## 2. Scope and non-scope

### In scope for v1

- Novel in **Spanish**, 30 chapters, target of 2,000 words per chapter (tolerance ±15%).
- Subgenre: **psychological domestic thriller**.
- Point of view: **third person limited**, alternating between 2 and 3 POV characters; **past**
  tense.
- Orchestration: **Claude Code**, with an orchestrating skill in the main session and one subagent
  per role. Inference does **not** use Anthropic models: Claude Code is pointed at OpenRouter via
  `ANTHROPIC_BASE_URL`, and OpenRouter serves the Messages format through its compatibility layer.
  No local proxy. Full configuration in **Annex A**.
- **The first deliverable is a POC**, not the novel: 3 chapters of about 60 words that exercise the
  whole machine in minutes rather than days (§15.1). It is not a separate mode or separate code: it
  is a profile in `config.json` (§6.0). The full novel is launched once the POC passes twice in a
  row.
- **Every system parameter lives in `novel/config.json`**, not in the code and not in this document:
  chapter count, length, thresholds, maximum rewrites, quota, temperatures. The document explains
  the numbers; the file fixes them (§6.0).
- **The runtime is isolated.** Sections 1 to 17 do not depend on it: they talk to it through the six
  ports of **Annex B**. Changing runtime means writing a new annex, not rewriting the
  specification.
- Interruptible, resumable execution, designed to run under a cap of **50 requests per day**.
- Version control with git: one commit per accepted chapter.

### Explicitly out of scope for v1

| Excluded | Reason |
|---|---|
| **Test-reader** agent (reads an act without knowing the plan and reports where tension sags) | High value for validating the mystery, but it consumes quota that v1 does not have. Candidate number 1 for v2. |
| **Final style editor** agent (polish pass over the whole manuscript) | Same. |
| **Scene-by-scene** generation as the default mode | Triples quota consumption. Implemented only as a recovery mechanism against truncation (§12). |
| Graphical interface | The system is operated from Claude Code. |
| Local Messages↔OpenAI translation gateway | Not needed: OpenRouter already serves the Messages format. It only comes into play as a contingency plan (§2, open risk). |
| Runtime bindings other than Claude Code | Annex B defines the contract for writing them; v1 implements one. |
| EPUB export / typesetting | The deliverable is Markdown. |
| Multi-language, translation | The novel is written directly in Spanish. |
| Rewriting already-accepted chapters because of later decisions | v1 only writes forward. Inconsistencies found after the fact are logged in `narrative-debt.md` for human review. |

### Accepted privacy limitation

OpenRouter's `:free` endpoints require the account to have training-on-inputs permissions enabled
and, depending on the provider, prompt publication as well. **The text of the novel, the bible and
the original idea will be training material for third parties.** This is inherent to the chosen
stack, not a defect of the design. If it stops being acceptable, the only mitigation is migrating to
the paid variants of the same models, which requires no architectural change: just edit the model
identifiers in the configuration.

### Open risk in the chosen stack

OpenRouter documents that its native Claude Code integration is guaranteed **only with first-party
Anthropic models**, which are paid. Third-party `:free` models go through the same compatibility
layer, but with no guarantee that they honour the Messages format or native tool use, and with
smaller context windows. Put bluntly: **the combination "Claude Code + OpenRouter + free models" is
not officially supported and may not work.**

This does not invalidate the design, precisely because the runtime is isolated (Annex B), but it
does require a smoke test **before** phase F1 begins: see §17, `[OPEN: stack viability]`. If the
`:free` models do not work down this path, the ways out are, from cheapest to most expensive:

1. Use paid Anthropic models through OpenRouter. It works, it costs money, and not one line of the
   rest of this document changes.
2. Insert a local Messages↔OpenAI translation gateway in front of OpenRouter, which does allow
   arbitrary `:free` models, at the price of maintaining one more component.
3. Change the runtime binding (Annex B.3) and leave Claude Code.

