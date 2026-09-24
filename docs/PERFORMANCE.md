# Performance Targets

## 1. Primary metric

TextJ optimizes **machine-facing request-to-response latency**.

For a warm local runtime:

```text
request accepted
-> input validated/acquired
-> image decoded/normalized
-> OCR
-> postprocess
-> result serialized
-> response ready
```

The measurement ends when the AI/tool caller can consume the structured result.

Do not optimize only model inference while protocol, decode, queue, or serialization dominate total latency.

---

## 2. Latency classes

These are engineering targets, not guarantees.

### Small crop

Examples:

- one UI label group
- one error message
- short terminal area
- a few text lines

Target:

- v1: <= 250 ms warm request-to-response
- stretch: <= 150 ms

### Ordinary screenshot/crop

Examples:

- chat region
- code excerpt
- UI panel
- article paragraph

Target:

- v1: <= 500 ms warm
- stretch: <= 300 ms

### Dense document-like image

Target:

- <= 1 second warm where the selected backend permits it

Real targets should be revised after measured baselines exist.

---

## 3. Cold vs warm

Report separately.

### Cold

May include:

- process start
- imports
- model acquisition
- model load
- session creation
- first inference

### Warm

Assumes:

- service alive
- backend loaded
- runtime ready

AI integration quality is judged primarily by warm latency.

---

## 4. Daemon timing

Once runtime/transport exists, expose stage timing where practical:

| Stage | Meaning |
| --- | --- |
| queue | wait before execution |
| input | path read / bytes decode / buffer acquisition |
| normalize | image representation conversion |
| detect | text detection |
| recognize | text recognition |
| postprocess | ordering/cleanup |
| serialize | response construction/JSON encoding |
| total | request-to-response latency |

Transport round-trip can be measured separately by clients.

---

## 5. Percentiles

At minimum:

- p50
- p95
- max

For stress tests, also consider p99.

p95 matters more than a single lucky run.

---

## 6. Throughput

For agent workloads, also record:

- requests/second
- images/second for batch
- queue depth
- BUSY rejects
- timeout count

Do not improve throughput by making interactive p95 latency unusable.

---

## 7. Accuracy

Recommended metrics:

- CER
- exact line match
- normalized text match
- detection quality where annotated boxes exist

Technical-text fixtures should include:

- URLs
- paths
- filenames
- code
- terminal output
- punctuation

---

## 8. Resource metrics

Track:

- idle RSS
- sampled/true peak RSS where available
- model memory
- GPU VRAM if applicable
- CPU utilization
- model/package size

For resident service mode, idle RSS is important because the process stays alive.

---

## 9. Protocol overhead

Benchmark:

- raw Python API call
- JSON serialization
- bytes decode
- local IPC round-trip
- MCP adapter overhead

This shows whether OCR or tool plumbing is the bottleneck.

---

## 10. Concurrency benchmark

Test defined request patterns:

### Sequential

One request at a time.

### Small burst

A few concurrent clients.

### Queue saturation

More requests than the configured queue allows.

Expected behavior must be bounded:

- queued
- BUSY
- timeout

Never allow uncontrolled memory growth.

---

## 11. Benchmark dataset

Include:

- KO
- EN
- MIX
- CODE
- TERM
- UI
- DARK
- TINY
- HARD

Also classify input size:

- S
- M
- L
- XL

---

## 12. Optimization order

Unless profiling says otherwise:

1. eliminate per-request model construction
2. establish stable request/result protocol
3. remove unnecessary encode/decode/copies
4. bound detector resolution
5. tune backend/runtime
6. batch useful work
7. tune providers/quantization
8. consider lower-level rewrites only after evidence

Do not rewrite TextJ in another language solely because it sounds faster.
