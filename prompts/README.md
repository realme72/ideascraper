# Prompt log

Every meaningful step of this project is logged here as a numbered entry, written
**at the time it happened**, not reconstructed afterwards.

## What goes in an entry

- `0001-kickoff.md`, `0002-sourcing.md`, ... — one file per working step.
- The **verbatim prompt(s)** given to the AI assistant. Not cleaned up, not
  rewritten to look smarter after the fact. Typos included.
- What the assistant actually did in response.
- What it got wrong, and how it was corrected.

## Rules

1. **Verbatim.** Prompts are copied exactly as typed. If a prompt was vague and
   produced the wrong thing, that's the interesting part — it stays in.
2. **Written before the commit**, not batched at the end. Each commit references
   the prompt entry that drove it.
3. **Reflection is written by Gaurav, not the model.** Entries record *facts* —
   what was asked, what happened, what broke. Any "what I learned from this"
   commentary is human-written. The assignment explicitly calls out
   model-ghostwritten reflection as an anti-pattern, and it is obvious when it
   happens.
4. **Attribution is explicit.** Where a module was written end-to-end by the
   assistant, the entry says so plainly.

## Commit convention

Commit messages reference the driving prompt entry:

```
sourcing: fetch Show HN launches via Algolia API

prompt: prompts/0002-sourcing.md
```
