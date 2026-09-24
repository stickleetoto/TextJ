import hashlib
import http.server
import threading
from functools import partial
from pathlib import Path

import pytest

from textj import model_store
from textj.model_store import ModelError

GOOD = b"fake onnx model bytes"
GOOD_SHA = hashlib.sha256(GOOD).hexdigest()


@pytest.fixture
def catalog(monkeypatch, tmp_path):
    """Replace rapidocr's catalog with one fake downloadable model."""
    entries = {
        "ch_PP-OCRv5_det_mobile": {"model_dir": "https://blocked.invalid/det.onnx", "SHA256": GOOD_SHA},
        "korean_PP-OCRv5_rec_mobile": {"model_dir": "https://blocked.invalid/kor.onnx", "SHA256": "0" * 64},
    }
    monkeypatch.setattr(model_store, "_load_catalog", lambda: entries)
    monkeypatch.setattr(model_store, "rapidocr_dir", lambda: tmp_path / "rapidocr")
    monkeypatch.delenv("TEXTJ_OFFLINE", raising=False)
    monkeypatch.delenv("TEXTJ_MODEL_BASE_URL", raising=False)
    return entries


def test_default_cache_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEXTJ_MODEL_DIR", str(tmp_path / "m"))
    assert model_store.default_cache_dir() == tmp_path / "m"


def test_real_catalog_pins_korean_model() -> None:
    det, rec = model_store.specs_for("ppocrv5-mobile", "ko-en")
    assert rec.filename == "korean_PP-OCRv5_rec_mobile.onnx"
    assert len(rec.sha256) == 64 and det.task == "det"
    with pytest.raises(ModelError):
        model_store.specs_for("ppocrv6-small", "ko-en")


def test_find_model_requires_matching_sha(catalog, tmp_path) -> None:
    spec = model_store.spec_for("ch_PP-OCRv5_det_mobile")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / spec.filename).write_bytes(b"corrupted")
    assert model_store.find_model(spec, cache) is None
    (cache / spec.filename).write_bytes(GOOD)
    assert model_store.find_model(spec, cache) == cache / spec.filename


def test_import_file(catalog, tmp_path) -> None:
    source = tmp_path / "downloaded.onnx"
    source.write_bytes(GOOD)
    spec, path = model_store.import_file(source, tmp_path / "cache")
    assert spec.key == "ch_PP-OCRv5_det_mobile"
    assert path.read_bytes() == GOOD
    source.write_bytes(b"something else")
    with pytest.raises(ModelError):
        model_store.import_file(source, tmp_path / "cache")


def test_offline_mode_never_downloads(catalog, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEXTJ_OFFLINE", "1")
    spec = model_store.spec_for("ch_PP-OCRv5_det_mobile")
    with pytest.raises(ModelError, match="TEXTJ_OFFLINE"):
        model_store.fetch(spec, tmp_path / "cache")


def test_resolve_never_reports_fetch_command(catalog, tmp_path) -> None:
    with pytest.raises(ModelError, match="textj-models fetch --profile ppocrv5-mobile --language ko-en"):
        model_store.resolve("ppocrv5-mobile", "ko-en", download="never", cache_dir=tmp_path)


@pytest.fixture
def mirror(tmp_path):
    root = tmp_path / "mirror"
    root.mkdir()
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield root, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_fetch_from_mirror_verifies_sha(catalog, mirror, monkeypatch, tmp_path) -> None:
    root, base = mirror
    monkeypatch.setenv("TEXTJ_MODEL_BASE_URL", base)
    det = model_store.spec_for("ch_PP-OCRv5_det_mobile")
    rec = model_store.spec_for("korean_PP-OCRv5_rec_mobile")
    (root / det.filename).write_bytes(GOOD)
    (root / rec.filename).write_bytes(b"tampered")
    cache = tmp_path / "cache"

    path = model_store.fetch(det, cache)
    assert path.read_bytes() == GOOD

    with pytest.raises(ModelError, match="SHA256 mismatch"):
        model_store.fetch(rec, cache)
    assert not (cache / rec.filename).exists()
    assert not list(cache.glob("*.part"))


def test_textj_models_cli_status_json(capsys) -> None:
    import json

    from textj.app.models import main

    assert main(["--json", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    files = {(row["profile"], row["language"], row["task"]): row for row in payload["models"]}
    assert files[("ppocrv5-mobile", "ko-en", "rec")]["file"] == "korean_PP-OCRv5_rec_mobile.onnx"
    assert files[("ppocrv6-small", "en", "rec")]["bundled"] is True
