# Investment thesis — Budget-line AI

> **We back seed-stage, AI-native software that takes over work an SMB or
> mid-market business is already paying for — a software subscription, an
> outsourced contractor, or a back-office role — sold to a non-technical
> operational buyer by a team with a working product in real users' hands.**

Every score in `data/analyses/` is measured against this document. Chosen from
three drafts; the alternatives and the reasoning are in
[thesis-candidates.md](thesis-candidates.md).

## The bet

At seed, the hard part of AI is not capability. Models are a commodity input and
getting cheaper. The hard part is distribution and willingness to pay.

A company taking over an existing line item does not have to create a category,
educate a market, or invent a budget. The buyer can already tell you what they
spend today, which means the sales conversation is a comparison rather than a
conversion. That is a structurally easier path to first revenue than anything
sold on novelty, and at seed the only thing worth underwriting is whether this
company can get to revenue at all.

The corollary is what makes this a thesis rather than a preference: we pass on
good companies. Developer tooling, model infrastructure and agent frameworks are
real businesses and several will be large. They are not this.

---

## How scoring works

**Only score what the pipeline can observe.** Revenue, funding, headcount growth
and retention are not available from Hacker News, the YC directory, GitHub or a
homepage. Every component below names the evidence it is scored from. A
component with no supporting evidence is scored at its neutral band, never
guessed.

**Claims and facts weigh differently.** A number on a landing page is a claim. The
same number in a founder's reply to a skeptic on HN is a claim made under
scrutiny. Commit history is a fact. Components state which they accept.

**Missing evidence caps confidence; it does not lower the score.** Otherwise the
pipeline scores its own scraping failures — a company would be marked down for
having a JavaScript homepage. Every memo carries an evidence-coverage figure
beside its score, and its effect on the call is asymmetric: low coverage can
never produce a *Take a meeting*, and can never turn a *Watch* into a *Pass*.

---

## Components

| # | Component | Weight |
|---|---|---|
| 1 | Displaced spend is nameable | 30 |
| 2 | Buyer is non-technical and operational | 15 |
| 3 | Product is in real users' hands | 20 |
| 4 | Founding team | 20 |
| 5 | Quality of outside reaction | 10 |
| 6 | Momentum | 5 |

### 1. Displaced spend is nameable — 30

*Evidence: `one_liner`, `company_profile`, `website_copy`, `hn_launch_text`.*

Can a reader name what stops being paid for? This component carries the thesis.

- **25–30** — Names a specific cost centre it takes over. "Agent-native
  accounting firm." "Autonomous insurance brokerage for small businesses."
- **15–24** — Names a real workflow but not a spend. "AI agents for compliance
  at institutional trading firms" — real work, unclear whose budget.
- **5–14** — Names a capability only. "AI agents for X."
- **0–4** — Horizontal infrastructure. No buyer budget implied.

### 2. Buyer is non-technical and operational — 15

*Evidence: as above, plus `keywords`.*

- **12–15** — Buyer is a business owner, ops lead, finance manager, clinic
  administrator. Someone who has a budget and does not write code.
- **7–11** — Mixed or unclear buyer; sold to a business but adopted by engineers.
- **0–6** — Buyer is a developer, ML engineer or platform team.

### 3. Product is in real users' hands — 20

*Evidence: `github_repo` recency, `hn_comment` from people describing use,
founder replies about production workloads. Landing-page customer claims are
noted but not scored on their own.*

- **16–20** — Independent evidence of real use: commenters describing their own
  deployment, active repo with outside contributors, founders answering
  specifics about production.
- **10–15** — Product demonstrably exists and is live, but all evidence of usage
  traces back to the company.
- **5–9** — Announced and shipped, no evidence anyone uses it.
- **0–4** — Waitlist, demo or concept.

### 4. Founding team — 20

*Evidence: `founder` bios, `hn_profile`, `github_contributors`.*

- **16–20** — A prior founder or exit, *or* deep operating background in the
  industry being sold into, *plus* a technical co-founder visible in commit
  history or answering technical questions publicly.
- **10–15** — Credible technical team, no prior company or domain history.
- **8 — neutral** — No founder information found. Flagged as reduced coverage.
  Not a penalty.
- **0–7** — Bios found and actively concerning: no relevant technical or domain
  background for what is being attempted.

### 5. Quality of outside reaction — 10

*Evidence: `hn_comment` — the substance of objections, and of the replies.*

A thread of hard questions answered well is worth more than a thread of
congratulations. This is also where the memo's risks come from: objections
raised by people with no stake are better than risks a model imagined.

- **8–10** — Substantive public scrutiny, engaged with directly and specifically.
- **5–7** — Real discussion, thin or evasive responses.
- **3–4** — Positive but shallow reaction.
- **0–2** — No discussion, or objections left unanswered.

### 6. Momentum — 5

*Evidence: batch recency, `pushed_at`, hiring signal.*

- **4–5** — Recent batch, active commits, hiring.
- **2–3** — Alive but quiet.
- **0–1** — Stale: no commits in six months, archived repo, or inactive status.

---

## From score to call

| Score | Call |
|---|---|
| **70+** | Take a meeting |
| **45–69** | Watch |
| **under 45** | Pass |

Three overrides, in order:

1. **Component 1 below 10 is a Pass regardless of total.** A company outside the
   thesis does not earn a meeting for having a strong team. This is the rule
   that makes the thesis binding rather than decorative.
2. **Evidence coverage below 0.5 caps the call at Watch.** We do not take
   meetings on companies we could not read.
3. **Low coverage never creates a Pass.** If the score is weak only because
   evidence is missing, the call is Watch.

## What would change our mind

Every memo ends with the 2–3 things that would move the call. These are not
free-form: they are the lowest-scoring components with the weakest supporting
evidence, stated as what would need to be true. A company scoring 18/30 on
component 1 should get "name the specific budget this replaces", not "grow
faster".

## What this thesis passes on

Developer tools and infrastructure. Model and agent frameworks. Anything
bottoms-up and free-to-start. Anything pre-product. Research-stage companies.
Horizontal assistants with no named buyer.

If most of a sourcing run scores below 45, that is the thesis working, not the
pipeline failing.
