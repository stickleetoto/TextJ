"""Newline-delimited JSON framing shared by stdio and socket transports.

One protocol message per line (UTF-8 JSON, no embedded newlines); one response
line per request line.
"""

from __future__ import annotations

import json
from typing import Any, BinaryIO

from textj.api.errors import ErrorCode, TextJError
from textj.api.response import encode_json, error_envelope

_CHUNK = 64 * 1024


class LineTooLong(Exception):
    """A line exceeded the configured limit; the rest of it was discarded."""


def read_line(stream: BinaryIO, limit: int) -> bytes | None:
    """Read one line of at most ``limit`` bytes (excluding the newline).

    Returns ``None`` at EOF. Raises :class:`LineTooLong` after discarding the
    remainder of an oversized line, so memory stays bounded by ``limit``.
    """
    line = stream.readline(limit + 1)
    if not line:
        return None
    if line.endswith(b"\n"):
        return line[:-1].rstrip(b"\r")
    if len(line) <= limit:
        return line  # final line without newline
    while True:  # discard the rest of the oversized line
        rest = stream.readline(_CHUNK)
        if not rest or rest.endswith(b"\n"):
            break
    raise LineTooLong()


def too_large_response(limit: int) -> str:
    error = TextJError(
        ErrorCode.REQUEST_TOO_LARGE,
        "request exceeds max_request_bytes",
        details={"max_request_bytes": limit},
    )
    return encode_json(error_envelope(None, error))


def decode_message(raw: bytes | str) -> tuple[Any, TextJError | None]:
    try:
        return json.loads(raw), None
    except (ValueError, UnicodeDecodeError) as exc:
        return None, TextJError(ErrorCode.INVALID_REQUEST, f"request is not valid JSON: {exc}")
