"""Protocol v1 request model and parser.

Every transport (Python API, JSON stdio, daemon, MCP) converts its input into
these types. Parsing is strict: unknown fields are rejected so that caller
typos surface as ``INVALID_REQUEST`` instead of being silently ignored.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Union

import numpy as np

from textj.api.errors import ErrorCode, TextJError
from textj.api.limits import Limits

PROTOCOL_VERSION = "1"

OP_OCR = "ocr"
OP_OCR_BATCH = "ocr_batch"
OP_STATUS = "status"
OPERATIONS = (OP_OCR, OP_OCR_BATCH, OP_STATUS)

MODES = ("fast",)
MAX_ID_LENGTH = 128

# Top-level keys that transports may attach and that carry no OCR semantics.
TRANSPORT_KEYS = frozenset({"auth_token"})


@dataclass(frozen=True, slots=True)
class ImageInput:
    """Validated image descriptor. Exactly one source field is set."""

    kind: str  # "path" | "bytes" | "ndarray"
    path: Path | None = None
    data: bytes | None = None
    array: np.ndarray | None = field(default=None, compare=False)

    @classmethod
    def from_path(cls, path: str | Path) -> "ImageInput":
        return cls(kind="path", path=Path(path))

    @classmethod
    def from_bytes(cls, data: bytes) -> "ImageInput":
        return cls(kind="bytes", data=bytes(data))

    @classmethod
    def from_array(cls, array: np.ndarray) -> "ImageInput":
        return cls(kind="ndarray", array=array)


@dataclass(frozen=True, slots=True)
class OCROptions:
    language: str | None = None
    mode: str = "fast"
    min_score: float = 0.5
    include_boxes: bool = True
    include_timings: bool = True


@dataclass(frozen=True, slots=True)
class OCRRequest:
    request_id: str
    image: ImageInput
    options: OCROptions = OCROptions()
    timeout_ms: int | None = None
    operation: str = OP_OCR


@dataclass(frozen=True, slots=True)
class BatchItem:
    item_id: str
    image: ImageInput | None
    # Item-level input problems are reported per item, not for the batch.
    error: TextJError | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class BatchRequest:
    request_id: str
    items: tuple[BatchItem, ...]
    options: OCROptions = OCROptions()
    timeout_ms: int | None = None
    operation: str = OP_OCR_BATCH


@dataclass(frozen=True, slots=True)
class StatusRequest:
    request_id: str
    operation: str = OP_STATUS


Request = Union[OCRRequest, BatchRequest, StatusRequest]


def new_request_id() -> str:
    return uuid.uuid4().hex


def _invalid(message: str, **details: Any) -> TextJError:
    return TextJError(ErrorCode.INVALID_REQUEST, message, details=details or None)


def _check_keys(obj: Mapping[str, Any], allowed: set[str] | frozenset[str],
                where: str) -> None:
    unknown = sorted(str(key) for key in obj if key not in allowed)
    if unknown:
        raise _invalid(
            f"unknown field(s) in {where}: {', '.join(unknown)}",
            field=where,
            unknown=unknown,
        )


def peek_request_id(payload: Any) -> str | None:
    """Best-effort request_id extraction for error responses."""
    if isinstance(payload, Mapping):
        value = payload.get("request_id")
        if isinstance(value, str) and 0 < len(value) <= MAX_ID_LENGTH:
            return value
    return None


def parse_request(payload: Any, limits: Limits = Limits()) -> Request:
    """Validate a decoded JSON protocol message and build a request object."""
    if not isinstance(payload, Mapping):
        raise _invalid("request must be a JSON object")

    if "protocol_version" not in payload:
        raise _invalid("missing protocol_version", field="protocol_version")
    version = payload["protocol_version"]
    if version != PROTOCOL_VERSION:
        raise TextJError(
            ErrorCode.UNSUPPORTED_PROTOCOL,
            f"unsupported protocol_version {version!r}",
            details={"supported": [PROTOCOL_VERSION]},
        )

    request_id = payload.get("request_id")
    if request_id is None:
        request_id = new_request_id()
    elif not isinstance(request_id, str) or not 0 < len(request_id) <= MAX_ID_LENGTH:
        raise _invalid(
            f"request_id must be a non-empty string of at most {MAX_ID_LENGTH} characters",
            field="request_id",
        )

    operation = payload.get("operation")
    if not isinstance(operation, str):
        raise _invalid("missing or non-string operation", field="operation")
    if operation not in OPERATIONS:
        raise TextJError(
            ErrorCode.UNSUPPORTED_OPERATION,
            f"unsupported operation {operation!r}",
            details={"supported": list(OPERATIONS)},
        )

    common = {"protocol_version", "request_id", "operation"} | TRANSPORT_KEYS

    if operation == OP_STATUS:
        _check_keys(payload, common, "request")
        return StatusRequest(request_id=request_id)

    timeout_ms = _parse_timeout(payload.get("timeout_ms"), limits)
    options = parse_options(payload.get("options"))

    if operation == OP_OCR:
        _check_keys(payload, common | {"input", "options", "timeout_ms"}, "request")
        image = parse_input(payload.get("input"), limits)
        return OCRRequest(
            request_id=request_id,
            image=image,
            options=options,
            timeout_ms=timeout_ms,
        )

    _check_keys(payload, common | {"items", "options", "timeout_ms"}, "request")
    items = _parse_items(payload.get("items"), limits)
    return BatchRequest(
        request_id=request_id,
        items=items,
        options=options,
        timeout_ms=timeout_ms,
    )


def _parse_timeout(value: Any, limits: Limits) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise _invalid("timeout_ms must be an integer", field="timeout_ms")
    if not 1 <= value <= limits.max_timeout_ms:
        raise _invalid(
            f"timeout_ms must be between 1 and {limits.max_timeout_ms}",
            field="timeout_ms",
            max=limits.max_timeout_ms,
        )
    return value


def parse_options(value: Any) -> OCROptions:
    if value is None:
        return OCROptions()
    if not isinstance(value, Mapping):
        raise _invalid("options must be an object", field="options")
    _check_keys(
        value,
        {"language", "mode", "min_score", "include_boxes", "include_timings"},
        "options",
    )

    language = value.get("language")
    if language is not None and not isinstance(language, str):
        raise _invalid("options.language must be a string", field="options.language")

    mode = value.get("mode", "fast")
    if mode not in MODES:
        raise _invalid(
            f"options.mode must be one of {list(MODES)}",
            field="options.mode",
            supported=list(MODES),
        )

    min_score = value.get("min_score", 0.5)
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)) or not (
        0.0 <= float(min_score) <= 1.0
    ):
        raise _invalid(
            "options.min_score must be a number between 0 and 1",
            field="options.min_score",
        )

    flags = {}
    for name in ("include_boxes", "include_timings"):
        flag = value.get(name, True)
        if not isinstance(flag, bool):
            raise _invalid(f"options.{name} must be a boolean", field=f"options.{name}")
        flags[name] = flag

    return OCROptions(
        language=language,
        mode=mode,
        min_score=float(min_score),
        **flags,
    )


def parse_input(value: Any, limits: Limits) -> ImageInput:
    if not isinstance(value, Mapping):
        raise _invalid("input must be an object", field="input")

    kind = value.get("type")
    if kind == "path":
        _check_keys(value, {"type", "path"}, "input")
        path = value.get("path")
        if not isinstance(path, str) or not path:
            raise _invalid("input.path must be a non-empty string", field="input.path")
        if "\x00" in path:
            raise _invalid("input.path contains a NUL character", field="input.path")
        return ImageInput.from_path(path)

    if kind == "bytes_base64":
        _check_keys(value, {"type", "data"}, "input")
        data = value.get("data")
        if not isinstance(data, str) or not data:
            raise _invalid("input.data must be a non-empty base64 string", field="input.data")
        # Reject before decoding: base64 expands 3 bytes into 4 characters.
        max_chars = (limits.max_image_bytes + 2) // 3 * 4
        if len(data) > max_chars:
            raise TextJError(
                ErrorCode.REQUEST_TOO_LARGE,
                "encoded image exceeds max_image_bytes",
                details={"max_image_bytes": limits.max_image_bytes},
            )
        try:
            raw = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise _invalid(f"input.data is not valid base64: {exc}", field="input.data")
        return ImageInput.from_bytes(raw)

    raise _invalid(
        "input.type must be 'path' or 'bytes_base64'",
        field="input.type",
        supported=["path", "bytes_base64"],
    )


def _parse_items(value: Any, limits: Limits) -> tuple[BatchItem, ...]:
    if not isinstance(value, list) or not value:
        raise _invalid("items must be a non-empty array", field="items")
    if len(value) > limits.max_batch_items:
        raise TextJError(
            ErrorCode.REQUEST_TOO_LARGE,
            f"batch has {len(value)} items; maximum is {limits.max_batch_items}",
            details={"max_batch_items": limits.max_batch_items},
        )

    items: list[BatchItem] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise _invalid(f"items[{index}] must be an object", field=f"items[{index}]")
        _check_keys(raw, {"id", "input"}, f"items[{index}]")
        item_id = raw.get("id", str(index))
        if not isinstance(item_id, str) or not 0 < len(item_id) <= MAX_ID_LENGTH:
            raise _invalid(
                f"items[{index}].id must be a non-empty string", field=f"items[{index}].id"
            )
        if item_id in seen:
            raise _invalid(f"duplicate item id {item_id!r}", field=f"items[{index}].id")
        seen.add(item_id)

        try:
            items.append(BatchItem(item_id=item_id, image=parse_input(raw.get("input"), limits)))
        except TextJError as exc:
            items.append(BatchItem(item_id=item_id, image=None, error=exc))

    return tuple(items)
