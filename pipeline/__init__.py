"""ideascraper — an AI-augmented investment triage pipeline.

Four stages, run in order, each handing off to the next through plain JSON
files on disk:

    source   topic query          -> data/candidates.json
    enrich   candidates           -> data/evidence/<slug>.json
    analyze  evidence             -> data/analyses/<slug>.json
    memo     analyses             -> memos/<slug>.md

Every stage is runnable on its own. Nothing holds state in memory between
stages, so a failure in analysis never costs a re-scrape.
"""

__version__ = "0.1.0"
