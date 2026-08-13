"""Stage 1 — Sourcing.

    topic query  ->  data/candidates.json

Given a seed input (a topic like "AI agents for SMBs"), collect 10-20 candidate
startups. Each candidate needs a name, website, one-line description, a
founders/team signal where findable, and at least one freshness or traction
signal.

Two sources, both free and keyless: the YC directory and Hacker News. The
adapters in `pipeline.sources` fetch and attach provenance; this module does the
three things that have to happen across sources — merge duplicates, rank by
relevance to the topic, and cut the list.

**Relevance here is topic fit, not quality.** A high score means "this is the
kind of company you asked about", nothing more. Judging the company is stage 3's
job, and it happens against the thesis, on evidence, with a model. Keeping the
two apart is what stops a keyword match from quietly becoming an investment
opinion.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import httpx

from pipeline.models import Candidate, CandidateSet
from pipeline.sources import hn, yc

OUTPUT_PATH = Path("data/candidates.json")
USER_AGENT = "ideascraper/0.1 (VC triage prototype; contact: gauravbharti586@gmail.com)"

# Dropped before matching — they carry no topic information and would otherwise
# match nearly every company.
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "with", "your",
}

# Abbreviations and phrasings that will never string-match the query term.
# Values are matched as *phrases* against normalised text, so "small business"
# works even though it tokenises as two words. Kept deliberately short: every
# entry is a thumb on the scale, so each has to earn its place rather than this
# becoming a general-purpose synonym list.
_ALIASES = {
    "smb": {"small business", "small and medium", "sme", "mid market", "main street", "local business"},
    "ai": {"llm", "genai", "artificial intelligence"},
    "agent": {"agentic"},
    "b2b": {"enterprise"},
    "devtool": {"developer tool", "sdk"},
}

# Tokens that appear in company names as decoration rather than description.
# Without this, every third YC company "matches" the term `ai` on its name
# alone at the highest field weight, which is not signal about anything.
_GENERIC_NAME_TOKENS = {
    "ai", "labs", "lab", "inc", "io", "hq", "app", "tech", "technologies",
    "systems", "software", "co", "corp", "the",
}

# Field weights. A topic word in the company name is worth more than the same
# word buried in a paragraph of marketing copy.
_FIELD_WEIGHTS = (("name", 3.0), ("one_liner", 2.0), ("keywords", 1.5), ("description", 1.0))
_MAX_FIELD_WEIGHT = max(w for _, w in _FIELD_WEIGHTS)

_WORD_RE = re.compile(r"[a-z0-9]+")


def _singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _terms(text: str | None) -> set[str]:
    """Query-side tokenisation: lowercase words, singularised, stopwords gone."""
    if not text:
        return set()
    return {_singular(w) for w in _WORD_RE.findall(text.lower())} - _STOPWORDS


def _normalize(text: str) -> str:
    """Candidate-side: punctuation to spaces, so "mid-market" can match "mid market"."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@lru_cache(maxsize=256)
def _matcher(variants: frozenset[str]) -> re.Pattern[str]:
    """Word-boundary matcher for a term and its aliases, tolerating plurals.

    Boundaries matter: without them `ai` matches "chain" and "email". The plural
    group has to allow "es" as well as "s", or the alias "small business" fails
    to match the far more common "small businesses".
    """
    alts = "|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True))
    return re.compile(rf"\b(?:{alts})(?:e?s)?\b")


def _field_text(candidate: Candidate, field: str) -> str:
    if field == "keywords":
        return " ".join(candidate.keywords)
    if field == "name":
        # Strip decorative tokens so "Agnost AI" doesn't score on `ai`.
        tokens = [t for t in _WORD_RE.findall(candidate.name.lower()) if t not in _GENERIC_NAME_TOKENS]
        return " ".join(tokens)
    return getattr(candidate, field) or ""


def relevance(candidate: Candidate, query_terms: set[str]) -> float:
    """How well a candidate matches the topic, in 0.0-1.0.

    Each query term scores the weight of the strongest field it appears in; the
    total is normalised by the best possible score. Term matching, not
    embeddings — the brief rules out a vector DB, and a score a partner can
    reason about beats one they can't.
    """
    if not query_terms:
        return 0.0

    total = 0.0
    for term in query_terms:
        pattern = _matcher(frozenset({term} | _ALIASES.get(term, set())))
        for field, weight in _FIELD_WEIGHTS:
            if pattern.search(_normalize(_field_text(candidate, field))):
                total += weight
                break  # strongest field only; don't pay twice for one term
    return round(total / (len(query_terms) * _MAX_FIELD_WEIGHT), 3)


