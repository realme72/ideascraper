"""Turning fetched markup into text a model can read.

Shared by the HN adapters (whose payloads are HTML fragments) and the website
fetcher (whose payloads are whole documents).
"""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str | None, limit: int | None = None) -> str | None:
    """Plain text from an HTML fragment, truncated on a word boundary.

    Returns None for anything that reduces to nothing, so callers can treat
    "empty after cleaning" the same as "absent" — which for evidence purposes
    it is.
    """
    if not text:
        return None
    plain = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", text))).strip()
    if not plain:
        return None
    if limit and len(plain) > limit:
        plain = plain[:limit].rsplit(" ", 1)[0] + "…"
    return plain
