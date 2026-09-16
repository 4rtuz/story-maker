# Failure modes and degradation

> Source: `docs/suspense-novel-harness.md` — §12 (lines 1353-1374). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- One table: every anticipated failure, how it is detected, and the exact response.
- Covers rate limits, daily quota, truncation, withdrawn models, malformed JSON, language drift, non-convergence, contradictions, patch regression.
- Covers the binding-specific failures: the compatibility layer rejecting a `:free` model, a subagent using tools, the orchestrating session running out of context.
- Load when adding error handling or diagnosing a run that stopped unexpectedly.

---

## 12. Failure modes and degradation

| Failure mode | Detection | Response |
|---|---|---|
| **429 from the 20 req/min limit** | HTTP 429 with a retry header | Exponential backoff of `2^n` seconds, n from 0 to 4. After 5 attempts, move to `QUOTA_PAUSED`. |
| **Daily quota exhausted (50/day)** | The governor's internal counter, or a persistent 429 | Transition to `QUOTA_PAUSED`, persist state, exit with code 0. Relaunching on a new UTC day continues with no intervention. |
| **Truncated response** | `finish_reason == "length"`, or the `<!-- FIN -->` marker is missing | Retry asking only for the missing scenes, with the generated ones as context. After 2 failures, reduce the word target by 20% and retry. After 3, move to the next model in the chain. |
| **Model withdrawn from the catalogue** | HTTP 404 or a `model_not_found` error | Advance in the fallback chain, record the switch in `state.json` and in the log. If the chain is exhausted: `ERROR` and exit. |
| **Malformed JSON from the Evaluator or Continuity Editor** | `json.loads` fails after extracting the first balanced object from the response | One retry with the parser's error message appended to the prompt. If it fails again: for the Evaluator, treat it as a generic `CORREGIR` and log it as debt; for the Continuity Editor, treat it as `CORREGIR` with the raw response attached. Never assume `OK`. |
| **Language drift** | Heuristic over the draft: proportion of Spanish function words below a threshold | Retry with an explicit language reminder. After 2 failures, move to the next model in the chain. |
| **The loop does not converge** | 2 iterations reached without approval | §9.4: accept the best attempt and log the debt. Execution continues. |
| **Irresolvable contradiction** | `veredicto == "BLOQUEO"` | Block gate (§11). |
| **A patch alters unflagged scenes** | Per-scene hash comparison | The original scenes are restored and only the patched ones are kept. |
| **The Writer cannot fulfil a beat** | The Evaluator scores `escaleta` 1 or 2 on two consecutive iterations | Accept with debt and mark the beat as unfulfilled; the Act Editor picks it up in its report. |
| **Final audit fails** | Clues unresolved before chapter 30 | Execution halts and a gate opens. Chapter 30 is never written with known loose ends. |
| **Network drop or process killed** | — | State was already persisted before the call; the run resumes by repeating the last call. |
| **The compatibility layer rejects a `:free` model** | Format error, tools unsupported, or an empty response right at the start | This is the open risk of §2. Not recoverable in flight: halt, record the offending model, and apply one of the three ways out in §2. The F0 smoke test in §14 exists to find this before a single line of novel is written. |
| **A subagent returns prose instead of JSON** | Same as "malformed JSON", but from a different cause: the subagent has "conversed" instead of answering | Same treatment. As prevention, the system prompt demands pure JSON and the orchestrator never shows the raw result to the human. |
| **A subagent uses tools and burns several turns** | The binding records more requests than expected for that role | A configuration defect, not a runtime one: the subagent is declared with no tools (Annex A.3). Detected by comparing actual requests against the model in §13. |
| **The orchestrating session runs out of context** | The session compacts or warns mid-chapter | Should not happen with one chapter per invocation (§7.5). If it does, it is a sign that chapters are being chained in a single session: go back to one chapter per invocation. State on disk guarantees nothing is lost. |
| **429 in the middle of a subagent's loop** | The subagent fails halfway | The orchestrator treats it as a failed logical call and repeats it whole; calls are idempotent (§10.2). The cost is that the quota already consumed is not recovered. |

