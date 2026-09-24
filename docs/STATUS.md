# Development Status

Last updated: 2026-09-24

## Product direction

**TextJ is an AI-facing local OCR tool/service.**

```text
AI agent -> image/screenshot request -> warm local runtime -> structured response
```

Human CLI and clipboard paths are secondary adapters/debugging tools.

## Current milestone

- v0.1 OCR core: implemented; real-model validation done for **English only**
  (PP-OCRv6 small, Linux). Korean pending (model download blocked here).
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
  - `ppocrv5-mobile` (default; Korean/English/Chinese; downloads models once)
  - `ppocrv6-small` (bundled in the rapidocr wheel, offline, **no Hangul**)
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
- legacy/debug: `textj`, `textj-clipboard`

### Benchmarks

- `textj-bench`, `textj-bench-suite` (`--tags`), `textj-bench-compare`
  (thresholds, exit code 1 on regression), `textj-bench-runtime`
- artifacts include textj version, git commit, image dimensions, backend config,
  package versions
- `benchmarks/fixtures/`: 11 synthetic cases with ground truth (EN, UI, URL,
  CODE, TERM, DARK, TINY, KO, MIX, screen-sized L) + generator script

### Tests

`pytest -q`: 99 tests, no model downloads (fake backends / injected engine).
`pytest -m integration`: real OCR on fixtures with bundled PP-OCRv6 (8 pass);
Korean cases run only with `TEXTJ_KOREAN_MODELS=1` (downloads models).

## Measured (see `docs/BENCHMARK_RESULTS.md`)

Linux 4-vCPU container, PP-OCRv6 small, English fixtures:

- detector `max 1280` vs RapidOCR default: mean p50 149.6 vs 806.6 ms, same CER 0.0181
- runtime request-to-response, 552×131 crop: p50 157–172 ms across Python
  API / JSON / TCP; 1280×720 screen: p50 414–428 ms
- protocol parse + queue + decode ≤ 5 ms in all measured cases
- `max_inflight` 1 gave the best burst throughput (5.91 req/s vs 4.70 / 4.36)

## Blockers

- **Korean model unavailable in the dev sandbox**: RapidOCR downloads
  PP-OCRv5 Korean models from modelscope.cn; the sandbox proxy denies it
  (HuggingFace too). KO/MIX fixtures exist but have no measured results.
  Validate on a machine with network access:
  `textj-bench-suite benchmarks/fixtures/manifest.json --runs 10 --warmups 2`
- **No Windows validation**: all runs were on Linux. Clipboard adapter and
  Windows path handling are untested on Windows.

## Known limitations

- one language per runtime (the loaded recognizer); `options.language` must match
- running inference cannot be cancelled; a timed-out request keeps its slot
  until the backend returns
- line order is backend order; no layout reconstruction
- recognition drops leading indentation (opt-in `preserve_indent` restores it
  for monospace crops) and collapses repeated inner spaces
- stdio transport handles requests sequentially (no pipelined concurrency)
- no Windows named-pipe transport; TCP loopback is used on all platforms
- no config file yet; configuration is CLI flags / `RuntimeConfig`
- sampled RSS only (not a continuous peak profiler)
