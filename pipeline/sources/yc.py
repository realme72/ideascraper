"""Y Combinator company directory.

Read through the yc-oss mirror (https://yc-oss.github.io/api/), a daily rebuild
of YC's public directory. Used in preference to scraping ycombinator.com because
it is stable, versioned JSON and needs no key.

What YC gives us that HN doesn't: a clean company record — website, one-liner,
long description, batch, team size, industry tags — for every company, whether
or not anyone ever posted about it. What it doesn't give us: founder names, or
any evidence a product works. HN covers the second; stage 2 chases the first.

Only the most recent batches are searched. A seed-stage triage tool wants
companies that are still raising, and pulling four batches instead of all 6,000+
companies keeps a run to ~1MB.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from pipeline import cache
from pipeline.models import Candidate, Provenance, Signal

META_URL = "https://yc-oss.github.io/api/meta.json"

# Batch keys look like "winter-2025"; order seasons within a year so batches
# can be sorted newest-first.
_SEASON_RANK = {"winter": 0, "spring": 1, "summer": 2, "fall": 3}


def _batch_sort_key(slug: str) -> tuple[int, int]:
    """Sort key for a batch slug. Unparseable slugs sort oldest."""
    season, _, year = slug.partition("-")
    if not year.isdigit() or season not in _SEASON_RANK:
        return (-1, -1)  # e.g. "unspecified"
    return (int(year), _SEASON_RANK[season])


def recent_batches(client: httpx.Client, count: int, *, refresh: bool = False) -> list[dict]:
    """The `count` most recent YC batches, newest first."""
    meta = cache.fetch(
        {"url": META_URL},
        lambda: client.get(META_URL).raise_for_status().json(),
        refresh=refresh,
    )
    batches = meta.get("batches", {})
    newest = sorted(batches, key=_batch_sort_key, reverse=True)[:count]
    return [{"slug": slug, **batches[slug]} for slug in newest]


def fetch_batch(client: httpx.Client, batch: dict, *, refresh: bool = False) -> list[dict]:
    url = batch["api"]
    return cache.fetch(
        {"url": url},
        lambda: client.get(url).raise_for_status().json(),
        refresh=refresh,
    )


def _to_candidate(record: dict, batch_name: str) -> Candidate:
    page = record.get("url") or f"https://www.ycombinator.com/companies/{record['slug']}"
    prov = Provenance(source="yc", url=page, retrieved_at=datetime.now(timezone.utc))

    launched_at = record.get("launched_at")
    launched = (
        datetime.fromtimestamp(launched_at, tz=timezone.utc) if launched_at else None
    )

    signals = [
        Signal(
            kind="freshness",
            label=f"YC {batch_name} batch",
            observed_at=launched,
            provenance=prov,
        )
    ]

    team_size = record.get("team_size")
    if team_size:
        signals.append(
            Signal(
                kind="team",
                label=f"Team of {team_size}",
                value=float(team_size),
                provenance=prov,
            )
        )

    stage = record.get("stage")
    if stage:
        signals.append(
            Signal(kind="team", label=f"Stage: {stage}", provenance=prov)
        )

    # YC's own "top company" flag — assigned by YC on later performance, so it
    # is a genuine outside judgement rather than something the company claims.
    if record.get("top_company"):
        signals.append(
            Signal(kind="traction", label="Flagged a YC Top Company", provenance=prov)
        )

    if record.get("isHiring"):
        signals.append(
            Signal(kind="traction", label="Currently hiring", provenance=prov)
        )

    status = record.get("status")
    if status and status.lower() != "active":
        # Inactive/acquired matters more than active — active is the default.
        signals.append(
            Signal(kind="traction", label=f"YC status: {status}", provenance=prov)
        )

    keywords = [*(record.get("tags") or []), *(record.get("industries") or [])]

    return Candidate(
        slug=record["slug"],
        name=record["name"],
        website=record.get("website") or None,
        one_liner=record.get("one_liner") or None,
        description=record.get("long_description") or None,
        keywords=sorted({k for k in keywords if k}),
        signals=signals,
        provenance=[prov],
    )


def search(
    client: httpx.Client, batches: int = 4, *, refresh: bool = False
) -> list[Candidate]:
    """Every company in the most recent `batches` batches.

    Deliberately returns everything rather than filtering by topic — relevance
    ranking is `pipeline.source`'s job, so it can be tested and tuned in one
    place across both sources.
    """
    candidates: list[Candidate] = []
    for batch in recent_batches(client, batches, refresh=refresh):
        for record in fetch_batch(client, batch, refresh=refresh):
            if not record.get("slug") or not record.get("name"):
                continue
            candidates.append(_to_candidate(record, batch.get("name", batch["slug"])))
    return candidates
