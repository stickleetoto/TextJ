"""TextJ - ultra-fast local OCR for AI agents and automation."""

from typing import Any

from .models import OCRLine, OCRResult

__all__ = ["OCRLine", "OCRResult", "RuntimeConfig", "TextJRuntime"]
__version__ = "0.1.0.dev0"


def __getattr__(name: str) -> Any:
    # Lazy so that light imports (models, CLI --help) stay cheap.
    if name in ("TextJRuntime", "RuntimeConfig"):
        from textj import runtime

        return getattr(runtime, name)
    raise AttributeError(f"module 'textj' has no attribute {name!r}")
