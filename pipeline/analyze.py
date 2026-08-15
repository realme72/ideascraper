"""Stage 3 — Analysis.

    data/evidence/<slug>.json  ->  data/analyses/<slug>.json

The only stage that calls a model — Gemini, on Google AI Studio's free tier, so
the pipeline costs nothing to run. It turns an evidence bundle into a structured
analysis: team, product, market, risks, open questions, and a score against the
thesis in `pipeline.thesis`.

**The model judges; this module does the arithmetic.** The model scores each
rubric component against its bands, cites the evidence it used, and says what
would change its mind. Summing, coverage, the call bands and the three overrides
are computed here, from the same table the prompt was rendered from. A thesis a
model can round up on is not being held consistently — and this way the rubric
and the scorer cannot drift, because there is only one of them.

The model only ever sees evidence gathered in stage 2, and every judgement must
cite the items it rests on. Citations are checked against the bundle afterwards;
anything that doesn't match a real item is recorded on the analysis rather than
quietly passed through to a memo.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline import cache, thesis
from pipeline.models import Analysis, AnalysisDraft, ComponentJudgement, EvidenceBundle

INPUT_DIR = Path("data/evidence")
OUTPUT_DIR = Path("data/analyses")
PROMPT_PATH = Path(__file__).parent / "prompts" / "analysis.md"

# Overridable so a reviewer can trade quality against whatever their own free
# tier allows without editing code. Flash is the default because it is the tier
# most likely to be free, and this task is structured judgement over evidence
# that has already been gathered — not open-ended reasoning.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")

# Free-tier accounts are rate limited, and the ceiling is lower than the docs
# suggest — a 15-company run trips it partway through. Spacing alone is guesswork
# because the limit isn't published per model, so the real handling is the
# backoff below; this just avoids provoking it on every call.
CALL_SPACING_SECONDS = float(os.environ.get("GEMINI_CALL_SPACING", "4"))

# Free quota is a *daily* cap (observed: 20 requests/day on gemini-3.7-flash)
# and it is per model. Retrying rides out a per-minute limit; it cannot ride out
# a daily one, so retries stay low and the run reports partial progress instead
# of sleeping through a wall.
MAX_RATE_LIMIT_RETRIES = 3
FALLBACK_RETRY_SECONDS = 60.0

# The 429 body carries the exact wait the server wants: "Please retry in 43.9s".
# Honouring it beats guessing an interval.
_RETRY_HINT_RE = re.compile(r"retry in ([\d.]+)s")


class MissingCredentials(RuntimeError):
    pass


class AnalysisRefused(RuntimeError):
    pass


def _load_env(path: Path = Path(".env")) -> None:
    """Read KEY=value lines from .env without taking a dependency for it."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def build_system() -> str:
    """The system prompt: instructions plus the rubric, rendered from thesis.py.

    Identical for every company in a run, which is what makes it worth caching —
    see `analyse_one`.
    """
    return PROMPT_PATH.read_text().replace("{rubric}", thesis.render_rubric())


def build_user(bundle: EvidenceBundle) -> str:
    """The evidence for one company, as the model sees it."""
    c = bundle.candidate
    parts = [
        f"# {c.name}",
        f"Website: {c.website or 'unknown'}",
        f"One-liner: {c.one_liner or 'unknown'}",
        "",
        "## Signals found while sourcing",
    ]
    parts += [f"- [{s.kind}] {s.label}" for s in c.signals] or ["- none"]

    parts += ["", "## Evidence", ""]
    for item in bundle.items:
        parts += [
            f"### {item.title}",
            f"kind: {item.kind} · source: {item.provenance.url}",
            "",
            item.content,
            "",
        ]

    parts += ["## Gaps — what we looked for and could not find", ""]
    parts += [f"- {g}" for g in bundle.gaps] or ["- none"]

    parts += [
        "",
        "Score this company against the thesis. Cite the evidence titles above "
        "in `evidence_refs`.",
    ]
    return "\n".join(parts)


def _retry_delay(error: Exception) -> float:
    """How long the server asked us to wait, or a conservative default."""
    match = _RETRY_HINT_RE.search(str(error))
    return float(match.group(1)) + 1 if match else FALLBACK_RETRY_SECONDS


def _is_rate_limit(error: Exception) -> bool:
    """Whether an SDK error is a 429.

    Identified by the response, not the exception class. The SDK ships two
    unrelated `APIError` hierarchies — a public one in `google.genai.errors` and
    a private one under `_gaos` — and the interactions endpoint raises from the
    private one, so `except errors.APIError` silently catches nothing. Matching
    on status and body survives both that split and a future reshuffle.
    """
    if getattr(error, "status_code", None) == 429 or getattr(error, "code", None) == 429:
        return True
    text = str(error)
    return "429" in text or "too_many_requests" in text or "RESOURCE_EXHAUSTED" in text


