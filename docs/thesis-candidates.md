# Candidate theses

Three drafts. **Thesis A was chosen** and is now the live rubric in
[thesis.md](thesis.md) — with score-to-call bands and overrides added. B and C
stay here as the record of what was considered and rejected.

A thesis is only worth having if a score of 72 and a score of 48 mean different
things. Each draft below is therefore written as a scoring rubric — weighted
components that add to 100, scoreable from evidence this pipeline actually
gathers, with the bands spelled out.

---

## Rules that apply to all three

**Only score what stage 2 can observe.** Revenue, funding, headcount growth,
retention and real market size are not available from HN, the YC directory,
GitHub or a homepage. A rubric with a "traction" component that silently means
"revenue" is a rubric that invites invention. Every component below names the
evidence kinds that feed it.

**Claims and facts are weighted differently.** A number on a landing page is a
claim (`website_copy`). The same number in a founder's reply to a skeptic on HN
is a claim made under scrutiny. Commit history is a fact. Components say which
they will accept.

**Missing evidence caps confidence; it does not lower the score.** If no founder
bio was found, the team component is scored at its documented neutral band and
the memo reports reduced coverage. Otherwise the pipeline scores its own
scraping failures rather than the company — a startup would be marked down for
having a JavaScript homepage. Every memo carries an explicit evidence-coverage
figure next to its score, and the recommendation band shifts toward **Watch**
(never toward Pass) when coverage is low.

**The seed topic and the thesis have to agree.** Sourcing searches a topic;
scoring judges against a thesis. Pick a thesis whose companies the chosen topic
will actually surface, or every run will source companies the thesis rejects on
principle. Noted per draft below.

---

## Thesis A — Budget-line AI

> **Seed-stage, AI-native software that takes over work an SMB or mid-market
> business is already paying for — a subscription, an outsourced contractor, or
> a back-office role — sold to a non-technical operational buyer by a team with
> a working product in real users' hands.**

The bet: at seed, the hard part of AI is not capability, it is distribution and
willingness to pay. A company replacing a line item that already exists does not
have to create a category, educate a market, or invent a budget. The buyer can
already tell you what they spend today.

**Components**

| # | Component | Weight | Evidence |
|---|---|---|---|
| 1 | Displaced spend is nameable | 30 | `one_liner`, `company_profile`, `website_copy`, `hn_launch_text` |
| 2 | Buyer is non-technical and operational | 15 | as above, plus `keywords` |
| 3 | Product is in real users' hands | 20 | `github_repo` recency, `hn_comment` from users, founder replies describing production use |
| 4 | Founding team | 20 | `founder` bios, `hn_profile`, `github_contributors` |
| 5 | Quality of outside reaction | 10 | `hn_comment` — substance of objections and of the replies |
| 6 | Momentum | 5 | batch recency, `pushed_at`, hiring signal |

**Bands for component 1 (the one that carries the thesis)**

- **25–30** — Names a specific cost centre it takes over. "Agent-native
  accounting firm", "autonomous insurance brokerage for small businesses". A
  reader can say what stops being paid for.
- **15–24** — Names a workflow but not a spend. "AI agents for compliance at
  trading firms" — real work, unclear whose budget.
- **5–14** — Names a capability only. "AI agents for X."
- **0–4** — Horizontal infrastructure. No buyer budget implied at all.

**Bands for component 4** — 16–20: a prior founder or exit, *or* deep domain
background, *plus* a technical co-founder who appears in commit history. 10–15:
credible technical team, no prior company. **8 (neutral)**: no bios found —
flagged as reduced coverage, not penalised. 0–7: bios found and actively
concerning (no relevant background at all).

**Deliberately passes on:** developer tools, model infrastructure, agent
frameworks, anything bottoms-up and free-to-start, and anything pre-product.
Those are real businesses; they are not this thesis.

**Topic fit:** matches "AI agents for SMBs" directly. Discriminates hard over
the current 15 — Async, Last Accounting Company and TryNearby rise; Plandex,
peerd and agent-desktop fall to Pass on component 1 alone.

---

## Thesis B — Picks and shovels for agent builders

