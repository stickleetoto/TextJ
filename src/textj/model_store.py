"""TextJ model resolver and local cache.

TextJ resolves every model file itself and passes explicit paths to the OCR
engine, so the engine never downloads anything on its own and OCR requests
never touch the network.

* Model identity and download URLs come from the installed rapidocr
  ``default_models.yaml`` (version-matched to the engine). Every file is
  verified against the SHA256 pinned there before it is used.
* Cache directory: ``TEXTJ_MODEL_DIR`` if set, else
  ``%LOCALAPPDATA%\\TextJ\\models`` on Windows, else
  ``$XDG_CACHE_HOME/textj/models`` (default ``~/.cache/textj/models``).
* Files already downloaded by RapidOCR into its package ``models`` directory
  are reused after verification.
* Downloads happen only through :func:`fetch` (``textj-models fetch``, or at
  runtime start when ``download="missing"``). ``TEXTJ_OFFLINE=1`` forbids them.
* Extra download sources: ``TEXTJ_MODEL_BASE_URL`` (tried first; file name is
  appended). Any source is safe because the SHA256 must match.
* Offline machines: copy the ``.onnx`` file over and run
  ``textj-models import <file>``; it is accepted only if its SHA256 matches a
  known model.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ENGINE = "onnxruntime"


class ModelError(RuntimeError):
    """Model missing, unverifiable, or download not allowed/failed."""


@dataclass(frozen=True, slots=True)
class ModelSpec:
    key: str           # rapidocr model key, e.g. korean_PP-OCRv5_rec_mobile
    task: str          # det | rec | cls
    filename: str
    sha256: str | None
    url: str | None
    bundled: bool = False


# (profile, language) -> (det key, rec key). Public languages: ko-en, en.
PROFILE_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    ("ppocrv5-mobile", "ko-en"): ("ch_PP-OCRv5_det_mobile", "korean_PP-OCRv5_rec_mobile"),
    ("ppocrv5-mobile", "en"): ("ch_PP-OCRv5_det_mobile", "en_PP-OCRv5_rec_mobile"),
    ("ppocrv6-small", "en"): ("multi_PP-OCRv6_det_small", "multi_PP-OCRv6_rec_small"),
}

_BUNDLED_FILES = {
    "multi_PP-OCRv6_det_small": "PP-OCRv6_det_small.onnx",
    "multi_PP-OCRv6_rec_small": "PP-OCRv6_rec_small.onnx",
}


def rapidocr_dir() -> Path:
    import rapidocr

    return Path(rapidocr.__file__).resolve().parent


def default_cache_dir() -> Path:
    override = os.environ.get("TEXTJ_MODEL_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "TextJ" / "models"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "textj" / "models"


def offline_mode() -> bool:
    return os.environ.get("TEXTJ_OFFLINE", "").strip().lower() in ("1", "true", "yes")


def _load_catalog() -> dict[str, dict]:
    """Model key -> {model_dir, SHA256} for the ONNX Runtime engine."""
    import yaml  # rapidocr dependency (PyYAML)

    data = yaml.safe_load((rapidocr_dir() / "default_models.yaml").read_text(encoding="utf-8"))
    catalog: dict[str, dict] = {}
    for version in (data.get(ENGINE) or {}).values():
        for task_models in (version or {}).values():
            for key, info in (task_models or {}).items():
                catalog[key] = info
    return catalog


def spec_for(key: str) -> ModelSpec:
    task = "det" if "_det_" in key else "rec" if "_rec_" in key else "cls"
    info = _load_catalog().get(key)
    if info is None:
        raise ModelError(f"unknown model key {key!r} for rapidocr {ENGINE}")
    url = str(info["model_dir"])
    bundled = key in _BUNDLED_FILES
    filename = _BUNDLED_FILES.get(key, Path(url).name)
    return ModelSpec(key, task, filename, str(info["SHA256"]), url, bundled=bundled)


def specs_for(profile: str, language: str) -> tuple[ModelSpec, ModelSpec]:
    try:
        det_key, rec_key = PROFILE_MODELS[(profile, language)]
    except KeyError:
        supported = sorted(f"{p}/{l}" for p, l in PROFILE_MODELS)
        raise ModelError(
            f"no models for profile {profile!r} with language {language!r}; "
            f"supported: {', '.join(supported)}"
        )
    return spec_for(det_key), spec_for(rec_key)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_paths(spec: ModelSpec, cache_dir: Path | None = None) -> list[Path]:
    if spec.bundled:
        # Shipped inside the rapidocr wheel; a cached copy is also accepted.
        return [rapidocr_dir() / "models" / spec.filename,
                (cache_dir or default_cache_dir()) / spec.filename]
    return [(cache_dir or default_cache_dir()) / spec.filename,
            rapidocr_dir() / "models" / spec.filename]


def find_model(spec: ModelSpec, cache_dir: Path | None = None) -> Path | None:
    """Return a verified local path for ``spec`` or ``None``."""
    for path in candidate_paths(spec, cache_dir):
        if not path.is_file():
            continue
        if spec.sha256 is None or sha256_file(path) == spec.sha256:
            return path
    return None


def _sources(spec: ModelSpec) -> list[str]:
    sources = []
    base = os.environ.get("TEXTJ_MODEL_BASE_URL")
    if base:
        sources.append(base.rstrip("/") + "/" + spec.filename)
    if spec.url:
        sources.append(spec.url)
    return sources


def fetch(spec: ModelSpec, cache_dir: Path | None = None, *, timeout: float = 120.0,
          log=None) -> Path:
    """Download ``spec`` into the cache (SHA256-verified, atomic)."""
    existing = find_model(spec, cache_dir)
    if existing is not None:
        return existing
    if offline_mode():
        raise ModelError(f"model {spec.filename} is not cached and TEXTJ_OFFLINE is set")

    target_dir = cache_dir or default_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    for url in _sources(spec):
        if log:
            log(f"downloading {spec.filename} from {url}")
        fd, tmp_name = tempfile.mkstemp(prefix=spec.filename, suffix=".part", dir=target_dir)
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response, open(tmp, "wb") as out:
                shutil.copyfileobj(response, out, 1 << 20)
            actual = sha256_file(tmp)
            if actual != spec.sha256:
                raise ModelError(f"SHA256 mismatch from {url}: {actual}")
            final = target_dir / spec.filename
            os.replace(tmp, final)
            return final
        except Exception as exc:  # try the next source
            errors.append(f"{url}: {exc}")
        finally:
            tmp.unlink(missing_ok=True)
    raise ModelError(f"could not download {spec.filename}: " + "; ".join(errors))


def import_file(source: Path, cache_dir: Path | None = None,
                keys: Iterable[str] | None = None) -> tuple[ModelSpec, Path]:
    """Install a manually obtained model file after SHA256 verification."""
    digest = sha256_file(source)
    candidates = keys if keys is not None else [
        key for pair in PROFILE_MODELS.values() for key in pair
    ]
    for key in dict.fromkeys(candidates):
        spec = spec_for(key)
        if spec.sha256 == digest:
            target_dir = cache_dir or default_cache_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / spec.filename
            shutil.copyfile(source, target)
            return spec, target
    raise ModelError(f"{source} (sha256 {digest}) does not match any known TextJ model")


def resolve(profile: str, language: str, *, download: str = "missing",
            cache_dir: Path | None = None, log=None) -> tuple[Path, Path]:
    """Return verified (det, rec) paths, downloading if allowed.

    ``download``: ``"missing"`` fetches absent files; ``"never"`` fails instead.
    """
    if download not in ("missing", "never"):
        raise ValueError("download must be 'missing' or 'never'")
    paths = []
    missing = []
    for spec in specs_for(profile, language):
        path = find_model(spec, cache_dir)
        if path is None and download == "missing" and not offline_mode():
            path = fetch(spec, cache_dir, log=log)
        if path is None:
            missing.append(spec)
        else:
            paths.append(path)
    if missing:
        names = ", ".join(spec.filename for spec in missing)
        raise ModelError(
            f"model file(s) not available: {names}. Run: textj-models fetch "
            f"--profile {profile} --language {language} "
            f"(cache: {cache_dir or default_cache_dir()})"
        )
    return paths[0], paths[1]


def _stderr_log(message: str) -> None:
    print(f"[textj] {message}", file=sys.stderr, flush=True)
