from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

from textj import __version__
from textj.app.common import add_backend_arguments, backend_kwargs
from textj.backends import RapidOCRBackend
from textj.pipeline import OCRPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj",
        description="Ultra-fast local OCR for images and screenshots.",
    )
    parser.add_argument("image", type=Path, help="Image file to recognize.")
    add_backend_arguments(parser)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON instead of plain text.",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Print timing information to stderr.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not 0.0 <= args.min_score <= 1.0:
        print("error: --min-score must be between 0 and 1", file=sys.stderr)
        return 2

    try:
        construct_start = perf_counter()
        backend = RapidOCRBackend(**backend_kwargs(args))
        backend_construct_ms = (perf_counter() - construct_start) * 1000.0

        result = OCRPipeline(backend).run(args.image)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # v0.1: keep CLI failure readable while backends mature.
        print(f"error: OCR failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = result.to_dict()
        payload["stages_ms"]["backend_construct"] = round(backend_construct_ms, 3)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if result.text:
            print(result.text)

    if args.timing:
        print(
            f"[TextJ] backend_construct={backend_construct_ms:.1f} ms "
            f"ocr_total={result.total_ms:.1f} ms "
            f"lines={len(result.lines)} "
            f"mean_score={result.mean_score:.3f}",
            file=sys.stderr,
        )

    return 0
