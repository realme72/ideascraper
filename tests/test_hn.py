"""Tests for parsing Hacker News posts into candidates.

Title parsing is the fragile part of this source. Launch HN has a strict format;
Show HN is freeform, so the company name often has to come from the URL instead.
"""

import pytest

from pipeline.sources import hn


class TestParseTitle:
    def test_launch_hn_yields_name_and_description(self):
        name, one_liner = hn._parse_title(
            "Launch HN: Skyvern (YC S23) – open-source AI agent for browser automations",
            "https://github.com/Skyvern-AI/Skyvern",
        )
        assert name == "Skyvern"
        assert one_liner == "open-source AI agent for browser automations"

    def test_show_hn_with_a_short_leading_name(self):
        name, one_liner = hn._parse_title(
            "Show HN: AgentMail – Email infra for AI agents", "https://agentmail.to"
        )
        assert name == "AgentMail"
        assert one_liner == "Email infra for AI agents"

    def test_show_hn_sentence_falls_back_to_the_domain(self):
        # "A real time AI video agent with under 1 second of latency" is a
        # sentence, not a company name.
        name, one_liner = hn._parse_title(
            "Show HN: A real time AI video agent with under 1 second of latency",
            "https://www.tavus.io",
        )
        assert name == "Tavus"
        assert one_liner.startswith("A real time")

    def test_github_url_uses_the_repo_not_the_host(self):
        assert hn._name_from_url("https://github.com/plandex-ai/plandex") == "Plandex"

    def test_subdomain_is_skipped_for_the_company_name(self):
        assert hn._name_from_url("https://app.linear.dev") == "Linear"

    def test_no_url_and_no_name_gives_nothing(self):
        assert hn._name_from_url(None) is None


class TestToCandidate:
    def _hit(self, **overrides):
        hit = {
            "objectID": "41710227",
            "title": "Launch HN: Skyvern (YC S23) – open-source AI agent for browser automations",
            "url": "https://skyvern.com",
            "points": 327,
            "num_comments": 44,
            "created_at_i": 1729785081,
            "author": "suchintan",
        }
        return {**hit, **overrides}

    def test_carries_traction_freshness_and_team_signals(self):
        c = hn._to_candidate(self._hit())
        assert {s.kind for s in c.signals} == {"traction", "freshness", "team"}

    def test_traction_signal_exposes_points_as_a_number(self):
        # Ranking reads `value`; nothing should be parsing the label text.
        traction = hn._to_candidate(self._hit()).signals_of("traction")[0]
        assert traction.value == 327.0

    def test_provenance_points_at_the_discussion_a_human_can_read(self):
        c = hn._to_candidate(self._hit())
        assert c.provenance[0].url == "https://news.ycombinator.com/item?id=41710227"

    def test_launch_hn_batch_becomes_a_freshness_signal(self):
        labels = [s.label for s in hn._to_candidate(self._hit()).signals]
        assert "YC S23 batch" in labels

    def test_unattributable_text_post_is_dropped(self):
        assert hn._to_candidate(self._hit(title="Ask HN: what are you working on?", url=None)) is None

    def test_missing_points_do_not_crash(self):
        c = hn._to_candidate(self._hit(points=None, num_comments=None))
        assert c.signals_of("traction")[0].value == 0.0


class TestClean:
    def test_strips_html_and_collapses_whitespace(self):
        assert hn._clean("<p>Hey it&#x27;s   Hassaan</p>") == "Hey it's Hassaan"

    def test_truncates_on_a_word_boundary(self):
        cleaned = hn._clean("word " * 400, limit=50)
        assert len(cleaned) <= 51 and cleaned.endswith("…")

    @pytest.mark.parametrize("empty", [None, "", "<p></p>"])
    def test_empty_input_gives_none(self, empty):
        assert hn._clean(empty) is None
