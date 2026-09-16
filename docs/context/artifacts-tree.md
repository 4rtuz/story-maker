# Artifact tree

> Source: `docs/suspense-novel-harness.md` — §6 preamble (lines 620-651). Section numbers below ("§7", "Annex A") refer to the original document's numbering, mapped in `index.md`.

## Scope
- The complete `novel/` directory layout: every file the system reads or writes, with its path.
- The rule that artifact Markdown headings and field names stay in Spanish on purpose.
- Load whenever you need to know where a file lives; this is the cheapest file in the set.
- See `config-schema.md`, `artifacts-bible.md` and `artifacts-state.md` for the schemas of each file listed here.

---

## 6. Artifact catalogue

Full tree. All paths are relative to the repository root.

```
novel/
├── config.json
├── state.json
├── author-notes.md
├── bible/
│   ├── interview.md
│   ├── premise.md
│   ├── characters.md
│   ├── voice-and-style.md
│   └── outline.md
├── state/
│   ├── rolling-summary.md
│   ├── clues.md
│   ├── timeline.md
│   ├── character-state.md
│   └── narrative-debt.md
├── chapters/
│   ├── 01-chapter.md
│   ├── 01-card.md
│   └── ...
└── reports/
    └── act-1.md
```

The Markdown schemas below keep their Spanish headings and field names, because they are the
literal shape of files the Spanish-writing agents produce and consume. Translating them would
change the system, not describe it.
