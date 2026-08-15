"""Tests for memo rendering.

Rendering is deterministic templating, so these check the things a partner
relies on being there: the call above the fold, the score breakdown matching the
rubric, and — most importantly — that nothing the pipeline failed to find gets
quietly dropped on the way to the page.
"""

from datetime import datetime, timezone

import pytest

from pipeline import memo, thesis
from pipeline.models import Analysis, Candidate, ComponentJudgement, Provenance

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def analysis(**overrides) -> Analysis:
    base = dict(
        candidate=Candidate(
            slug="acme",
            name="Acme",
            website="https://acme.com",
            one_liner="Bookkeeping for cafes",
        ),
        generated_at=NOW,
        model="test-model",
        team="Two founders, ex-Stripe.",
        product="Does the books for small cafes.",
        market="UK cafes paying a bookkeeper monthly.",
        risks=["Regulatory change could kill it"],
        open_questions=["How many paying customers?"],
        components=[
            ComponentJudgement(
                component_id=c.id,
                score=c.weight,
                observed=True,
                rationale="because",
                evidence_refs=["Homepage"],
                what_would_change="do the thing",
            )
            for c in thesis.COMPONENTS
        ],
        score=100,
        coverage=1.0,
        call="Take a meeting",
        call_reason="Scores 100/100.",
        what_would_change_my_mind=["Name the budget"],
    )
    return Analysis(**{**base, **overrides})


class TestRender:
    def test_call_is_in_the_title(self):
        assert memo.render(analysis()).splitlines()[0] == "# Acme — Take a meeting"

    def test_score_and_coverage_are_above_the_fold(self):
        head = "\n".join(memo.render(analysis()).splitlines()[:8])
        assert "100/100" in head and "100% evidence coverage" in head

    def test_every_rubric_component_appears_with_its_weight(self):
        rendered = memo.render(analysis())
        for c in thesis.COMPONENTS:
            assert c.name in rendered and f"/{c.weight} |" in rendered

    def test_an_unobserved_component_says_so_rather_than_looking_bad(self):
        a = analysis()
        a.components[0].observed = False
        assert "No evidence found; scored at the neutral band" in memo.render(a)

    def test_gaps_are_printed_not_hidden(self):
        rendered = memo.render(analysis(gaps=["No launch thread found"]))
        assert "What we could not find" in rendered
        assert "No launch thread found" in rendered

    def test_unverified_citations_are_flagged_loudly(self):
        rendered = memo.render(analysis(uncited_refs=["TechCrunch profile"]))
        assert "Unverified references" in rendered
        assert "TechCrunch profile" in rendered

    def test_a_clean_memo_has_no_warning_section(self):
        assert "Unverified references" not in memo.render(analysis())

    def test_sources_prefer_evidence_provenance_over_candidate_provenance(self):
        # The reader checking a founder claim needs the page the bio came from,
        # not the search result that surfaced the company.
        a = analysis(
            sources=[Provenance(source="web", url="https://acme.com", retrieved_at=NOW)]
        )
        a.candidate.provenance = [
            Provenance(source="yc", url="https://ycombinator.com/companies/acme", retrieved_at=NOW)
        ]
        rendered = memo.render(a)
        assert "https://acme.com" in rendered
        assert "https://ycombinator.com/companies/acme" in rendered

    def test_pipe_characters_in_rationale_do_not_break_the_table(self):
        a = analysis()
        a.components[0].rationale = "revenue | margin"
        assert "revenue \\| margin" in memo.render(a)

    def test_footer_states_the_call_was_computed_not_chosen(self):
        assert "not chosen by the model" in memo.render(analysis())

    @pytest.mark.parametrize("call", ["Take a meeting", "Watch", "Pass"])
    def test_every_call_renders(self, call):
        assert call in memo.render(analysis(call=call))


class TestIndex:
    def test_ranks_by_score_descending(self):
        rendered = memo.render_index([analysis(score=40, call="Pass"), analysis(score=90)])
        assert rendered.index("90/100") < rendered.index("40/100")

    def test_shows_the_gate_component_so_the_ordering_reads_correctly(self):
        # A company can outscore one above it and still be a Pass. Without the
        # thesis-fit column that looks like a bug rather than the rule working.
        gate = thesis.BY_ID[thesis.GATE_COMPONENT]
        rendered = memo.render_index([analysis()])
        assert "Thesis fit" in rendered
        assert f"{gate.weight}/{gate.weight}" in rendered
        assert gate.name.lower() in rendered

    def test_counts_passes(self):
        rendered = memo.render_index([analysis(call="Pass"), analysis(call="Watch")])
        assert "1 of 2 are a Pass" in rendered

    def test_links_to_each_memo(self):
        assert "(acme.md)" in memo.render_index([analysis()])


class TestRun:
    def test_missing_analyses_points_at_the_command_that_makes_them(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="python -m pipeline analyze"):
            memo.run(input_dir=tmp_path)

    def test_writes_one_memo_per_analysis_plus_an_index(self, tmp_path):
        (tmp_path / "a.json").write_text(analysis().model_dump_json())
        out = tmp_path / "out"
        memo.run(input_dir=tmp_path, output_dir=out)
        assert (out / "acme.md").exists() and (out / "index.md").exists()
