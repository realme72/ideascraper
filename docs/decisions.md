# Decision log

Running log of choices made and — more usefully — what was rejected and why.
Appended to as decisions happen, newest at the bottom.

---

## D1 — Log prompts in-repo, from commit one

**Date:** 2026-08-13 · **Status:** active

Process & AI workflow visibility is 40% of the rubric, and the brief deliberately
declines to say what form the evidence should take. It also names
"a trail clearly assembled after the fact" as an anti-pattern.

A trail written at the end cannot be made convincing, because it isn't true. So
prompts get committed alongside the code they produced, starting before any
pipeline code exists.

**Rejected:** writing a single reflective `PROCESS.md` at the end of the project.
Faster, and worth nothing — it is the exact anti-pattern named in the brief.

---

## D2 — No standalone summary cache; cache inside the pipeline instead

**Date:** 2026-08-13 · **Status:** active

A `.cache/` of document summaries was proposed to reduce token use, then dropped.
It does not save tokens within a session — the assistant already holds what it has
read, and does not re-read files each turn. The saving only appears across
sessions and after compaction, which is not where this project's cost sits.

Caching moves inside the pipeline instead: raw HTTP responses and LLM responses
written to disk, keyed by hash. That buys something the rubric actually asks for
under System Design — **replayable** runs — and makes re-runs deterministic and
free. Same idea, aimed at the place where it pays.

---

## D3 — Stages hand off via JSON files on disk

**Date:** 2026-08-13 · **Status:** active

`source → enrich → analyze → memo`, each stage reading and writing plain JSON in
`data/`. Each stage runs independently; a failure in analysis doesn't cost a
re-scrape.

**Rejected:** a job queue, a database, or any orchestration framework. The brief
is explicit — *"if you're building a job queue, vector DB cluster, or React
frontend — stop."*

---

## Open

- **Sources.** Leaning Hacker News (Algolia API — no key, and points/comments are
  a real traction signal) plus the YC public directory (founders, batch). Product
  Hunt needs OAuth; Crunchbase and Twitter are paid. *Undecided.*
- **Thesis.** Must be specific enough that a score of 72 vs 48 means something.
  *Undecided — Gaurav's call.*
- **LLM.** No API key set in the environment yet. Open question is whether to
  commit cached model responses so reviewers can run the pipeline with no key at
  all. *Undecided.*
