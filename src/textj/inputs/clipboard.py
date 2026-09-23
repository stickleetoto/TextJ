from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageGrab


class ClipboardImageError(RuntimeError):
    """Raised when the clipboard does not contain a usable image."""


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    """Convert a PIL image to a contiguous uint8 BGR array for RapidOCR."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return np.ascontiguousarray(rgb[:, :, ::-1])


def grab_clipboard_bgr() -> np.ndarray:
    """Read an image from the OS clipboard without writing a temporary file."""
    content = ImageGrab.grabclipboard()

    if isinstance(content, Image.Image):
        return pil_to_bgr(content)

    if isinstance(content, list):
        for raw_path in content:
            path = Path(raw_path)
            if not path.is_file():
                continue
            try:
                with Image.open(path) as image:
                    return pil_to_bgr(image)
            except (OSError, ValueError):
                continue

    raise ClipboardImageError(
        "Clipboard does not contain an image or a readable image file."
    )
