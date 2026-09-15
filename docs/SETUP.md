# Setup — running the POC

Operator guide for the Claude Code binding (Annex A of the spec). Everything here is
binding-side: nothing in this file constrains the core, and replacing the runtime means
rewriting this document and nothing else.

---

## 0. Read this before you spend an afternoon on it

Three facts that decide whether this works at all. None of them is a defect in the design;
all three are consequences of the chosen stack, and the spec calls out each one.

**The stack is not officially supported.** OpenRouter guarantees its Claude Code integration
only with first-party Anthropic models, which are paid. Third-party `:free` models go
through the same compatibility layer with no guarantee they honour the Messages format.
"Claude Code + OpenRouter + free models" may simply not work (§2). That is what step 3
below exists to find out, in ten minutes, before you write a line of novel.

**A full POC pass does not fit in the free daily cap.** One pass is ~58 requests against a
cap of 50/day, and the exit criterion is two clean passes in a row (§13.5, §15.1). On the
free tier that is three to four days to validate the machine. **Loading $10 of OpenRouter
credit raises the cap to 1,000 requests/day** and turns the POC into something you run
several times in an afternoon. If there is one moment in this project where the money pays
for itself, this is it.

**Free endpoints train on your inputs.** The novel, the bible and your original idea become
training material for third parties (§2). Migrating to the paid variants of the same models
fixes it and requires no architectural change — just different identifiers in step 2.

---

## 1. Point Claude Code at OpenRouter

Copy the template and fill in your key:

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

Edit `env` in that file. The equivalent shell form, if you prefer environment variables:

```bash
export OPENROUTER_API_KEY="<your OpenRouter key>"
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=""
```

Three silent-failure traps, all from §A.1:

- Define `OPENROUTER_API_KEY` **before** `ANTHROPIC_AUTH_TOKEN`, or the expansion is empty
  and auth falls back to a path you did not intend.
- `ANTHROPIC_API_KEY` must be an **empty string, not absent**. Left undefined, Claude Code
  may authenticate against Anthropic and the whole run works without ever touching
  OpenRouter — the exact opposite of the requirement, and it looks like success.
- `.claude/settings.local.json` holds your key. `.gitignore` already excludes it. Keep it
  that way.

---

## 2. Choose the three models

Claude Code offers **three model slots**, not one per agent, so the five roles share at most
three identifiers (§A.4). The mapping the core requires:

| Role | Class | Slot | Selection criterion |
|---|---|---|---|
| Architect | high | `opus` | structured reasoning |
| Writer | high | `opus` | Spanish prose quality, window ≥ 32k |
| Evaluator | balanced | `sonnet` | reliable valid JSON, more than literary ability |
| Continuity Editor | balanced | `sonnet` | same |
| Act Editor | high | `opus` | same as Architect |

**The one rule you cannot break**: `opus` and `sonnet` must resolve to *different*
identifiers. §5.2 requires the Writer and the Evaluator not to share a model — a model
grading its own prose is not an evaluation. Pointing all three slots at one identifier is
permitted by the configuration and silently destroys the evaluation loop.

The free catalogue rotates and cannot be pinned down here — this is `[OPEN: models]` in §17.
Check <https://openrouter.ai/models?q=free>, then set the identifiers in
`.claude/settings.local.json`. The values in the template are a starting point, not a
recommendation.

Model identifiers live **only** in this file. They are deliberately absent from
`novela/config.json`, which declares model *classes*: freezing identifiers into the core
would break the portability the spec is built around (§4.5, §6.0).

---

## 3. Smoke test — phase F0

**Nothing else starts until this passes** (§14). It is the cheapest possible answer to the
open risk in §2.

1. Open Claude Code in this repo and run `/status`. Confirm the routing points at
   OpenRouter. **A session that answers is not proof that it is routed** — a
   misconfigured `ANTHROPIC_API_KEY` gives you a perfectly working session against
   Anthropic.
2. Cross-check against the OpenRouter activity dashboard. Requests must appear there.
3. Ask the `evaluador` subagent for a verdict on a throwaway paragraph, ten times. It must
   return parseable JSON **10 out of 10**. Anything less and that model is not usable for
   the Evaluator or the Continuity Editor, whatever its prose is like.
4. Confirm the subagent declaration is actually tool-less. `.claude/agents/*.md` ships
   `tools: []`, which is the design intent, but the exact syntax for "zero tools" is
   `[OPEN: exact syntax]` in §A.3 and must be checked against your installed version. The
   test: a subagent call should cost **one** request, not three to six. If the dashboard
   shows the higher number, the field is not being honoured and the novel goes from nine
   days to twenty-five (§13.3).

