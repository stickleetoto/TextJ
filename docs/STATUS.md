# Development Status

Last updated: 2026-09-24 (session 2)

## Product direction

**TextJ is an AI-facing local OCR tool/service.**

```text
AI agent -> image/screenshot request -> warm local runtime -> structured response
```

Human CLI and clipboard paths are secondary adapters/debugging tools.

## Current milestone

- v0.1 OCR core: implemented; real-model validation done for **English only**
  (PP-OCRv6 small, Linux). **Korean and mixed Korean/English are NOT yet
  validated with a real Korean model** — the model host is blocked in the dev
  sandbox. Everything needed is in place and runs with one command once the
  model is cached (see Blockers).
- v0.2 benchmark foundation: implemented (suite, comparator, fixtures, runtime bench).
- v0.3 protocol v1: **implemented** (`docs/AI_TOOL_PROTOCOL.md`).
- v0.4 resident runtime: **implemented** (`TextJRuntime`).
- v0.5 local tool API: **implemented** (stdio, loopback TCP daemon, client).
- v0.6 batch + concurrency: **implemented**; stress-tested with fake backends and
  one real burst benchmark.
- MCP adapter: **implemented** (`textj-mcp`), dependency-free.
- Headless packaging: not started.

## Implemented

### OCR core

- backend interface (`recognize`, `describe`, `close`)
- RapidOCR backend with profiles:
  - `ppocrv5-mobile` (default) with language `ko-en` (default, Korean PP-OCRv5
    recognizer) or `en`; files fetched once into the TextJ model cache
  - `ppocrv6-small` (bundled in the rapidocr wheel, offline, English only —
    measured KO CER 0.8799)
- model resolver/cache (`textj.model_store`, `textj-models`): SHA256-pinned,
  per-user cache, offline mode, mirror override, manual import; explicit model
  paths so the engine never downloads (`docs/MODELS.md`)
- language policy (`textj.languages`): runtime `ko-en` | `en`; request option
  `auto` | `ko-en` | `korean` | `en` as a coverage requirement
- detector resize policy options; TextJ default `max`, 1280 (measured, see
  `docs/BENCHMARK_RESULTS.md`)
- fixed: RapidOCR reports `None` for the skipped classifier stage; the backend
  crashed with `TypeError` on every real call before this fix

### Protocol v1 (`src/textj/api/`)

- request envelope with strict validation, `request_id`, operations
  `ocr` / `ocr_batch` / `status`
- inputs: `path`, `bytes_base64`, ndarray (Python API)
- options: `mode`, `language`, `min_score`, `include_boxes`, `include_timings`,
  `preserve_indent`
- 13 stable error codes with `retryable` and `details`
- limits (request bytes, image bytes/pixels/side, batch size, timeouts),
  checked from headers before full decode
- single decode to contiguous BGR (OpenCV, Pillow fallback), alpha
  compositing, 16-bit and gray handling
- deterministic compact JSON

### Runtime (`src/textj/runtime/`)

- lifecycle: created → starting → ready / failed → closing → closed
- backend constructed once per worker, warmup incl. decode path
- bounded admission `max_inflight + max_queue`, immediate `BUSY` beyond it
- deadline-based `TIMEOUT` (queued jobs are removed; running jobs are
  abandoned, not interrupted)
- batch: sequential in one slot, per-item errors/timeouts, order preserved
- status: state, backend, scheduler, limits, counters, errors by code,
  latency p50/p95/max
- stage timings: parse, queue, input, ocr, detect, recognize, postprocess, total

### Transports / adapters

- `textj-serve --stdio` (NDJSON)
- `textj-serve --tcp`: loopback only, auth token in owner-only state file,
  bounded connections, idle timeout, SIGTERM shutdown
- `TextJClient`, `textj-client`
- `textj-mcp`: tools `ocr_image`, `ocr_batch`, `textj_status`; in-process
  runtime or `--daemon`
- TOML config (`--config`) for `textj-serve` / `textj-mcp`; example in `examples/textj.toml`
- legacy/debug: `textj`, `textj-clipboard`

### Benchmarks

- `textj-bench`, `textj-bench-suite` (`--tags`), `textj-bench-compare`
  (thresholds, exit code 1 on regression), `textj-bench-runtime`
