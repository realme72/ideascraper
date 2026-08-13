# 0002 — Folder structure

Date: 2026-08-13
Assistant: Claude Opus 5 (Claude Code)

---

## Prompt

> now we have the clear problem statement, now before we begin implementing that
> we have to have the code in structured way, we will do everything step by step,
> so lets start by creating folder structure

**What happened.** Skeleton only — directories, module files carrying a docstring
that states what each one is responsible for, and no implementation. Written by
the assistant end-to-end.

The four pipeline stages come straight from the brief's three stages, with
enrichment split out of sourcing:

| Module | Responsibility |
|---|---|
| `source.py` | topic → 10-20 candidates |
| `enrich.py` | candidates → cited evidence, no judgement |
| `analyze.py` | evidence → structured analysis + 0-100 score |
| `memo.py` | analysis → one-page markdown memo |
| `cli.py` | the one command, plus per-stage entry points |
| `models.py` | the schemas that move between stages |
| `cache.py` | disk cache for HTTP and LLM calls |

## Decisions taken while laying it out

**Enrichment is its own stage, not part of sourcing.** Sourcing answers "who is
worth looking at", enrichment answers "what do we know about them". Splitting
them means a bad analysis run costs no re-scraping, and it keeps the LLM's input
to a bundle of already-collected, already-cited facts.

**Enrichment collects, it does not interpret.** All judgement lives in stage 3.
Provenance is attached at collection time and travels with the data, rather than
being reconstructed when the memo is rendered — the brief requires a reviewer to
spot-check a claim and trace it.

**Memo rendering is deterministic, with no LLM call.** The judgement was already
made and scored in stage 3. Templating the output means memos can never disagree
with the scores they came from, and fixing a layout problem costs nothing.

**Dependencies get added per stage, not up front.** `requirements.txt` currently
lists only what stage 1 needs.

## Not decided

Sources, thesis and model are all still open. Nothing in this structure commits
to any of them — `docs/thesis.md` exists as an empty slot with a note on what
belongs in it.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
