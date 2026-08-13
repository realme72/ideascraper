# 0001 — Kickoff: reading the brief, scoping, repo setup

Date: 2026-08-13
Assistant: Claude Opus 5 (Claude Code)

---

## Prompt 1 — token budgeting

> okay, before we start anything, we need to make sure we dont over consume the
> tokens so create a cache where you will store the summary of every text so that
> you dont have to rescan everything from the start this will save the token
> right ?

**What happened.** The assistant pushed back on the premise before building
anything. Its answer: a summary cache does *not* save tokens within a single
conversation, because the assistant already holds what it has read in context and
does not re-scan files each turn. The cache pays off in two other places — across
separate sessions, and after context compaction — and it is a different mechanism
from the provider-level prompt cache, which is automatic.

It started creating a `.cache/` directory and **the step was cancelled** before
any files were written. Decision deferred; see `docs/decisions.md`.

The idea did not go to waste: caching raw HTTP and LLM responses to disk is now
planned inside the pipeline itself, where it buys replayable and deterministic
re-runs — which the assignment's rubric asks for under System Design.

---

## Prompt 2 — read the brief and scope it

> okay in the current directory ideascraper, there's a assighment pdf, go through
> that, tell me what is the problems statement, we have to build the working
> prototype as soon as possible, and we should also keep in mind to make it like
> as askedin the assignment no overengineering exactly whats asked for, and then
> we'll divide the problems and we can start building it one by one

**What happened.** The PDF could not be read directly — no PDF text extractor was
installed. The assistant installed `poppler` via Homebrew and extracted the text
with `pdftotext -layout`.

It then summarised the brief: a three-stage triage pipeline (Sourcing → Analysis →
Recommendation) for a seed-stage VC, 10–20 candidates from one or two sources,
structured analysis scored 0–100 against a self-defined thesis, and a one-page
memo per startup ending in Pass / Watch / Take a meeting.

The observation it led with, from the rubric: **Process & AI workflow visibility
is 40% of the grade** — the single largest line item, and larger than output
quality and code quality combined. The brief refuses to specify what form that
trail should take, and lists "a trail clearly assembled after the fact to look
thorough" as an anti-pattern. Conclusion: the trail has to be produced live,
starting at commit one. That is the direct cause of this `prompts/` directory
existing before any pipeline code does.

It proposed a five-module shape (`source` → `enrich` → `analyze` → `memo` → `cli`)
with JSON files as the hand-off between stages, and asked three scoping questions
— which sources, which thesis, which LLM. **The questions were cancelled** rather
than answered; they remain open.

---

## Prompt 3 — repo first

> okay lets push this ideascrapper to github first then we can start building
> things one by one and while commting we will push the prompt as well

**What happened.** This entry, the prompt-log convention in `prompts/README.md`,
the decision log, and the initial repo scaffolding. No pipeline code yet — the
folder structure follows in `0002`, and stage 1 in `0003`.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
