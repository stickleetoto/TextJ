import numpy as np
from PIL import Image

from textj.inputs.clipboard import pil_to_bgr


def test_pil_to_bgr_channel_order() -> None:
    image = Image.new("RGB", (1, 1), (10, 20, 30))

    array = pil_to_bgr(image)

    assert array.dtype == np.uint8
    assert array.shape == (1, 1, 3)
    assert array[0, 0].tolist() == [30, 20, 10]
    assert array.flags["C_CONTIGUOUS"]
