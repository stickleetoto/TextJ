from __future__ import annotations

import argparse

from textj.backends.rapidocr_backend import DEFAULT_PROFILE, LANGUAGES, PROFILES

# TextJ detector default: cap the longest side instead of RapidOCR's
# upscaling "min 736" policy. Evidence: docs/BENCHMARK_RESULTS.md (2026-09-24).
DEFAULT_DET_LIMIT_TYPE = "max"
DEFAULT_DET_LIMIT_SIDE_LEN = 1280


def add_model_arguments(parser: argparse.ArgumentParser) -> None:
    """Model/backend selection options shared by every TextJ command."""
    parser.add_argument(
        "--language",
        choices=LANGUAGES,
        default="korean",
        help="Recognition model language (default: korean).",
    )
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=DEFAULT_PROFILE,
        help=(
            "RapidOCR model profile (default: %(default)s). "
            "'ppocrv6-small' is bundled/offline but has no Korean."
        ),
    )
    parser.add_argument(
        "--det-limit-type",
        choices=("min", "max"),
        default=DEFAULT_DET_LIMIT_TYPE,
        help="Detector resize policy (default: %(default)s).",
    )
    parser.add_argument(
        "--det-limit-side-len",
        type=int,
        default=DEFAULT_DET_LIMIT_SIDE_LEN,
        help="Detector resize side length in pixels (default: %(default)s).",
    )


def add_backend_arguments(parser: argparse.ArgumentParser) -> None:
    """Model options plus the minimum score used by one-shot commands."""
    add_model_arguments(parser)
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.5,
        help="Minimum OCR confidence (default: 0.5).",
    )


def backend_kwargs(args: argparse.Namespace) -> dict:
    """RapidOCRBackend keyword arguments from parsed common options."""
    return {
        "language": args.language,
        "text_score": args.min_score,
        "profile": args.profile,
        "det_limit_type": args.det_limit_type,
        "det_limit_side_len": args.det_limit_side_len,
    }
