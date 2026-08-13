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

from pipeline import source


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

    for name, help_text in [
        ("enrich", "gather evidence for each candidate"),
        ("analyze", "score each candidate against the thesis"),
        ("memo", "render one-page memos"),
        ("run", "all four stages, end to end"),
    ]:
        stage = sub.add_parser(name, help=f"{help_text} (not implemented yet)")
        stage.add_argument("topic", nargs="?", help=argparse.SUPPRESS)

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

    print(f"stage '{args.command}' is not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