def _create_with_backoff(client, **kwargs):
    """One model call, waiting out free-tier rate limits rather than dying on them.

    A fifteen-company run reliably exceeds the free quota partway through. Every
    completed analysis is cached, so a crash here loses nothing — but the run
    should finish unattended, and the server tells us exactly how long to wait.
    """
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            return client.interactions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — filtered by _is_rate_limit below
            if not _is_rate_limit(exc) or attempt == MAX_RATE_LIMIT_RETRIES - 1:
                raise
            delay = _retry_delay(exc)
            print(f"    rate limited — waiting {delay:.0f}s (retry {attempt + 1})", flush=True)
            time.sleep(delay)
    raise RuntimeError("unreachable")


def _call_model(system: str, user: str, *, refresh: bool) -> dict:
    """One structured-output call, cached to disk by prompt.

    The cached payload is committed, so a reviewer can regenerate every memo
    without a key of their own and get byte-identical output.

    The rubric and the evidence are concatenated into one input rather than
    split across a system and a user turn. On a paid provider that split buys
    prompt caching — the rubric is identical for all fifteen companies — but on
    a free tier there is no cost to save, and one input is the shape the SDK
    documents.
    """

    def produce() -> dict:
        _load_env()
        if not os.environ.get("GEMINI_API_KEY"):
            raise MissingCredentials(
                "GEMINI_API_KEY is not set and this analysis is not cached.\n"
                "Get a free key at https://aistudio.google.com/apikey (no billing "
                "required) and add it to .env — see .env.example.\n"
                "The analyses committed to this repo were generated with the "
                "cached responses in data/raw/, so reading them needs no key at all."
            )
        from google import genai  # imported lazily so stages 1, 2 and 4 need no SDK

        client = genai.Client()
        interaction = _create_with_backoff(
            client,
            model=MODEL,
            input=f"{system}\n\n---\n\n{user}",
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": AnalysisDraft.model_json_schema(),
            },
        )
        text = (interaction.output_text or "").strip()
        if not text:
            raise AnalysisRefused(
                "the model returned nothing for this company — most likely a safety "
                "filter or a truncated response"
            )
        # Validated against our own schema regardless of what the provider
        # enforced, so a malformed response fails loudly here rather than
        # becoming a memo full of empty sections.
        return AnalysisDraft.model_validate_json(text).model_dump()

    return cache.fetch({"model": MODEL, "system": system, "user": user}, produce, refresh=refresh)


def score(components: list[ComponentJudgement]) -> tuple[int, float]:
    """Total score, and the share of the rubric that rests on real evidence.

    Coverage is weighted: failing to observe the 30-point component costs more
    confidence than failing to observe the 5-point one.
    """
    total = 0
    observed_weight = 0
    for judgement in components:
        component = thesis.BY_ID.get(judgement.component_id)
        if not component:
            continue
        total += max(0, min(judgement.score, component.weight))
        if judgement.observed:
            observed_weight += component.weight
    return total, round(observed_weight / thesis.TOTAL_WEIGHT, 2)


def decide(total: int, coverage: float, components: list[ComponentJudgement]) -> tuple[str, str]:
    """Score to call, applying the three overrides in docs/thesis.md, in order."""
    gate = next((c for c in components if c.component_id == thesis.GATE_COMPONENT), None)
    if gate and gate.score < thesis.GATE_MINIMUM:
        return "Pass", (
            f"Scores {gate.score}/{thesis.BY_ID[thesis.GATE_COMPONENT].weight} on "
            "displaced spend — outside the thesis, so the call is Pass regardless "
            "of the total."
        )

    if total >= thesis.CALL_TAKE_MEETING:
        base = "Take a meeting"
    elif total >= thesis.CALL_WATCH:
        base = "Watch"
    else:
        base = "Pass"

    if coverage < thesis.COVERAGE_FLOOR:
        if base == "Take a meeting":
            return "Watch", (
                f"Scores {total}/100, but only {coverage:.0%} of the rubric rests on "
                "observed evidence. We do not take meetings on companies we could not read."
            )
        if base == "Pass":
            return "Watch", (
                f"Scores {total}/100 on {coverage:.0%} evidence coverage. The score is "
                "low because the evidence is thin, not because the company is — so this "
                "is a Watch, not a Pass."
            )

    return base, f"Scores {total}/100 with {coverage:.0%} evidence coverage."


