"""Tests for relevance scoring, merging and ranking.

These cover the judgement calls, not the plumbing. Each test below exists
because the behaviour it pins down was wrong at some point during stage 1 — the
first run of the pipeline ranked purely alphabetically because every candidate
tied, and `smb` silently matched nothing.
"""

from datetime import datetime, timedelta, timezone

import pytest

from pipeline import source
from pipeline.models import Candidate, Provenance, Signal

NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


def candidate(name="Acme", one_liner=None, description=None, keywords=(), website=None):
    return Candidate(
        slug=name.lower(),
        name=name,
        website=website,
        one_liner=one_liner,
        description=description,
        keywords=list(keywords),
    )


def prov(source_name="yc", url="https://example.com/a"):
    return Provenance(source=source_name, url=url, retrieved_at=NOW)


def signal(kind="traction", label="x", value=None, observed_at=None, source_name="yc"):
    return Signal(
        kind=kind,
        label=label,
        value=value,
        observed_at=observed_at,
        provenance=prov(source_name),
    )


TOPIC = "AI agents for SMBs"


def terms():
    return source._terms(TOPIC)


class TestTerms:
    def test_drops_stopwords_and_singularises(self):
        assert terms() == {"ai", "agent", "smb"}


class TestRelevance:
    def test_scores_higher_when_topic_words_hit_stronger_fields(self):
        in_name = candidate(name="Agent Co", one_liner="does things")
        in_body = candidate(name="Zeta", description="we build an agent")
        assert source.relevance(in_name, terms()) > source.relevance(in_body, terms())

    def test_matches_plural_alias_phrases(self):
        # Regression: "small business" + `s?` could not match "small businesses",
        # so every SMB-focused company scored zero on the `smb` term.
        c = candidate(name="Async", one_liner="Transforming small businesses with AI agents")
        assert source.relevance(c, terms()) == pytest.approx(0.667, abs=0.01)

    @pytest.mark.parametrize("phrase", ["small business", "SMEs", "mid-market retail", "main street"])
    def test_smb_aliases(self, phrase):
        c = candidate(name="Zeta", one_liner=f"tools for {phrase}")
        assert source.relevance(c, {"smb"}) > 0

    def test_ignores_decorative_name_tokens(self):
        # "Agnost AI" should not score on `ai` at full name weight — nearly
        # every company in a recent YC batch would.
        decorated = candidate(name="Agnost AI", one_liner="product analytics")
        plain = candidate(name="Agnost", one_liner="product analytics")
        assert source.relevance(decorated, {"ai"}) == source.relevance(plain, {"ai"}) == 0.0

    def test_respects_word_boundaries(self):
        # Without \b, `ai` matches "chain" and "email".
        c = candidate(name="Zeta", one_liner="blockchain email infrastructure")
        assert source.relevance(c, {"ai"}) == 0.0

    def test_counts_each_term_once_at_its_best_field(self):
        everywhere = candidate(name="Agent", one_liner="agent", description="agent agent")
        once = candidate(name="Agent", one_liner="hello")
        assert source.relevance(everywhere, {"agent"}) == source.relevance(once, {"agent"})

    def test_empty_query_scores_zero(self):
        assert source.relevance(candidate(), set()) == 0.0


