"""Tests for the evidence fetchers.

All offline — each test drives the parsing/selection logic with a fixture
shaped like the real payload. The network shapes themselves were verified by
probing the live APIs before any of this was written (prompts/0004).
"""

import html
import json

import pytest

from pipeline.fetchers import github, hn_thread, hn_user, web, yc_page
from pipeline.models import Candidate, Provenance
from tests.test_source import NOW, prov


def candidate_with(*provs, signals=()):
    c = Candidate(slug="acme", name="Acme", provenance=list(provs))
    c.signals = list(signals)
    return c


class TestYCPage:
    COMPANY = {
        "name": "Async",
        "batch_name": "Summer 2026",
        "year_founded": 2025,
        "team_size": 2,
        "location": "New York City, NY",
        "website": "https://withasync.com",
        "github_url": "https://github.com/withasync/core",
        "long_description": "Async builds agents that change how businesses run.",
        "founders": [
            {
                "full_name": "Ben Smith",
                "title": "Co-Founder",
                "founder_bio": "Dropped out of college at 20 to build software.",
                "linkedin_url": "https://linkedin.com/in/ben",
                "twitter_url": "https://x.com/ben",
            },
            {"full_name": "Connor Park", "title": "Co-Founder, CTO", "founder_bio": ""},
        ],
    }

    def test_slug_comes_from_the_yc_provenance(self):
        c = candidate_with(prov("yc", "https://www.ycombinator.com/companies/withasync"))
        assert yc_page.yc_slug(c) == "withasync"

    def test_no_yc_provenance_means_no_slug(self):
        c = candidate_with(prov("hn", "https://news.ycombinator.com/item?id=1"))
        assert yc_page.yc_slug(c) is None

    def test_embedded_json_is_read_from_the_data_page_attribute(self):
        payload = {"props": {"company": self.COMPANY}}
        page = f"<div id='app' data-page=\"{html.escape(json.dumps(payload), quote=True)}\"></div>"
        match = yc_page._DATA_PAGE_RE.search(page)
        parsed = json.loads(html.unescape(match.group(1)))
        assert parsed["props"]["company"]["name"] == "Async"

    def test_one_item_per_named_founder(self):
        items, _ = yc_page.to_items(self.COMPANY, "withasync")
        founders = [i for i in items if i.kind == "founder"]
        assert [i.title for i in founders] == [
            "Ben Smith — Co-Founder",
            "Connor Park — Co-Founder, CTO",
        ]

    def test_founder_socials_are_kept_for_traceability(self):
        items, _ = yc_page.to_items(self.COMPANY, "withasync")
        assert "x.com/ben" in items[1].content

    def test_a_founder_without_a_bio_says_so_rather_than_being_dropped(self):
        items, _ = yc_page.to_items(self.COMPANY, "withasync")
        assert "No bio published" in items[2].content

    def test_company_profile_carries_the_structured_facts(self):
        items, _ = yc_page.to_items(self.COMPANY, "withasync")
        profile = next(i for i in items if i.kind == "company_profile")
        assert "Batch: Summer 2026" in profile.content
        assert "Team size: 2" in profile.content

    def test_a_page_with_no_founders_records_a_gap(self):
        _, gaps = yc_page.to_items({"name": "X", "founders": []}, "x")
        assert gaps == ["YC company page lists no founders"]

    def test_named_founders_with_no_bios_record_a_gap(self):
        company = {"name": "X", "founders": [{"full_name": "A", "founder_bio": "  "}]}
        _, gaps = yc_page.to_items(company, "x")
        assert "no published bios" in gaps[0]


class TestHNThread:
    def thread(self, **overrides):
        base = {
            "id": 100,
            "author": "founder",
            "text": "<p>We built this because...</p>",
            "points": 257,
            "created_at_i": 1729785081,
            "children": [
                {"id": 1, "author": "critic", "text": "<p>How is this different from SES?</p>",
                 "points": None, "created_at_i": 1729785100, "children": [
                     {"id": 5, "author": "founder", "text": "<p>SES has no inboxes.</p>",
                      "points": None, "created_at_i": 1729785200, "children": []}
                 ]},
                {"id": 2, "author": "founder", "text": "<p>Thanks all!</p>",
                 "points": None, "created_at_i": 1729785300, "children": []},
                {"id": 3, "author": "someone", "text": "<p>Is 10M emails all beta testers?</p>",
                 "points": None, "created_at_i": 1729785400, "children": []},
            ],
        }
        return {**base, **overrides}

    def test_item_id_comes_from_the_hn_provenance(self):
        c = candidate_with(prov("hn", "https://news.ycombinator.com/item?id=43710576"))
        assert hn_thread.hn_item_id(c) == "43710576"

    def test_launch_text_is_captured_as_the_founders_own_pitch(self):
        items, _ = hn_thread.to_items(self.thread())
        launch = next(i for i in items if i.kind == "hn_launch_text")
        assert launch.content == "We built this because..."
        assert launch.value == 257.0

    def test_outside_comments_exclude_the_poster(self):
        items, _ = hn_thread.to_items(self.thread())
        outside = [i for i in items if i.kind == "hn_comment" and "founder reply" not in i.title]
        assert [i.title for i in outside] == ["HN comment by @critic", "HN comment by @someone"]

    def test_founder_replies_are_pulled_from_anywhere_in_the_tree(self):
        # id=5 is nested one level down, under a critic's comment.
        items, _ = hn_thread.to_items(self.thread())
        replies = [i for i in items if "founder reply" in i.title]
        assert "SES has no inboxes." in replies[0].content

    def test_comments_cite_their_own_permalink_not_the_thread(self):
        items, _ = hn_thread.to_items(self.thread())
        comment = next(i for i in items if i.kind == "hn_comment")
        assert comment.provenance.url == "https://news.ycombinator.com/item?id=1"

    def test_a_link_only_post_records_a_gap(self):
        _, gaps = hn_thread.to_items(self.thread(text=None))
        assert "no written pitch" in gaps[0]

    def test_a_thread_nobody_replied_to_records_gaps(self):
        _, gaps = hn_thread.to_items(self.thread(children=[]))
        assert any("no discussion" in g for g in gaps)
        assert any("did not reply" in g for g in gaps)

    def test_a_candidate_with_no_thread_records_a_gap(self, monkeypatch):
        items, gaps = hn_thread.fetch(None, candidate_with(prov("yc")))
        assert items == [] and "No Hacker News launch thread" in gaps[0]


