"""Evidence fetchers.

One module per place we look. Each takes an already-sourced candidate and
returns `(items, gaps)` — material found, and an honest note about what it
looked for and could not find.

Fetchers never raise for an absent or broken source. A dead website, a company
with no launch thread and a repo that 404s are all normal, and each produces a
gap rather than an exception. `pipeline.enrich` still guards every call, but the
fetchers are expected to handle their own emptiness.

Fetchers also never interpret. They extract and cite. Judgement is stage 3.
"""

from pipeline.fetchers import github, hn_thread, hn_user, web, yc_page

__all__ = ["github", "hn_thread", "hn_user", "web", "yc_page"]
