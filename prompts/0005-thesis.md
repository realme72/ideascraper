# 0005 — Choosing the thesis

Date: 2026-08-14
Assistant: Claude Opus 5 (Claude Code)

---

## Prompts

> yes draft those 2-3 theses as scoring rubrics

> lets go with thesis A, write it into docs/thesis.md

**Written by.** The assistant drafted all three rubrics and wrote
`docs/thesis.md`. **The choice was Gaurav's** — this is the one decision in the
project that is a judgement about what to back rather than about how to build.

---

## Why they were drafted as rubrics, not statements

The brief names "a thesis so broad that the score is meaningless" as an
anti-pattern, and marks Scoping & Judgement on whether the thesis is specific
and held consistently. A one-line positioning statement cannot be held
consistently because there is nothing to hold it to.

So each draft was written as weighted components adding to 100, with the bands
spelled out, and — critically — with each component naming **the evidence kinds
from stage 2 that feed it**. Writing them this way surfaced a problem that a
prose thesis would have hidden: several obvious-sounding components turned out
to be unscoreable.

## Three rules that came out of the drafting

**Only score what stage 2 can observe.** The first draft of Thesis A had a
"traction" component that quietly meant revenue. Revenue, funding, retention and
real market size are not available from HN, the YC directory, GitHub or a
homepage. A rubric that implies otherwise is an instruction to the model to
invent — and "claims in memos with no traceable source" is a named anti-pattern.
Cut and replaced with "product is in real users' hands", which is observable.

**Claims and facts weigh differently.** A number on a landing page is a claim. The
same number in a founder's reply to a skeptic on HN is a claim made under
scrutiny. Commit history is a fact. Each component now states which it accepts.

**Missing evidence caps confidence; it does not lower the score.** This one
matters most and was not in the first pass. If a low team score can come from
"no bio found", the pipeline scores its own scraping failures — TryNearby would
be marked down for having a JavaScript homepage rather than for anything about
the business. Components now have documented neutral bands, memos carry an
evidence-coverage figure, and coverage moves the call asymmetrically: it can
never produce a *Take a meeting*, and can never turn a *Watch* into a *Pass*.

## The choice

Gaurav picked **A — Budget-line AI**. Recorded in D10 with the reasoning.

The assistant recommended A, and said plainly that **B was the tempting one and
the weakest**: our sources *are* GitHub and HN, so almost every candidate would
score something on it, scores would cluster in the middle, and it rewards
open-source visibility over business quality. Writing that weakness into the
draft rather than letting B look flattering was deliberate.

## Added when A became the live thesis

Two things the candidate draft did not have:

**Score-to-call bands** — 70+ take a meeting, 45–69 watch, under 45 pass — plus
three overrides. The first matters most: **component 1 below 10 is a Pass
regardless of total**. Without it, a company outside the thesis could earn a
meeting on the strength of its team, and the thesis would be decorative rather
than binding.

**A rule for "what would change my mind"** — these are not free-form. They are
the lowest-scoring components with the weakest evidence, stated as what would
need to be true. A company scoring 18/30 on component 1 gets "name the specific
budget this replaces", not "grow faster".

## Consequence worth stating up front

If most of a sourcing run scores below 45, that is the thesis working, not the
pipeline failing. The current 15 candidates are mostly developer tooling, and
Thesis A should reject most of them loudly.

---

## Notes from Gaurav

<!-- Human-written. Left empty deliberately rather than filled in by the model. -->
