from __future__ import annotations

import argparse
import json
import sys
from time import perf_counter

from textj.app.common import add_backend_arguments, backend_kwargs
from textj.backends import RapidOCRBackend
from textj.inputs import ClipboardImageError, grab_clipboard_bgr
from textj.pipeline import OCRPipeline
from textj.windows.clipboard_text import set_clipboard_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj-clipboard",
        description="OCR the current clipboard image and copy recognized text.",
    )
    add_backend_arguments(parser)
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Do not replace the clipboard with recognized text.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON.",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Print capture/OCR/copy timings to stderr.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from textj.app.common import ensure_utf8_stdio

    ensure_utf8_stdio()
    args = build_parser().parse_args(argv)

    if not 0.0 <= args.min_score <= 1.0:
        print("error: --min-score must be between 0 and 1", file=sys.stderr)
        return 2

    try:
        capture_started = perf_counter()
        image = grab_clipboard_bgr()
        capture_ms = (perf_counter() - capture_started) * 1000.0

        construct_started = perf_counter()
        backend = RapidOCRBackend(**backend_kwargs(args))
        construct_ms = (perf_counter() - construct_started) * 1000.0

        result = OCRPipeline(backend).run(image)

        clipboard_ms = 0.0
        copied = False
        if result.text and not args.no_copy:
            clipboard_started = perf_counter()
            set_clipboard_text(result.text)
            clipboard_ms = (perf_counter() - clipboard_started) * 1000.0
            copied = True
    except (ClipboardImageError, RuntimeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"error: clipboard OCR failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = result.to_dict()
        payload["clipboard"] = {
            "capture_ms": round(capture_ms, 3),
            "backend_construct_ms": round(construct_ms, 3),
            "write_ms": round(clipboard_ms, 3),
            "copied": copied,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif result.text:
        print(result.text)

    if args.timing:
        print(
            f"[TextJ] clipboard_capture={capture_ms:.1f} ms "
            f"backend_construct={construct_ms:.1f} ms "
            f"ocr={result.total_ms:.1f} ms "
            f"clipboard_write={clipboard_ms:.1f} ms",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
