# 0008 — Stage 4: memos, and two bugs found by running it

Date: 2026-08-15
Assistant: Claude Opus 5 (Claude Code)

---

## Prompts

> go with option A, start stage 4, how much more is remaining ?

> since we have fresh lmit we can directly go with option b

> running a

**What happened.** Option A was to finish the remaining analyses on
`gemini-3.7-flash`; option B was to re-run all fifteen on Flash-Lite. Gaurav
switched to B on the basis that quota had reset — but the reset was on
`gemini-3.7-flash`, the *better* model, which made A strictly cheaper (eight
calls, not fifteen) and higher quality, and kept the seven good analyses instead
of replacing them. The assistant said so in two sentences and proceeded with A;
Gaurav confirmed.

Three more analyses completed before quota ran out again — ten of fifteen, all
from one model.

**Written by.** The assistant: `memo.py`, the `run` command, and the tests.

---

## The memo design

Deterministic templating, no model call. The judgement was made and scored in
stage 3, so a memo can never disagree with the score it came from, and fixing a
layout problem costs nothing.

The brief's bar is that a partner understands the call in 60 seconds, so the
call and its reason sit above everything else, and every factual section ends at
a list of openable sources.

Three things are printed rather than hidden, all for the same reason — a partner
deciding how much to trust a memo needs to know what is behind it:

- **`What we could not find`** — the gaps from stage 2, verbatim.
- **`⚠ Unverified references`** — anything the model cited that does not resolve
  to a real evidence item. Zero across all ten, but the section exists because
  an uncheckable citation is worse than none.
- **A footer** stating that the total, the coverage and the call were computed
  from the component scores rather than chosen by the model.

---

## Bug 1 — the memo cited the wrong provenance

The first rendered memo listed **one** source: the YC page. The analysis had
plainly used the company's website too.

`_sources` was reading `candidate.provenance` — stage 1's record of *where the
company was found* — rather than the provenance of the evidence the claims
actually rest on. For a company sourced from YC, that is one URL, no matter how
much was later gathered.

Fixed by carrying evidence provenance forward onto the `Analysis`. It matters
more than it looks: the brief asks that a reviewer be able to spot-check a claim
and trust where it came from, and the memo was pointing at the wrong page.

## Bug 2 — a Hacker News comment orphaned a committed analysis

Found by running `python -m pipeline run` end to end rather than trusting the
stages individually.

`sources/hn.py` sends `numericFilters=created_at_i>{now - 540 days}`. That bound
is computed at call time, so **every run has a different cache key** and the
search always refetches. The refetch picked up a real change — a 15th comment on
Sprocket's launch thread against the committed 14 — which changed the signal
label, the evidence bundle, the analysis prompt, and finally invalidated that
company's model-response cache.

One new comment on a website silently orphaned a committed analysis. That breaks
the byte-identical replay the whole caching design exists to provide.

**Deliberately not fixed yet** (P4). The fix changes the cache key, which
re-sources everything and invalidates all ten analyses — and free-tier quota
cannot regenerate them today. Finish the analyses, then fix, then re-run once
from clean. The churn from the end-to-end run was reverted and all ten analyses
match their committed evidence again.

---

## What the output actually says

Ten companies scored. Six Pass, three Watch, one Take a meeting.

The striking part is that the thesis gate did all the discriminating on its own.
Every Pass scores under 10/30 on displaced spend (2, 2, 3, 3, 4, 6); every Watch
or meeting scores 10 or above (11, 14, 17, 29). Nothing was tuned to produce
that.

It also surfaced a presentation problem. Plandex scores 54 and is a Pass while
Mount scores 49 and is a Watch — correct (Plandex is developer tooling and the
gate fires) but it reads as a bug in a ranked list. The index now shows the
thesis-fit column and explains that the ordering is by fit, not by total.

Spot-checked two memos against their evidence: Agent-desktop's "1,006 stars, 66
forks", "Apache-2.0", "self-described 2X founder"; and Last Accounting Company's
four named founders, Token Terminal, BCG, Intera Partners. All resolve.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
