from __future__ import annotations

import platform
import sys
from typing import Any


def collect_system_info() -> dict[str, Any]:
    """Collect lightweight runtime metadata for benchmark reproducibility."""
    info: dict[str, Any] = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable_bits": 64 if sys.maxsize > 2**32 else 32,
    }

    try:
        import onnxruntime as ort

        info["onnxruntime"] = ort.__version__
        info["onnxruntime_providers"] = ort.get_available_providers()
    except Exception:
        info["onnxruntime"] = None
        info["onnxruntime_providers"] = []

    try:
        import rapidocr

        info["rapidocr"] = getattr(rapidocr, "__version__", None)
    except Exception:
        info["rapidocr"] = None

    return info