If step 1 or 3 fails, pick one of the three ways out in §2 before going further: paid
Anthropic models through OpenRouter, a local Messages↔OpenAI gateway, or a different runtime
binding (Annex B.3). That choice belongs to the author, not to the implementer.

---

## 4. Run the POC

The POC is not separate code. It is the `poc` profile in `novela/config.json`, already
active: 3 chapters of ~60 words, one act per chapter so all three act gates fire (§15.1).

```bash
python -m harness init          # creates novela/ and estado.json
python -m harness status        # should print INIT
```

Then, in Claude Code:

```
/novela
```

The skill reads the state, does exactly one thing, and stops. Invoke it again for the next
step. It will ask you for a two-or-three-sentence starting idea — that is the only mandatory
human input before Gate 1 (§17, `[OPEN: initial idea]`).

Expect to be stopped at four kinds of gate: the plan (once), each act close (three times in
the POC), a continuity block (only if one occurs), and the final delivery. The system does
not advance past any of them without your answer.

### What the POC validates, and what it does not

It validates **the machine**: state, gates, resumption, delta application, ledger updates,
rolling-summary regeneration, attempt promotion, the patch loop, quota accounting, commits.

It does **not** validate literary quality. At 60 words there is no pacing and no prose to
judge, which is why the profile drops the threshold from 4.0 to 3.0. **Evaluator scores in
POC mode are not a quality signal** — their only job is to push the machine down both
branches of the loop. Draw no conclusions about the writing from them.

### Exit criterion

All thirteen checks in §15.1 pass **and** the whole POC runs twice in a row without changing
anything. A POC that only works the first time has validated nothing.

Check 13 is the one people skip and shouldn't: **count the actual requests in the OpenRouter
dashboard** and compare against §13.5. An overshoot almost always means a subagent is using
tools and burning turns.

---

## 5. Dry run — validating the machine without spending quota

Before you spend a single request, the whole loop runs offline with canned agent responses:

```bash
python tests/dry_run.py
```

40 checks covering the state machine, both branches of the evaluation loop, scene-hash
verification, iteration exhaustion with narrative debt, mid-chapter resumption, the sliding
context window, act gates, the final audit and one commit per accepted chapter.

This is not a substitute for the POC: it exercises the core, and it deliberately knows
nothing about OpenRouter or Claude Code. What it buys you is that when the POC fails, you
know the failure is in the binding, not in the machine.

---

## 6. After the POC

Switch `perfil_activo` to `"completo"` in `novela/config.json` and set
`capitulos.total` temporarily to 3 for the real-chapter rehearsal (§15.2). No code changes:
that is the point of the profile mechanism.

Then recalibrate the probabilities in §13.1 against what you actually observed. If fewer
than 1 in 3 chapters were approved first time, the problem is almost always the outline
(vague beats) or the anchor passage — not the Writer.

---

## Layout

```
harness/                     núcleo determinista — no menciona el runtime
├── config.py                perfiles y fusión profunda (§6.0)
├── state.py                 estado.json atómico y cuota (§10.1, §12)
├── artifacts.py             esquemas Markdown de §6
├── context.py               ensamblador y presupuesto de contexto (§7)
├── scenes.py                marcadores, hashes y parches (§9.5)
├── rules.py                 reglas bloqueantes y auditoría (§8.2, §8.3)
├── summary.py               resumen rodante determinista (§6.9)
├── deltas.py                aplicación de deltas y deuda (§6.10)
├── cli.py                   órdenes que invoca la skill
└── schemas/                 esquemas de §6 citados literalmente

.claude/                     binding de Claude Code (Anexo A) — solo P1 y P4
├── agents/                  los cinco system prompts de §5, literales
├── skills/novela/SKILL.md   skill orquestadora (§A.5)
└── settings.local.json      claves y modelos — NO se versiona

novela/                      artefactos de §6
tests/dry_run.py             simulacro del POC sin red
```

The split is the port contract of Annex B: `harness/` never names Claude Code, OpenRouter or
a model identifier; `.claude/` never reimplements core logic. If you find yourself breaking
that in either direction, the next runtime change will hurt.

---

## Note on language

This project follows the **Spanish** document, `docs/harness-novela-suspense.md`, as
canonical: `novela/config.json` already declared Spanish paths, and §6.0 is explicit that
when the file and the document disagree, the file wins. The English translation
(`docs/suspense-novel-harness.md`) describes the same system and is the better read if you
prefer English, but do not build a second directory tree from it — its translator's note
warns about exactly that.

The five system prompts are used **verbatim from the Spanish document**, which is also what
the English one recommends when driving Spanish prose on free models, to lower the
language-drift risk documented in §12.

Profile overrides (60 words instead of 2,000, 3 chapters instead of 30) reach the agents
through the **invocation prompt**, never by editing a system prompt. Annex B.2 point 2
requires the prompts stay literal.
