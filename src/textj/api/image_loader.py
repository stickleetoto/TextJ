"""Image acquisition and normalization for protocol requests.

All inputs are converted exactly once into a contiguous ``uint8`` BGR array of
shape ``(H, W, 3)``, which is what the OCR backend receives. Limits are
checked from the image header before the full decode whenever possible.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from textj.api.errors import ErrorCode, TextJError
from textj.api.limits import Limits
from textj.api.request import ImageInput

try:  # OpenCV is a RapidOCR dependency; Pillow is the fallback decoder.
    import cv2 as _cv2
except Exception:  # pragma: no cover - exercised only without OpenCV
    _cv2 = None


@dataclass(frozen=True, slots=True)
class LoadedImage:
    array: np.ndarray
    width: int
    height: int
    source: str
    encoded_bytes: int | None
    format: str | None

    def describe(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "width": self.width,
            "height": self.height,
            "source": self.source,
        }
        if self.format is not None:
            info["format"] = self.format
        if self.encoded_bytes is not None:
            info["bytes"] = self.encoded_bytes
        return info


def load_image(image: ImageInput, limits: Limits = Limits()) -> LoadedImage:
    if image.kind == "ndarray":
        assert image.array is not None
        array = normalize_array(image.array, limits)
        height, width = array.shape[:2]
        return LoadedImage(array, width, height, "ndarray", None, None)

    if image.kind == "path":
        assert image.path is not None
        data = _read_path(image.path, limits)
        source = "path"
    elif image.kind == "bytes":
        assert image.data is not None
        data = image.data
        if len(data) > limits.max_image_bytes:
            raise _too_large("encoded image exceeds max_image_bytes", limits)
        source = "bytes"
    else:
        raise TextJError(ErrorCode.INVALID_REQUEST, f"unknown input kind {image.kind!r}")

    array, fmt = decode_image_bytes(data, limits)
    height, width = array.shape[:2]
    return LoadedImage(array, width, height, source, len(data), fmt)


def _too_large(message: str, limits: Limits) -> TextJError:
    return TextJError(
        ErrorCode.REQUEST_TOO_LARGE,
        message,
        details={
            "max_image_bytes": limits.max_image_bytes,
            "max_image_pixels": limits.max_image_pixels,
            "max_image_side": limits.max_image_side,
        },
    )


def _read_path(path: Path, limits: Limits) -> bytes:
    try:
        stat = path.stat()
    except (FileNotFoundError, NotADirectoryError):
        raise TextJError(
            ErrorCode.IMAGE_NOT_FOUND, "input image was not found", details={"path": str(path)}
        )
    except OSError as exc:
        raise TextJError(
            ErrorCode.IMAGE_NOT_FOUND,
            f"input image is not accessible: {exc.strerror or exc}",
            details={"path": str(path)},
        )
    if not path.is_file():
        raise TextJError(
            ErrorCode.IMAGE_NOT_FOUND,
            "input path is not a regular file",
            details={"path": str(path)},
        )
    if stat.st_size > limits.max_image_bytes:
        raise _too_large("image file exceeds max_image_bytes", limits)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TextJError(
            ErrorCode.IMAGE_NOT_FOUND,
            f"input image could not be read: {exc.strerror or exc}",
            details={"path": str(path)},
        )


def _check_dimensions(width: int, height: int, limits: Limits) -> None:
    if width <= 0 or height <= 0:
        raise TextJError(ErrorCode.UNSUPPORTED_IMAGE, "image has zero width or height")
    if width > limits.max_image_side or height > limits.max_image_side:
        raise _too_large(
            f"image dimensions {width}x{height} exceed max_image_side", limits
        )
    if width * height > limits.max_image_pixels:
        raise _too_large(
            f"image pixel count {width * height} exceeds max_image_pixels", limits
        )


def _probe_header(data: bytes) -> tuple[int, int, str | None]:
    """Read dimensions from the image header without decoding pixels."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as probe:
            return probe.width, probe.height, probe.format
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise TextJError(
            ErrorCode.IMAGE_DECODE_FAILED, f"image could not be identified: {exc}"
        )
    except Image.DecompressionBombError:
        raise TextJError(ErrorCode.REQUEST_TOO_LARGE, "image exceeds decoder pixel limit")


