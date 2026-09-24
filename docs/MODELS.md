# OCR Models

TextJ does not commit model binaries. Model files are resolved, verified and
cached by `src/textj/model_store.py`; the OCR engine receives explicit file
paths and never downloads anything itself.

## Profiles and languages

| Profile | Language | Detector file | Recognizer file | Source | Network |
| --- | --- | --- | --- | --- | --- |
| `ppocrv5-mobile` (default) | `ko-en` (default) | `ch_PP-OCRv5_det_mobile.onnx` | `korean_PP-OCRv5_rec_mobile.onnx` | download once | first fetch only |
| `ppocrv5-mobile` | `en` | `ch_PP-OCRv5_det_mobile.onnx` | `en_PP-OCRv5_rec_mobile.onnx` | download once | first fetch only |
| `ppocrv6-small` | `en` | `PP-OCRv6_det_small.onnx` | `PP-OCRv6_rec_small.onnx` | bundled in the `rapidocr` wheel | never |

- `ko-en` is the Korean PP-OCRv5 recognizer. Its intended coverage is Korean
  plus Latin letters, digits and punctuation, which is why one resident
  runtime is meant to serve Korean, English and mixed screens. **TextJ has not
  yet measured this model** (see `docs/BENCHMARK_RESULTS.md`, pending).
- `ppocrv6-small` has no Hangul in its dictionary. Measured on the TextJ
  fixtures: KO CER 0.8799, MIX CER 0.3216 — not usable for Korean.
- Download URLs and SHA256 values come from the installed rapidocr
  `default_models.yaml` (rapidocr 3.9.2 at the time of writing), so they stay
  version-matched with the engine.

## Commands

```bash
textj-models status                 # what is present/verified, and where
textj-models fetch                  # ppocrv5-mobile / ko-en (default)
textj-models fetch --language en    # English PP-OCRv5 recognizer
textj-models fetch --all            # every supported profile/language
textj-models import FILE.onnx ...   # install files copied from elsewhere
textj-models path                   # print the cache directory
```

All commands accept `--model-dir DIR` and `--json`.

## Cache location

1. `--model-dir` / config `runtime.model_dir`
2. `TEXTJ_MODEL_DIR`
3. Windows: `%LOCALAPPDATA%\TextJ\models`
4. Linux/macOS: `$XDG_CACHE_HOME/textj/models` (default `~/.cache/textj/models`)

Files that RapidOCR itself downloaded into its package `models` directory are
also accepted after SHA256 verification.

## Integrity

Every file is checked against the SHA256 pinned in rapidocr's catalog:

- before use (a corrupted or substituted file is treated as missing),
- after download (mismatches are deleted, never installed),
- on `textj-models import` (unknown files are rejected).

Because of the pin, any download source is safe to use:
`TEXTJ_MODEL_BASE_URL=https://mirror.example/models` is tried before the
official URL (the file name is appended).

## Offline behavior

- OCR requests never access the network. Inputs are local paths or bytes;
  URL inputs are not accepted.
- Model downloads happen only via `textj-models fetch`, or at runtime start
  when `model_download = "missing"` (default) and a file is absent.
- `TEXTJ_OFFLINE=1`, `--offline`, or config `runtime.model_download = "never"`
  forbid downloads entirely.
- Verified by `benchmarks/tools/validate_languages.py`: a fresh process with
  `TEXTJ_OFFLINE=1` and a Python audit hook recorded 0 network events while
  starting the runtime and OCRing EN/KO/MIX fixtures (bundled PP-OCRv6 run;
  the ko-en run is pending the model download).

Offline machine setup: fetch on a networked machine (or download the files
from any mirror), copy the `.onnx` files over, then `textj-models import *.onnx`.

## Missing model error

Runtime start fails with `BACKEND_NOT_READY`, `retryable: false`,
`details.reason: "MODEL_MISSING"`; every later request returns the same code
and reason. The message names the missing files and the exact fix, e.g.

```text
model file(s) not available: ch_PP-OCRv5_det_mobile.onnx, korean_PP-OCRv5_rec_mobile.onnx.
Run: textj-models fetch --profile ppocrv5-mobile --language ko-en (cache: ~/.cache/textj/models)
```

`textj-mcp` keeps running in this state so agents receive the structured
error from `textj_status` / `ocr_image` instead of a dead server.

## Licenses

| Artifact | License | Notes |
| --- | --- | --- |
| PP-OCR models (PaddleOCR) | Apache-2.0 | trained by PaddlePaddle |
| ONNX conversions distributed by RapidOCR | Apache-2.0 (RapidOCR project) | downloaded from RapidOCR's model host |
| rapidocr wheel (incl. bundled PP-OCRv6 small) | Apache-2.0 | installed via pip |

TextJ redistributes no model files. If a future release bundles models, ship
the upstream license and NOTICE files with them.

## Download hosts

The official URLs point to `www.modelscope.cn`. In restricted networks, allow
that host (and the storage host it redirects to), use `TEXTJ_MODEL_BASE_URL`
for an internal mirror, or use `textj-models import`.
