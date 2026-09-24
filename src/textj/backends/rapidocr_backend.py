from __future__ import annotations

from typing import Any

from textj.backends.base import BackendResult, OCRBackend
from textj.image_types import OCRInput
from textj.models import Box, OCRLine

# Model profiles map a stable TextJ name to RapidOCR model selection.
#
# ppocrv5-mobile: PP-OCRv5 mobile detector + language-specific PP-OCRv5 mobile
#   recognizer. Required for Korean. Models are downloaded by RapidOCR on first
#   use (network access to RapidOCR's model host is required once).
# ppocrv6-small: PP-OCRv6 small multilingual detector/recognizer bundled inside
#   the rapidocr wheel. Works fully offline, but has no Hangul in its
#   dictionary, so it is only suitable for English/Latin/Chinese text.
PROFILES = ("ppocrv5-mobile", "ppocrv6-small")
DEFAULT_PROFILE = "ppocrv5-mobile"
LANGUAGES = ("korean", "en", "ch")


class RapidOCRBackend(OCRBackend):
    """RapidOCR backend on ONNX Runtime."""

    name = "rapidocr-onnx"

    def __init__(
        self,
        *,
        language: str = "korean",
        text_score: float = 0.5,
        profile: str = DEFAULT_PROFILE,
        log_level: str = "warning",
        det_limit_type: str | None = None,
        det_limit_side_len: int | None = None,
        engine: Any = None,
    ) -> None:
        if language not in LANGUAGES:
            raise ValueError(f"Unsupported RapidOCR language: {language}")
        if profile not in PROFILES:
            raise ValueError(f"Unsupported RapidOCR profile: {profile}")

        self.language = language
        self.text_score = text_score
        self.profile = profile
        if det_limit_type not in (None, "min", "max"):
            raise ValueError(f"Unsupported det_limit_type: {det_limit_type}")
        if det_limit_side_len is not None and det_limit_side_len < 32:
            raise ValueError("det_limit_side_len must be at least 32")
        self.det_limit_type = det_limit_type
        self.det_limit_side_len = det_limit_side_len

        if engine is not None:
            # Injected engine: used by tests to exercise result conversion.
            self._engine = engine
            return

        try:
            from rapidocr import (
                EngineType,
                LangDet,
                LangRec,
                ModelType,
                OCRVersion,
                RapidOCR,
            )
        except ImportError as exc:
            raise RuntimeError(
                "RapidOCR backend is unavailable. "
                "Install TextJ dependencies with: pip install -e ."
            ) from exc

        params: dict[str, Any] = {
            "Global.text_score": text_score,
            "Global.log_level": log_level,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
        }

        if profile == "ppocrv5-mobile":
            lang_map = {
                "korean": LangRec.KOREAN,
                "en": LangRec.EN,
                "ch": LangRec.CH,
            }
            params.update({
                "Det.lang_type": LangDet.CH,
                "Det.model_type": ModelType.MOBILE,
                "Det.ocr_version": OCRVersion.PPOCRV5,
                "Rec.lang_type": lang_map[language],
                "Rec.model_type": ModelType.MOBILE,
                "Rec.ocr_version": OCRVersion.PPOCRV5,
            })
        else:
            if language == "korean":
                raise ValueError(
                    "Profile 'ppocrv6-small' has no Korean recognizer; "
                    "use profile 'ppocrv5-mobile' for Korean."
                )
            params.update({
                "Det.model_type": ModelType.SMALL,
                "Det.ocr_version": OCRVersion.PPOCRV6,
                "Rec.model_type": ModelType.SMALL,
                "Rec.ocr_version": OCRVersion.PPOCRV6,
            })

        # Detector resizing policy. RapidOCR's default ("min", 736) upscales the
        # short side to 736 px, which is very expensive for wide screen crops.
        if det_limit_type is not None:
            params["Det.limit_type"] = det_limit_type
        if det_limit_side_len is not None:
            params["Det.limit_side_len"] = det_limit_side_len

        self._engine = RapidOCR(params=params)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "profile": self.profile,
            "language": self.language,
            "text_score": self.text_score,
            "det_limit_type": self.det_limit_type,
            "det_limit_side_len": self.det_limit_side_len,
        }

    def recognize(self, image: OCRInput) -> BackendResult:
        # ndarray inputs are expected to already use OpenCV/BGR channel order.
        # Screen text is normally upright, so classification stays disabled on
        # the fast path.
        result = self._engine(image, use_cls=False)

        raw_txts = getattr(result, "txts", None)
        raw_scores = getattr(result, "scores", None)
        raw_boxes = getattr(result, "boxes", None)

        txts = tuple(raw_txts) if raw_txts is not None else ()
        scores = tuple(raw_scores) if raw_scores is not None else ()
        boxes = raw_boxes if raw_boxes is not None else ()

        lines: list[OCRLine] = []
        for index, text in enumerate(txts):
            clean_text = str(text).strip()
            if not clean_text:
                continue

            score = float(scores[index]) if index < len(scores) else 0.0
            box: Box | None = None
            if index < len(boxes):
                box = _normalize_box(boxes[index])

            lines.append(OCRLine(text=clean_text, score=score, box=box))

        metadata: dict[str, Any] = {
            "language": self.language,
            "text_score": self.text_score,
            "profile": self.profile,
        }

        engine_elapsed = getattr(result, "elapse", None)
        if isinstance(engine_elapsed, (int, float)):
            metadata["engine_elapsed_ms"] = float(engine_elapsed) * 1000.0

        engine_stages = getattr(result, "elapse_list", None)
        if engine_stages is not None:
            # RapidOCR reports None for skipped stages (classification is
            # disabled on the fast path), so only numeric entries are kept.
            names = ("detect", "classify", "recognize")
            stages = {
                name: float(value) * 1000.0
                for name, value in zip(names, list(engine_stages))
                if isinstance(value, (int, float))
            }
            if stages:
                metadata["engine_stages_ms"] = stages

        return BackendResult(lines=tuple(lines), metadata=metadata)


def _normalize_box(raw_box: Any) -> Box | None:
    if hasattr(raw_box, "tolist"):
        raw_box = raw_box.tolist()

    try:
        points = tuple(
            (float(point[0]), float(point[1]))
            for point in raw_box
        )
    except (TypeError, ValueError, IndexError):
        return None

    if len(points) != 4:
        return None

    return points  # type: ignore[return-value]
