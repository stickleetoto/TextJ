from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

from textj.backends import RapidOCRBackend
from textj.benchmark import run_benchmark
from textj.pipeline import OCRPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj-bench",
        description="Benchmark warm TextJ OCR latency on one image.",
    )
    parser.add_argument("image", type=Path, help="Image file used for the benchmark.")
    parser.add_argument("--runs", type=int, default=20, help="Measured runs (default: 20).")
    parser.add_argument(
        "--warmups",
        type=int,
        default=2,
        help="Warm-up OCR runs discarded before measurement (default: 2).",
    )
    parser.add_argument(
        "--language",
        choices=("korean", "en", "ch"),
        default="korean",
        help="Recognition model language.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.5,
        help="Minimum OCR confidence passed to RapidOCR (default: 0.5).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.runs < 1:
        print("error: --runs must be at least 1", file=sys.stderr)
        return 2
    if args.warmups < 0:
        print("error: --warmups cannot be negative", file=sys.stderr)
        return 2
    if not 0.0 <= args.min_score <= 1.0:
        print("error: --min-score must be between 0 and 1", file=sys.stderr)
        return 2

    try:
        construct_started = perf_counter()
        backend = RapidOCRBackend(
            language=args.language,
            text_score=args.min_score,
        )
        backend_construct_ms = (perf_counter() - construct_started) * 1000.0

        summary = run_benchmark(
            OCRPipeline(backend),
            args.image,
            runs=args.runs,
            warmups=args.warmups,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"error: benchmark failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = summary.to_dict()
        payload["backend_construct_ms"] = round(backend_construct_ms, 3)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("TextJ benchmark")
    print(f"  backend:            {summary.backend}")
    print(f"  backend construct:  {backend_construct_ms:.3f} ms")
    print(f"  warmups:            {summary.warmups}")
    print(f"  measured runs:      {summary.runs}")
    print(f"  min:                {summary.minimum_ms:.3f} ms")
    print(f"  mean:               {summary.mean_ms:.3f} ms")
    print(f"  p50:                {summary.p50_ms:.3f} ms")
    print(f"  p95:                {summary.p95_ms:.3f} ms")
    print(f"  max:                {summary.maximum_ms:.3f} ms")
    print(f"  lines:              {summary.line_count}")
    print(f"  mean score:         {summary.mean_score:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
