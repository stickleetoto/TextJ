from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from textj.models import OCRLine


@dataclass(frozen=True, slots=True)
class BackendResult:
    lines: tuple[OCRLine, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


class OCRBackend(ABC):
    """Interface implemented by OCR engines used by TextJ."""

    name: str

    @abstractmethod
    def recognize(self, image_path: Path) -> BackendResult:
        """Recognize text from an image file."""
        raise NotImplementedError
