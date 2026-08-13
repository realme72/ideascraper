# ideascraper

An AI-augmented investment triage pipeline for a seed-stage VC.

Point it at a topic, get one-page investment memos out the other end — each
ending in a clear **Pass / Watch / Take a meeting**, and each claim traceable back
to the source it came from.

> **Status: scaffolding.** The four stages exist as modules with their
> responsibilities documented, but no implementation yet. Stage 1 (sourcing) is
> next — see `prompts/0003`.

---

## The problem

Partners at a seed-stage fund spend ~10 hours a week manually scanning Product
Hunt, YC, Hacker News, Twitter and Crunchbase, then hand-writing memos. Most
candidates get passed on anyway. This automates the triage layer, so partners only
spend their time on the top 10%.

## Planned shape

```
pipeline/source.py   →  data/candidates.json    find 10–20 startups for a topic
pipeline/enrich.py   →  data/evidence/*.json    gather evidence + provenance
pipeline/analyze.py  →  data/analyses/*.json    structured analysis + 0–100 score
pipeline/memo.py     →  memos/*.md             one-page memo per startup
pipeline/cli.py                                 one command, runs the lot
```

Stages hand off through plain JSON files on disk. Each stage runs on its own, so a
failure in analysis doesn't cost a re-scrape. Raw HTTP and LLM responses are
cached by hash, which makes re-runs deterministic and free.

No queue, no vector DB, no frontend — the brief explicitly rules those out.

## Repo layout

| Path | What's in it |
|---|---|
| `prompts/` | Verbatim prompt log, written as work happened. Start here. |
| `docs/decisions.md` | What was chosen, what was rejected, and why. |
| `docs/thesis.md` | The thesis every score is measured against. |
| `pipeline/` | The four stages, plus shared schemas (`models.py`) and the disk cache (`cache.py`). |
| `data/` | Committed intermediate outputs — reviewers don't need to re-run. |
| `memos/` | Committed final memos. |
| `tests/` | Tests. |

## How this was built

Built with heavy use of an AI coding assistant (Claude Opus 5 via Claude Code).
`prompts/` has the verbatim prompts in order, including the ones that were vague
or produced the wrong thing. Where a module was written end-to-end by the
assistant, the prompt entry says so.

## Running it

Not yet runnable. Instructions land with stage 1.
