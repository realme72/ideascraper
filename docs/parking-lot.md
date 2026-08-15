# Parking lot

Known problems, deliberately deferred. Reviewed before submission — nothing here
is forgotten, and nothing here is pretended away.

---

## P1 — `data/raw/` is 7MB and grows with every run

**Raised:** 2026-08-13 (stage 1) · **Updated:** 2026-08-14 (stage 2)
**Revisit:** before submission

The HTTP cache is committed so reviewers can re-run offline and get identical
output. That is the point of it. But it grows with every distinct query and
every `--refresh`.

**2MB → 7MB across 65 entries after stage 2**, roughly a third of the way to the
point where this stops being a convenience and starts being a repo that is
annoying to clone. Now diagnosed: the bulk is **raw HTML**, not API JSON. YC
company pages are ~100KB each and one candidate homepage was 367KB, against
~10KB for a typical Algolia response.

Options, cheapest first:
- Cache extracted text rather than raw HTML for `web` and `yc_page`. Biggest
  win by far, but it makes the cache lossy — re-parsing with improved
  extraction would need a refetch.
- Gzip payloads on write.
- Commit one canonical run's cache and gitignore the rest.

Stages 3 and 4 will add LLM responses, which are small by comparison.

**Do not fix early.** Pruning the cache before the pipeline is finished risks
breaking replay for outputs we still care about.

---

## P4 — The HN search cache key changes every run

**Raised:** 2026-08-15 (stage 4) · **Revisit:** as soon as the remaining
analyses are done — this is a correctness bug, not a nicety

`pipeline/sources/hn.py` sends `numericFilters=created_at_i>{now - 540 days}`.
That bound is computed at call time, so **every run produces a different cache
key**, the HTTP cache never hits, and the search refetches.

That is not just wasted requests. Found by running `python -m pipeline run` end
to end: the refetch picked up a real-world change — a 15th comment on Sprocket's
launch thread, where the committed evidence recorded 14 — which changed the
candidate's signal label, which changed the evidence bundle, which changed the
analysis prompt, which invalidated that company's **model-response cache**. One
new comment on Hacker News silently orphaned a committed analysis.

This breaks the claim that the committed caches replay byte-identically, which
is the one thing the whole caching design exists to provide.

**The fix:** drop `numericFilters` from the request and apply the `since_days`
window client-side after fetching. The key then contains no timestamp at all and
is stable indefinitely. `hitsPerPage` needs raising to compensate, since the
window is no longer applied server-side.

**Why it is not fixed yet:** changing the request changes the cache key, which
re-sources every candidate and invalidates all ten completed analyses — and
free-tier quota cannot regenerate them today (P3). Sequencing matters: finish
the analyses, then fix this, then re-run the whole pipeline once from clean.

Interim state is safe: the evidence churn from the end-to-end run was reverted,
and all ten analyses match their committed evidence again.

---

## P3 — Free-tier quota caps a full run at ~20 companies/day

**Raised:** 2026-08-14 (stage 3) · **Revisit:** before submission

Google AI Studio's free tier allows **20 requests per day, per model** — measured,
not documented; the published rate-limit page defers to a per-account dashboard.
A 15-company run fits in principle, but retries and any re-run do not, and the
first live run stopped after 7.

Three properties make this survivable rather than fatal:

- Quota is **per model**, so `GEMINI_MODEL` switches to a fresh budget.
- Every completed analysis is cached and committed, so a re-run resumes rather
  than restarting.
- The run now stops cleanly and says how far it got, instead of raising.

**The constraint that matters for submission:** all fifteen scores should come
from the *same* model, or they aren't comparable to each other and the thesis
isn't being applied consistently. Finishing a partial run on a second model
would be the fast fix and the wrong one.

---

## P2 — The YC directory has no founder names — RESOLVED

**Raised:** 2026-08-13 (stage 1) · **Resolved:** 2026-08-14 (stage 2)

The YC *company page* carries what the directory API omits. It is an Inertia.js
app that ships its props as JSON in a `data-page` attribute, including a
`founders` array with full names, titles, bios and LinkedIn/X links — structured
data, not scraped markup. Every YC candidate in the current run yields 2–4 named
founders with bios.

For HN-only candidates the answer turned out to be the poster's HN profile,
where people list what they built before. One example from the live run: *"Past
founder of EnvKey (YC W18)"* — a prior company, for the cost of one request.

Residual risk: the `data-page` shape is not a documented API and can change
without notice. A parse failure records a gap rather than raising.

The original analysis is kept below.

---

**Raised:** 2026-08-13 (stage 1) · **Revisit:** during stage 2

The brief asks for a "founders/team signal where findable", and analysis wants
founder backgrounds, prior exits and technical depth. The yc-oss mirror carries
`team_size`, `stage` and `status` — company facts, not people.

Stage 1 gets a partial answer from HN: on Launch HN and Show HN the poster is
nearly always a founder, so the handle is a real lead. Stage 2 has to do better
than a handle. Candidate routes, in rough order of expected yield:

1. The company's own `/about`, `/team` or `/founders` page.
2. The HN launch thread — founders answer questions in it at length.
3. The HN user profile behind the posting handle.
4. The YC company page HTML, which does list founders but means parsing markup
   that can change under us.

Worth saying plainly: "where findable" is doing real work in the brief. Some
candidates will have no discoverable founder information, and the right output
for those is a recorded gap, not a guess.
