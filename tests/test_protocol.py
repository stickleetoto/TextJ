import json

import numpy as np
import pytest

from conftest import b64, png_bytes, request
from textj.api import ErrorCode, Limits, TextJError, parse_request
from textj.api.image_loader import decode_image_bytes, load_image, normalize_array
from textj.api.request import BatchRequest, ImageInput, OCRRequest, StatusRequest
from textj.api.response import encode_json, error_envelope


def code_of(payload, limits=Limits()) -> str:
    with pytest.raises(TextJError) as info:
        parse_request(payload, limits)
    return info.value.code.value


def test_parse_ocr_path_request() -> None:
    parsed = parse_request(request(
        request_id="r1",
        input={"type": "path", "path": "/tmp/x.png"},
        options={"min_score": 0.7, "include_boxes": False},
        timeout_ms=500,
    ))
    assert isinstance(parsed, OCRRequest)
    assert parsed.request_id == "r1"
    assert parsed.image.kind == "path"
    assert parsed.options.min_score == 0.7
    assert parsed.options.include_boxes is False
    assert parsed.timeout_ms == 500


def test_generates_request_id_and_parses_base64() -> None:
    parsed = parse_request(request(input={"type": "bytes_base64", "data": b64(b"abc")}))
    assert len(parsed.request_id) == 32
    assert parsed.image.data == b"abc"


def test_status_request() -> None:
    assert isinstance(parse_request(request("status", request_id="s")), StatusRequest)


@pytest.mark.parametrize(
    "payload, code",
    [
        ([], "INVALID_REQUEST"),
        ({"operation": "ocr"}, "INVALID_REQUEST"),
        ({"protocol_version": "2", "operation": "ocr"}, "UNSUPPORTED_PROTOCOL"),
        ({"protocol_version": 1, "operation": "ocr"}, "UNSUPPORTED_PROTOCOL"),
        (request("translate"), "UNSUPPORTED_OPERATION"),
        (request(), "INVALID_REQUEST"),
        (request(input={"type": "url", "url": "http://x"}), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": ""}), "INVALID_REQUEST"),
        (request(input={"type": "bytes_base64", "data": "!!!"}), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, options={"min_scor": 1}), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, options={"mode": "accurate"}), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, options={"min_score": 2}), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, options={"include_boxes": 1}), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, timeout_ms=0), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, timeout_ms=True), "INVALID_REQUEST"),
        (request(input={"type": "path", "path": "a"}, extra=1), "INVALID_REQUEST"),
        (request(request_id="", input={"type": "path", "path": "a"}), "INVALID_REQUEST"),
        (request("ocr_batch", items=[]), "INVALID_REQUEST"),
        (request("ocr_batch", items=[{"id": "a", "input": {"type": "path", "path": "x"}}] * 2),
         "INVALID_REQUEST"),
    ],
)
def test_invalid_requests_map_to_stable_codes(payload, code) -> None:
    assert code_of(payload) == code


def test_oversized_base64_rejected_before_decode() -> None:
    limits = Limits(max_image_bytes=10)
    payload = request(input={"type": "bytes_base64", "data": "A" * 100})
    assert code_of(payload, limits) == "REQUEST_TOO_LARGE"


def test_batch_limits_and_item_level_errors() -> None:
    limits = Limits(max_batch_items=2)
    items = [{"id": str(i), "input": {"type": "path", "path": "x"}} for i in range(3)]
    assert code_of(request("ocr_batch", items=items), limits) == "REQUEST_TOO_LARGE"

    parsed = parse_request(request("ocr_batch", items=[
        {"id": "good", "input": {"type": "path", "path": "x"}},
        {"id": "bad", "input": {"type": "bytes_base64", "data": "@@"}},
        {"input": {"type": "path", "path": "y"}},
    ]))
    assert isinstance(parsed, BatchRequest)
    assert [item.item_id for item in parsed.items] == ["good", "bad", "2"]
    assert parsed.items[1].error.code is ErrorCode.INVALID_REQUEST
    assert parsed.items[1].image is None


def test_error_envelope_shape_is_stable() -> None:
    error = TextJError(ErrorCode.BUSY, "queue full", details={"max_queue": 1})
    payload = error_envelope("r", error)
    assert payload == {
        "protocol_version": "1",
        "request_id": "r",
        "ok": False,
        "error": {
            "code": "BUSY",
            "message": "queue full",
            "retryable": True,
            "details": {"max_queue": 1},
        },
    }
    assert TextJError(ErrorCode.OCR_FAILED, "x").retryable is False


