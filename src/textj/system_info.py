from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


def git_commit() -> str | None:
    """Return the TextJ source checkout commit, if running from a git tree."""
    source_dir = Path(__file__).resolve().parent
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_dir,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and commit else None


def collect_system_info() -> dict[str, Any]:
    """Collect lightweight runtime metadata for benchmark reproducibility."""
    from textj import __version__

    info: dict[str, Any] = {
        "textj_version": __version__,
        "git_commit": git_commit(),
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

    # rapidocr has no __version__ attribute; use installed distribution metadata.
    from importlib.metadata import PackageNotFoundError, version

    for dist in ("rapidocr", "numpy", "opencv-python", "Pillow"):
        try:
            info[dist.lower()] = version(dist)
        except PackageNotFoundError:
            info[dist.lower()] = None

    return info
