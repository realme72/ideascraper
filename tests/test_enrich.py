"""Tests for bundle assembly: the text budget and the failure path.

The budget matters because stage 3 pays for every character. The failure path
matters more: one dead website must not stop a fifteen-company run, and
whatever went wrong has to end up in `gaps` rather than being swallowed.
"""

import pytest

from pipeline import enrich
from pipeline.models import Candidate, EvidenceItem
from tests.test_source import prov


def item(kind, size, value=None, title="x"):
    return EvidenceItem(
        kind=kind, title=title, content="c" * size, value=value, provenance=prov()
    )


class TestApplyBudget:
    def test_everything_within_budget_is_kept(self):
        items = [item("founder", 100), item("hn_comment", 100)]
        kept, notes = enrich.apply_budget(items, budget=1000)
        assert len(kept) == 2 and notes == []

    def test_comments_are_dropped_before_founders(self):
        items = [item("hn_comment", 400, title="comment"), item("founder", 400, title="founder")]
        kept, _ = enrich.apply_budget(items, budget=500)
        assert [i.title for i in kept] == ["founder"]

    def test_the_loudest_comment_survives_the_quietest(self):
        items = [item("hn_comment", 400, value=2, title="quiet"),
                 item("hn_comment", 400, value=300, title="loud")]
        kept, _ = enrich.apply_budget(items, budget=500)
        assert [i.title for i in kept] == ["loud"]

    def test_dropping_is_reported_as_a_gap(self):
        items = [item("founder", 400), item("hn_comment", 400), item("hn_comment", 400)]
        _, notes = enrich.apply_budget(items, budget=500)
        assert "2 lower-priority evidence items dropped" in notes[0]

    def test_one_oversized_item_is_still_kept(self):
        # Better a single over-budget bundle than an empty one.
        kept, _ = enrich.apply_budget([item("founder", 5000)], budget=1000)
        assert len(kept) == 1

    def test_output_is_ordered_by_priority(self):
        items = [item("hn_comment", 10, title="c"), item("founder", 10, title="f"),
                 item("website_copy", 10, title="w")]
        kept, _ = enrich.apply_budget(items, budget=1000)
        assert [i.title for i in kept] == ["f", "w", "c"]


class TestEnrichOne:
    def test_a_fetcher_that_raises_becomes_a_gap_not_a_crash(self, monkeypatch):
        def explode(*args, **kwargs):
            raise ConnectionError("host unreachable")

        for module in ("yc_page", "github", "hn_thread", "hn_user", "web"):
            monkeypatch.setattr(getattr(enrich, module), "fetch", explode)

        bundle = enrich.enrich_one(None, Candidate(slug="acme", name="Acme"))
        assert bundle.items == []
        assert len(bundle.gaps) == 6  # five fetchers, plus "no evidence at all"
        assert all("ConnectionError" in g for g in bundle.gaps[:5])

    def test_one_broken_fetcher_does_not_lose_the_others(self, monkeypatch):
        monkeypatch.setattr(enrich.yc_page, "fetch", lambda *a, **k: (_ for _ in ()).throw(ValueError("bad json")))
        monkeypatch.setattr(enrich.github, "fetch", lambda *a, **k: ([item("github_repo", 50)], []))
        for module in ("hn_thread", "hn_user", "web"):
            monkeypatch.setattr(getattr(enrich, module), "fetch", lambda *a, **k: ([], []))

        bundle = enrich.enrich_one(None, Candidate(slug="acme", name="Acme"))
        assert len(bundle.items) == 1
        assert any("bad json" in g for g in bundle.gaps)

    def test_a_bundle_with_nothing_in_it_says_so(self, monkeypatch):
        for module in ("yc_page", "github", "hn_thread", "hn_user", "web"):
            monkeypatch.setattr(getattr(enrich, module), "fetch", lambda *a, **k: ([], []))
        bundle = enrich.enrich_one(None, Candidate(slug="acme", name="Acme"))
        assert bundle.gaps == ["No evidence could be gathered from any source"]


class TestRun:
    def test_missing_input_points_at_the_command_that_makes_it(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="python -m pipeline source"):
            enrich.run(input_path=tmp_path / "nope.json")
