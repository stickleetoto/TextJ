from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Write UTF-8 JSON atomically enough for local benchmark artifacts."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination
