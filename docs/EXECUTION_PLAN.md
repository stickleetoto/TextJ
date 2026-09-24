# TextJ Execution Plan

This is the active queue for autonomous development.

TextJ is an **AI-facing OCR tool/service**.

Do not prioritize human desktop UI.

---

# Phase A — Stabilize Existing Core

- [ ] clean install
- [ ] run `pytest -q`
- [ ] fix packaging/import failures
- [ ] validate file OCR
- [ ] validate ndarray OCR
- [ ] validate Korean
- [ ] validate English
- [ ] validate mixed Korean/English
- [ ] record real warm p50/p95
- [ ] record first known OCR failures

Exit: existing OCR path is trustworthy enough to become a service.

---

# Phase B — Finish Benchmark Foundation

## B1. Improve artifact metadata

- [ ] TextJ version
- [ ] git commit when available
- [ ] image dimensions
- [ ] backend model config
- [ ] provider
- [ ] cold construction
- [ ] warm service latency

## B2. Regression comparator

Implement benchmark JSON comparison.

Report separately:

- p50 delta
- p95 delta
- CER delta
- RSS delta

- [ ] console output
- [ ] JSON output
- [ ] configurable fail thresholds
- [ ] tests

## B3. Safe fixture corpus

- [ ] KO
- [ ] EN
- [ ] MIX
- [ ] CODE
- [ ] TERM
- [ ] UI
- [ ] DARK
- [ ] TINY

Exit: performance/accuracy changes are evidence-based.

---

# Phase C — Protocol v1

This is now higher priority than desktop UX.

## C1. Internal request/response types

Create backend-independent types.

Need:

- [ ] protocol_version
- [ ] request_id
- [ ] operation
- [ ] image input descriptor
- [ ] OCR options
- [ ] success response
- [ ] error response

## C2. Stable error codes

Implement and test:

- [ ] INVALID_REQUEST
- [ ] UNSUPPORTED_PROTOCOL
- [ ] UNSUPPORTED_OPERATION
- [ ] IMAGE_NOT_FOUND
- [ ] IMAGE_DECODE_FAILED
- [ ] UNSUPPORTED_IMAGE
- [ ] REQUEST_TOO_LARGE
- [ ] BACKEND_NOT_READY
- [ ] BUSY
- [ ] TIMEOUT
- [ ] OCR_FAILED
- [ ] INTERNAL_ERROR

## C3. Input limits

Define:

- [ ] max bytes
- [ ] max pixels
- [ ] max dimensions
- [ ] max batch size
- [ ] timeout bounds

Reject early.

## C4. Serialization

- [ ] deterministic JSON
- [ ] Unicode-safe
- [ ] optional boxes
- [ ] optional timings
- [ ] tests for backward stability

Exit: protocol v1 draft is usable independently of transport.

---

# Phase D — Resident Runtime

## D1. TextJRuntime

Own:

- backend
- warmup
- readiness
- queue
- concurrency
- timeouts
- shutdown

- [ ] fake-backend lifecycle tests
- [ ] backend initialization once
- [ ] repeated OCR calls
- [ ] failure state
- [ ] clean close

## D2. Bounded scheduling

Start conservative.

Suggested initial policy:

- max in-flight OCR = 1
- bounded queue

Then benchmark.

- [ ] queue wait timing
- [ ] BUSY behavior
- [ ] timeout behavior
- [ ] cancellation where practical

Exit: repeated requests do not reconstruct the model and overload is bounded.

---

# Phase E — Machine-facing Transports

## E1. Python API

Expose a stable high-level API without requiring CLI parsing.

## E2. JSON stdio reference

Useful for agents that spawn TextJ as a subprocess.

Requirements:

- one JSON request per frame/message
- one JSON response
- no debug logs on stdout
- stderr reserved for diagnostics

## E3. Local daemon

Choose simplest local transport first.

Candidates:

- named pipe
- Unix domain socket
- loopback TCP

Requirements:

- local-only by default
- health/status
- protocol version
- request IDs
- timeouts
- graceful shutdown

Exit: an external process can repeatedly call warm TextJ.

---

# Phase F — Batch and Agent Workloads

## F1. OCR batch

- [ ] stable item IDs
- [ ] preserve order
- [ ] per-item error
- [ ] batch limits
- [ ] no all-or-nothing failure unless required

## F2. Concurrency stress

Test:

- [ ] parallel clients
- [ ] queue full
- [ ] slow request
- [ ] malformed request
- [ ] timeout
- [ ] backend exception
- [ ] daemon shutdown during requests

## F3. Throughput vs latency

Record both.

Do not maximize throughput by destroying p95 latency.

Exit: TextJ behaves predictably under agent bursts.

---

# Phase G — MCP Adapter

Build only after runtime/protocol are stable enough.

MCP should be thin.

Suggested tools:

- `ocr_image`
- `ocr_batch`
- `textj_status`

Requirements:

- [ ] map MCP args to protocol request
- [ ] return structured results
- [ ] reuse resident runtime
- [ ] no model lifecycle duplication
- [ ] tool descriptions optimized for AI callers

Exit: MCP clients can use TextJ directly.

---

# Phase H — Fast Pipeline Optimization

Use benchmarks.

Potential work:

- detector resolution sweep
- image copy reduction
- decode fast paths
- crop filtering
- crop bucketing
- recognition batching
- provider tuning
- INT8/FP16 experiments
- direct bytes decoding
- shared memory experiment

Every performance change must report accuracy impact.

---

# Phase I — Reliability and Packaging

- [ ] headless service packaging
- [ ] deterministic config
- [ ] model cache/offline behavior
- [ ] startup readiness
- [ ] local logging
- [ ] crash recovery
- [ ] version command
- [ ] protocol compatibility tests
- [ ] clean uninstall/update story

Exit: TextJ can be deployed as local AI infrastructure.

---

# Deprioritized / Optional

Do not pull these into the main path unless specifically requested:

- tray icon
- global hotkey
- drag-selection overlay
- clipboard-centric UX
- human history UI
- desktop settings UI

Existing clipboard code may remain as a useful adapter/test utility.
