"""Client for the TextJ local daemon (protocol v1 over loopback TCP)."""

from __future__ import annotations

import base64
import json
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from textj.api.request import PROTOCOL_VERSION
from textj.transport.server import default_state_file


class TextJClientError(ConnectionError):
    """Transport-level failure (daemon unreachable, connection dropped)."""


class TextJClient:
    """Persistent connection to a TextJ daemon.

    Methods return protocol v1 response envelopes (dicts). OCR failures are
    reported inside the envelope (``ok: false``); only transport failures
    raise :class:`TextJClientError`. One request is in flight per client;
    use one client per thread for parallel calls.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 47631,
        *,
        token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._file = None
        self._lock = threading.Lock()

    @classmethod
    def from_state_file(cls, path: str | Path | None = None, **kwargs: Any) -> "TextJClient":
        state_path = Path(path) if path is not None else default_state_file()
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise TextJClientError(f"cannot read daemon state file {state_path}: {exc}") from exc
        return cls(state["host"], int(state["port"]), token=state.get("token"), **kwargs)

    # ---------------------------------------------------------------- connection

    def connect(self) -> "TextJClient":
        if self._sock is None:
            try:
                sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            except OSError as exc:
                raise TextJClientError(
                    f"cannot connect to TextJ daemon at {self.host}:{self.port}: {exc}"
                ) from exc
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sock = sock
            self._file = sock.makefile("rwb")
        return self

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._file = None

    def __enter__(self) -> "TextJClient":
        return self.connect()

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # ---------------------------------------------------------------- protocol

    def request(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Send one raw protocol message and return the decoded response."""
        message = dict(payload)
        if self.token is not None:
            message["auth_token"] = self.token
        data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with self._lock:
            self.connect()
            assert self._file is not None
            try:
                self._file.write(data + b"\n")
                self._file.flush()
                line = self._file.readline()
            except OSError as exc:
                self.close()
                raise TextJClientError(f"connection to TextJ daemon failed: {exc}") from exc
            if not line:
                self.close()
                raise TextJClientError("TextJ daemon closed the connection")
        return json.loads(line)

    def _envelope(self, operation: str, request_id: str | None, **fields: Any) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id or uuid.uuid4().hex,
            "operation": operation,
            **{key: value for key, value in fields.items() if value is not None},
        }

    def status(self, *, request_id: str | None = None) -> dict[str, Any]:
        return self.request(self._envelope("status", request_id))

    def ocr_path(self, path: str | Path, *, request_id: str | None = None,
                 timeout_ms: int | None = None, **options: Any) -> dict[str, Any]:
        return self.request(self._envelope(
            "ocr", request_id,
            input={"type": "path", "path": str(Path(path).resolve())},
            options=options or None,
            timeout_ms=timeout_ms,
        ))

    def ocr_bytes(self, data: bytes, *, request_id: str | None = None,
                  timeout_ms: int | None = None, **options: Any) -> dict[str, Any]:
        return self.request(self._envelope(
            "ocr", request_id,
            input={"type": "bytes_base64", "data": base64.b64encode(data).decode("ascii")},
            options=options or None,
            timeout_ms=timeout_ms,
        ))

    def ocr_batch(self, items: Iterable[Mapping[str, Any]], *, request_id: str | None = None,
                  timeout_ms: int | None = None, **options: Any) -> dict[str, Any]:
        """``items``: protocol item objects ``{"id": ..., "input": {...}}``."""
        return self.request(self._envelope(
            "ocr_batch", request_id,
            items=[dict(item) for item in items],
            options=options or None,
            timeout_ms=timeout_ms,
        ))
