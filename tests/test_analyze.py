"""Tests for scoring, the call bands, and citation checking.

These cover everything stage 3 decides *without* the model — which is
deliberately most of it. The model scores components and says why; the
arithmetic, the overrides and the citation check are the fund's, and they are
the parts that have to be right every time.

No network. `analyse_one` is exercised against a stubbed model call.
"""

import pytest

from pipeline import analyze, thesis
from pipeline.models import Candidate, ComponentJudgement, EvidenceBundle, EvidenceItem
from tests.test_source import NOW, prov


def judgement(component_id, score, observed=True, refs=(), change="do the thing"):
    return ComponentJudgement(
        component_id=component_id,
        score=score,
        observed=observed,
        rationale="because",
        evidence_refs=list(refs),
        what_would_change=change,
    )


def full_marks(**overrides):
    """One judgement per component at full weight, before overrides."""
    scores = {c.id: c.weight for c in thesis.COMPONENTS}
    scores.update(overrides)
    return [judgement(cid, s) for cid, s in scores.items()]


class TestRubric:
    def test_weights_total_one_hundred(self):
        assert thesis.TOTAL_WEIGHT == 100

    def test_every_component_has_a_neutral_within_its_weight(self):
        for c in thesis.COMPONENTS:
            assert 0 <= c.neutral <= c.weight

    def test_call_bands_are_ordered(self):
        assert thesis.CALL_TAKE_MEETING > thesis.CALL_WATCH > 0

    def test_rendered_rubric_names_every_component_and_weight(self):
        rendered = thesis.render_rubric()
        for c in thesis.COMPONENTS:
            assert c.id in rendered and f"{c.weight} points" in rendered


class TestScore:
    def test_sums_component_scores(self):
        assert analyze.score(full_marks())[0] == 100

    def test_clamps_a_score_above_the_component_weight(self):
        # The model returning 40 on a 30-point component must not inflate the total.
        assert analyze.score([judgement("displaced_spend", 40)])[0] == 30

    def test_clamps_a_negative_score(self):
        assert analyze.score([judgement("momentum", -5)])[0] == 0

    def test_ignores_an_unknown_component_id(self):
        assert analyze.score([judgement("invented_component", 50)])[0] == 0

    def test_coverage_is_weighted_not_counted(self):
        # Missing the 30-point component costs more coverage than missing the 5-pointer.
        heavy = analyze.score([
            judgement(c.id, c.weight, observed=(c.id != "displaced_spend"))
            for c in thesis.COMPONENTS
        ])[1]
        light = analyze.score([
            judgement(c.id, c.weight, observed=(c.id != "momentum"))
            for c in thesis.COMPONENTS
        ])[1]
        assert heavy == 0.7 and light == 0.95

    def test_full_coverage_when_everything_observed(self):
        assert analyze.score(full_marks())[1] == 1.0


class TestDecide:
    def test_strong_score_takes_a_meeting(self):
        call, _ = analyze.decide(75, 1.0, full_marks())
        assert call == "Take a meeting"

    def test_middling_score_is_a_watch(self):
        assert analyze.decide(50, 1.0, full_marks())[0] == "Watch"

    def test_weak_score_is_a_pass(self):
        assert analyze.decide(30, 1.0, full_marks(displaced_spend=15))[0] == "Pass"

    def test_outside_the_thesis_is_a_pass_however_good_the_rest(self):
        # Override 1 — the rule that makes the thesis binding rather than decorative.
        components = full_marks(displaced_spend=5)
        call, reason = analyze.decide(analyze.score(components)[0], 1.0, components)
        assert call == "Pass" and "outside the thesis" in reason

    def test_low_coverage_caps_a_meeting_at_watch(self):
        # Override 2 — we don't take meetings on companies we couldn't read.
        call, reason = analyze.decide(85, 0.3, full_marks())
        assert call == "Watch" and "could not read" in reason

    def test_low_coverage_never_creates_a_pass(self):
        # Override 3 — a thin file scores as thin, not as bad.
        call, reason = analyze.decide(30, 0.3, full_marks())
        assert call == "Watch" and "thin" in reason

    def test_the_thesis_gate_outranks_the_coverage_floor(self):
        # A company outside the thesis is a Pass even on thin evidence: the gate
        # is about what the company is, not about what we failed to find.
        components = full_marks(displaced_spend=2)
        assert analyze.decide(20, 0.2, components)[0] == "Pass"

    @pytest.mark.parametrize("total,expected", [(70, "Take a meeting"), (69, "Watch"), (45, "Watch"), (44, "Pass")])
    def test_band_boundaries(self, total, expected):
        assert analyze.decide(total, 1.0, full_marks())[0] == expected


