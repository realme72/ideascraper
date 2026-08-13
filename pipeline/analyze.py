"""Stage 3 — Analysis.

    data/evidence/<slug>.json  ->  data/analyses/<slug>.json

The only stage that calls an LLM. Turns an evidence bundle into a structured
analysis:

  - **Team** — founder backgrounds, prior exits, technical depth
  - **Product** — what they actually do, in plain language
  - **Market** — size hint, competitive landscape, why now
  - **Risks / open questions** — what would kill this?
  - **Score (0-100)** against the stated thesis

The model only ever sees evidence collected in stage 2, and every claim it makes
must cite one of those items. Claims in memos with no traceable source are a
named anti-pattern, and an LLM left to free-associate about a startup will
produce them.
"""

# Thesis and model: undecided — see docs/decisions.md "Open".
