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
