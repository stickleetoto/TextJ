from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

from textj.image_types import OCRInput
from textj.models import OCRLine


@dataclass(frozen=True, slots=True)
class BackendResult:
    lines: tuple[OCRLine, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


class OCRBackend(ABC):
    """Interface implemented by OCR engines used by TextJ."""

    name: str

    @abstractmethod
    def recognize(self, image: OCRInput) -> BackendResult:
        """Recognize text from an in-memory image or image file."""
        raise NotImplementedError
