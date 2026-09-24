"""textj-client: call a running TextJ daemon and print the JSON response."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from textj.transport.client import TextJClient, TextJClientError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj-client",
        description="Send protocol v1 requests to a running textj-serve --tcp daemon.",
    )
    parser.add_argument("--state-file", help="Daemon state file (default: ~/.textj/daemon.json).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Runtime status.")
    ocr = sub.add_parser("ocr", help="OCR one or more image files (2+ uses ocr_batch).")
    ocr.add_argument("--timeout-ms", type=int, help="Request timeout_ms.")
    ocr.add_argument("--min-score", type=float)
    ocr.add_argument("--no-boxes", action="store_true")
    ocr.add_argument("images", nargs="+", type=Path)
    ocr.add_argument("--bytes", action="store_true", help="Send image bytes instead of paths.")
    sub.add_parser("raw", help="Read one protocol request JSON from stdin.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = {}
    if getattr(args, "min_score", None) is not None:
        options["min_score"] = args.min_score
    if getattr(args, "no_boxes", False):
        options["include_boxes"] = False

    try:
        with TextJClient.from_state_file(args.state_file) as client:
            if args.command == "status":
                response = client.status()
            elif args.command == "raw":
                response = client.request(json.loads(sys.stdin.read()))
            elif len(args.images) == 1:
                image = args.images[0]
                if args.bytes:
                    response = client.ocr_bytes(image.read_bytes(), timeout_ms=args.timeout_ms, **options)
                else:
                    response = client.ocr_path(image, timeout_ms=args.timeout_ms, **options)
            else:
                items = [
                    {"id": str(index), "input": {"type": "path", "path": str(image.resolve())}}
                    for index, image in enumerate(args.images)
                ]
                response = client.ocr_batch(items, timeout_ms=args.timeout_ms, **options)
    except (TextJClientError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
