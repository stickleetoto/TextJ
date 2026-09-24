from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class Limits:
    """Input/request limits enforced before any expensive work.

    Oversized work is rejected with ``REQUEST_TOO_LARGE``.
    """

    # Maximum size of one encoded protocol message (JSON line) in bytes.
    max_request_bytes: int = 64 * MIB
    # Maximum encoded image size (file size or decoded base64 bytes).
    max_image_bytes: int = 32 * MIB
    # Maximum decoded pixel count (width * height).
    max_image_pixels: int = 50_000_000
    # Maximum width or height in pixels.
    max_image_side: int = 16_384
    # Maximum number of items in one ocr_batch request.
    max_batch_items: int = 64
    # Timeout used when a request does not specify timeout_ms.
    default_timeout_ms: int = 30_000
    # Upper bound for a caller-supplied timeout_ms.
    max_timeout_ms: int = 600_000

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"limit {name} must be a positive integer")
        if self.default_timeout_ms > self.max_timeout_ms:
            raise ValueError("default_timeout_ms cannot exceed max_timeout_ms")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
