"""The company's own homepage — the claim, in their words.

Homepage only. Multi-page crawling was tried during stage 2 probing and cut:
guessing `/about`, `/team`, `/pricing` returned about one hit per site, following
the homepage's own links returned nothing for sites whose nav is JS-rendered,
and single-page apps serve byte-identical text on every path — `voker.ai/pricing`
matched `voker.ai` exactly. That is four to six extra requests per candidate for
almost no new information, plus duplicate copy that stage 3 would mistake for
corroboration. See prompts/0004-enrichment.md.

What is left is one fetch that answers one question: what does this company say
it does? Everything a marketing site asserts is a claim, not a fact, so it is
stored under its own `website_copy` kind and cited to the page.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from pipeline import cache
from pipeline.models import EvidenceItem, Provenance

_COPY_CAP = 3000
# Below this, a page is a JavaScript shell rather than a document. trynearby.com
# returns 64 characters of text — recording that as "website copy" would hand
# stage 3 a site title and let it think it had read the site.
_MIN_USEFUL_TEXT = 300

_DROP_TAGS = ("script", "style", "noscript", "nav", "header", "footer", "svg", "form")


def extract_text(document: str) -> tuple[str | None, str]:
    """Return (page title, visible body text) for an HTML document."""
    soup = BeautifulSoup(document, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else None

    description = ""
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta and meta.get("content"):
        description = meta["content"].strip() + " "

    for tag in soup(list(_DROP_TAGS)):
        tag.decompose()
    body = " ".join(soup.get_text(" ").split())
    return title, (description + body).strip()


def allowed_by_robots(client: httpx.Client, url: str, *, refresh: bool = False) -> bool:
    """Honour robots.txt. Anything unreadable is treated as permitted.

    A missing or broken robots.txt is not a prohibition, and every site probed
    during development either allowed everything or had no file at all.
    """
    robots_url = urljoin(url, "/robots.txt")

    def get() -> str:
        response = client.get(robots_url)
        return response.text if response.status_code == 200 else ""

    try:
        body = cache.fetch({"url": robots_url}, get, refresh=refresh)
    except httpx.HTTPError:
        return True
    if not body:
        return True

    parser = RobotFileParser()
    parser.parse(body.splitlines())
    return parser.can_fetch("*", url)


def apex_of(host: str) -> str | None:
    """The registrable domain, when `host` is a subdomain of it.

    Stage 1 takes a website straight from whatever URL was posted, which is
    sometimes a subdomain that doesn't serve the marketing site —
    `chat.agentmail.to` refuses connections while `agentmail.to` is fine.
    Naive on multi-part suffixes like `.co.uk`; the cost of being wrong is one
    failed request that is recorded as a gap.
    """
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) > 2 else None


def _get(client: httpx.Client, url: str, *, refresh: bool) -> str | None:
    def call() -> str:
        return client.get(url).raise_for_status().text

    try:
        return cache.fetch({"url": url}, call, refresh=refresh)
    except httpx.HTTPError:
        return None


def fetch(
    client: httpx.Client, website: str | None, *, refresh: bool = False
) -> tuple[list[EvidenceItem], list[str]]:
    if not website:
        return [], ["No website recorded for this company"]

    host = urlparse(website).netloc.removeprefix("www.")
    if host.endswith("github.com"):
        # The "website" is the repo; the GitHub fetcher already covers it.
        return [], []

    if not allowed_by_robots(client, website, refresh=refresh):
        return [], [f"robots.txt at {host} disallows fetching the homepage"]

    gaps: list[str] = []
    document = _get(client, website, refresh=refresh)

    if document is None:
        apex = apex_of(host)
        if not apex:
            return [], [f"Website {host} could not be fetched"]
        website = f"https://{apex}"
        if not allowed_by_robots(client, website, refresh=refresh):
            return [], [f"robots.txt at {apex} disallows fetching the homepage"]
        document = _get(client, website, refresh=refresh)
        if document is None:
            return [], [f"Neither {host} nor {apex} could be fetched"]
        gaps.append(f"{host} did not respond; read {apex} instead")
        host = apex

    title, body = extract_text(document)
    if len(body) < _MIN_USEFUL_TEXT:
        gaps.append(
            f"Website {host} rendered only {len(body)} characters of text "
            "— likely a JavaScript app, so its content is unavailable"
        )
        return [], gaps

    prov = Provenance(
        source="web", url=website, retrieved_at=datetime.now(timezone.utc)
    )
    return [
        EvidenceItem(
            kind="website_copy",
            title=f"Homepage of {host}" + (f" — {title}" if title else ""),
            content=body[:_COPY_CAP],
            provenance=prov,
        )
    ], gaps