class TestChangeMyMind:
    def test_ranks_by_points_given_up_not_by_raw_score(self):
        components = [
            judgement("displaced_spend", 10, change="name the budget this replaces"),
            judgement("momentum", 0, change="ship something"),
        ]
        assert analyze.change_my_mind(components)[0] == "name the budget this replaces"

    def test_ignores_components_at_full_marks(self):
        assert analyze.change_my_mind(full_marks()) == []

    def test_returns_at_most_three(self):
        components = [judgement(c.id, 0) for c in thesis.COMPONENTS]
        assert len(analyze.change_my_mind(components)) == 3


class TestCheckCitations:
    def bundle(self, *titles):
        return EvidenceBundle(
            candidate=Candidate(slug="acme", name="Acme"),
            gathered_at=NOW,
            items=[
                EvidenceItem(kind="founder", title=t, content="x", provenance=prov())
                for t in titles
            ],
        )

    def test_exact_reference_matches(self):
        b = self.bundle("Ben Smith — Co-Founder")
        assert analyze.check_citations([judgement("momentum", 5, refs=["Ben Smith — Co-Founder"])], b) == []

    def test_case_and_whitespace_are_forgiven(self):
        b = self.bundle("Ben Smith — Co-Founder")
        assert analyze.check_citations([judgement("momentum", 5, refs=["  ben smith — co-founder "])], b) == []

    def test_a_paraphrased_substring_matches(self):
        b = self.bundle("GitHub repo plandex-ai/plandex")
        assert analyze.check_citations([judgement("momentum", 5, refs=["plandex-ai/plandex"])], b) == []

    def test_an_invented_reference_is_reported(self):
        b = self.bundle("Ben Smith — Co-Founder")
        found = analyze.check_citations([judgement("momentum", 5, refs=["TechCrunch profile"])], b)
        assert found == ["TechCrunch profile"]

    def test_duplicates_are_reported_once(self):
        b = self.bundle("Real item")
        components = [judgement("momentum", 5, refs=["Ghost"]), judgement("founding_team", 5, refs=["Ghost"])]
        assert analyze.check_citations(components, b) == ["Ghost"]


class TestAnalyseOne:
    def test_derives_score_call_and_change_list_from_the_draft(self, monkeypatch):
        draft = {
            "team": "two founders", "product": "does a thing", "market": "SMBs",
            "risks": ["could fail"], "open_questions": ["how many customers?"],
            "components": [
                judgement(c.id, c.weight, refs=["Homepage of acme.com"]).model_dump()
                for c in thesis.COMPONENTS
            ],
        }
        monkeypatch.setattr(analyze, "_call_model", lambda *a, **k: draft)

        bundle = EvidenceBundle(
            candidate=Candidate(slug="acme", name="Acme"),
            gathered_at=NOW,
            items=[EvidenceItem(kind="website_copy", title="Homepage of acme.com", content="x", provenance=prov())],
            gaps=["no repo"],
        )
        analysis = analyze.analyse_one(bundle)

        assert analysis.score == 100
        assert analysis.call == "Take a meeting"
        assert analysis.coverage == 1.0
        assert analysis.what_would_change_my_mind == []
        assert analysis.uncited_refs == []
        assert analysis.gaps == ["no repo"]
        assert analysis.model == "claude-opus-5"


class TestPrompt:
    def test_system_prompt_embeds_the_rubric(self):
        system = analyze.build_system()
        assert "{rubric}" not in system
        assert "displaced_spend" in system and thesis.THESIS_STATEMENT in system

    def test_user_prompt_carries_evidence_gaps_and_sources(self):
        bundle = EvidenceBundle(
            candidate=Candidate(slug="acme", name="Acme", one_liner="Bookkeeping for cafes"),
            gathered_at=NOW,
            items=[EvidenceItem(kind="founder", title="A Founder", content="ex-Stripe", provenance=prov())],
            gaps=["no launch thread"],
        )
        user = analyze.build_user(bundle)
        assert "Bookkeeping for cafes" in user
        assert "A Founder" in user and "ex-Stripe" in user
        assert "no launch thread" in user
        assert prov().url in user
