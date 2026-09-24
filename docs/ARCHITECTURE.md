# Architecture

## 1. Overview

TextJ is an AI-facing OCR service/tool.

The primary architecture is:

```text
AI agent / automation
        |
        +-----------------------------+
        | Python API                  |
        | JSON stdio                  |
        | local daemon client         |
        | MCP adapter                 |
        +--------------+--------------+
                       |
                       v
                Request model
                       |
                       v
              Long-lived TextJ runtime
                       |
               +-------+--------+
               | queue/limits   |
               | lifecycle      |
               | warm backend   |
               +-------+--------+
                       |
                       v
                  OCR pipeline
                       |
                       v
                Result serializer
                       |
                       v
            structured OCR response
```

Human-facing desktop UI is not the architectural center.

---

## 2. Core separation

### Core

Platform-agnostic where practical:

- request model
- result model
- validation
- OCR pipeline
- backend abstraction
- batching
- error model
- timing
- benchmark logic

### Runtime

Long-lived process/object:

- model lifecycle
- readiness
- queue
- concurrency
- request timeout
- shutdown
- health/status

### Adapters

Thin machine-facing interfaces:

- Python API
- JSON CLI/stdin
- local IPC client/server
- MCP

Optional adapters:

- clipboard
- screen capture
- human CLI

---

## 3. Proposed repository direction

```text
src/textj/
├─ api/
│  ├─ request.py
│  ├─ response.py
│  ├─ errors.py
│  └─ protocol.py
├─ runtime/
│  ├─ runtime.py
│  ├─ queue.py
│  ├─ lifecycle.py
│  └─ config.py
├─ transport/
│  ├─ stdio.py
│  ├─ local_server.py
│  └─ local_client.py
├─ adapters/
│  ├─ mcp/
│  ├─ clipboard/
│  └─ capture/
├─ backends/
├─ pipeline.py
├─ models.py
├─ benchmark.py
└─ app/
```

Do not refactor solely to match this tree. Migrate incrementally as implementation requires.

---

## 4. Canonical internal request

All external interfaces should become one internal request type.

Conceptually:

```python
@dataclass
class OCRRequest:
    request_id: str
    image: ImageInput
    mode: str
    language: str
    min_score: float
    include_boxes: bool
    include_timings: bool
    timeout_ms: int | None
```

Likewise, all paths should return one internal response/result type.

This prevents MCP, CLI, daemon, and Python API behavior from drifting.

---

## 5. Runtime lifecycle

```text
process start
-> load config
-> initialize backend
-> model warmup
-> ready

request
-> validate
-> queue
-> acquire execution slot
-> OCR
-> serialize result
-> return

shutdown
-> stop accepting requests
-> finish/cancel bounded work
-> release backend
```

Do not initialize the backend per request.

---

## 6. Concurrency

Start conservatively.

OCR backends may not benefit from unrestricted parallel inference.

The runtime should own concurrency policy.

Potential first policy:

```text
max_inflight = 1
bounded queue = N
```

Then benchmark alternatives.

Important metrics:

- queue wait
- service time
- total latency
- throughput
- memory
- error rate

Do not use an unbounded executor.

---

## 7. Image input path

Preferred internal representation:

- validated ndarray
- contiguous bytes/buffer where appropriate

Avoid:

```text
agent screenshot
-> encode
-> temp file
-> decode
-> OCR
```

Where transport requires encoded bytes, decode exactly once near the boundary.

---

## 8. Batch path

Batching can mean two things:

### Request batching

One caller sends many independent images.

### Model batching

Recognizer processes multiple crops together.

Keep these concepts separate.

The public API can support request batching even if the backend initially processes sequentially.

---

## 9. Error model

Internal exceptions should map to stable public error codes.

Adapters must not expose raw Python tracebacks as the normal protocol.

Debug logging may retain traces locally.

---

## 10. Transport

Preferred progression:

1. Python API
2. JSON/stdio reference protocol
3. long-lived local daemon
4. MCP adapter

For daemon transport, compare:

- Windows named pipe
- Unix domain socket where available
- loopback TCP

Keep network exposure local by default.

---

## 11. Observability

Every request can optionally report:

```text
queue
decode
normalize
detect
recognize
postprocess
serialize
total
```

Also track daemon-level counters later:

- requests
- failures by code
- queue depth
- busy rejects
- average/p95 latency

Avoid high-overhead telemetry in the hot path by default.

---

## 12. Human utilities

The CLI and clipboard prototype remain useful for:

- debugging
- manual smoke tests
- benchmark input
- integration diagnosis

They are adapters, not the main product.
