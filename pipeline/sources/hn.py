"""Hacker News, via the public Algolia search API.

No key, no OAuth, generous rate limits. Two tags matter here:

  - `launch_hn` — YC companies' official launch posts. Strict title format, and
    the batch is right there in it.
  - `show_hn`   — everyone else shipping something. Freeform titles, so the
    company name has to be inferred.

What HN gives us that the YC directory doesn't: evidence that a product exists
and that people reacted to it. Points and comment count are a crude proxy for
attention, but they are *outside* signal — the company doesn't control them —
which is exactly what the brief means by a traction signal.

Only the last ~18 months are searched. A launch from 2022 is not a seed-stage
sourcing lead, and leaving it in would pad the candidate list with companies
that have long since raised or died.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

from pipeline import cache
from pipeline.models import Candidate, Provenance, Signal
from pipeline.textutil import strip_html

SEARCH_URL = "https://hn.algolia.com/api/v1/search"
ITEM_URL = "https://news.ycombinator.com/item?id={id}"

# "Launch HN: Skyvern (YC S23) – open-source AI agent for browser automations"
_LAUNCH_RE = re.compile(
    r"^Launch HN:\s*(?P<name>.+?)\s*\(YC\s*(?P<batch>[WSF]\d{2})\)\s*[–—-]\s*(?P<desc>.+)$"
)
# "Show HN: Foo – does a thing".  The separator is the only reliable landmark.
_SHOW_RE = re.compile(r"^Show HN:\s*(?P<rest>.+)$")
_SEPARATOR_RE = re.compile(r"\s+[–—]\s+|\s+-\s+|:\s+")

def _clean(text: str | None, limit: int = 800) -> str | None:
    """HN story text is HTML fragments. Strip to plain text for storage."""
    return strip_html(text, limit)


def _name_from_url(url: str | None) -> str | None:
    """Best-effort company name from a product URL.

    Works because Show HN posts almost always link to the product itself, so the
    domain *is* the company. GitHub is special-cased — the repo name is the
    project, `github.com` is not.
    """
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if not host:
        return None
    if host.endswith("github.com"):
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            return parts[1].replace("-", " ").replace("_", " ").title()
        return None
    label = host.split(".")[0]
    if label in {"app", "docs", "blog", "get", "try", "my"}:
        parts = host.split(".")
        label = parts[1] if len(parts) > 2 else label
    return label.replace("-", " ").title()


def _parse_title(title: str, url: str | None) -> tuple[str | None, str | None]:
    """Return (company_name, one_liner) for an HN post title."""
    launch = _LAUNCH_RE.match(title)
    if launch:
        return launch.group("name"), launch.group("desc")

    show = _SHOW_RE.match(title)
    if not show:
        return _name_from_url(url), title

    rest = show.group("rest")
    parts = _SEPARATOR_RE.split(rest, maxsplit=1)
    if len(parts) == 2:
        head, tail = parts
        # A short leading fragment is a name; a long one is just a sentence.
        if len(head.split()) <= 4:
            return head.strip(), tail.strip()
    # No usable name in the title — fall back to the product's domain.
    return _name_from_url(url), rest.strip()


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"


def _to_candidate(hit: dict) -> Candidate | None:
    title = hit.get("title")
    if not title:
        return None

    website = hit.get("url")
    name, one_liner = _parse_title(title, website)
    if not name:
        # A text-only post we can't attribute to a company is not a candidate.
        return None

    discussion = ITEM_URL.format(id=hit["objectID"])
    prov = Provenance(source="hn", url=discussion, retrieved_at=datetime.now(timezone.utc))
    posted = (
        datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc)
        if hit.get("created_at_i")
        else None
    )

    points = hit.get("points") or 0
    comments = hit.get("num_comments") or 0
    signals = [
        Signal(
            kind="traction",
            label=f"{points} points and {comments} comments on Hacker News",
            value=float(points),
            observed_at=posted,
            provenance=prov,
        )
    ]

    if posted:
        signals.append(
            Signal(
                kind="freshness",
                label=f"Launched on HN {posted:%d %b %Y}",
                observed_at=posted,
                provenance=prov,
            )
        )

    author = hit.get("author")
    if author:
        # On Show HN and Launch HN the poster is nearly always a founder.
        signals.append(
            Signal(
                kind="team",
                label=f"Posted and answered questions as HN user @{author}",
                observed_at=posted,
                provenance=prov,
            )
        )

    launch = _LAUNCH_RE.match(title)
    if launch:
        signals.append(
            Signal(
                kind="freshness",
                label=f"YC {launch.group('batch')} batch",
                observed_at=posted,
                provenance=prov,
            )
        )

    return Candidate(
        slug=_slugify(name),
        name=name.strip(),
        website=website,
        one_liner=one_liner,
        description=_clean(hit.get("story_text")),
        signals=signals,
        provenance=[prov],
    )


def _query(
    client: httpx.Client, topic: str, tag: str, hits: int, since: datetime, refresh: bool
) -> list[dict]:
    params = {
        "query": topic,
        "tags": tag,
        "hitsPerPage": hits,
        "numericFilters": f"created_at_i>{int(since.timestamp())}",
    }
    payload = cache.fetch(
        {"url": SEARCH_URL, "params": params},
        lambda: client.get(SEARCH_URL, params=params).raise_for_status().json(),
        refresh=refresh,
    )
    return payload.get("hits", [])


def search(
    client: httpx.Client,
    topic: str,
    *,
    hits_per_tag: int = 40,
    since_days: int = 540,
    refresh: bool = False,
) -> list[Candidate]:
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    candidates: list[Candidate] = []
    for tag in ("launch_hn", "show_hn"):
        for hit in _query(client, topic, tag, hits_per_tag, since, refresh):
            candidate = _to_candidate(hit)
            if candidate:
                candidates.append(candidate)
    return candidates