def change_my_mind(components: list[ComponentJudgement], limit: int = 3) -> list[str]:
    """The 2-3 things that would move the call.

    Not free-form: the components that gave up the most weight, worst first, so
    a company losing 22 points on displaced spend is asked about that rather
    than about momentum.
    """
    gaps = []
    for judgement in components:
        component = thesis.BY_ID.get(judgement.component_id)
        if not component:
            continue
        missed = component.weight - max(0, min(judgement.score, component.weight))
        if missed > 0 and judgement.what_would_change.strip():
            gaps.append((missed, component.weight, judgement.what_would_change.strip()))
    gaps.sort(key=lambda g: (-g[0], -g[1]))
    return [text for _, _, text in gaps[:limit]]


def check_citations(components: list[ComponentJudgement], bundle: EvidenceBundle) -> list[str]:
    """Evidence references that don't match anything in the bundle.

    The model is told to cite item titles verbatim. Anything that doesn't
    resolve is recorded on the analysis and surfaced in the memo rather than
    passed through — an uncheckable citation is worse than none, because it
    looks checkable.
    """
    titles = {item.title.lower() for item in bundle.items}
    unmatched = []
    for judgement in components:
        for ref in judgement.evidence_refs:
            key = ref.strip().lower()
            if not key or key in titles:
                continue
            if any(key in title or title in key for title in titles):
                continue  # close enough — the model paraphrased a long title
            unmatched.append(ref.strip())
    return sorted(set(unmatched))


def _is_cached(bundle: EvidenceBundle, *, refresh: bool) -> bool:
    """Whether this company's analysis would come from disk rather than the API."""
    if refresh:
        return False
    key = cache.key({"model": MODEL, "system": build_system(), "user": build_user(bundle)})
    return cache.get(key) is not None


def _evidence_sources(bundle: EvidenceBundle) -> list:
    """One entry per distinct page the evidence came from, in bundle order."""
    seen: dict[str, object] = {}
    for item in bundle.items:
        seen.setdefault(item.provenance.url, item.provenance)
    return list(seen.values())


def analyse_one(bundle: EvidenceBundle, *, refresh: bool = False) -> Analysis:
    draft = AnalysisDraft.model_validate(
        _call_model(build_system(), build_user(bundle), refresh=refresh)
    )
    total, coverage = score(draft.components)
    call, reason = decide(total, coverage, draft.components)

    return Analysis(
        candidate=bundle.candidate,
        generated_at=datetime.now(timezone.utc),
        model=MODEL,
        team=draft.team,
        product=draft.product,
        market=draft.market,
        risks=draft.risks,
        open_questions=draft.open_questions,
        components=draft.components,
        score=total,
        coverage=coverage,
        call=call,
        call_reason=reason,
        what_would_change_my_mind=change_my_mind(draft.components),
        gaps=bundle.gaps,
        uncited_refs=check_citations(draft.components, bundle),
        sources=_evidence_sources(bundle),
    )


def run(
    *,
    limit: int | None = None,
    refresh: bool = False,
    input_dir: Path = INPUT_DIR,
    output_dir: Path = OUTPUT_DIR,
) -> list[Analysis]:
    bundles = sorted(input_dir.glob("*.json"))
    if not bundles:
        raise FileNotFoundError(
            f"no evidence in {input_dir} — run `python -m pipeline enrich` first"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    analyses: list[Analysis] = []
    called_model = False

    for path in bundles[:limit] if limit else bundles:
        bundle = EvidenceBundle.model_validate_json(path.read_text())
        # Space out live calls to stay inside a free-tier per-minute limit.
        # Cached companies cost nothing and are not paced.
        if called_model and not _is_cached(bundle, refresh=refresh):
            time.sleep(CALL_SPACING_SECONDS)
        called_model = called_model or not _is_cached(bundle, refresh=refresh)

        try:
            analysis = analyse_one(bundle, refresh=refresh)
        except Exception as exc:  # noqa: BLE001 — re-raised unless it's quota
            if not _is_rate_limit(exc):
                raise
            # Everything analysed so far is already cached and written. Stopping
            # cleanly beats a traceback that hides how much actually succeeded.
            remaining = len(bundles) - len(analyses)
            print(
                f"\nFree-tier quota exhausted for {MODEL} after {len(analyses)} "
                f"of {len(bundles)} companies.\n"
                f"{remaining} left. Nothing is lost — completed analyses are cached, "
                "so re-running picks up where this stopped.\n"
                "Either wait for the daily quota to reset, or set GEMINI_MODEL to a "
                "model with its own budget (quota is per model).",
            )
            break
        (output_dir / f"{analysis.slug}.json").write_text(analysis.model_dump_json(indent=2))
        analyses.append(analysis)
        flag = f"  ⚠ {len(analysis.uncited_refs)} uncited" if analysis.uncited_refs else ""
        print(
            f"{analysis.name:26.26} {analysis.score:3}/100  "
            f"{analysis.coverage:.0%} coverage  {analysis.call:<15}{flag}"
        )

    return analyses
