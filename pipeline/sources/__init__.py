"""Source adapters.

One module per source. Each exposes `search(client, topic, ...) -> list[Candidate]`
and is responsible for attaching provenance to everything it returns. Adapters
never rank across sources and never merge — `pipeline.source` does both, so the
adapters stay independently testable and replaceable.

The brief says to pick one or two sources and go deep, and names a twelve-source
layer returning two garbage results each as an anti-pattern. There are two here
and there is no plumbing for a third.
"""

from pipeline.sources import hn, yc

__all__ = ["hn", "yc"]
