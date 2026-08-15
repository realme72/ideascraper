"""The data shapes that move between stages.

These are the contract. Each stage reads one of these off disk and writes the
next one back, so the schemas are the only coupling between modules.

Every factual claim carries a `Provenance` with it — the brief requires a
reviewer to be able to spot-check an analysis and trust where its claims came
from, so provenance travels with the data rather than being reconstructed at
render time. A `Signal` cannot be built without one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceName = Literal["yc", "hn", "github", "web"]
SignalKind = Literal["team", "traction", "freshness"]

EvidenceKind = Literal[
    "founder",              # a named person, with whatever background is public
    "company_profile",      # structured facts from the YC directory page
    "website_copy",         # what the company says about itself, in its words
    "github_repo",          # stars, recency, language, license
    "github_contributors",  # who actually commits
    "hn_launch_text",       # the founders' own launch post
    "hn_comment",           # what outsiders said back
    "hn_profile",           # the posting founder's HN bio
]

# Trimming order when a bundle is over budget: the last kinds go first.
# Founders and the company's own description of itself are the least
# replaceable; the eighth-best HN comment is the most.
EVIDENCE_PRIORITY: tuple[EvidenceKind, ...] = (
    "founder",
    "company_profile",
    "hn_launch_text",
    "website_copy",
    "github_repo",
    "hn_profile",
    "github_contributors",
    "hn_comment",
)


class Provenance(BaseModel):
    """Where a piece of information came from, and when we fetched it.

    `url` must be a page a human can open to check the claim — not an API
    endpoint.
    """

    source: SourceName
    url: str
    retrieved_at: datetime


class Signal(BaseModel):
    """One observed, attributable fact about a candidate.

    `label` is written to be read as-is in a memo, so it carries its own units
    and context ("327 points on Hacker News", not "327"). `value` is the same
    fact as a number where one exists, for ranking and scoring — anything that
    needs to compare signals should read `value`, never parse `label`.
    """

    kind: SignalKind
    label: str
    value: float | None = None
    observed_at: datetime | None = None
    provenance: Provenance


class Candidate(BaseModel):
    """A startup worth looking at, as far as stage 1 can tell.

    Stage 1 makes no judgement about quality — `relevance` scores fit against
    the *topic that was searched for*, not against the investment thesis. Thesis
    scoring happens in stage 3, on evidence, by a model.
    """

    slug: str
    name: str
    website: str | None = None
    one_liner: str | None = None
    description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    relevance: float = 0.0
    signals: list[Signal] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)

    def signals_of(self, kind: SignalKind) -> list[Signal]:
        return [s for s in self.signals if s.kind == kind]

    @property
    def sources(self) -> list[str]:
        return sorted({p.source for p in self.provenance})


class EvidenceItem(BaseModel):
    """One piece of gathered material, attributable to a page.

    `content` is raw material for stage 3 to read — a founder's bio, a
    skeptical HN comment, a paragraph of landing-page copy. It is never a
    summary or a judgement; stage 2 does not interpret.
    """

    kind: EvidenceKind
    title: str
    content: str
    value: float | None = None
    observed_at: datetime | None = None
    provenance: Provenance

    def __len__(self) -> int:
        return len(self.content)


class EvidenceBundle(BaseModel):
    """Stage 2's output: everything gathered about one candidate.

    The bundle embeds the stage-1 `candidate` rather than referring to it, so
    stage 3 reads exactly one file per company and nothing has to be joined
    back together.

    `gaps` is the load-bearing field. It records what we looked for and could
    not find — a dead website, a company with no launch thread, a repo we
    couldn't identify. Stage 3 is shown the gaps alongside the evidence,
    because a model given silence will fill it with plausible invention, and
    "claims with no traceable source" is a named anti-pattern.
    """

    candidate: Candidate
    gathered_at: datetime
    items: list[EvidenceItem] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.candidate.slug

    @property
    def name(self) -> str:
        return self.candidate.name

    def items_of(self, kind: EvidenceKind) -> list[EvidenceItem]:
        return [i for i in self.items if i.kind == kind]

    @property
    def size(self) -> int:
        """Total characters of evidence — the stage 3 prompt budget."""
        return sum(len(i) for i in self.items)


class ComponentJudgement(BaseModel):
    """One rubric component, scored by the model.

    The model scores and justifies; it never sums, never picks a call, and never
    reasons about thresholds. `observed=False` means no evidence was found
    either way and the component took its documented neutral value — an absence
    in our research, not a finding about the company.
    """

    component_id: str
    score: int
    observed: bool
    rationale: str
    evidence_refs: list[str]
    what_would_change: str


class AnalysisDraft(BaseModel):
    """Exactly what the model is asked to return.

    Kept separate from `Analysis` so the boundary is visible: everything in this
    class is judgement, and everything `Analysis` adds on top is arithmetic.
    """

    team: str
    product: str
    market: str
    risks: list[str]
    open_questions: list[str]
    components: list[ComponentJudgement]


class Analysis(BaseModel):
    """Stage 3's output: the draft, plus everything computed from it.

    `score`, `coverage`, `call` and `what_would_change_my_mind` are derived in
    `pipeline.analyze` from `pipeline.thesis` — not returned by the model. A
    thesis a model can round up on is not being held consistently.
    """

    candidate: Candidate
    generated_at: datetime
    model: str

    team: str
    product: str
    market: str
    risks: list[str]
    open_questions: list[str]
    components: list[ComponentJudgement]

    score: int
    coverage: float
    call: str
    call_reason: str
    what_would_change_my_mind: list[str]

    gaps: list[str] = Field(default_factory=list)
    uncited_refs: list[str] = Field(default_factory=list)
    # Every page the evidence came from, carried forward so a memo can be
    # spot-checked without opening the evidence bundle. Stage 1's provenance
    # only records where the *candidate* was found, which is a smaller set.
    sources: list[Provenance] = Field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.candidate.slug

    @property
    def name(self) -> str:
        return self.candidate.name

    def component(self, component_id: str) -> ComponentJudgement | None:
        return next((c for c in self.components if c.component_id == component_id), None)


class CandidateSet(BaseModel):
    """Stage 1's output: everything found for one topic, ranked.

    `term_coverage` counts how many returned candidates matched each word of
    the query. A term sitting at zero means the search quietly ignored part of
    what was asked for — worth surfacing rather than hiding behind a ranked
    list that looks confident.
    """

    topic: str
    generated_at: datetime
    sources_used: list[str]
    term_coverage: dict[str, int] = Field(default_factory=dict)
    candidates: list[Candidate]

    def __len__(self) -> int:
        return len(self.candidates)