> **Infrastructure and tooling that teams shipping AI agents adopt in
> production, judged by observable code adoption and the quality of developer
> scrutiny rather than by claims.**

The bet: the agent ecosystem is early enough that the tooling layer is
unsettled, and adoption by builders is the leading indicator of everything else.

**Components**

| # | Component | Weight | Evidence |
|---|---|---|---|
| 1 | Independent adoption | 30 | `github_repo` (forks, issues, `pushed_at`), `github_contributors` count, `hn_comment` from people saying they use it |
| 2 | Technical differentiation holds up | 20 | `hn_launch_text` vs the objections raised, and how founders answered |
| 3 | Quality of developer scrutiny | 20 | `hn_comment` points and substance — a thread of hard questions beats a thread of congratulations |
| 4 | Team technical depth | 20 | `github_contributors` overlap with the founder handle, `hn_profile` prior projects |
| 5 | Business model is not fatally at odds with being open | 10 | `github_repo` license, what the launch text says about monetisation |

**Bands for component 1** — 25–30: contributors beyond the founding team, recent
pushes, and at least one commenter describing production use. 15–24: active repo,
single-author commits, interested but non-committal discussion. 5–14: repo exists,
last push stale. **0–4**: no public repo identified.

**Honest weakness:** this is the easiest thesis to evidence and the least
differentiated. Our sources *are* GitHub and HN, so almost every candidate will
score something, and scores will cluster in the middle — the exact failure the
brief warns about. It also rewards open-source visibility over business quality,
which is a real bias, not a neutral one.

**Deliberately passes on:** anything sold to a non-technical buyer, closed-source
products with no public code surface, and services businesses.

**Topic fit:** would need the seed topic changed to something like "AI agent
infrastructure" — "AI agents for SMBs" would source companies this thesis rejects.

---

## Thesis C — Vertical AI into unglamorous operations

> **AI-native companies attacking operationally messy or regulated industries —
> insurance, accounting, compliance, logistics, public sector — where the
> defensibility is workflow depth and domain access, not model quality.**

The bet: horizontal AI capability commoditises fast; the durable advantage is
knowing the workflow well enough to be trusted with it, and having the licences,
integrations or relationships to be allowed near it.

**Components**

| # | Component | Weight | Evidence |
|---|---|---|---|
| 1 | Domain specificity and workflow depth | 30 | `company_profile` long description, `website_copy`, `hn_launch_text` |
| 2 | Regulatory or operational moat | 20 | evidence of licensing, certification, integrations, or being the system of record |
| 3 | Founder domain access | 20 | `founder` bios, `hn_profile` — prior time in the industry, not just in software |
| 4 | Evidence of live deployment | 20 | named customers under scrutiny, `hn_comment` from operators, `github_repo` recency |
| 5 | Momentum | 10 | batch recency, hiring, `pushed_at` |

**Bands for component 2** — 16–20: holds a licence, is the regulated entity, or
sits inside a certified workflow ("insurance carrier", "brokerage"). 10–15:
integrates deeply with the systems of record. 5–9: sells alongside the workflow.
0–4: a generic tool pointed at a vertical.

**Deliberately passes on:** all horizontal tooling and infrastructure, and
vertical companies whose only claim is a generic model applied to a niche.

**Topic fit:** partially matches "AI agents for SMBs" — the current run surfaced
Mount (insurance), TovenAI (compliance), Last Accounting Company and Stratum
(government backlog). Would work better with a topic like "AI for regulated
operations".

---

## Recommendation

**Thesis A.** Three reasons.

It **discriminates** over the corpus we actually have. Run against the current
15, it produces a real spread rather than a cluster — the developer tooling that
dominates recent YC batches fails component 1 honestly and loudly, and the
handful of SMB-focused companies rise to the top.

It is **scoreable from evidence we hold**, without needing revenue or funding
data we cannot see. "Can a reader name what stops being paid for?" is answerable
from a one-liner and a homepage.

It **agrees with the seed topic** already in use, so sourcing and scoring point
the same way with no re-run.

Thesis B is the tempting one and the weakest — easiest to evidence, most likely
to cluster, and biased toward open-source visibility over business quality.
Thesis C is genuinely good and would be the pick if the fund's topic were
regulated industries; it stays on file.
