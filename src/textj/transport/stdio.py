"""JSON stdio transport: one request per stdin line, one response per stdout line.

Intended for agents that spawn TextJ as a long-lived subprocess. stdout carries
protocol messages only; diagnostics go to stderr.
"""

from __future__ import annotations

from typing import BinaryIO

from textj.runtime import TextJRuntime
from textj.transport.framing import LineTooLong, read_line, too_large_response


def serve_stdio(runtime: TextJRuntime, stdin: BinaryIO, stdout: BinaryIO) -> int:
    """Serve requests sequentially until EOF. Returns the number handled."""
    limit = runtime.config.limits.max_request_bytes
    handled = 0
    while True:
        try:
            line = read_line(stdin, limit)
        except LineTooLong:
            response = too_large_response(limit)
        else:
            if line is None:
                return handled
            if not line.strip():
                continue
            response = runtime.handle_json(line)
        stdout.write(response.encode("utf-8") + b"\n")
        stdout.flush()
        handled += 1
