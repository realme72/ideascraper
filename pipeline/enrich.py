"""Stage 2 — Enrichment.

    data/candidates.json  ->  data/evidence/<slug>.json

Gather the raw material an analyst would want before forming a view: what the
landing page claims, what the GitHub activity looks like, what the launch
discussion said. No judgement here — this stage collects and cites, it does not
interpret. Interpretation is stage 3's job.

Missing data is normal and expected. A candidate with no GitHub and a dead
website still produces a valid (thin) evidence file — the rubric asks for
robustness to bad or missing data, so gaps are recorded as gaps rather than
crashing the run.
"""