- artifacts include textj version, git commit, image dimensions, backend config,
  package versions
- `benchmarks/fixtures/`: 20 synthetic cases with ground truth — EN (5),
  KO (5: sentence, UI, numbers, punctuation, dark UI), MIX (7: tech terms,
  Windows/Unix paths, URLs, library/model names, numbers, terminal, UI),
  plus CODE/TERM/DARK/TINY/screen-sized L — and the generator script
- suite results aggregate per tag (EN / KO / MIX separately), comparator
  compares tag scopes
- `benchmarks/tools/validate_languages.py`: one-command EN/KO/MIX validation
  (accuracy, latency, RSS, offline audit)

### Tests

`pytest -q`: 132 tests, no model downloads (fake backends / injected engine),
incl. Unicode round-trips (Hangul, Windows paths, URLs, symbols) through the
Python API, JSON, stdio, TCP and MCP.
`pytest -m integration`: real OCR. Here: 9 passed (English fixtures + MCP
subprocess on bundled PP-OCRv6), 23 skipped (Korean). The ko-en tests (all
fixtures through one ko-en runtime, mixed-language batch, stdio, MCP
subprocess with Korean) run automatically once `textj-models fetch` has cached
the Korean model.

## Measured (see `docs/BENCHMARK_RESULTS.md`)

Linux 4-vCPU container, PP-OCRv6 small, English fixtures:

- detector `max 1280` vs RapidOCR default: mean p50 149.6 vs 806.6 ms, same CER 0.0181
- runtime request-to-response, 552×131 crop: p50 157–172 ms across Python
  API / JSON / TCP; 1280×720 screen: p50 414–428 ms
- protocol parse + queue + decode ≤ 5 ms in all measured cases
- `max_inflight` 1 gave the best burst throughput (5.91 req/s vs 4.70 / 4.36)

## Blockers

- **Korean model unavailable in the dev sandbox**: the official source
  (`www.modelscope.cn`) is denied by the sandbox network policy; HuggingFace,
  Baidu BOS and conda are denied too. PyPI and npm were searched exhaustively
  for a redistributed `korean_PP-OCRv5_rec_mobile.onnx`: none found (only
  Chinese/English/Latin/Japanese PP-OCR models). Fix: allow `www.modelscope.cn`
  (and its storage redirect host) in the environment's network settings, or run
  on any networked machine:
  ```bash
  textj-models fetch && textj-models fetch --language en
  pytest -m integration
  python benchmarks/tools/validate_languages.py
  ```
- **No Windows validation**: all runs were on Linux. Static review + tests
  done for Windows-specific risks:
  - daemon: `SO_REUSEADDR` replaced by `SO_EXCLUSIVEADDRUSE` on Windows
    (prevents another process binding the port) — unit-tested
  - protocol stdout (`textj-serve --stdio`, `textj-mcp`) writes UTF-8 bytes to
    the binary buffer; tested with hostile `PYTHONIOENCODING`; CRLF input lines
    are accepted
  - human CLIs force UTF-8 stdout when the pipe encoding is cp949/cp1252
  - Hangul file/folder names as `path` inputs: tested (images are read as
    bytes by Python, never by OpenCV path APIs)
  - model cache default `%LOCALAPPDATA%\TextJ\models`
  - state file: `0o600` has no effect on Windows; protection relies on the
    per-user profile directory ACL (`%USERPROFILE%\.textj`)
  Still needs a real Windows run: install, ONNX Runtime/RapidOCR wheels,
  model cache, `textj-serve`, `textj-client`, `textj-mcp`, Ctrl+C/SIGTERM.

## Known limitations

- one recognizer per runtime (default ko-en); `options.language` is checked
  against what the loaded recognizer serves
- whether the ko-en recognizer matches the en recognizer on English text is
  unmeasured (decides if dual residency is ever needed)
- running inference cannot be cancelled; a timed-out request keeps its slot
  until the backend returns
- line order is backend order; no layout reconstruction
- recognition drops leading indentation (opt-in `preserve_indent` restores it
  for monospace crops) and collapses repeated inner spaces
- stdio transport handles requests sequentially (no pipelined concurrency)
- no Windows named-pipe transport; TCP loopback is used on all platforms
- sampled RSS only (not a continuous peak profiler)
