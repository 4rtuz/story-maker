# Port contract and alternative bindings (Annex B)

> Source: `docs/suspense-novel-harness.md` — Annex B (B.1-B.3) (lines 1849-1899). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The six ports (P1 invoke, P2 artifacts, P3 state, P4 human, P5 version, P6 budget) with conceptual signatures and required semantics (B.1).
- What the core never does, and therefore what no binding must expose.
- The five checks any new binding must pass, including that §5 system prompts are used literally and §6 schemas byte for byte (B.2).
- The documented, unimplemented Python-script binding and its port mapping (B.3).
- Load when writing a new binding, or when auditing whether core logic has leaked into the current one.

---

# Annex B — Port contract and how to write another binding

## B.1 The six ports

The core (§1-17) can ask the outside world for six things only. Any runtime that provides them can
execute this specification without modifying it.

| Port | Conceptual signature | Required semantics |
|---|---|---|
| **P1 invoke** | `invoke(role, prompt) -> text` | Sends `prompt` to the model of the class that role declares in §5 and returns plain text. **Stateless**: two invocations of the same role share no memory. If the role returns JSON, the port does not interpret it; it only transports it. |
| **P2 artifacts** | `read(path) -> text`<br>`write(path, text)` | Storage for the `.md` files of §6. Must preserve text byte for byte: the scene markers and the hashes of §9.5 depend on it. |
| **P3 state** | `read_state() -> object`<br>`write_state(object)` | **Atomic** persistence of `state.json`. An interrupted write must not leave a half-written file. It is the single point of truth for the run (§10.2). |
| **P4 human** | `ask(text, options) -> answer` | Presents a gate (§11) and **blocks** until an answer arrives. It may be synchronous or deferred to another session; the core only requires that nothing advances without an answer. |
| **P5 version** | `commit(message)` | Records a restore point after each accepted chapter. **Optional**: a binding without version control may implement it as a no-op, at the cost of losing the second safety net in §10.2. |
| **P6 budget** | `has_budget() -> bool`<br>`record_usage(n)` | Decides whether one more logical call may start. Encapsulates the daily cap, the per-minute limit and the backoff. **The unit of consumption is defined by the binding**, not the core: in Claude Code it is HTTP requests; in another it might be tokens or euros. |

What the core **never** does, and therefore no binding needs to expose: pick a concrete model, know
a network protocol, know whether there are subagents or threads, or manage a conversational
orchestrator's context.

## B.2 Writing a new binding

Checks for accepting an alternative binding. They apply equally to Annex A and to any replacement:

1. **All six ports are implemented**, each in exactly one place. If a port's logic appears in two
   places, the next runtime change will hurt again.
2. **The five system prompts of §5 are used literally**, unrewritten, unsummarised and without
   runtime-specific additions. If a binding needs to add instructions to a prompt, those go in the
   invocation prompt, not in the system prompt.
3. **The artifact schemas of §6 are honoured byte for byte.** A binding that moves or reshapes
   `novel/state/clues.md` breaks compatibility with a run already in progress.
4. **A request table equivalent to §13.3 is published.** It is the thing that always changes and
   that nobody remembers to recompute. Without that table, the projected wall-clock time is fiction.
5. **A run started under the previous binding can continue under the new one.** This is the acid
   test, and it passes for free if point 3 was honoured: copy `novel/` and resume. Worth actually
   testing rather than assuming.

### B.3 Documented alternative binding: Python script

This was the runtime of the previous version of this specification. It is kept here because it
remains the lowest-quota option, in case the requirement to use Claude Code is lifted. Summary:
Python script with no framework, direct HTTP calls to OpenRouter's `/api/v1/chat/completions`, every
logical call equal to exactly **one** request, a conversion factor of 1.0 instead of 2.5. With it,
the full novel is ~162 requests and about **4 days** of wall-clock time instead of nine.

The ports would map as follows: P1 with `requests` or `httpx`; P2 and P3 with the file system and
`os.replace` for atomicity; P4 with `input()` at the console; P5 with `subprocess` over git; P6 with
a counter in `state.json`, which in that binding is exact because one logical call is one request.

`[OPEN: author's decision]` This binding is **not implemented in v1**. It is documented to this
level of detail and no further, so that it does not age unnoticed (§16, decision 1b).
