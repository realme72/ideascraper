"""Stage 4 — Recommendation.

    data/analyses/<slug>.json  ->  memos/<slug>.md

Renders the one-page memo. Ends in a clear call — **Pass / Watch / Take a
meeting** — with the rationale and the 2-3 things that would change that call.

Deterministic templating, no LLM. The judgement was already made and scored in
stage 3; this stage only lays it out. That keeps memos consistent with the
scores they came from, and means fixing a formatting problem costs nothing.

The bar: a partner understands the call in 60 seconds.
"""
