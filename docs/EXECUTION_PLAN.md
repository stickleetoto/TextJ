# TextJ Execution Plan

This is the active queue for autonomous development.

TextJ is an **AI-facing OCR tool/service**. Do not prioritize human desktop UI.

Checkboxes are honest: `[x]` = implemented and tested; `[~]` = partially done
(see note); `[ ]` = open. Blocked items say why.

---

# Phase A — Stabilize Existing Core

- [x] clean install (`pip install -e ".[dev]"`, Linux, Python 3.11)
- [x] run `pytest -q`
- [x] fix packaging/import failures (none found)
- [x] fix real-backend crash: `elapse_list` contains `None` for skipped classifier
- [x] validate file OCR (English, PP-OCRv6 small)
- [x] validate ndarray OCR
- [ ] validate Korean — **blocked**: PP-OCRv5 Korean model host unreachable from sandbox
- [x] validate English
- [ ] validate mixed Korean/English — **blocked** (same)
- [x] record real warm p50/p95 (English, Linux; `docs/BENCHMARK_RESULTS.md`)
- [x] record first known OCR failures (indentation, repeated spaces, `AI`→`Al`)
- [ ] validate on target Windows machine — **blocked**: no Windows here

---

# Phase B — Benchmark Foundation

## B1. Artifact metadata

- [x] TextJ version
- [x] git commit when available
- [x] image dimensions
- [x] backend model config
- [x] provider (onnxruntime providers + package versions)
- [x] cold construction (`backend_construct_ms`, runtime `startup_ms`)
- [x] warm service latency (`textj-bench-runtime`)

## B2. Regression comparator (`textj-bench-compare`)

- [x] console output
- [x] JSON output
- [x] configurable fail thresholds (p50 %, p95 %, CER abs, RSS MB)
- [x] tests

## B3. Safe fixture corpus (`benchmarks/fixtures/`)

- [x] KO (generated; unmeasured — blocked)
- [x] EN
- [x] MIX (generated; unmeasured — blocked)
- [x] CODE
- [x] TERM
- [x] UI
- [x] DARK
- [x] TINY
- [ ] HARD (low contrast, blur, JPEG artifacts)
- [ ] XL (1440p/4K screenshots)

---

# Phase C — Protocol v1  ✅

- [x] C1 request/response types (`textj.api`)
- [x] C2 stable error codes (13, frozen by test)
- [x] C3 input limits, rejected before decode
- [x] C4 deterministic, Unicode-safe serialization; optional boxes/timings;
      schema stability tests

---

# Phase D — Resident Runtime  ✅

- [x] D1 `TextJRuntime`: backend once, warmup, readiness, failure state, clean close
- [x] D2 bounded scheduling: queue wait timing, `BUSY`, `TIMEOUT`,
      cancellation of queued work on timeout/close

---

# Phase E — Machine-facing Transports  ✅

- [x] E1 Python API (`TextJRuntime.ocr/handle/handle_json`)
- [x] E2 JSON stdio (`textj-serve --stdio`)
- [x] E3 local daemon: loopback TCP, token auth, status, graceful shutdown,
      client + `textj-client`
- [ ] E4 Windows named pipe transport (only if TCP loopback proves inadequate)

---

# Phase F — Batch and Agent Workloads

## F1. OCR batch

- [x] stable item IDs
- [x] preserve order
- [x] per-item error
- [x] batch limits
- [x] no all-or-nothing failure

## F2. Concurrency stress (fake backends)

- [x] parallel clients
- [x] queue full → BUSY
- [x] slow request / timeout
- [x] malformed request
- [x] backend exception
- [x] shutdown during requests

## F3. Throughput vs latency

- [x] measured on Linux 4 vCPU: `max_inflight=1` best (see results)
- [ ] re-measure on target Windows hardware

---

# Phase G — MCP Adapter  ✅

- [x] map MCP args to protocol request
- [x] structured results (`structuredContent` + JSON text)
- [x] reuse resident runtime (in-process or `--daemon`)
- [x] no model lifecycle duplication
- [x] AI-oriented tool descriptions
- [ ] validate with a real MCP client (Claude Desktop / Claude Code config)

---

# Phase H — Fast Pipeline Optimization  (next)

Every change must report p50/p95/CER (use `textj-bench-compare`).

- [x] detector resolution policy: `max 1280` default (measured)
- [ ] large screenshot sweep (1440p/4K) for `det_limit_side_len`
- [ ] detection dominates 1280×720 (~80%): try `det_limit_side_len` 960 on
      large inputs only, `box_thresh`/`unclip_ratio`, dilation off
- [x] ONNX Runtime thread settings: all-cores default kept (measured); small crops
      faster with 2 threads — size-dependent policy is an open experiment
- [ ] recognizer batch size (`rec_batch_num`) vs latency
- [x] code/terminal indentation: opt-in `options.preserve_indent` (code CER
      0.0741 → 0; harmful on UI layouts, so off by default)
- [ ] repeated inner spaces (`File   Edit`) — needs word boxes (`return_word_box`)
- [ ] crop filtering / tiny-noise suppression
- [ ] INT8/FP16 experiments
- [ ] shared-memory input experiment (only if decode/transport shows up in profiles;
      currently ≤ 5 ms)

---

# Phase I — Reliability and Packaging

- [ ] headless service packaging (PyInstaller / Nuitka evaluation)
- [ ] deterministic config file (TOML) for runtime + limits
- [ ] model cache/offline behavior: document + `textj-models` prefetch command
- [x] startup readiness (`status.state`, `BACKEND_NOT_READY`)
- [ ] local logging to file (currently stderr)
- [ ] crash recovery / supervisor guidance
- [x] version command (`textj --version`, `status.textj_version`)
- [x] protocol compatibility tests (shape + error code freeze)
- [ ] clean uninstall/update story

---

# Next concrete tasks (in order)

1. On a networked machine: run KO/MIX fixtures with `ppocrv5-mobile`, add to
   `docs/BENCHMARK_RESULTS.md`, confirm `max 1280` does not hurt Korean CER.
2. Add HARD and XL fixtures; sweep `det_limit_side_len` for large screenshots.
3. Size-dependent ORT thread policy experiment (2 threads helped tiny crops).
4. TOML config for `textj-serve` / `textj-mcp` (runtime config + limits).
5. Model prefetch/offline command and cache documentation.
6. Packaging evaluation.

---

# Deprioritized / Optional

- tray icon, global hotkey, drag-selection overlay
- clipboard-centric UX (existing clipboard code remains as a debug adapter)
- human history UI, desktop settings UI
