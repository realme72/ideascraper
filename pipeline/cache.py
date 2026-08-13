"""Disk cache for anything expensive or non-deterministic.

Every outbound HTTP request and every LLM call is cached to disk under
`data/raw/`, keyed by a hash of its inputs. Two reasons, both from the brief:

  - **Replayable.** A reviewer can re-run the pipeline and get the same output
    without re-hitting the network or spending tokens. The cache is committed.
  - **Cheap iteration.** Re-running after a change only pays for the calls that
    actually differ.

Entries record the inputs they were keyed on alongside the payload, so the
cache directory can be read by a human trying to work out where a claim came
from. See docs/decisions.md D2.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CACHE_DIR = Path("data/raw")


def key(*parts: Any) -> str:
    """Stable short hash of a call's inputs.

    Parts are JSON-encoded with sorted keys so that equal inputs always produce
    an equal key regardless of dict ordering.
    """
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _path(k: str) -> Path:
    return CACHE_DIR / f"{k}.json"


def get(k: str) -> Any | None:
    """Return a cached payload, or None on a miss or an unreadable entry."""
    path = _path(k)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())["payload"]
    except (json.JSONDecodeError, KeyError, OSError):
        # A corrupt entry is a cache miss, not a crash — worst case we refetch.
        return None


def put(k: str, payload: Any, inputs: Any = None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "key": k,
        "inputs": inputs,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    _path(k).write_text(json.dumps(entry, indent=2, default=str))


def fetch(inputs: Any, producer: Callable[[], Any], *, refresh: bool = False) -> Any:
    """Return the cached result for `inputs`, calling `producer` on a miss.

    `refresh=True` forces the call and overwrites the entry.
    """
    k = key(inputs)
    if not refresh:
        hit = get(k)
        if hit is not None:
            return hit
    payload = producer()
    put(k, payload, inputs=inputs)
    return payload
