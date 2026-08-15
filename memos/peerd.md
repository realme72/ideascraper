# peerd — Pass

**36/100** against [the thesis](../docs/thesis.md) · 100% evidence coverage · [github.com/NotASithLord/peerd](https://github.com/NotASithLord/peerd)

> AI agent harness that runs entirely in your browser

## 🔴 Pass

Scores 2/30 on displaced spend — outside the thesis, so the call is Pass regardless of the total.

## What they do

peerd is a browser extension that runs autonomous AI agents directly inside the user's browser without requiring an external backend or custom browser. It executes tasks using isolated browser tabs, JavaScript workers, and WebAssembly-based Linux virtual machines, using the user's own LLM API keys.

## Team

The project is created and maintained primarily by the pseudonymous developer @NotASithLord, with outside open-source contributions from contributors like jonybur and mariazuheros. No formal founder background, prior company history, or employment details are publicly available.

## Market

The project targets software developers, AI hobbyists, and power users looking for local, sandboxed agent execution and browser automation. Current alternatives include cloud-hosted agent sandboxes (e.g., Cloudflare Workers), MCP-based local agent runners, and dedicated AI browsers.

## Score against the thesis

| Component | Score | Reasoning |
|---|---:|---|
| Displaced spend is nameable | 2/30 | peerd is described as an 'AI agent harness that lives entirely in your browser as a web extension.' It is horizontal developer tooling and open-source infrastructure with no specific business workflow, cost centre, or existing budget line displaced. |
| Buyer is non-technical and operational | 1/15 | The software is designed for technical users and developers who configure their own API keys ('BYOK') and want local compute sandboxes (WASM Linux VMs, JS notebooks). Non-technical operational buyers are not the audience for this extension. |
| Product is in real users' hands | 11/20 | The repository is public with 384 stars, 38 forks, and open-source contributions from several distinct developers. While the tool is actively available and usable, there is limited independent evidence of ongoing enterprise or production usage. |
| Founding team | 10/20 | The author demonstrates strong technical competence in browser internals, WebAssembly, WebRTC, and sandboxing via extensive code commits and detailed architecture explanations. However, the developer is pseudonymous with no documented track record, prior startups, or domain background. |
| Quality of outside reaction | 8/10 | The HN launch received substantive technical scrutiny regarding prompt injection vectors, container necessity, and browser extension limits. The creator engaged directly with thorough, highly technical defenses regarding defense-in-depth security. |
| Momentum | 4/5 | The project was launched in late June 2026 and has maintained continuous commit activity through mid-August 2026 alongside multiple open-source contributors. |

**Total: 36/100**

## Risks

- Prompt injections from untrusted web runner outputs could compromise agent orchestrations and bypass browser sandbox defenses.
- Browser extension distribution and Discoverability limitations may restrict adoption compared to native applications or web-hosted platforms.
- A pure open-source, BYOK browser extension with no backend or monetization mechanism lacks a clear commercial business model.

## Open questions

- What commercialization path or enterprise software use case is planned beyond an open-source developer side project?
- How does the browser-based execution sandbox handle resource-heavy multi-agent workloads without crashing the host browser?
- Who is the target paying customer if the product remains fully client-side and open source under Apache 2.0?

## What would change our mind

1. Pivot from a generic local agent harness to taking over a concrete operational cost centre (e.g., outsourced data extraction or automated back-office browser workflows).
2. Package the browser automation capabilities into a non-technical SaaS interface targeted at business ops or administrative leads rather than developers.
3. Disclose founder background showing prior startup leadership or relevant commercial operational experience.

## What we could not find

- HN user @NotASithLord has no bio on their profile

## Sources

Every claim above traces to one of these pages.

- `hn` — [https://news.ycombinator.com/item?id=48646165](https://news.ycombinator.com/item?id=48646165)
- `github` — [https://github.com/NotASithLord/peerd](https://github.com/NotASithLord/peerd)
- `hn` — [https://news.ycombinator.com/item?id=48662684](https://news.ycombinator.com/item?id=48662684)
- `hn` — [https://news.ycombinator.com/item?id=48662996](https://news.ycombinator.com/item?id=48662996)
- `hn` — [https://news.ycombinator.com/item?id=48663052](https://news.ycombinator.com/item?id=48663052)
- `hn` — [https://news.ycombinator.com/item?id=48663119](https://news.ycombinator.com/item?id=48663119)
- `hn` — [https://news.ycombinator.com/item?id=48664711](https://news.ycombinator.com/item?id=48664711)
- `hn` — [https://news.ycombinator.com/item?id=48662624](https://news.ycombinator.com/item?id=48662624)
- `hn` — [https://news.ycombinator.com/item?id=48663792](https://news.ycombinator.com/item?id=48663792)
- `hn` — [https://news.ycombinator.com/item?id=48662836](https://news.ycombinator.com/item?id=48662836)

---

*Generated by [ideascraper](../README.md) from evidence gathered 15 Aug 2026. Scored by `gemini-3.7-flash` against the components in [docs/thesis.md](../docs/thesis.md); the total, the coverage figure and this call were computed from those scores, not chosen by the model.*
