# Overall architecture

> Source: `docs/suspense-novel-harness.md` — §4 (4.1-4.5) (lines 140-280). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The full flow diagram, from the author's idea through the three gates to the finished manuscript (4.1).
- The one-chapter cycle as a sequence diagram: write, evaluate in parallel, accept or patch (4.2).
- Why the design splits planning from writing, and why only the Continuity Editor writes state (4.3).
- The mapping from the original Spanish diagram to this specification (4.4).
- The core / port / binding layering and what must never leak between layers (4.5).
- Load when changing how the phases fit together, or before touching anything near the core/binding boundary.

---

## 4. Overall architecture

### 4.1 Full flow

```mermaid
flowchart TD
    A["Author initial idea<br/>2-3 sentences"] --> B["Architect: interview"]
    B -->|"3 rounds of max 6 questions"| C["bible/interview.md"]
    C --> D["Architect: bible generation"]
    D --> E["bible/premise.md"]
    D --> F["bible/characters.md"]
    D --> G["bible/voice-and-style.md"]
    D --> H["bible/outline.md<br/>30 entries, 3 acts"]
    E & F & G & H --> P1{{"GATE 1<br/>Plan approval"}}
    P1 -->|rejected with notes| D
    P1 -->|approved| I["Initialise state/<br/>clues, timeline, character-state"]
    I --> J["Chapter cycle"]
    J --> K{"End of act?"}
    K -->|no| J
    K -->|yes| L["Act Editor"]
    L --> P2{{"GATE 2<br/>Act close"}}
    P2 -->|adjustments| M["Architect: revise remaining outline"]
    M --> N{"Chapter 30<br/>reached?"}
    P2 -->|continue| N
    N -->|no| J
    N -->|yes| P3{{"GATE 3<br/>Final delivery"}}
    P3 --> O["Complete manuscript<br/>+ narrative-debt.md"]
```

### 4.2 The cycle of one chapter

```mermaid
sequenceDiagram
    participant R as Runtime
    participant E as Writer
    participant V as Evaluator
    participant C as Continuity
    participant F as File system

    R->>F: assemble context for chapter N
    R->>E: write chapter N
    E-->>R: draft with scene markers
    R->>F: save .attempts/NN-i0.md
    par Evaluation in parallel
        R->>V: assess literary quality
        V-->>R: 6 criteria 1-5 + proposed patches
    and
        R->>C: verify continuity + extract state
        C-->>R: verdict + conditional state deltas
    end
    alt Approved by both
        R->>F: promote attempt to chapters/NN-chapter.md
        R->>F: apply deltas to clues, timeline, character-state
        R->>F: write NN-card.md and update rolling-summary.md
        R->>F: git commit
    else Rejected, iterations remaining
        R->>E: apply targeted patch to flagged scenes
        E-->>R: patched chapter
        R->>F: save .attempts/NN-i1.md
        Note over R,C: evaluation repeats
    else Rejected, 2 iterations exhausted
        R->>F: promote best attempt by mean, not the last
        R->>F: log defects in narrative-debt.md
        R->>F: git commit
    end
```

### 4.3 Explanation

The system has **two very different phases**. The planning phase is conversational, expensive in
human attention and cheap in quota (about 12 logical calls). The writing phase is autonomous, cheap
in human attention and expensive in quota (about 150 logical calls, which in Claude Code translate
into considerably more actual requests: §13). The design deliberately concentrates human
intervention in the first, because a mistake in the outline costs 30 chapters and a mistake in a
chapter costs one chapter.

The piece that makes the whole thing viable is the **accumulating state** (`novel/state/`). The
Writer never receives the whole novel: it receives an assembled, bounded view of it, built by the
runtime from those files according to the rules in §7. The Continuity Editor is the only agent that
writes into `novel/state/`, and it does so after a chapter has been accepted. This separation — one
agent that writes fiction and another that maintains the facts — is what prevents continuity drift
over the long stretch of the novel.

### 4.4 Mapping to the original diagram

| Original diagram (Spanish) | In this specification |
|---|---|
| Agente Inicio | **Architect** (§5.1), with the interview as its own subprocess |
| `.md con respuestas` | `bible/interview.md` |
| `Desarrollo de personajes` | `bible/characters.md` |
| `Resumen de la historia completa` | `bible/premise.md` |
| `Introducción, nudo y desenlace` (1 artifact) and `Desarrollo Introducción / nudo / desenlace` (3 artifacts) | **Resolved**: a single `bible/outline.md` with 30 entries grouped under three act headings. The three-way split stops being a decision about files and becomes a grouping inside one. |
| Agente Escritor | **Writer** (§5.2) |
| Agente Evaluador returning "fix this" | **Evaluator** (§5.3) with a numeric rubric + **Continuity Editor** (§5.4), kept separate |
| *(did not exist)* | **Act Editor** (§5.5), the whole of `state/`, `state.json`, `author-notes.md` |

### 4.5 Core / runtime binding separation

The orchestration runtime has already changed once and may change again. So that such a change costs
an annex rather than a rewrite, the system is split into two layers with an explicit boundary.

```mermaid
flowchart TD
    subgraph CORE["CORE - sections 1 to 17, runtime agnostic"]
        N1["Agent catalogue<br/>and system prompts"]
        N2["Artifact catalogue<br/>and schemas"]
        N3["Context assembly<br/>rules"]
        N4["Rubric, threshold<br/>and quality loop"]
        N5["State machine<br/>and gates"]
    end
    subgraph PORTS["PORT CONTRACT - annex B"]
        P1["P1 invoke"]
        P2["P2 artifacts"]
        P3["P3 state"]
        P4["P4 human"]
        P5["P5 version"]
        P6["P6 budget"]
    end
    subgraph BINDING["BINDING - annex A, Claude Code over OpenRouter"]
        B1["Orchestrating skill"]
        B2["Subagents .claude/agents"]
        B3["Read and Write tools"]
        B4["Environment variables<br/>and model mapping"]
    end
    CORE --> PORTS
    PORTS --> BINDING
```

The core **never** names Claude Code, or OpenRouter, or a concrete model. When it needs something
from the outside world, it asks for it through a port. Three practical consequences:

1. **The system prompts in §5 are portable as they stand.** They are text; they do not depend on
   who sends them.
2. **The artifact schemas in §6 are portable as they stand.** They are files on disk.
3. **The only thing to rewrite when the runtime changes is Annex A.** Annex B defines what the
   replacement has to satisfy.

The two things that do change with the runtime, and are therefore kept out of the core, are **the
assignment of a concrete model to each role** (§5 speaks of model classes, not identifiers) and
**request accounting** (§13, which carries one table per binding).

