"""The YC company page — founders, and the facts the directory API leaves out.

The public directory mirror used in stage 1 carries no founder names, which was
the biggest gap coming out of sourcing (docs/parking-lot.md P2). The company
page itself does: it is an Inertia.js app that ships its props as a JSON blob in
a `data-page` attribute, so this reads structured data rather than scraping
rendered markup. That JSON also carries `github_url` and `year_founded`, which
saves guessing a repo later.

The shape can still change under us — it is not a documented API. A parse
failure produces a gap, never an exception.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone

import httpx

from pipeline import cache
from pipeline.models import Candidate, EvidenceItem, Provenance

PAGE_URL = "https://www.ycombinator.com/companies/{slug}"

_DATA_PAGE_RE = re.compile(r'data-page="([^"]+)"')
_BIO_CAP = 500
_PROFILE_CAP = 1500


def yc_slug(candidate: Candidate) -> str | None:
    """The company's YC slug, from whichever provenance points at the directory."""
    for prov in candidate.provenance:
        if prov.source == "yc":
            match = re.search(r"/companies/([^/?#]+)", prov.url)
            if match:
                return match.group(1)
    return None


def load(client: httpx.Client, slug: str, *, refresh: bool = False) -> dict | None:
    """The `company` prop from the page's embedded JSON, or None."""
    url = PAGE_URL.format(slug=slug)

    def get() -> str:
        return client.get(url).raise_for_status().text

    try:
        page = cache.fetch({"url": url}, get, refresh=refresh)
    except httpx.HTTPError:
        return None

    match = _DATA_PAGE_RE.search(page)
    if not match:
        return None
    try:
        payload = json.loads(html.unescape(match.group(1)))
    except json.JSONDecodeError:
        return None
    return payload.get("props", {}).get("company") or None


def _profile_text(company: dict) -> str:
    fields = [
        ("Batch", company.get("batch_name")),
        ("Founded", company.get("year_founded")),
        ("Team size", company.get("team_size")),
        ("Location", company.get("location")),
        ("Status", company.get("ycdc_status")),
        ("Website", company.get("website")),
        ("GitHub", company.get("github_url")),
        ("LinkedIn", company.get("linkedin_url")),
    ]
    lines = [f"{label}: {value}" for label, value in fields if value]
    if company.get("long_description"):
        lines.append("")
        lines.append(company["long_description"])
    return "\n".join(lines)[:_PROFILE_CAP]


def to_items(company: dict, slug: str) -> tuple[list[EvidenceItem], list[str]]:
    url = PAGE_URL.format(slug=slug)
    prov = Provenance(source="yc", url=url, retrieved_at=datetime.now(timezone.utc))

    items = [
        EvidenceItem(
            kind="company_profile",
            title=f"{company.get('name', slug)} — YC directory profile",
            content=_profile_text(company),
            provenance=prov,
        )
    ]

    founders = company.get("founders") or []
    for founder in founders:
        name = founder.get("full_name")
        if not name:
            continue
        title = founder.get("title") or "Founder"
        bio = (founder.get("founder_bio") or "").strip()
        links = [
            founder.get(k) for k in ("linkedin_url", "twitter_url") if founder.get(k)
        ]
        content = bio[:_BIO_CAP] or "No bio published on the YC profile."
        if links:
            content += "\nLinks: " + ", ".join(links)
        items.append(
            EvidenceItem(
                kind="founder",
                title=f"{name} — {title}",
                content=content,
                provenance=prov,
            )
        )

    gaps = []
    if not founders:
        gaps.append("YC company page lists no founders")
    elif not any((f.get("founder_bio") or "").strip() for f in founders):
        gaps.append("YC founder profiles have names but no published bios")

    return items, gaps


def fetch(
    client: httpx.Client, candidate: Candidate, *, refresh: bool = False
) -> tuple[list[EvidenceItem], list[str], dict]:
    """Returns (items, gaps, company) — `company` lets the caller reuse github_url."""
    slug = yc_slug(candidate)
    if not slug:
        # Not a YC company as far as stage 1 could tell. Not a gap worth
        # reporting: plenty of good candidates were never in a batch.
        return [], [], {}

    company = load(client, slug, refresh=refresh)
    if not company:
        return [], [f"YC company page for '{slug}' could not be read"], {}

    items, gaps = to_items(company, slug)
    return items, gaps, company
