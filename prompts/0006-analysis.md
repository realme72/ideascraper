# 0006 — Stage 3: analysis

Date: 2026-08-14
Assistant: Claude Opus 5 (Claude Code)

---

## Prompts

> okay , for now use this and later on i'll simply write in readme.md to use
> your own api-key that'd be better

> i was refering to use claude -opus model, and when we push the complete
> working model then i'll ask the reviewers to put their own api keys

**What happened.** The assistant misread the first message as "here is a key"
and reported that no key had come through, offering two ways to supply one. The
second message clarified: *use the Opus model*, and reviewers will bring their
own keys once the pipeline ships.

**Written by.** The assistant, end to end — rubric-as-data, prompt, scorer,
overrides, citation check and tests. Gaurav chose the model and the
bring-your-own-key posture for reviewers.

---

## Checked the API reference before writing client code

Rather than writing from memory. Four things came back that would otherwise
have been wrong or missed:

- **Thinking is on by default on `claude-opus-5`**, and it shares the
  `max_tokens` budget with the response. `max_tokens` is 16k for an analysis
  that is nowhere near that long, because the budget is not the answer's alone.
- **`temperature` and `top_p` now return a 400** on this model. Neither is used.
- **`messages.parse()` with a Pydantic schema** validates the response instead of
  parsing JSON out of prose and hoping.
- **The prompt-cache minimum is 512 tokens on this model.** The system prompt is
  ~1,950, so the rubric caches comfortably.

## The design decision that matters

**The model judges; the pipeline does the arithmetic** (D11). The model scores
each component against its bands, cites what it used, and says what would change
its mind. It never sums, never computes coverage, never picks the call — and the
prompt tells it not to reason about thresholds at all.

A thesis a model can round up on is not being held consistently. The three
overrides in `docs/thesis.md` are the part that has to be right every time, so
they are the part with unit tests rather than the part with a prompt.

The knock-on decision (D12): the rubric lives in `pipeline/thesis.py` as data,
the system prompt is **rendered from it**, and the scorer sums the same table.
Writing the rubric into a prompt string and the weights into the scorer
separately means they drift the first time a weight changes — silently, with the
scores still looking plausible.

## Prompt choices worth arguing with

**No pressure language.** The API guidance is explicit that current models
follow the system prompt closely and that `CRITICAL:` / `You MUST` phrasing —
written to overcome older models' reluctance — now causes overtriggering. The
prompt states things once, plainly.

**No "double-check your work" instruction.** Same source: this model verifies
its own work unprompted, and telling it to causes over-verification. Deleting
that instinct was deliberate, not an oversight.

**Claims and facts are separated in the prompt itself.** Each evidence kind is
described by how much it can be trusted — a number on a landing page is a claim,
the same number in a founder's reply to a skeptic has been under scrutiny, and
commit history is a fact.

**Gaps are handed to the model explicitly**, with instructions to score absent
evidence at the documented neutral value and say so. The alternative is a model
filling silence with plausible invention.

## The citation check

The model is told to cite evidence item titles verbatim. After the call,
`check_citations` resolves every reference against the actual bundle and records
anything that doesn't match on the analysis, where the memo will surface it.

An uncheckable citation is worse than no citation, because it looks checkable.
The check tolerates case, whitespace and paraphrase of long titles; it does not
tolerate a source that isn't there.

## Not yet run

There is no API key in the environment, so stage 3 has never executed against
the live model. Everything above is built and unit-tested — 121 tests, all
offline — but the memos in this repo do not exist yet. That is honest and worth
stating rather than implying otherwise; the first real run happens when a key
lands, and the prompt log will record what it found.

Estimated cost of one full run over 15 companies: well under a dollar, most of
it output tokens.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
