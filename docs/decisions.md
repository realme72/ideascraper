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

## D4 — Sources: Hacker News + the YC directory

**Date:** 2026-08-13 · **Status:** active

Both are free and need no key. They fail in opposite directions, which is why
two rather than one: YC gives a clean company record for every company whether
or not anyone noticed it, and no evidence any of it works. HN gives evidence
people reacted to a product, and no reliable company name.

YC is read through the [yc-oss mirror](https://yc-oss.github.io/api/), a daily
rebuild of the public directory, rather than by scraping ycombinator.com —
stable versioned JSON, no key. Only the four most recent batches are pulled
(~1MB rather than the 10MB full dump); seed-stage triage wants companies that
are still raising.

**Rejected:** Product Hunt (OAuth), Crunchbase and Twitter/X (paid). The brief
allows free tiers only and names a twelve-source layer returning garbage as an
anti-pattern.

---

## D5 — Stage 1 relevance means topic fit, never quality

**Date:** 2026-08-13 · **Status:** active

`Candidate.relevance` answers "is this the kind of company that was asked
about". It is a weighted term match over name, one-liner, tags and description.
It is deliberately *not* blended with traction, team size or recency — those
only break ties in the sort order.

Keeping them apart is what stops a keyword match from quietly becoming an
investment opinion. Judging a company happens once, in stage 3, against the
thesis, on gathered evidence.

**Rejected:** embeddings or a vector search over company descriptions. The brief
rules out a vector DB, and a partner cannot argue with a cosine distance. A term
score can be explained in one sentence and its failures are visible — which is
how the `smb` bug below got caught.

---

## D6 — An HN-only candidate must clear 10 points

**Date:** 2026-08-13 · **Status:** active

The first working run surfaced a company whose entire traction signal was a Show
HN post with 2 points and 0 comments. That is not evidence anyone reacted to the
product, and "a source where each result is garbage" is a named anti-pattern.

Candidates also in the YC directory are exempt — being in the batch is
independent of how a launch post happened to do on the day.

---

## D7 — Homepage only; no multi-page website crawling

**Date:** 2026-08-14 · **Status:** active

The stage 2 plan had the website fetcher pulling `/about`, `/team` and
`/pricing` as well as the homepage. Probing killed it before it was written:

- Guessing paths returned about one usable page per site, sometimes none.
- Following the homepage's own links returned nothing for sites whose nav is
  JS-rendered — two of four probed.
- Single-page apps serve **byte-identical text on every path**. `voker.ai/pricing`
  matched `voker.ai` exactly, at 15,224 characters.

Four to six extra requests per candidate for almost no new information, plus
duplicate copy stage 3 would have mistaken for corroboration. The founder data
it was meant to reach turned out to live on the YC company page and in HN
profiles instead.

---

## D8 — Gaps are recorded, and travel with the evidence

**Date:** 2026-08-14 · **Status:** active

Every bundle carries an explicit `gaps` list: dead website, no launch thread, no
repo identified, founder profiles with no bios, evidence dropped for budget. The
live run records 26 gaps across 15 companies.

This is the load-bearing part of stage 2. Coverage is structurally uneven — a
YC-only candidate has founder bios and no discussion, an HN-only candidate has
the reverse — and a model handed silence will fill it with plausible invention.
Stage 3 sees the gaps next to the evidence so it can say "unknown" and so a
thin file scores as thin rather than as bad.

**Rejected:** dropping candidates we couldn't enrich well. That would quietly
select for companies with good SEO rather than good businesses.

---

## D9 — 10,000 characters of evidence per company

**Date:** 2026-08-14 · **Status:** provisional

Bundles are trimmed to a character budget, dropping lowest-priority evidence
first (comments before founders) and reporting anything dropped as a gap. At
roughly four characters per token that is ~2.5k tokens of evidence per memo.

Provisional on purpose: the right time to tune it is when stage 3 exists and we
can see what the model actually needs. Current live run peaks at 8.7k, so
nothing is being trimmed yet.

---

## Open

- **Thesis.** Must be specific enough that a score of 72 vs 48 means something.
  *Undecided — Gaurav's call.* `docs/thesis.md` is the empty slot.
- **LLM.** No API key set in the environment yet. Open question is whether to
  commit cached model responses so reviewers can run the pipeline with no key at
  all. *Undecided.*
