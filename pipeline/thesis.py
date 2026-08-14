"""The thesis, in the form the code scores against.

`docs/thesis.md` is the human document — the argument, the bet, and what this
fund passes on. This module is the same rubric as data, and it is the single
source of truth for anything executable: the prompt sent to the model is
rendered from these components, and the scorer sums these weights. Neither can
drift from the other, because there is only one of them.

Two things deliberately live here rather than in the model's hands:

  - **The arithmetic.** The model scores each component against its bands and
    says why. Summing, coverage, the call bands and the overrides are computed
    in `pipeline.analyze` from this table. A thesis a model can round up on is
    not being held consistently.
  - **The neutral band.** Every component names the score it takes when no
    evidence was found. Missing evidence must not read as a bad company — see
    docs/thesis.md, and D8 in docs/decisions.md.
"""

from __future__ import annotations

from dataclasses import dataclass

CALL_TAKE_MEETING = 70
CALL_WATCH = 45

# Override 1: the thesis is binding, not decorative. A company outside it does
# not earn a meeting on the strength of its team.
GATE_COMPONENT = "displaced_spend"
GATE_MINIMUM = 10

# Override 2: we do not take meetings on companies we could not read.
COVERAGE_FLOOR = 0.5


@dataclass(frozen=True)
class Band:
    low: int
    high: int
    description: str


@dataclass(frozen=True)
class Component:
    id: str
    name: str
    weight: int
    question: str
    evidence: str
    bands: tuple[Band, ...]
    neutral: int
    neutral_note: str

    def render(self) -> str:
        lines = [
            f"### {self.name} — {self.weight} points (id: `{self.id}`)",
            "",
            self.question,
            "",
            f"*Score from: {self.evidence}*",
            "",
        ]
        lines += [f"- **{b.low}–{b.high}** — {b.description}" for b in self.bands]
        lines += ["", f"- **{self.neutral} (neutral)** — {self.neutral_note}"]
        return "\n".join(lines)


COMPONENTS: tuple[Component, ...] = (
    Component(
        id="displaced_spend",
        name="Displaced spend is nameable",
        weight=30,
        question=(
            "Can a reader name what stops being paid for? This component carries the "
            "thesis — it is the difference between a company selling into a budget that "
            "already exists and one that has to create it."
        ),
        evidence="the company's one-liner, YC profile, homepage copy, and HN launch text",
        bands=(
            Band(25, 30, 'Names a specific cost centre it takes over. "Agent-native accounting firm." "Autonomous insurance brokerage for small businesses."'),
            Band(15, 24, 'Names a real workflow but not a spend. "AI agents for compliance at institutional trading firms" — real work, unclear whose budget.'),
            Band(5, 14, 'Names a capability only. "AI agents for X."'),
            Band(0, 4, "Horizontal infrastructure. No buyer budget implied."),
        ),
        neutral=8,
        neutral_note=(
            "No usable description found at all. Rare — a one-liner is almost always "
            "available, so prefer a real band."
        ),
    ),
    Component(
        id="operational_buyer",
        name="Buyer is non-technical and operational",
        weight=15,
        question="Who signs for this, and do they write code?",
        evidence="the one-liner, homepage copy, industry tags, and HN discussion",
        bands=(
            Band(12, 15, "A business owner, ops lead, finance manager, clinic administrator. Someone with a budget who does not write code."),
            Band(7, 11, "Mixed or unclear buyer; sold to a business but adopted by engineers."),
            Band(0, 6, "The buyer is a developer, ML engineer or platform team."),
        ),
        neutral=7,
        neutral_note="No indication of who the customer is.",
    ),
    Component(
        id="in_users_hands",
        name="Product is in real users' hands",
        weight=20,
        question=(
            "Is there evidence anyone outside the company uses this? Landing-page "
            "customer claims are noted but do not score on their own — a claim under "
            "public scrutiny is worth more than a claim on a homepage."
        ),
        evidence="GitHub commit recency and contributors, HN commenters describing their own use, founder replies about production workloads",
        bands=(
            Band(16, 20, "Independent evidence of real use: commenters describing their own deployment, outside contributors, founders answering specifics about production."),
            Band(10, 15, "Product demonstrably exists and is live, but all evidence of usage traces back to the company."),
            Band(5, 9, "Announced and shipped, no evidence anyone uses it."),
            Band(0, 4, "Waitlist, demo or concept."),
        ),
        neutral=10,
        neutral_note="Nothing found either way — no repo, no discussion, no readable site.",
    ),
    Component(
        id="founding_team",
        name="Founding team",
        weight=20,
        question="Has this team done something that makes them the right people for this?",
        evidence="YC founder bios, HN profiles (which often name prior companies), GitHub contributor overlap with the founder's handle",
        bands=(
            Band(16, 20, "A prior founder or exit, or deep operating background in the industry being sold into, plus a technical co-founder visible in commit history or answering technical questions publicly."),
            Band(10, 15, "Credible technical team, no prior company or domain history."),
            Band(0, 7, "Bios found and actively concerning: no relevant technical or domain background for what is being attempted."),
        ),
        neutral=8,
        neutral_note=(
            "No founder information found. This is a gap in our evidence, not a "
            "judgement about the team — do not score 0-7 for absence."
        ),
    ),
    Component(
        id="outside_reaction",
        name="Quality of outside reaction",
        weight=10,
        question=(
            "Did anyone with no stake in this push back, and how did the founders "
            "handle it? A thread of hard questions answered well beats a thread of "
            "congratulations."
        ),
        evidence="HN comments and the founders' replies to them",
        bands=(
            Band(8, 10, "Substantive public scrutiny, engaged with directly and specifically."),
            Band(5, 7, "Real discussion, thin or evasive responses."),
            Band(3, 4, "Positive but shallow reaction."),
            Band(0, 2, "Objections left unanswered."),
        ),
        neutral=5,
        neutral_note="No launch thread exists. Common for YC-only candidates — not a mark against them.",
    ),
    Component(
        id="momentum",
        name="Momentum",
        weight=5,
        question="Is this company still moving?",
        evidence="YC batch recency, GitHub last-push date, hiring signal",
        bands=(
            Band(4, 5, "Recent batch, active commits, hiring."),
            Band(2, 3, "Alive but quiet."),
            Band(0, 1, "Stale: no commits in six months, archived repo, or inactive status."),
        ),
        neutral=3,
        neutral_note="No dated signal available.",
    ),
)

BY_ID = {c.id: c for c in COMPONENTS}
TOTAL_WEIGHT = sum(c.weight for c in COMPONENTS)

THESIS_STATEMENT = (
    "We back seed-stage, AI-native software that takes over work an SMB or "
    "mid-market business is already paying for — a software subscription, an "
    "outsourced contractor, or a back-office role — sold to a non-technical "
    "operational buyer by a team with a working product in real users' hands."
)


def render_rubric() -> str:
    """The rubric as markdown, for the model's system prompt."""
    parts = [f"## The thesis\n\n> {THESIS_STATEMENT}", "", "## Components", ""]
    parts += [c.render() + "\n" for c in COMPONENTS]
    return "\n".join(parts)
