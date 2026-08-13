"""GitHub — activity rather than claims.

Stars are a popularity number and easy to over-read, so the more useful fields
here are the boring ones: when the repo was last pushed to, how many people have
ever committed, and whether it is archived. A repo with 15k stars and no commit
in a year says something a landing page never will.

Contributors also identify people. Where the top contributor is the same handle
that posted the launch to HN, that is independent confirmation that a named
founder actually writes the code — which is exactly what "technical depth" is
asking about.

Unauthenticated the API allows 60 requests an hour, which covers a full run of
15 candidates twice over. `GITHUB_TOKEN` in `.env` raises it to 5,000.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import httpx

from pipeline import cache
from pipeline.models import EvidenceItem, Provenance

REPO_API = "https://api.github.com/repos/{repo}"
CONTRIBUTORS_API = "https://api.github.com/repos/{repo}/contributors?per_page=10"
REPO_URL = "https://github.com/{repo}"

_REPO_RE = re.compile(r"github\.com/([^/\s]+/[^/\s#?]+)", re.I)


def repo_from_url(*urls: str | None) -> str | None:
    """First `owner/repo` found in any of the given URLs."""
    for url in urls:
        if not url:
            continue
        match = _REPO_RE.search(url)
        if match:
            return match.group(1).removesuffix(".git").rstrip("/")
    return None


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def load(client: httpx.Client, repo: str, *, refresh: bool = False) -> tuple[dict | None, list]:
    def get_repo() -> dict:
        return client.get(REPO_API.format(repo=repo), headers=_headers()).raise_for_status().json()

    def get_contributors() -> list:
        response = client.get(CONTRIBUTORS_API.format(repo=repo), headers=_headers())
        return response.json() if response.status_code == 200 else []

    try:
        meta = cache.fetch({"url": REPO_API.format(repo=repo)}, get_repo, refresh=refresh)
    except httpx.HTTPError:
        return None, []
    try:
        contributors = cache.fetch(
            {"url": CONTRIBUTORS_API.format(repo=repo)}, get_contributors, refresh=refresh
        )
    except httpx.HTTPError:
        contributors = []
    return meta, contributors


def to_items(repo: str, meta: dict, contributors: list) -> tuple[list[EvidenceItem], list[str]]:
    prov = Provenance(
        source="github",
        url=REPO_URL.format(repo=repo),
        retrieved_at=datetime.now(timezone.utc),
    )

    pushed_raw = meta.get("pushed_at")
    pushed = (
        datetime.fromisoformat(pushed_raw.replace("Z", "+00:00")) if pushed_raw else None
    )
    stars = meta.get("stargazers_count") or 0

    facts = [
        f"Stars: {stars}",
        f"Forks: {meta.get('forks_count')}",
        f"Open issues: {meta.get('open_issues_count')}",
        f"Language: {meta.get('language')}",
        f"Created: {(meta.get('created_at') or '')[:10]}",
        f"Last pushed: {(pushed_raw or '')[:10]}",
        f"License: {(meta.get('license') or {}).get('spdx_id')}",
        f"Archived: {meta.get('archived')}",
    ]
    if meta.get("description"):
        facts.append(f"Description: {meta['description']}")
    if meta.get("topics"):
        facts.append("Topics: " + ", ".join(meta["topics"][:12]))

    items = [
        EvidenceItem(
            kind="github_repo",
            title=f"GitHub repo {repo}",
            content="\n".join(facts),
            value=float(stars),
            observed_at=pushed,
            provenance=prov,
        )
    ]

    gaps = []
    if contributors:
        lines = [
            f"{c.get('login')}: {c.get('contributions')} commits"
            for c in contributors[:10]
            if c.get("login")
        ]
        items.append(
            EvidenceItem(
                kind="github_contributors",
                title=f"Top contributors to {repo}",
                content="\n".join(lines),
                value=float(len(contributors)),
                provenance=prov,
            )
        )
    else:
        gaps.append(f"GitHub contributor list for {repo} was unavailable")

    if meta.get("archived"):
        gaps.append(f"GitHub repo {repo} is archived")

    return items, gaps


def fetch(
    client: httpx.Client, repo: str | None, *, refresh: bool = False
) -> tuple[list[EvidenceItem], list[str]]:
    if not repo:
        return [], ["No public GitHub repository identified for this company"]

    meta, contributors = load(client, repo, refresh=refresh)
    if not meta or meta.get("message"):
        return [], [f"GitHub repo {repo} could not be read"]
    return to_items(repo, meta, contributors)
