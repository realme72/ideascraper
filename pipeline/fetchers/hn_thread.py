"""The Hacker News launch thread.

The most useful source in the pipeline, and the cheapest. A launch thread gives
two things nothing else does:

  - The founders' own pitch, at length, written for a skeptical technical
    audience rather than for a landing page.
  - Substantive public criticism. The highest-voted comments on a launch are
    routinely the sharpest available objections to the business, written by
    people with no stake in it. That is the honest raw material for "what would
    kill this?", and it beats asking a model to imagine risks.

Founder replies are pulled separately from anywhere in the tree, because how a
founder answers the hardest question in their own thread is signal about the
team that no bio captures.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from pipeline import cache
from pipeline.models import Candidate, EvidenceItem, Provenance
from pipeline.textutil import strip_html

ITEM_API = "https://hn.algolia.com/api/v1/items/{id}"
ITEM_URL = "https://news.ycombinator.com/item?id={id}"

_LAUNCH_CAP = 2500
_COMMENT_CAP = 700
_TOP_COMMENTS = 5
_FOUNDER_REPLIES = 3


def hn_item_id(candidate: Candidate) -> str | None:
    for prov in candidate.provenance:
        if prov.source == "hn":
            match = re.search(r"id=(\d+)", prov.url)
            if match:
                return match.group(1)
    return None


def load(client: httpx.Client, item_id: str, *, refresh: bool = False) -> dict | None:
    url = ITEM_API.format(id=item_id)

    def get() -> dict:
        return client.get(url).raise_for_status().json()

    try:
        return cache.fetch({"url": url}, get, refresh=refresh)
    except httpx.HTTPError:
        return None


def _walk(node: dict):
    """Every comment in the tree, depth-first."""
    for child in node.get("children") or []:
        yield child
        yield from _walk(child)


def _comment_item(comment: dict, *, founder: bool) -> EvidenceItem | None:
    text = strip_html(comment.get("text"), _COMMENT_CAP)
    if not text:
        return None

    author = comment.get("author") or "unknown"
    points = comment.get("points")
    posted = (
        datetime.fromtimestamp(comment["created_at_i"], tz=timezone.utc)
        if comment.get("created_at_i")
        else None
    )
    prov = Provenance(
        source="hn",
        url=ITEM_URL.format(id=comment["id"]),
        retrieved_at=datetime.now(timezone.utc),
    )
    role = "founder reply" if founder else "comment"
    score = f", {points} points" if points else ""
    return EvidenceItem(
        kind="hn_comment",
        title=f"HN {role} by @{author}{score}",
        content=text,
        value=float(points) if points else None,
        observed_at=posted,
        provenance=prov,
    )


def to_items(thread: dict) -> tuple[list[EvidenceItem], list[str]]:
    items: list[EvidenceItem] = []
    gaps: list[str] = []

    story_author = thread.get("author")
    posted = (
        datetime.fromtimestamp(thread["created_at_i"], tz=timezone.utc)
        if thread.get("created_at_i")
        else None
    )
    prov = Provenance(
        source="hn",
        url=ITEM_URL.format(id=thread["id"]),
        retrieved_at=datetime.now(timezone.utc),
    )

    launch_text = strip_html(thread.get("text"), _LAUNCH_CAP)
    if launch_text:
        items.append(
            EvidenceItem(
                kind="hn_launch_text",
                title=f"Launch post by @{story_author}",
                content=launch_text,
                value=float(thread.get("points") or 0),
                observed_at=posted,
                provenance=prov,
            )
        )
    else:
        gaps.append("HN post links straight to the product with no written pitch")

    top_level = thread.get("children") or []
    outsiders = [c for c in top_level if c.get("author") != story_author]
    # In practice this sort is inert: Algolia's /items/ endpoint returns
    # `points: null` for comments, so every key is 0 and Python's stable sort
    # preserves the API's own ordering. That happens to be what we want — it is
    # HN's ranked display order, already sorted by what the crowd upvoted. The
    # key stays for the occasional thread where points do come through.
    outsiders.sort(key=lambda c: c.get("points") or 0, reverse=True)

    seen: set[int] = set()
    for comment in outsiders[:_TOP_COMMENTS]:
        item = _comment_item(comment, founder=False)
        if item:
            items.append(item)
            seen.add(comment["id"])

    replies = [
        c for c in _walk(thread) if c.get("author") == story_author and c["id"] not in seen
    ]
    for comment in replies[:_FOUNDER_REPLIES]:
        item = _comment_item(comment, founder=True)
        if item:
            items.append(item)

    if not outsiders:
        gaps.append("HN launch drew no discussion — nobody publicly reacted")
    if not replies:
        gaps.append("Founders did not reply in their own HN thread")

    return items, gaps


def fetch(
    client: httpx.Client, candidate: Candidate, *, refresh: bool = False
) -> tuple[list[EvidenceItem], list[str]]:
    item_id = hn_item_id(candidate)
    if not item_id:
        # No launch thread at all. Worth recording — it means the only outside
        # traction signal available to stage 3 is missing.
        return [], ["No Hacker News launch thread found for this company"]

    thread = load(client, item_id, refresh=refresh)
    if not thread:
        return [], [f"HN thread {item_id} could not be read"]
    return to_items(thread)
