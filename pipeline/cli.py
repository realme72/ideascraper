"""The one command.

    python -m pipeline source "AI agents for SMBs"

Each stage is also runnable on its own, so a reviewer can re-render memos
without re-scraping, or re-analyse without re-fetching. "A partner can run one
command, point it at a topic, and get memos out the other end" is the brief's
first definition of done; `run` is that command once all four stages exist.
"""

from __future__ import annotations

import argparse
import sys

from pipeline import analyze, enrich, memo, source


def _print_summary(result) -> None:
    print(f'\n{len(result)} candidates for "{result.topic}"')

    coverage = ", ".join(f"{t} ({n})" for t, n in result.term_coverage.items())
    print(f"term coverage: {coverage}")
    missed = [t for t, n in result.term_coverage.items() if n == 0]
    if missed:
        print(f"⚠  no candidate matched: {', '.join(missed)} — results ignore that part of the topic")
    print()
    for i, c in enumerate(result.candidates, 1):
        sources = "+".join(c.sources)
        print(f"{i:2}. {c.name}  [{c.relevance:.2f} · {sources}]")
        if c.one_liner:
            print(f"    {c.one_liner}")
        for signal in c.signals_of("traction") + c.signals_of("freshness"):
            print(f"    · {signal.label}")
        print(f"    {c.website or 'no website found'}")
        print()
    print(f"written to {source.OUTPUT_PATH}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    src = sub.add_parser("source", help="find candidate startups for a topic")
    src.add_argument("topic", help='e.g. "AI agents for SMBs"')
    src.add_argument("--limit", type=int, default=15, help="max candidates (default: 15)")
    src.add_argument(
        "--batches", type=int, default=4, help="YC batches to search, newest first (default: 4)"
    )
    src.add_argument(
        "--min-relevance",
        type=float,
        default=0.2,
        help="drop candidates below this topic-fit score (default: 0.2)",
    )
    src.add_argument(
        "--refresh", action="store_true", help="bypass the cache and refetch everything"
    )

    enr = sub.add_parser("enrich", help="gather cited evidence for each candidate")
    enr.add_argument("--limit", type=int, default=None, help="only enrich the first N candidates")
    enr.add_argument(
        "--refresh", action="store_true", help="bypass the cache and refetch everything"
    )

    ana = sub.add_parser("analyze", help="score each candidate against the thesis")
    ana.add_argument("--limit", type=int, default=None, help="only analyse the first N")
    ana.add_argument(
        "--refresh", action="store_true", help="bypass the cache and re-call the model"
    )

    sub.add_parser("memo", help="render one-page memos from the analyses")

    full = sub.add_parser("run", help="all four stages, end to end")
    full.add_argument("topic", help='e.g. "AI agents for SMBs"')
    full.add_argument("--limit", type=int, default=15, help="max candidates (default: 15)")
    full.add_argument("--refresh", action="store_true", help="bypass every cache")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "source":
        result = source.run(
            args.topic,
            limit=args.limit,
            batches=args.batches,
            min_relevance=args.min_relevance,
            refresh=args.refresh,
        )
        if not result.candidates:
            print(
                f'No candidates matched "{args.topic}".\n'
                "Try a broader topic, --min-relevance 0.1, or --batches 8.",
                file=sys.stderr,
            )
            return 1
        _print_summary(result)
        return 0

    if args.command == "enrich":
        try:
            bundles = enrich.run(limit=args.limit, refresh=args.refresh)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        total_gaps = sum(len(b.gaps) for b in bundles)
        print(
            f"\n{len(bundles)} bundles written to {enrich.OUTPUT_DIR}/ "
            f"({total_gaps} gaps recorded)"
        )
        return 0

    if args.command == "analyze":
        try:
            analyses = analyze.run(limit=args.limit, refresh=args.refresh)
        except (FileNotFoundError, analyze.MissingCredentials) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        calls: dict[str, int] = {}
        for a in analyses:
            calls[a.call] = calls.get(a.call, 0) + 1
        summary = ", ".join(f"{n} {call}" for call, n in sorted(calls.items()))
        print(f"\n{len(analyses)} analysed — {summary}")
        print(f"written to {analyze.OUTPUT_DIR}/")
        return 0

    if args.command == "memo":
        try:
            written = memo.run()
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"\n{len(written)} memos written to {memo.OUTPUT_DIR}/ — start at index.md")
        return 0

    if args.command == "run":
        print("── sourcing ──")
        found = source.run(args.topic, limit=args.limit, refresh=args.refresh)
        if not found.candidates:
            print(f'No candidates matched "{args.topic}".', file=sys.stderr)
            return 1
        _print_summary(found)

        print("── enrichment ──")
        enrich.run(refresh=args.refresh)

        print("\n── analysis ──")
        try:
            analyze.run(refresh=args.refresh)
        except analyze.MissingCredentials as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print("\n── memos ──")
        written = memo.run()
        print(f"\n{len(written)} memos in {memo.OUTPUT_DIR}/ — start at index.md")
        return 0

    print(f"stage '{args.command}' is not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
