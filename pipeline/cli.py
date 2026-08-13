"""The one command.

    python -m pipeline run "AI agents for SMBs"

Runs all four stages end to end. Each stage is also runnable on its own, so a
reviewer can re-render memos without re-scraping, or re-analyse without
re-fetching:

    python -m pipeline source  "AI agents for SMBs"
    python -m pipeline enrich
    python -m pipeline analyze
    python -m pipeline memo

"A partner can run one command, point it at a topic, and get memos out the other
end" is the brief's first definition of done.
"""
