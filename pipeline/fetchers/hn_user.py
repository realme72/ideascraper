"""The HN profile behind the launch post.

On Show HN and Launch HN the poster is nearly always a founder, and HN bios are
where people list what they built before. The Plandex poster's profile, for
instance, names a prior YC company — that is "founder background, prior exits"
for the cost of one request, and for HN-only candidates it is often the only
founder information that exists anywhere public.

The bio is free text a person wrote about themselves. It is stored as-is and
cited; stage 3 decides what it's worth.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from pipeline import cache
from pipeline.models import Candidate, EvidenceItem, Provenance
from pipeline.textutil import strip_html

USER_API = "https://hn.algolia.com/api/v1/users/{username}"
USER_URL = "https://news.ycombinator.com/user?id={username}"

_BIO_CAP = 700

# Set by the HN source when it builds the team signal in stage 1.
_HANDLE_RE = re.compile(r"@([A-Za-z0-9_\-]+)")


def hn_handle(candidate: Candidate) -> str | None:
    for signal in candidate.signals_of("team"):
        match = _HANDLE_RE.search(signal.label)
        if match:
            return match.group(1)
    return None


def load(client: httpx.Client, username: str, *, refresh: bool = False) -> dict | None:
    url = USER_API.format(username=username)

    def get() -> dict:
        return client.get(url).raise_for_status().json()

    try:
        return cache.fetch({"url": url}, get, refresh=refresh)
    except httpx.HTTPError:
        return None


def to_items(profile: dict) -> tuple[list[EvidenceItem], list[str]]:
    username = profile.get("username")
    bio = strip_html(profile.get("about"), _BIO_CAP)
    if not bio:
        return [], [f"HN user @{username} has no bio on their profile"]

    karma = profile.get("karma")
    prov = Provenance(
        source="hn",
        url=USER_URL.format(username=username),
        retrieved_at=datetime.now(timezone.utc),
    )
    return [
        EvidenceItem(
            kind="hn_profile",
            title=f"HN profile of @{username} ({karma} karma)",
            content=bio,
            value=float(karma) if karma is not None else None,
            provenance=prov,
        )
    ], []


def fetch(
    client: httpx.Client, candidate: Candidate, *, refresh: bool = False
) -> tuple[list[EvidenceItem], list[str]]:
    username = hn_handle(candidate)
    if not username:
        return [], []  # No HN post; hn_thread already reports that gap.

    profile = load(client, username, refresh=refresh)
    if not profile or not profile.get("username"):
        return [], [f"HN profile for @{username} could not be read"]
    return to_items(profile)
