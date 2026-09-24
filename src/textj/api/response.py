"""Protocol v1 response construction and deterministic JSON encoding."""

from __future__ import annotations

import json
from typing import Any, Mapping

from textj.api.errors import TextJError
from textj.api.request import PROTOCOL_VERSION, OCROptions
from textj.models import OCRLine

SCORE_DIGITS = 6
COORD_DIGITS = 2
TIMING_DIGITS = 3


def success_envelope(request_id: str | None, result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "ok": True,
        "result": dict(result),
    }


def error_envelope(request_id: str | None, error: TextJError) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "ok": False,
        "error": error.to_dict(),
    }


def line_payload(line: OCRLine, include_boxes: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "text": line.text,
        "score": round(float(line.score), SCORE_DIGITS),
    }
    if include_boxes:
        payload["box"] = (
            [[round(x, COORD_DIGITS), round(y, COORD_DIGITS)] for x, y in line.box]
            if line.box is not None
            else None
        )
    return payload


def round_timings(timings: Mapping[str, float]) -> dict[str, float]:
    return {key: round(float(value), TIMING_DIGITS) for key, value in timings.items()}


def ocr_result_payload(
    *,
    lines: tuple[OCRLine, ...],
    backend: str,
    image_info: Mapping[str, Any],
    options: OCROptions,
    timings_ms: Mapping[str, float] | None,
) -> dict[str, Any]:
    """Build the ``result`` object of a successful ``ocr`` response.

    Line order is the backend's order (RapidOCR: top-to-bottom, then
    left-to-right). ``text`` joins non-empty line texts with ``\\n``.
    """
    scores = [line.score for line in lines]
    result: dict[str, Any] = {
        "text": "\n".join(line.text for line in lines if line.text),
        "lines": [line_payload(line, options.include_boxes) for line in lines],
        "line_count": len(lines),
        "mean_score": round(sum(scores) / len(scores), SCORE_DIGITS) if scores else 0.0,
        "backend": backend,
        "input": dict(image_info),
    }
    if options.include_timings and timings_ms is not None:
        result["timings_ms"] = round_timings(timings_ms)
    return result


def encode_json(payload: Mapping[str, Any]) -> str:
    """Compact, Unicode-preserving, NaN-free JSON. Key order is construction order."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
