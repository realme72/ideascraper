# 0003 — Stage 1: sourcing

Date: 2026-08-13
Assistant: Claude Opus 5 (Claude Code)

---

## Prompt

> yes go ahead with HN + YC, lets build the sourcing stage

**Written by.** The assistant, end to end — models, cache, both source adapters,
ranking and tests. Reviewed and iterated on across three runs (below).

---

## Probing the APIs before writing anything

The assistant hit both APIs with curl first rather than coding against
remembered shapes. This changed the design twice:

- `launch_hn` exists as an Algolia tag — YC companies' official launch posts,
  with the batch in a strict title format. That is a far better fit than the
  freeform `show_hn` alone, so both tags are queried.
- The YC directory has **no founder names**, which was assumed at planning time.
  `team_size`, `stage` and `status` are the team signal from YC; founders come
  from HN launch posts (the poster is nearly always one) and from stage 2.
- `meta.json` exposes per-batch endpoints (~270KB) instead of the 10MB full
  dump. Pulling four recent batches replaced downloading all 6,156 companies.

## Structure change from 0002

`source.py` was one module in the committed skeleton. It became `source.py` plus
`sources/hn.py` and `sources/yc.py` — the adapters fetch and attach provenance,
`source.py` does the three things that must happen across sources: merge, rank,
cut. Worth the extra files because the adapters are now testable without
touching ranking.

---

## Three runs, two real bugs

**Run 1 — the ranking did nothing.** Every one of the top 8 candidates scored
exactly 0.56, so the list was really sorted alphabetically: five of eight names
began with A. Three separate causes:

1. `smb` matched nothing at all, so the most distinguishing word in "AI agents
   for SMBs" was silently ignored.
2. `ai` matched *company names* — "Agnost AI", "Callab AI", "Alkera AI" — at the
   highest field weight. Roughly a third of any recent YC batch has AI in its
   name; it is decoration, not signal.
3. A Show HN post with 2 points ranked alongside one with 257, because nothing
   compared traction.

Fixes: strip decorative tokens (`ai`, `labs`, `inc`, …) from names before
matching; add explicit tie-breaks on corroboration, then traction, then recency;
require HN-only candidates to clear 10 points.

**Run 2 — the `smb` alias was still broken.** Aliases had been written as single
tokens (`smallbusiness`), which can never match text that tokenises as two
words. Rewritten to match alias *phrases* against normalised text with word
boundaries. That surfaced a second bug immediately: the plural group was `s?`,
which cannot match "small business**es**" — by far the more common phrasing. One
character, `(?:e?s)?`, and the term went from 0 matches to 4.

Both bugs shared a shape: the pipeline looked confident while ignoring part of
the query. That is why `term_coverage` now ships in the output and prints a
warning — a term matching zero candidates is reported rather than hidden.

**Run 3 — sensible.** Top result is Async, *"Transforming small businesses with
AI agents"*, at 0.667. Coverage: `agent (15), ai (15), smb (4)`.

---

## Judgement calls worth arguing with

- **Relevance is topic fit, not quality** (D5). Traction and recency only break
  ties; they never move the score. Judging a company happens once, in stage 3.
- **Only 4 YC batches.** Seed triage wants companies still raising. Costs recall
  on older companies that would match the topic.
- **HN limited to ~18 months.** A 2022 launch is not a sourcing lead.
- **Term matching over embeddings.** The brief rules out a vector DB, and a
  partner cannot argue with a cosine distance. Both bugs above were catchable
  *because* the scoring is inspectable.
- **`smb (4)` was not "fixed" further.** Only 6 of 417 companies across four YC
  batches mention small business at all. The corpus genuinely skews to developer
  tooling, and padding the list would be worse than reporting the gap.

## Tests

43 tests. Every one covers a judgement call that was wrong at some point above —
plural aliases, decorative name tokens, word boundaries (`ai` must not match
"blockchain" or "email"), tie-break order, the 10-point bar, and HN title
parsing including the fallback from title to domain.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
