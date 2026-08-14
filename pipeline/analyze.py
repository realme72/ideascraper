"""Stage 3 — Analysis.

    data/evidence/<slug>.json  ->  data/analyses/<slug>.json

The only stage that calls a model. It turns an evidence bundle into a structured
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
from datetime import datetime, timezone
from pathlib import Path

from pipeline import cache, thesis
from pipeline.models import Analysis, AnalysisDraft, ComponentJudgement, EvidenceBundle

INPUT_DIR = Path("data/evidence")
OUTPUT_DIR = Path("data/analyses")
PROMPT_PATH = Path(__file__).parent / "prompts" / "analysis.md"

MODEL = "claude-opus-5"
# Thinking is on by default on this model and shares the max_tokens budget with
# the response, so this is not sized to the analysis alone.
MAX_TOKENS = 16_000
EFFORT = "high"


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


def _call_model(system: str, user: str, *, refresh: bool) -> dict:
    """One structured-output call, cached to disk by prompt.

    The cached payload is committed, so a reviewer can regenerate every memo
    without a key and get byte-identical output.
    """

    def produce() -> dict:
        _load_env()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise MissingCredentials(
                "ANTHROPIC_API_KEY is not set and this analysis is not cached.\n"
                "Add it to .env (see .env.example), or run against the committed "
                "cache with the analyses that ship in this repo."
            )
        import anthropic  # imported lazily so stages 1, 2 and 4 need no SDK

        client = anthropic.Anthropic()
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            output_config={"effort": EFFORT},
            system=[
                # Stable across every company in the run; the evidence that
                # follows is not. Caching the rubric turns 15 calls into one
                # full-price prefix and fourteen cache reads.
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user}],
            output_format=AnalysisDraft,
        )
        if response.stop_reason == "refusal":
            raise AnalysisRefused(
                f"model declined to analyse this company ({response.stop_details})"
            )
        return response.parsed_output.model_dump()

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

    for path in bundles[:limit] if limit else bundles:
        bundle = EvidenceBundle.model_validate_json(path.read_text())
        analysis = analyse_one(bundle, refresh=refresh)
        (output_dir / f"{analysis.slug}.json").write_text(analysis.model_dump_json(indent=2))
        analyses.append(analysis)
        flag = f"  ⚠ {len(analysis.uncited_refs)} uncited" if analysis.uncited_refs else ""
        print(
            f"{analysis.name:26.26} {analysis.score:3}/100  "
            f"{analysis.coverage:.0%} coverage  {analysis.call:<15}{flag}"
        )

    return analyses