class TestHNUser:
    def test_handle_is_recovered_from_the_stage_one_team_signal(self):
        from pipeline.models import Signal

        c = candidate_with(
            prov("hn", "https://news.ycombinator.com/item?id=1"),
            signals=[Signal(kind="team", label="Posted and answered questions as HN user @danenania",
                            provenance=prov("hn"))],
        )
        assert hn_user.hn_handle(c) == "danenania"

    def test_bio_becomes_evidence(self):
        items, gaps = hn_user.to_items(
            {"username": "danenania", "karma": 8084, "about": "Past founder of EnvKey (YC W18)"}
        )
        assert gaps == []
        assert "EnvKey" in items[0].content
        assert items[0].value == 8084.0

    def test_an_empty_bio_records_a_gap(self):
        items, gaps = hn_user.to_items({"username": "ghost", "karma": 1, "about": None})
        assert items == [] and "no bio" in gaps[0]


class TestGitHub:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://github.com/plandex-ai/plandex", "plandex-ai/plandex"),
            ("https://github.com/owner/repo.git", "owner/repo"),
            ("https://github.com/owner/repo/tree/main", "owner/repo"),
            ("https://example.com", None),
            (None, None),
        ],
    )
    def test_repo_extraction(self, url, expected):
        assert github.repo_from_url(url) == expected

    def test_first_usable_url_wins(self):
        assert github.repo_from_url(None, "https://x.com", "https://github.com/a/b") == "a/b"

    META = {
        "stargazers_count": 15581, "forks_count": 1171, "open_issues_count": 60,
        "language": "Go", "created_at": "2023-10-24T22:11:43Z",
        "pushed_at": "2025-10-03T21:49:58Z", "license": {"spdx_id": "MIT"},
        "archived": False, "description": "Open source AI coding agent.",
        "topics": ["ai", "cli"],
    }

    def test_repo_facts_include_recency_not_just_stars(self):
        items, _ = github.to_items("a/b", self.META, [])
        assert "Last pushed: 2025-10-03" in items[0].content
        assert items[0].value == 15581.0

    def test_contributors_become_their_own_item(self):
        items, _ = github.to_items("a/b", self.META, [{"login": "danenania", "contributions": 821}])
        contributors = next(i for i in items if i.kind == "github_contributors")
        assert "danenania: 821 commits" in contributors.content

    def test_an_archived_repo_is_flagged_as_a_gap(self):
        _, gaps = github.to_items("a/b", {**self.META, "archived": True}, [{"login": "x", "contributions": 1}])
        assert any("archived" in g for g in gaps)

    def test_no_repo_identified_records_a_gap(self):
        items, gaps = github.fetch(None, None)
        assert items == [] and "No public GitHub repository" in gaps[0]


class TestWeb:
    @pytest.mark.parametrize(
        "host,expected",
        [("chat.agentmail.to", "agentmail.to"), ("agentmail.to", None), ("a.b.example.com", "example.com")],
    )
    def test_apex_domain(self, host, expected):
        assert web.apex_of(host) == expected

    def test_extraction_drops_chrome_and_keeps_copy(self):
        title, body = web.extract_text(
            "<html><head><title>Acme</title>"
            '<meta name="description" content="We do things.">'
            "</head><body><nav>Home Pricing</nav><script>x=1</script>"
            "<main>Acme automates invoicing.</main><footer>© 2026</footer></body></html>"
        )
        assert title == "Acme"
        assert "We do things." in body and "Acme automates invoicing." in body
        assert "Pricing" not in body and "© 2026" not in body and "x=1" not in body

    def test_a_github_website_is_left_to_the_github_fetcher(self):
        items, gaps = web.fetch(None, "https://github.com/a/b")
        assert items == [] and gaps == []

    def test_no_website_records_a_gap(self):
        items, gaps = web.fetch(None, None)
        assert items == [] and "No website recorded" in gaps[0]
