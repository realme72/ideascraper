# ideascraper

An AI-augmented investment triage pipeline for a seed-stage VC.

Point it at a topic, get one-page investment memos out the other end — each
ending in a clear **Pass / Watch / Take a meeting**, and each claim traceable back
to the source it came from.

> **Status: stages 1–2 of 4 working.** Sourcing and enrichment run end to end
> against live data. Analysis and memo rendering are next.

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

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pipeline source "AI agents for SMBs"
```

No API key needed for sourcing — both sources are public and keyless. Every HTTP
response is cached under `data/raw/` and committed, so a re-run works offline
and returns the same result.

```
15 candidates for "AI agents for SMBs"
term coverage: agent (15), ai (15), smb (4)

 1. Async  [0.67 · yc]
    Transforming small businesses with AI agents
    · YC Summer 2026 batch
    https://withasync.com

 2. Agent-desktop  [0.56 · hn]
    Native desktop automation CLI for AI agents
    · 99 points and 44 comments on Hacker News
    · Launched on HN 02 May 2026
    https://github.com/lahfir/agent-desktop
...
```

`term coverage` reports how many results matched each word of the query. `smb
(4)` above is the honest answer that recent YC batches skew to developer tooling
— a partner should see that rather than assume the list is SMB-focused.

Useful flags: `--limit`, `--batches` (YC batches to search), `--min-relevance`,
`--refresh` (bypass the cache).

### Stage 2 — enrichment

```bash
.venv/bin/python -m pipeline enrich
```

Gathers cited evidence for each candidate from four places: the YC company page
(founders, bios, socials), the HN launch thread (the founders' pitch and what
outsiders said back), GitHub (stars, recency, contributors) and the company
homepage. Writes one bundle per company to `data/evidence/`.

```
Async                       4 items   3,221 chars  2 gaps
Plandex v2                 12 items   6,698 chars  0 gaps
TryNearby                   4 items   1,465 chars  3 gaps
...
15 bundles written to data/evidence/ (26 gaps recorded)
```

**`gaps` is the point.** Coverage is structurally uneven — a YC-only candidate
has founder bios and no launch discussion, an HN-only candidate has the reverse
— so every bundle records what was looked for and not found:

```
GAP: No Hacker News launch thread found for this company
GAP: Website trynearby.com rendered only 224 characters of text
     — likely a JavaScript app, so its content is unavailable
GAP: chat.agentmail.to did not respond; read agentmail.to instead
```

Stage 3 is shown the gaps alongside the evidence. A model given silence fills it
with plausible invention, and a thin file should score as thin rather than bad.

Nothing in this stage interprets — it collects and cites. Judgement happens once,
in stage 3.

```bash
.venv/bin/python -m pytest tests/ -q      # 89 tests
```
