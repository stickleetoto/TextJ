from types import SimpleNamespace

import numpy as np
import pytest

from textj.backends.rapidocr_backend import RapidOCRBackend


class FakeEngine:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def __call__(self, image, use_cls=None):
        self.calls.append(use_cls)
        return self.output


def test_skipped_classifier_stage_does_not_crash() -> None:
    # RapidOCR 3.x reports None for the classifier stage when use_cls=False.
    output = SimpleNamespace(
        txts=("Hello", "  ", "TextJ"),
        scores=(0.99, 0.5, 0.9),
        boxes=np.array(
            [[[0, 0], [10, 0], [10, 5], [0, 5]]] * 3, dtype=np.float32
        ),
        elapse=0.03,
        elapse_list=[0.02, None, 0.01],
    )
    engine = FakeEngine(output)
    backend = RapidOCRBackend(engine=engine)

    result = backend.recognize(np.zeros((5, 10, 3), dtype=np.uint8))

    assert engine.calls == [False]
    assert [line.text for line in result.lines] == ["Hello", "TextJ"]
    assert result.lines[0].box == ((0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0))
    assert result.metadata["engine_stages_ms"] == pytest.approx(
        {"detect": 20.0, "recognize": 10.0}
    )
    assert result.metadata["engine_elapsed_ms"] == pytest.approx(30.0)


def test_empty_engine_output() -> None:
    output = SimpleNamespace(
        txts=None, scores=None, boxes=None, elapse=None, elapse_list=None
    )
    result = RapidOCRBackend(engine=FakeEngine(output)).recognize(
        np.zeros((5, 10, 3), dtype=np.uint8)
    )
    assert result.lines == ()
    assert "engine_stages_ms" not in result.metadata


def test_rejects_unknown_language_and_profile() -> None:
    with pytest.raises(ValueError):
        RapidOCRBackend(language="xx", engine=object())
    with pytest.raises(ValueError):
        RapidOCRBackend(profile="nope", engine=object())