def test_error_code_values_are_frozen() -> None:
    # Protocol v1 contract: renaming a code is a breaking change.
    assert [code.value for code in ErrorCode] == [
        "INVALID_REQUEST", "UNSUPPORTED_PROTOCOL", "UNSUPPORTED_OPERATION",
        "IMAGE_NOT_FOUND", "IMAGE_DECODE_FAILED", "UNSUPPORTED_IMAGE",
        "REQUEST_TOO_LARGE", "BACKEND_NOT_READY", "BUSY", "TIMEOUT",
        "OCR_FAILED", "UNAUTHORIZED", "INTERNAL_ERROR",
    ]


def test_encode_json_is_compact_unicode_and_rejects_nan() -> None:
    assert encode_json({"text": "한글", "n": 1}) == '{"text":"한글","n":1}'
    with pytest.raises(ValueError):
        encode_json({"x": float("nan")})


# ---------------------------------------------------------------- image loading


def test_load_path_and_bytes(png_path) -> None:
    loaded = load_image(ImageInput.from_path(png_path))
    assert loaded.array.shape == (20, 40, 3)
    assert loaded.array.dtype == np.uint8
    assert loaded.array.flags["C_CONTIGUOUS"]
    assert loaded.describe() == {
        "width": 40, "height": 20, "source": "path", "format": "PNG",
        "bytes": png_path.stat().st_size,
    }
    assert load_image(ImageInput.from_bytes(png_bytes())).source == "bytes"


def test_load_errors(tmp_path) -> None:
    def code(image, limits=Limits()):
        with pytest.raises(TextJError) as info:
            load_image(image, limits)
        return info.value.code.value

    assert code(ImageInput.from_path(tmp_path / "missing.png")) == "IMAGE_NOT_FOUND"
    assert code(ImageInput.from_path(tmp_path)) == "IMAGE_NOT_FOUND"
    assert code(ImageInput.from_bytes(b"not an image")) == "IMAGE_DECODE_FAILED"
    assert code(ImageInput.from_bytes(png_bytes(100, 100)), Limits(max_image_pixels=500)) == "REQUEST_TOO_LARGE"
    assert code(ImageInput.from_bytes(png_bytes(100, 10)), Limits(max_image_side=50)) == "REQUEST_TOO_LARGE"
    assert code(ImageInput.from_bytes(png_bytes()), Limits(max_image_bytes=10)) == "REQUEST_TOO_LARGE"
    big = tmp_path / "big.png"
    big.write_bytes(png_bytes())
    assert code(ImageInput.from_path(big), Limits(max_image_bytes=10)) == "REQUEST_TOO_LARGE"
    assert code(ImageInput.from_array(np.zeros((4, 4), dtype=np.float32))) == "UNSUPPORTED_IMAGE"
    assert code(ImageInput.from_array(np.zeros((4, 4, 5), dtype=np.uint8))) == "UNSUPPORTED_IMAGE"
    assert code(ImageInput.from_array(np.zeros((0, 4, 3), dtype=np.uint8))) == "UNSUPPORTED_IMAGE"
    assert code(ImageInput.from_array(np.zeros((2, 2, 2, 2), dtype=np.uint8))) == "UNSUPPORTED_IMAGE"


def test_normalize_array_variants() -> None:
    bgr = np.zeros((3, 4, 3), dtype=np.uint8)
    assert normalize_array(bgr) is bgr  # contiguous uint8 BGR passes without copy
    assert normalize_array(np.zeros((3, 4), dtype=np.uint8)).shape == (3, 4, 3)
    assert normalize_array(np.zeros((3, 4, 1), dtype=np.uint8)).shape == (3, 4, 3)
    assert normalize_array(np.full((3, 4, 3), 65535, dtype=np.uint16)).max() == 255
    bgra = np.zeros((3, 4, 4), dtype=np.uint8)
    bgra[..., 3] = 255
    assert normalize_array(bgra).shape == (3, 4, 3)


def test_transparent_black_text_is_composited_on_white() -> None:
    from PIL import Image
    import io

    image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    image.putpixel((5, 5), (0, 0, 0, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    array, fmt = decode_image_bytes(buffer.getvalue())
    assert fmt == "PNG"
    assert array[0, 0].tolist() == [255, 255, 255]
    assert array[5, 5].tolist() == [0, 0, 0]


def test_bgr_channel_order_from_png() -> None:
    from PIL import Image
    import io

    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, format="PNG")
    array, _ = decode_image_bytes(buffer.getvalue())
    assert array[0, 0].tolist() == [30, 20, 10]


def test_pillow_fallback_decoder(monkeypatch) -> None:
    from PIL import Image
    import io
    import textj.api.image_loader as loader

    monkeypatch.setattr(loader, "_cv2", None)
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, format="PNG")
    array, _ = loader.decode_image_bytes(buffer.getvalue())
    assert array[0, 0].tolist() == [30, 20, 10]
    assert array.flags["C_CONTIGUOUS"]
