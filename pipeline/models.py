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

SourceName = Literal["yc", "hn"]
SignalKind = Literal["team", "traction", "freshness"]


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