def term_coverage(candidates: list[Candidate], query_terms: set[str]) -> dict[str, int]:
    """How many candidates matched each query term.

    A zero here is the honest answer to "did you actually search for that?" —
    for "AI agents for SMBs" against a corpus that is mostly developer tooling,
    `smb` legitimately comes back near-empty, and a partner should see that
    rather than assume the list is SMB-focused.
    """
    counts = {}
    for term in sorted(query_terms):
        pattern = _matcher(frozenset({term} | _ALIASES.get(term, set())))
        counts[term] = sum(
            1
            for c in candidates
            if any(
                pattern.search(_normalize(_field_text(c, field)))
                for field, _ in _FIELD_WEIGHTS
            )
        )
    return counts


def _best_value(candidate: Candidate, kind: str) -> float:
    return max((s.value or 0.0 for s in candidate.signals_of(kind)), default=0.0)


def _freshest(candidate: Candidate) -> float:
    stamps = [s.observed_at for s in candidate.signals if s.observed_at]
    return max(s.timestamp() for s in stamps) if stamps else 0.0


def rank_key(candidate: Candidate) -> tuple:
    """Sort order. Topic fit first, then how much we actually know.

    Ties on relevance are common — plenty of companies match "AI agents" equally
    well — so the tie-breaks carry real weight. Corroboration by both sources
    comes first (two independent records beat one), then measured traction, then
    recency.
    """
    return (
        -candidate.relevance,
        -len(candidate.sources),
        -_best_value(candidate, "traction"),
        -_freshest(candidate),
        candidate.name.lower(),
    )


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower().removeprefix("www.").split(":")[0]
    return host or None


def _merge_key(candidate: Candidate) -> str:
    """What counts as "the same company" across sources.

    Domain first — two records pointing at the same site are the same company.
    Name only as a fallback, because HN names are inferred and collide more.
    """
    domain = _domain(candidate.website)
    if domain and not domain.endswith("github.com"):
        return f"domain:{domain}"
    return f"name:{re.sub(r'[^a-z0-9]', '', candidate.name.lower())}"


def _merge(base: Candidate, other: Candidate) -> Candidate:
    """Fold `other` into `base`. `base` is whichever source was seen first."""
    seen_signals = {(s.kind, s.label) for s in base.signals}
    base.signals.extend(
        s for s in other.signals if (s.kind, s.label) not in seen_signals
    )

    seen_urls = {p.url for p in base.provenance}
    base.provenance.extend(p for p in other.provenance if p.url not in seen_urls)

    base.website = base.website or other.website
    base.one_liner = base.one_liner or other.one_liner
    base.keywords = sorted(set(base.keywords) | set(other.keywords))
    if other.description and len(other.description) > len(base.description or ""):
        base.description = other.description
    return base


def merge(*groups: list[Candidate]) -> list[Candidate]:
    """Deduplicate across and within sources, preserving argument order.

    Earlier groups win on conflicting fields, so callers pass the source with
    the cleaner records first.
    """
    merged: dict[str, Candidate] = {}
    for group in groups:
        for candidate in group:
            key = _merge_key(candidate)
            if key in merged:
                _merge(merged[key], candidate)
            else:
                merged[key] = candidate
    return list(merged.values())


def _worth_keeping(candidate: Candidate, min_hn_points: float) -> bool:
    """Drop candidates that can't support a claim.

    Two bars. Every candidate must carry a freshness or traction signal — the
    brief requires it, so a record that can't produce one isn't a candidate no
    matter how well it matches the topic.

    And an HN-only candidate must have cleared `min_hn_points`. A Show HN post
    that got 2 points is not evidence anyone reacted to the product; it is the
    kind of result that pads a list without informing it. Candidates
    corroborated by the YC directory skip this bar — being in the batch is
    independent of how a launch post happened to do.
    """
    if not (candidate.signals_of("traction") or candidate.signals_of("freshness")):
        return False
    if "yc" not in candidate.sources:
        return _best_value(candidate, "traction") >= min_hn_points
    return True


def run(
    topic: str,
    *,
    limit: int = 15,
    batches: int = 4,
    min_relevance: float = 0.2,
    min_hn_points: float = 10,
    refresh: bool = False,
    output: Path = OUTPUT_PATH,
) -> CandidateSet:
    """Search both sources for `topic` and write the ranked candidate set."""
    query_terms = _terms(topic)
    headers = {"User-Agent": USER_AGENT}

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        # YC first: its records are cleaner, so it wins on conflicting fields.
        yc_candidates = yc.search(client, batches=batches, refresh=refresh)
        hn_candidates = hn.search(client, topic, refresh=refresh)

    candidates = merge(yc_candidates, hn_candidates)
    for candidate in candidates:
        candidate.relevance = relevance(candidate, query_terms)

    ranked = [
        c
        for c in candidates
        if c.relevance >= min_relevance and _worth_keeping(c, min_hn_points)
    ]
    ranked.sort(key=rank_key)

    kept = ranked[:limit]
    result = CandidateSet(
        topic=topic,
        generated_at=datetime.now(timezone.utc),
        sources_used=["yc", "hn"],
        term_coverage=term_coverage(kept, query_terms),
        candidates=kept,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.model_dump_json(indent=2))
    return result
