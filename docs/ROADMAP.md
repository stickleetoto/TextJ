# Roadmap

## North star

```text
AI agent
-> sends image/screenshot
-> TextJ warm runtime
-> structured OCR
-> response returned with minimal latency
```

TextJ is an AI/tooling component, not primarily a desktop OCR app.

---

# v0.1 — OCR Core

**Status: implemented; English validated on Linux; Korean and Windows validation pending.**

Goal: obtain useful Korean/English OCR through a backend-independent core.

Deliverables:

- package structure
- file input
- ndarray input
- backend abstraction
- RapidOCR baseline
- text / score / boxes
- JSON serialization
- timing
- unit tests

Exit:

- OCR core can be called without depending on a GUI.

---

# v0.2 — Benchmark Foundation

**Status: implemented (runner, suite, comparator, runtime bench, synthetic fixtures). HARD/XL fixtures pending.**

Goal: make latency, accuracy, and memory measurable.

Deliverables:

- benchmark runner
- p50/p95
- warmup separation
- CER
- sampled RSS
- JSON artifacts
- benchmark suite
- regression comparison
- safe fixture corpus

Exit:

- optimization regressions can be detected automatically.

---

# v0.3 — Protocol v1

**Status: implemented 2026-09-24 — see `docs/AI_TOOL_PROTOCOL.md`.**


Goal: define a stable machine-facing contract.

Deliverables:

- request schema
- response schema
- protocol version
- error codes
- size limits
- options
- deterministic serialization
- JSON schema tests
- batch request schema

Exit:

- an external AI tool can integrate without importing TextJ internals.

---

# v0.4 — Resident Runtime

**Status: implemented 2026-09-24 (`textj.runtime.TextJRuntime`).**


Goal: remove model construction from each call.

Deliverables:

- TextJRuntime
- lifecycle
- warmup
- readiness
- bounded queue
- request timeout
- structured errors
- graceful shutdown
- fake-backend tests

Exit:

- repeated OCR calls reuse one loaded backend.

---

# v0.5 — Local Tool API

**Status: implemented 2026-09-24 (stdio, loopback TCP daemon, client). Named pipe not implemented.**


Goal: expose the resident runtime to external agents.

Deliverables:

- reference JSON stdio interface
- local daemon
- local client
- health/status method
- request IDs
- protocol version negotiation
- local-only default binding
- benchmark request-to-response latency

Exit:

- another process can use TextJ reliably as a local OCR service.

---

# v0.6 — Batch and Concurrency

**Status: implemented 2026-09-24; burst measured on Linux only. MCP adapter (`textj-mcp`) also implemented.**


Goal: support real agent workloads.

Deliverables:

- batch OCR
- bounded concurrency
- queue depth
- BUSY/timeout semantics
- per-item errors
- batch ordering guarantees
- stress tests
- throughput + latency benchmarks

Exit:

- bursty callers cannot exhaust memory or corrupt runtime state.

---

# v0.7 — MCP Adapter

Goal: make TextJ directly usable as an AI tool.

Deliverables:

- thin MCP adapter
- `ocr_image`
- `ocr_batch`
- `textj_status`
- stable schema mapping
- no separate OCR model lifecycle inside MCP adapter

Exit:

- MCP-capable agents can invoke the same TextJ runtime.

---

# v0.8 — Fast Pipeline Optimization

Goal: improve measured request latency.

Candidates:

- detector resolution tuning
- direct image buffer paths
- copy reduction
- crop bucketing
- recognition batching
- provider tuning
- quantization
- fast/accurate modes

Rule:

- no optimization claim without benchmark + accuracy evidence.

---

# v0.9 — Reliability and Packaging

Goal: make TextJ deployable as an AI infrastructure component.

Deliverables:

- service/daemon packaging
- configuration
- logging
- crash recovery
- startup readiness
- offline model handling
- clean install
- version reporting
- protocol compatibility tests

---

# v1.0 — AI OCR Tool

Required:

- stable protocol v1
- warm resident runtime
- local machine-facing API
- structured text/boxes/confidence
- path + in-memory/encoded input adapters
- batch OCR
- bounded concurrency
- timeouts and machine-readable errors
- reproducible benchmark suite
- Korean + English
- backend abstraction
- headless packaging
- MCP adapter or equivalent agent-tool integration

Not required for v1:

- tray UI
- global hotkey
- screen-region selection GUI
- human workflow polish

---

# After v1

Possible work:

- shared-memory image transport
- zero-copy capture integration
- continuous OCR
- change-region OCR
- more languages
- layout reconstruction
- NPU/GPU providers
- custom distilled recognizer
- optional human desktop wrapper
