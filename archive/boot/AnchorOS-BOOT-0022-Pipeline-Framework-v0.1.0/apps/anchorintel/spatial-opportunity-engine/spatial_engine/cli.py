"""Command-line interface for the S.P.A.T.I.A.L. engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import InputError, SpatialEngine
from .report import render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spatial-engine",
        description="Evaluate infrastructure opportunities under SIO-001 S.P.A.T.I.A.L.",
    )
    parser.add_argument("input", type=Path, help="Opportunity record JSON file")
    parser.add_argument("--json-out", type=Path, help="Write the complete result as JSON")
    parser.add_argument("--md-out", type=Path, help="Write a controlled Markdown decision report")
    parser.add_argument(
        "--format",
        choices=("summary", "json", "markdown"),
        default="summary",
        help="Standard output format",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        result = SpatialEngine().analyze(raw)
    except FileNotFoundError:
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 2
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result_json = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    result_markdown = render_markdown(result)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(result_json, encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(result_markdown, encoding="utf-8")

    if args.format == "json":
        print(result_json, end="")
    elif args.format == "markdown":
        print(result_markdown, end="")
    else:
        suffix = " (PROVISIONAL)" if result.provisional else ""
        print(f"{result.opportunity_id}: {result.recommendation.value}{suffix}")
        print(f"score={result.score:.2f}/100 confidence={result.confidence.value}")
        print(result.recommendation_reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