def decode_image_bytes(data: bytes, limits: Limits = Limits()) -> tuple[np.ndarray, str | None]:
    if not data:
        raise TextJError(ErrorCode.IMAGE_DECODE_FAILED, "image data is empty")

    width, height, fmt = _probe_header(data)
    _check_dimensions(width, height, limits)

    decoded: np.ndarray | None = None
    if _cv2 is not None:
        buffer = np.frombuffer(data, dtype=np.uint8)
        # IMREAD_UNCHANGED keeps alpha/16-bit but ignores EXIF orientation;
        # JPEG has no alpha and is where EXIF orientation matters.
        flags = _cv2.IMREAD_COLOR if fmt in ("JPEG", "MPO") else _cv2.IMREAD_UNCHANGED
        decoded = _cv2.imdecode(buffer, flags)
        if decoded is not None and decoded.ndim == 3 and decoded.shape[2] == 4:
            decoded = _composite_alpha(decoded)

    if decoded is None:
        decoded = _decode_with_pillow(data)

    return normalize_array(decoded, limits, color_order="bgr"), fmt


def _decode_with_pillow(data: bytes) -> np.ndarray:
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image) or image
            if image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
                bgra = np.ascontiguousarray(rgba[:, :, [2, 1, 0, 3]])
                return _composite_alpha(bgra)
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    except TextJError:
        raise
    except Exception as exc:
        raise TextJError(ErrorCode.IMAGE_DECODE_FAILED, f"image could not be decoded: {exc}")
    return rgb[:, :, ::-1]


def _composite_alpha(bgra: np.ndarray) -> np.ndarray:
    """Flatten BGRA onto a background that contrasts with the visible pixels."""
    alpha = bgra[:, :, 3]
    if alpha.dtype != np.uint8:
        bgra = _to_uint8(bgra)
        alpha = bgra[:, :, 3]
    if bool((alpha == 255).all()):
        return bgra[:, :, :3]

    bgr = bgra[:, :, :3].astype(np.float32)
    visible = alpha > 0
    if visible.any():
        pixels = bgr[visible]
        luminance = float(
            (0.114 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.299 * pixels[:, 2]).mean()
        )
    else:
        luminance = 0.0
    background = 255.0 if luminance < 128.0 else 0.0
    weight = alpha.astype(np.float32)[:, :, None] / 255.0
    blended = bgr * weight + background * (1.0 - weight)
    return np.clip(blended + 0.5, 0, 255).astype(np.uint8)


def _to_uint8(array: np.ndarray) -> np.ndarray:
    if array.dtype == np.uint8:
        return array
    if array.dtype == np.uint16:
        return (array >> 8).astype(np.uint8)
    raise TextJError(
        ErrorCode.UNSUPPORTED_IMAGE,
        f"unsupported pixel dtype {array.dtype}",
        details={"dtype": str(array.dtype)},
    )


def normalize_array(
    array: np.ndarray,
    limits: Limits = Limits(),
    *,
    color_order: str = "bgr",
) -> np.ndarray:
    """Return a contiguous uint8 (H, W, 3) BGR view/copy of ``array``.

    Accepted: (H, W) gray, (H, W, 1) gray, (H, W, 3) BGR, (H, W, 4) BGRA.
    uint16 input is scaled to uint8. Other dtypes are ``UNSUPPORTED_IMAGE``.
    """
    if not isinstance(array, np.ndarray):
        raise TextJError(ErrorCode.UNSUPPORTED_IMAGE, "image must be a numpy array")
    if array.ndim not in (2, 3):
        raise TextJError(
            ErrorCode.UNSUPPORTED_IMAGE,
            f"image array must have 2 or 3 dimensions, got {array.ndim}",
        )
    height, width = int(array.shape[0]), int(array.shape[1])
    _check_dimensions(width, height, limits)

    array = _to_uint8(array)

    if array.ndim == 2:
        array = np.repeat(array[:, :, None], 3, axis=2)
    else:
        channels = array.shape[2]
        if channels == 1:
            array = np.repeat(array, 3, axis=2)
        elif channels == 4:
            array = _composite_alpha(array)
        elif channels != 3:
            raise TextJError(
                ErrorCode.UNSUPPORTED_IMAGE,
                f"unsupported channel count {channels}",
                details={"channels": int(channels)},
            )

    if color_order != "bgr":  # pragma: no cover - reserved for future adapters
        raise ValueError(f"unsupported color order {color_order}")

    return np.ascontiguousarray(array)
