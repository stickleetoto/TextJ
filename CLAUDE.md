# TextJ — Claude Development Instructions

You are working on **TextJ**, an ultra-fast local OCR tool for AI agents and automated toolchains.

TextJ is **not primarily a human-facing desktop OCR application**.

The product goal is:

> **An AI agent supplies an image or screenshot and receives structured OCR output with minimal latency, predictable behavior, and no unnecessary UI.**

Primary consumers include:

- LLM agents
- computer-use agents
- automation workers
- local AI runtimes
- MCP/tool servers
- OCR-heavy pipelines
- code/terminal/UI analysis systems

Human-facing CLI commands exist mainly for debugging, benchmarking, and integration testing.

Read these before major work:

1. `docs/HANDOFF_CLAUDE.md`
2. `docs/STATUS.md`
3. `docs/PRODUCT.md`
4. `docs/ARCHITECTURE.md`
5. `docs/AI_TOOL_PROTOCOL.md`
6. `docs/EXECUTION_PLAN.md`
7. `docs/PERFORMANCE.md`
8. `docs/ROADMAP.md`

---

## 1. Development mode

Work autonomously and keep moving.

Prefer:

```text
inspect
-> implement
-> test
-> benchmark
-> update schemas/docs
-> continue to next unblocked task
```

Do not stop after writing plans when implementation is possible.

If model downloads, hardware, or OS-specific validation are unavailable, record the blocker and continue with independent work.

---

## 2. Non-negotiable product rules

### AI-first interface

The canonical TextJ interface is machine-facing.

The primary result should be structured data such as:

```json
{
  "text": "...",
  "lines": [
    {
      "text": "...",
      "score": 0.98,
      "box": [[0,0],[10,0],[10,5],[0,5]]
    }
  ],
  "timings_ms": {},
  "backend": "...",
  "request_id": "..."
}
```

Plain text output is a convenience adapter, not the protocol.

### Stable schemas

AI tools must not depend on undocumented output shape.

Version machine-facing request/response schemas.

Backward-incompatible schema changes require an explicit protocol version change.

### Latency first

Optimize **request-to-structured-response latency**, not isolated model inference.

Measure:

```text
request parsing
+ image acquisition/decode
+ normalization
+ detection
+ recognition
+ postprocess
+ serialization
= total tool latency
```

### Local first

Default OCR runs locally and should work offline after models are present.

Do not require cloud OCR.

### Warm runtime

Repeated AI calls must not reconstruct the OCR model every time.

A long-lived runtime/daemon is a core requirement.

### In-memory first

Prefer:

- ndarray
- bytes
- mapped/shared buffers
- existing local file references

Avoid temporary image files and unnecessary PNG/JPEG re-encoding.

### Korean + English first

Mixed Korean/English is the first language target.

Preserve:

- code
- terminal output
- URLs
- paths
- filenames
- identifiers
- punctuation

### Replaceable backend

RapidOCR is the first backend, not the architecture.

---

## 3. Product priority

Unless evidence requires otherwise:

1. validate current OCR core
2. finish benchmark/regression infrastructure
3. define and freeze protocol v1 draft
4. build long-lived OCR runtime
5. add local machine-facing IPC/API
6. add batch OCR
7. add concurrency/backpressure
8. add MCP adapter
9. optimize measured bottlenecks
10. package a headless service/tool

Human desktop UX is optional and lower priority.

Do **not** prioritize tray UI, global hotkeys, screen-selection overlays, or decorative GUI work.

---

## 4. Canonical interface layers

Target layers:

```text
AI caller / agent
    |
    +-- Python API
    +-- JSON CLI/stdio
    +-- local daemon API
    +-- MCP adapter
            |
            v
      TextJ Runtime
            |
            v
       OCR Backend
```

Keep adapters thin.

All adapters should converge on the same internal request/result model.

---

## 5. Error behavior

Machine callers need deterministic failures.

Prefer explicit error codes, for example:

- `INVALID_REQUEST`
- `IMAGE_NOT_FOUND`
- `IMAGE_DECODE_FAILED`
- `UNSUPPORTED_IMAGE`
- `BACKEND_NOT_READY`
- `OCR_FAILED`
- `REQUEST_TOO_LARGE`
- `BUSY`
- `TIMEOUT`
- `INTERNAL_ERROR`

Do not rely on parsing human prose to understand failures.

---

## 6. Performance and resource rules

Measure at minimum:

- warm p50
- warm p95
- max
- request size/image dimensions
- CER when ground truth exists
- RSS
- queue time when daemon mode exists
- serialization overhead when protocol mode exists

Do not claim optimization without measurements.

Do not optimize only for throughput if single-request latency regresses badly.

---

## 7. Concurrency rules

AI systems may call TextJ concurrently.

The runtime should eventually define:

- maximum in-flight requests
- bounded queue
- backpressure behavior
- cancellation/timeout behavior
- deterministic overload response

Never allow unbounded request accumulation.

---

## 8. Security boundary

TextJ is a local tool, but machine-facing interfaces still need boundaries.

Do not:

- expose arbitrary code execution
- accept arbitrary shell commands
- deserialize unsafe Python objects
- trust unbounded base64 payloads
- expose a network listener beyond loopback by default

Local APIs should bind to loopback or OS-local IPC by default.

---

## 9. Testing rules

Before meaningful completion:

```powershell
pytest -q
```

Pure tests should not require model downloads.

Use fake backends for:

- protocol tests
- runtime lifecycle tests
- queue tests
- timeout tests
- batch tests
- error schema tests

Real OCR/model tests should be integration tests.

---

## 10. Development logging

After meaningful work, update:

- `docs/STATUS.md`
- `docs/DEV_WORKLOG.md`
- `docs/EXECUTION_PLAN.md` when task state changes

Keep factual implementation status separate from future plans.

Never invent benchmark numbers.

---

## 11. Things not to prioritize

Do not spend major effort on:

- tray UI
- global hotkeys
- human region-selection UX
- cloud accounts
- translation/summarization
- document editor
- Electron shell
- custom OCR foundation model
- speculative language rewrites
- aesthetic UI

Those are not the core product.

---

## 12. Safe autonomy

Normal code edits, tests, docs, benchmark tooling, protocol work, runtime work, local IPC, and adapters are expected.

Do not:

- force-push
- rewrite history
- delete major user work without necessity
- commit secrets
- commit private screenshots
- commit downloaded model caches by accident

At the end of a long session, leave the repository self-explanatory for the next agent.