class TestMerge:
    def test_same_domain_is_one_company(self):
        a = candidate(name="Voker", website="https://voker.ai")
        b = candidate(name="Voker AI", website="https://www.voker.ai/")
        assert len(source.merge([a], [b])) == 1

    def test_same_name_without_website_is_one_company(self):
        assert len(source.merge([candidate(name="Spine Swarm")], [candidate(name="spine swarm")])) == 1

    def test_github_urls_do_not_collapse_unrelated_projects(self):
        a = candidate(name="Plandex", website="https://github.com/plandex-ai/plandex")
        b = candidate(name="Peerd", website="https://github.com/NotASithLord/peerd")
        assert len(source.merge([a], [b])) == 2

    def test_union_of_signals_and_provenance(self):
        a = candidate(name="Voker", website="https://voker.ai")
        a.signals = [signal(label="YC S24 batch", kind="freshness")]
        a.provenance = [prov("yc", "https://ycombinator.com/companies/voker")]

        b = candidate(name="Voker", website="https://voker.ai")
        b.signals = [signal(label="59 points", source_name="hn")]
        b.provenance = [prov("hn", "https://news.ycombinator.com/item?id=1")]

        merged = source.merge([a], [b])[0]
        assert len(merged.signals) == 2
        assert merged.sources == ["hn", "yc"]

    def test_duplicate_signals_are_not_repeated(self):
        a = candidate(name="Voker", website="https://voker.ai")
        a.signals = [signal(label="same")]
        b = candidate(name="Voker", website="https://voker.ai")
        b.signals = [signal(label="same")]
        assert len(source.merge([a], [b])[0].signals) == 1

    def test_first_group_wins_on_conflicting_fields(self):
        clean = candidate(name="Voker", website="https://voker.ai", one_liner="Analytics for AI agents")
        inferred = candidate(name="voker.ai", website="https://voker.ai", one_liner="a thing i built")
        assert source.merge([clean], [inferred])[0].one_liner == "Analytics for AI agents"

    def test_longer_description_wins(self):
        a = candidate(name="Voker", website="https://voker.ai", description="short")
        b = candidate(name="Voker", website="https://voker.ai", description="a much longer description")
        assert source.merge([a], [b])[0].description == "a much longer description"


class TestRanking:
    def test_relevance_dominates(self):
        weak = candidate(name="Zeta", one_liner="AI agents for small businesses")
        weak.relevance = 0.9
        strong = candidate(name="Alpha", one_liner="something else")
        strong.relevance = 0.4
        strong.signals = [signal(value=500.0)]
        assert sorted([strong, weak], key=source.rank_key)[0] is weak

    def test_corroborated_candidates_beat_single_source_on_a_tie(self):
        both = candidate(name="Zeta")
        both.provenance = [prov("yc"), prov("hn", "https://news.ycombinator.com/item?id=1")]
        one = candidate(name="Alpha")
        one.provenance = [prov("yc")]
        assert sorted([one, both], key=source.rank_key)[0] is both

    def test_traction_breaks_remaining_ties(self):
        quiet = candidate(name="Alpha")
        quiet.signals = [signal(value=5.0)]
        loud = candidate(name="Zeta")
        loud.signals = [signal(value=300.0)]
        assert sorted([quiet, loud], key=source.rank_key)[0] is loud

    def test_recency_breaks_ties_when_traction_is_equal(self):
        old = candidate(name="Alpha")
        old.signals = [signal(kind="freshness", observed_at=NOW - timedelta(days=400))]
        new = candidate(name="Zeta")
        new.signals = [signal(kind="freshness", observed_at=NOW)]
        assert sorted([old, new], key=source.rank_key)[0] is new


class TestWorthKeeping:
    def test_requires_a_freshness_or_traction_signal(self):
        c = candidate()
        c.signals = [signal(kind="team", label="Team of 3")]
        assert not source._worth_keeping(c, min_hn_points=10)

    def test_drops_hn_only_candidates_nobody_reacted_to(self):
        c = candidate(name="Frost AI")
        c.provenance = [prov("hn", "https://news.ycombinator.com/item?id=1")]
        c.signals = [signal(label="2 points", value=2.0, source_name="hn")]
        assert not source._worth_keeping(c, min_hn_points=10)

    def test_yc_membership_exempts_a_quiet_launch_post(self):
        # Being in the batch is independent of how the launch post happened to do.
        c = candidate(name="Quiet Co")
        c.provenance = [prov("yc"), prov("hn", "https://news.ycombinator.com/item?id=1")]
        c.signals = [signal(label="2 points", value=2.0, source_name="hn")]
        assert source._worth_keeping(c, min_hn_points=10)


class TestTermCoverage:
    def test_reports_a_term_that_matched_nothing(self):
        found = [candidate(name="Zeta", one_liner="AI agents for developers")]
        assert source.term_coverage(found, terms()) == {"agent": 1, "ai": 1, "smb": 0}
