import json
from pathlib import Path

from textj.result_io import write_json


def test_write_json_creates_parent_and_unicode(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "result.json"

    written = write_json(output, {"text": "한글"})

    assert written == output
    assert json.loads(output.read_text(encoding="utf-8"))["text"] == "한글"
