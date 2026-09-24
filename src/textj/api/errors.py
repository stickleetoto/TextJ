"""Stable machine-facing error codes for TextJ protocol v1.

Codes are part of the public contract. Do not rename or remove them without a
protocol version change. Agents should branch on ``code``, never on
``message``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_PROTOCOL = "UNSUPPORTED_PROTOCOL"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    IMAGE_DECODE_FAILED = "IMAGE_DECODE_FAILED"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    BACKEND_NOT_READY = "BACKEND_NOT_READY"
    BUSY = "BUSY"
    TIMEOUT = "TIMEOUT"
    OCR_FAILED = "OCR_FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Default retry hint per code. ``retryable`` means an identical request may
# succeed later without the caller changing it.
_RETRYABLE = {
    ErrorCode.BUSY: True,
    ErrorCode.TIMEOUT: True,
    ErrorCode.BACKEND_NOT_READY: True,
}


class TextJError(Exception):
    """Exception carrying a stable protocol error code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = ErrorCode(code)
        self.message = message
        self.retryable = (
            _RETRYABLE.get(self.code, False) if retryable is None else retryable
        )
        self.details = dict(details) if details else {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            payload["details"] = self.details
        return payload

    def __repr__(self) -> str:
        return f"TextJError({self.code.value}, {self.message!r})"
