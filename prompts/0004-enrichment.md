# 0004 — Stage 2: enrichment

Date: 2026-08-14
Assistant: Claude Opus 5 (Claude Code)

---

## Prompts

> that's a genuine concert when data/raw/ grows more than that, remind me about
> this when we are about to be done. and about second stage 2 that;s one of the
> problem mentioned in the problem statement alright keep these problems in a
> bucket we'll owrk on these at the end. now lets start with stage 2 and before
> that breif me the execution plan

> sure lets start with step 1

> yes go ahead with the revised plan, drop the website crawling

**Written by.** The assistant, end to end — models, five fetchers, orchestration
and tests. Gaurav set the sequencing (plan before code, probe before plan) and
made the call to drop website crawling.

This prompt also created `docs/parking-lot.md`: deferred problems get collected
rather than fixed mid-stage, and reviewed before submission.

---

## Probing changed the plan before any code was written

Four probes against live APIs. Two of them overturned decisions from the plan.

**The YC company page solves the founder gap outright.** It is an Inertia.js app
that ships its props as JSON in a `data-page` attribute — founders with full
names, titles, bios and LinkedIn/X links, plus `github_url` and `year_founded`.
Structured data, not scraped markup. This was parking-lot P2, the biggest known
hole coming out of stage 1, and it closed in one request per company.

**HN profiles carry prior exits.** The Plandex poster's bio reads *"Past founder
of EnvKey (YC W18)"*. For HN-only candidates that is often the only public
founder information anywhere. Same handle is also the top GitHub contributor —
cross-referencing the two confirms a named founder actually writes the code.

**Website crawling was cut on evidence** (D7). Guessing `/about`, `/team`,
`/pricing` yielded about one page per site; following homepage links yielded
nothing on JS-rendered navs; and SPAs serve byte-identical text on every path —
`voker.ai/pricing` matched `voker.ai` exactly at 15,224 characters. That is 4–6
requests per candidate for no new information plus duplicate copy stage 3 would
have read as corroboration.

**HN threads are the best source in the pipeline.** 67 comments on the Plandex
thread with the founders answering throughout. The top comments are real
objections written by people with no stake — *"what is the benefit over SES?"*,
*"is 10M emails processed all from beta testers?"*. That is honest raw material
for "what would kill this?", far better than asking a model to imagine risks.

---

## Two bugs found by reading the output

Stage 1's lesson was that the first run looks fine and isn't, so the run was
read by hand rather than trusted.

**The comment sort was inert.** Every `hn_comment` came back with `value=None`:
Algolia's `/items/` endpoint does not populate `points` on comments, so the
sort key was 0 for everything. The *behaviour* is fine — Python's sort is
stable, so the API's own ordering carries, and that ordering is HN's ranked
display order. The code was wrong about itself, claiming to rank by crowd
judgement when it never did. Fixed the comment, not the behaviour.

**One candidate's website never loaded.** Stage 1 took AgentMail's website from
the URL posted to HN, `chat.agentmail.to`, which refuses connections. Added an
apex-domain fallback: on failure, retry the registrable domain. AgentMail's
bundle went from 2,543 to 5,543 characters, and the substitution is recorded as
a gap so a reader can see we read `agentmail.to` rather than what stage 1 said.

---

## The part that matters most

`gaps` (D8). Every bundle records what was looked for and not found — 26 gaps
across 15 companies in the live run. Coverage is structurally uneven: YC-only
candidates get founder bios and no discussion; HN-only candidates get the
reverse. TryNearby's site rendered 224 characters because it is a JavaScript
shell, and that is written down rather than passed off as having read the site.

A model handed silence fills it with plausible invention, and "claims in memos
with no traceable source" is a named anti-pattern. Stage 3 has to see the shape
of its own ignorance.

## Judgement calls worth arguing with

- **Homepage copy is stored as a claim, not a fact.** Its own evidence kind,
  cited to the page. Stage 3 should treat "we serve 500 customers" on a landing
  page differently from the same number in a GitHub commit history.
- **Candidates we couldn't enrich are kept.** Dropping them would select for
  good SEO rather than good businesses.
- **10k character budget** (D9) is a first guess, unverified until stage 3 runs.
  Nothing is being trimmed yet — the largest live bundle is 8.7k.
- **The `data-page` shape is undocumented** and can change under us. Parse
  failure records a gap; it does not raise.

## Tests

89 total, 46 new. All offline, driven by fixtures shaped like the real payloads.
The failure-path tests are the ones that matter: a fetcher that raises becomes a
gap, one broken fetcher does not lose the other four, and a bundle with nothing
in it says so out loud.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
