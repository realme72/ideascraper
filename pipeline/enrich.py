"""Stage 2 — Enrichment.

    data/candidates.json  ->  data/evidence/<slug>.json

Gather the raw material an analyst would want before forming a view: who the
founders are, what the company claims, what the code shows, and what outsiders
said back. No judgement here — this stage collects and cites. Interpretation is
stage 3's job, and keeping the two apart is what stops "the site says they have
500 customers" from quietly becoming "they have 500 customers".

Missing data is normal, not exceptional. Coverage is deliberately uneven: a
YC-only candidate gets founder bios and no launch discussion, an HN-only
candidate gets the reverse. Every fetcher records what it looked for and could
not find, and those gaps travel with the evidence so stage 3 can see the shape
of its own ignorance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx

from pipeline.fetchers import github, hn_thread, hn_user, web, yc_page
from pipeline.models import (
    EVIDENCE_PRIORITY,
    Candidate,
    CandidateSet,
    EvidenceBundle,
    EvidenceItem,
)
from pipeline.source import USER_AGENT

INPUT_PATH = Path("data/candidates.json")
OUTPUT_DIR = Path("data/evidence")

# Characters of evidence per company. This is the stage 3 prompt budget: at
# roughly four characters per token, 10k lands near 2.5k tokens of evidence per
# memo, which leaves comfortable room for instructions and a structured reply.
# It is a first guess, and the right time to revisit it is when stage 3 exists
# and we can see what the model actually needs.
BUDGET = 10_000


def apply_budget(
    items: list[EvidenceItem], budget: int = BUDGET
) -> tuple[list[EvidenceItem], list[str]]:
    """Trim a bundle to `budget` characters, dropping the least useful first.

    Ordered by `EVIDENCE_PRIORITY`, then by value within a kind so the
    highest-voted comment survives before the fifth-best one. Anything dropped
    is reported as a gap — a silently truncated bundle would let stage 3 treat
    a partial picture as a complete one.
    """
    rank = {kind: i for i, kind in enumerate(EVIDENCE_PRIORITY)}
    ranked = sorted(items, key=lambda i: (rank.get(i.kind, 99), -(i.value or 0)))

    kept: list[EvidenceItem] = []
    total = 0
    dropped = 0
    for item in ranked:
        if kept and total + len(item) > budget:
            dropped += 1
            continue
        kept.append(item)
        total += len(item)

    notes = (
        [f"{dropped} lower-priority evidence items dropped to fit the {budget:,} character budget"]
        if dropped
        else []
    )
    return kept, notes


def enrich_one(
    client: httpx.Client, candidate: Candidate, *, refresh: bool = False
) -> EvidenceBundle:
    items: list[EvidenceItem] = []
    gaps: list[str] = []

    def collect(label: str, call) -> dict:
        """Run a fetcher. A fetcher that raises becomes a gap, never a crash."""
        try:
            result = call()
        except Exception as exc:  # noqa: BLE001 — one bad site must not stop the run
            gaps.append(f"{label} failed unexpectedly ({type(exc).__name__}: {exc})")
            return {}
        found, missing = result[0], result[1]
        items.extend(found)
        gaps.extend(missing)
        return result[2] if len(result) > 2 else {}

    company = collect("YC company page", lambda: yc_page.fetch(client, candidate, refresh=refresh))

    # The YC page hands us the company's own GitHub link, which beats guessing.
    # For HN-only candidates the "website" is often the repo itself.
    repo = github.repo_from_url(company.get("github_url"), candidate.website)
    collect("GitHub", lambda: github.fetch(client, repo, refresh=refresh))
    collect("HN thread", lambda: hn_thread.fetch(client, candidate, refresh=refresh))
    collect("HN profile", lambda: hn_user.fetch(client, candidate, refresh=refresh))
    collect("Website", lambda: web.fetch(client, candidate.website, refresh=refresh))

    items, budget_notes = apply_budget(items)
    gaps.extend(budget_notes)

    if not items:
        gaps.append("No evidence could be gathered from any source")

    return EvidenceBundle(
        candidate=candidate,
        gathered_at=datetime.now(timezone.utc),
        items=items,
        gaps=gaps,
    )


def run(
    *,
    limit: int | None = None,
    refresh: bool = False,
    input_path: Path = INPUT_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> list[EvidenceBundle]:
    if not input_path.exists():
        raise FileNotFoundError(
            f"{input_path} not found — run `python -m pipeline source \"<topic>\"` first"
        )

    candidate_set = CandidateSet.model_validate_json(input_path.read_text())
    candidates = candidate_set.candidates[:limit] if limit else candidate_set.candidates

    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    bundles: list[EvidenceBundle] = []

    with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
        for candidate in candidates:
            bundle = enrich_one(client, candidate, refresh=refresh)
            (output_dir / f"{bundle.slug}.json").write_text(bundle.model_dump_json(indent=2))
            bundles.append(bundle)
            print(
                f"{bundle.name:26.26} {len(bundle.items):2} items  "
                f"{bundle.size:>6,} chars  {len(bundle.gaps)} gaps"
            )

    return bundles
