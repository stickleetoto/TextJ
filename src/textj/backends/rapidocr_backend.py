from __future__ import annotations

from pathlib import Path
from typing import Any

from textj.backends.base import BackendResult, OCRBackend
from textj.models import Box, OCRLine


class RapidOCRBackend(OCRBackend):
    """RapidOCR backend using PP-OCRv5 mobile recognition on ONNX Runtime."""

    name = "rapidocr-onnx"

    def __init__(self, *, language: str = "korean", text_score: float = 0.5) -> None:
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

        lang_map = {
            "korean": LangRec.KOREAN,
            "en": LangRec.EN,
            "ch": LangRec.CH,
        }
        try:
            rec_lang = lang_map[language]
        except KeyError as exc:
            raise ValueError(f"Unsupported RapidOCR language: {language}") from exc

        self.language = language
        self.text_score = text_score

        # PP-OCRv5 Korean mobile recognition officially supports Korean text and
        # is paired with the multilingual/ch detector. Models are managed by RapidOCR.
        params = {
            "Global.text_score": text_score,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.CH,
            "Det.model_type": ModelType.MOBILE,
            "Det.ocr_version": OCRVersion.PPOCRV5,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.lang_type": rec_lang,
            "Rec.model_type": ModelType.MOBILE,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
        }
        self._engine = RapidOCR(params=params)

    def recognize(self, image_path: Path) -> BackendResult:
        # Screen text is normally upright. Skipping classification saves work on
        # the fast path; orientation handling belongs to the later accurate path.
        result = self._engine(str(image_path), use_cls=False)

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
        }

        engine_elapsed = getattr(result, "elapse", None)
        if engine_elapsed is not None:
            metadata["engine_elapsed_ms"] = float(engine_elapsed) * 1000.0

        engine_stages = getattr(result, "elapse_list", None)
        if engine_stages is not None:
            values = list(engine_stages)
            if len(values) >= 3:
                metadata["engine_stages_ms"] = {
                    "detect": float(values[0]) * 1000.0,
                    "classify": float(values[1]) * 1000.0,
                    "recognize": float(values[2]) * 1000.0,
                }

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
