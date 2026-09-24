from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from textj.benchmark_compare import Thresholds, compare, format_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj-bench-compare",
        description=(
            "Compare two textj-bench / textj-bench-suite JSON artifacts. "
            "Exit code 1 when a configured threshold is exceeded."
        ),
    )
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--max-p50-regression-pct", type=float)
    parser.add_argument("--max-p95-regression-pct", type=float)
    parser.add_argument("--max-cer-increase", type=float, help="Absolute CER increase.")
    parser.add_argument("--max-rss-increase-mb", type=float)
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        result = compare(
            baseline,
            candidate,
            Thresholds(
                max_p50_regression_pct=args.max_p50_regression_pct,
                max_p95_regression_pct=args.max_p95_regression_pct,
                max_cer_increase=args.max_cer_increase,
                max_rss_increase_mb=args.max_rss_increase_mb,
            ),
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_comparison(result))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
