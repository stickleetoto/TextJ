"""Local daemon: newline-delimited JSON protocol v1 over loopback TCP.

Security boundary
-----------------
* Binds to loopback addresses only; other hosts are refused.
* By default every request must carry ``auth_token`` equal to a random token
  that is written, with owner-only permissions, to the state file together
  with the port. Other local users therefore cannot use the daemon to read
  images they have no access to. ``--no-auth`` disables this explicitly.
* Concurrent connections are bounded; excess connections get one ``BUSY``
  response and are closed. OCR concurrency is bounded by the runtime.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
import secrets
import socket
import socketserver
import threading
from pathlib import Path
from time import perf_counter
from typing import Any

from textj import __version__
from textj.api.errors import ErrorCode, TextJError
from textj.api.request import PROTOCOL_VERSION, peek_request_id
from textj.api.response import encode_json, error_envelope
from textj.runtime import TextJRuntime
from textj.transport.framing import LineTooLong, decode_message, read_line, too_large_response

log = logging.getLogger("textj.server")

_IS_WINDOWS = os.name == "nt"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47631


def default_state_file() -> Path:
    override = os.environ.get("TEXTJ_STATE_FILE")
    if override:
        return Path(override)
    return Path.home() / ".textj" / "daemon.json"


def ensure_loopback(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError(f"host must be a loopback IP address or 'localhost', got {host!r}")
    if not address.is_loopback:
        raise ValueError(f"refusing to bind non-loopback address {host!r}")


def write_state_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    os.replace(temporary, path)


class _Handler(socketserver.StreamRequestHandler):
    server: "TextJServer"

    def handle(self) -> None:
        server = self.server
        if not server.acquire_connection():
            error = TextJError(
                ErrorCode.BUSY,
                "too many open connections",
                details={"max_connections": server.max_connections},
            )
            self._send(encode_json(error_envelope(None, error)))
            return
        try:
            self.connection.settimeout(server.idle_timeout)
            limit = server.runtime.config.limits.max_request_bytes
            while not server.stopping.is_set():
                try:
                    line = read_line(self.rfile, limit)
                except LineTooLong:
                    self._send(too_large_response(limit))
                    continue
                except (socket.timeout, OSError):
                    return
                if line is None:
                    return
                if not line.strip():
                    continue
                if not self._send(server.process(line)):
                    return
        finally:
            server.release_connection()

    def _send(self, message: str) -> bool:
        try:
            self.wfile.write(message.encode("utf-8") + b"\n")
            self.wfile.flush()
            return True
        except OSError:
            return False


class TextJServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets another process bind the same port and
    # steal connections; use SO_EXCLUSIVEADDRUSE there instead (server_bind).
    allow_reuse_address = not _IS_WINDOWS

    def __init__(
        self,
        runtime: TextJRuntime,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        token: str | None = None,
        max_connections: int = 16,
        idle_timeout: float = 300.0,
    ) -> None:
        ensure_loopback(host)
        if max_connections < 1:
            raise ValueError("max_connections must be at least 1")
        self.runtime = runtime
        self.token = token
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.stopping = threading.Event()
        self._connections = threading.BoundedSemaphore(max_connections)
        if ":" in host:
            self.address_family = socket.AF_INET6
        super().__init__((host, port), _Handler)

    def server_bind(self) -> None:
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if _IS_WINDOWS and exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        super().server_bind()

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def host(self) -> str:
        return str(self.server_address[0])

    def acquire_connection(self) -> bool:
        return self._connections.acquire(blocking=False)

    def release_connection(self) -> None:
        self._connections.release()

    def state_payload(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "token": self.token,
            "pid": os.getpid(),
            "protocol_version": PROTOCOL_VERSION,
            "textj_version": __version__,
        }

    def process(self, raw: bytes) -> str:
        """Handle one framed request line and return the encoded response."""
        received = perf_counter()
        payload, error = decode_message(raw)
        if error is None and self.token is not None:
            supplied = payload.get("auth_token") if isinstance(payload, dict) else None
            if not isinstance(supplied, str) or not hmac.compare_digest(
                supplied.encode("utf-8"), self.token.encode("utf-8")
            ):
                error = TextJError(ErrorCode.UNAUTHORIZED, "missing or invalid auth_token")
        if error is not None:
            self.runtime.record_error(error)
            return encode_json(error_envelope(peek_request_id(payload), error))
        return encode_json(self.runtime.handle(payload, received_at=received))

    def shutdown(self) -> None:
        self.stopping.set()
        super().shutdown()


def new_token() -> str:
    return secrets.token_urlsafe(32)
