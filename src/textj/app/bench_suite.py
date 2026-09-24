from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

from textj.app.common import add_backend_arguments, backend_kwargs
from textj.backends import RapidOCRBackend
from textj.benchmark_suite import run_suite
from textj.pipeline import OCRPipeline
from textj.result_io import write_json
from textj.system_info import collect_system_info


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj-bench-suite",
        description="Run a reproducible TextJ OCR benchmark manifest.",
    )
    parser.add_argument("manifest", type=Path, help="Benchmark manifest JSON.")
    parser.add_argument("--runs", type=int, default=10, help="Measured runs per case.")
    parser.add_argument("--warmups", type=int, default=1, help="Warmups per case.")
    add_backend_arguments(parser)
    parser.add_argument("--output", type=Path, help="Optional JSON result path.")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
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
        backend = RapidOCRBackend(**backend_kwargs(args))
        construct_ms = (perf_counter() - construct_started) * 1000.0

        suite = run_suite(
            OCRPipeline(backend),
            args.manifest,
            runs=args.runs,
            warmups=args.warmups,
        )
    except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"error: benchmark suite failed: {exc}", file=sys.stderr)
        return 1

    payload = suite.to_dict()
    payload["backend_construct_ms"] = round(construct_ms, 3)
    payload["system"] = collect_system_info()
    payload["backend_config"] = backend.describe()
    payload["config"] = {
        "language": args.language,
        "profile": args.profile,
        "det_limit_type": args.det_limit_type,
        "det_limit_side_len": args.det_limit_side_len,
        "min_score": args.min_score,
        "runs": args.runs,
        "warmups": args.warmups,
    }

    if args.output is not None:
        write_json(args.output, payload)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("TextJ benchmark suite")
    print(f"  cases:              {payload['case_count']}")
    print(f"  backend construct:  {construct_ms:.3f} ms")
    print(f"  mean p50:           {payload['mean_p50_ms']:.3f} ms")
    print(f"  mean p95:           {payload['mean_p95_ms']:.3f} ms")
    if payload["mean_cer"] is not None:
        print(f"  mean CER:           {payload['mean_cer']:.4f}")
    if args.output is not None:
        print(f"  result:             {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
