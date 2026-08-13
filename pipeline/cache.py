"""Disk cache for anything expensive or non-deterministic.

Every outbound HTTP request and every LLM call is cached to disk under
`data/raw/`, keyed by a hash of its inputs. Two reasons, both from the brief:

  - **Replayable.** A reviewer can re-run the pipeline and get the same output
    without re-hitting the network or spending tokens.
  - **Cheap iteration.** Re-running after a prompt tweak only pays for the
    calls that actually changed.

See docs/decisions.md D2.
"""

# Planned:
#   key(*parts)       -> stable hash of the call's inputs
#   get(key)          -> cached payload, or None
#   put(key, payload) -> write through
