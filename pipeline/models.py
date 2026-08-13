"""The data shapes that move between stages.

These are the contract. Each stage reads one of these off disk and writes the
next one back, so the schemas are the only coupling between modules.

Every factual claim that ends up in a memo carries a `Source` with it — the
brief requires a reviewer to be able to spot-check an analysis and trust where
its claims came from, so provenance travels with the data rather than being
reconstructed at render time.
"""

# Planned:
#   Source     — url + how it was retrieved + when. Attaches to every claim.
#   Candidate  — name, website, one-liner, team signal, freshness/traction signal.
#   Evidence   — everything gathered about one candidate, each item cited.
#   Analysis   — team / product / market / risks, score 0-100, cited throughout.
#   Memo       — the rendered one-pager + the Pass / Watch / Take a meeting call.
