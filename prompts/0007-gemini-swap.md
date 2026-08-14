# 0007 — Swapping the model provider to Gemini

Date: 2026-08-14
Assistant: Claude Opus 5 (Claude Code)

---

## Prompts

> I'm using you, you should have the claude api key, if its not there let me know

> i pay 20$ a month, do i still need to set up billing ?

> I dont want to spend any money right now, so the remaining option we have is
> to go with gemini

**What happened.** Two reasonable misunderstandings, then a decision.

The assistant clarified that its own access runs through Claude Code's
authentication, which is not an API key it can read or hand to a Python script —
a different product surface. It re-checked all four places a key could live
(`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `~/.config/anthropic`, `.env`)
and confirmed none existed, having noticed its earlier check had a shell quirk
that could have masked a result.

Then: a Claude Pro subscription covers claude.ai and Claude Code, not the
developer API, which bills separately pay-as-you-go. The assistant said a $5
minimum top-up would cover the whole take-home several times over, but also
flagged that the brief permits any model and free tiers — so Gemini was a real
option, not a consolation prize. Gaurav chose not to spend.

---

## Checked the API before writing, again — and it mattered again

Writing the Gemini client from memory would have produced dead code. Four
fetches against the live docs:

- **The SDK surface has moved on.** The current call is
  `client.interactions.create(model=..., input=...)` returning `.output_text` —
  not the `generate_content` shape that would have been written from memory.
  Package `google-genai`, env var `GEMINI_API_KEY`.
- **Model IDs were ambiguous** between the summarised pages, so the raw markdown
  was fetched to get the identifier table verbatim: `gemini-3.7-flash`,
  `gemini-3.1-pro-preview`, and the rest.
- **Free-tier limits are not documented per model** — they are per-account and
  visible only in AI Studio. Historically 100–250 requests/day, and this run is
  fifteen, so the daily cap is not a constraint; the per-minute one might be,
  hence the call spacing.
- **Verified against the installed package, not just the docs.** `google-genai`
  2.18.1 installs and `Client.interactions` exists — so the documented surface
  is real in the version that will actually run.

## What the switch cost, and what it didn't

**Cost:** the prompt-caching design. The rubric is identical for all fifteen
companies, so on a paid provider it carried a cache breakpoint — one full-price
prefix, fourteen cache reads. On a free tier there is no cost to save, so rubric
and evidence are now one concatenated input. Quality may also differ from Opus;
that is measurable once the run happens, and it will be recorded rather than
assumed.

**Didn't cost:** anything above the client call. The rubric, the scoring, the
three overrides, the citation check and all 122 tests were untouched. The diff
is `_call_model` plus a few constants.

That is a direct payoff from D11 — the model was only ever asked to *judge*, and
the thesis logic lives in `pipeline/thesis.py` rather than in a prompt. Had the
model been asked for a total and a call, swapping providers would have meant
re-validating every score. The provider turned out to be the cheapest thing in
the stage to change.

## Still unverified

Stage 3 has *still* never run — there is no Gemini key yet either. Two things
are unverified until it does, and both are honest unknowns rather than
oversights:

1. **Schema handling.** Pydantic's `model_json_schema()` emits `$defs`/`$ref`
   for the nested component list. Whether Gemini's `response_format` accepts
   that shape is untested. The response is validated against `AnalysisDraft`
   afterwards regardless, so a malformed reply fails loudly instead of becoming
   a memo with empty sections — but if the schema is rejected outright, that
   surfaces on the first call. No workaround was pre-built for a failure that
   has not been observed.
2. **Model choice.** `gemini-3.7-flash` is a reasoned default, not a measured
   one. `GEMINI_MODEL` overrides it without a code change.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
