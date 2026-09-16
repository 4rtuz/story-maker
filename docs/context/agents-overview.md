# Agent catalogue: shared conventions

> Source: `docs/suspense-novel-harness.md` — §5 preamble (lines 283-300). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The conventions every one of the five agents obeys: system prompt in `system`, assembled context in one `user` message.
- The no-tools rule, and why it is the main quota lever under the Claude Code binding.
- The rule that an agent declares a model *class*, never a concrete identifier.
- Load before defining any subagent; then load that agent's own file.

---

## 5. Agent catalogue

Conventions common to all five: `temperature` and `max_tokens` are given per agent; all of them
receive their system prompt in the `system` message and the assembled context in a single `user`
message.

**None has access to tools or to the internet**: the runtime reads and writes every file (ports P2
and P3 in Annex B); the agents only receive text and return text. This was already deliberate in the
previous design, because it eliminates an entire class of failures and because `:free` models have
erratic function-calling support. With Claude Code as the runtime it becomes, in addition, **the
main lever for quota control**: a subagent with no tools resolves its task in a single turn and
therefore in a single request; a subagent with `Read` and `Write` spends between three and six. Under
a cap of 50 requests a day, that difference decides whether the novel takes eight days or
twenty-five. See §13 and Annex A.3.

**On models**: each agent declares a model *class* (high-capability, balanced or fast), never a
concrete identifier. The mapping from class to identifier lives in the binding, because it is the
only thing in §5 that changes when the runtime changes. See Annex A.4.
