# Benchmark Results

Measured results only. Every row names its configuration. Do not copy these
numbers into claims about other hardware, models, or configurations.

Raw artifacts are written to `benchmarks/results/` (git-ignored). To reproduce,
rerun the listed command.

---

## 2026-09-24 — Linux cloud container, PP-OCRv6 small (bundled), English fixtures

### Environment

- CPU: Intel Xeon @ 2.10 GHz, 4 vCPU; 16 GB RAM; Linux 6.18 x86_64
- Python 3.11.15, onnxruntime 1.30.0 (CPUExecutionProvider), rapidocr 3.9.2,
  numpy 2.4.6, opencv-python 5.0.0.93, Pillow 12.3.0
- Profile `ppocrv6-small` (models bundled in the rapidocr wheel), `--language en`
- Commit: working state between `964db73` and the runtime/fixture commit
- **Not** the target Windows machine. **Not** the Korean PP-OCRv5 model:
  its download host was blocked by the sandbox network policy.

### Detector resize policy sweep

Corpus: `benchmarks/fixtures/manifest.json`, tags `EN,CODE,TERM,DARK,TINY`
(8 cases). `--runs 10 --warmups 2`. Latency = warm `OCRPipeline.run` per call.

```bash
textj-bench-suite benchmarks/fixtures/manifest.json --tags EN,CODE,TERM,DARK,TINY \
  --language en --profile ppocrv6-small --runs 10 --warmups 2 \
  --det-limit-type <min|max> --det-limit-side-len <N>
```

| Det policy | mean p50 ms | mean p95 ms | mean CER | max sampled RSS |
| --- | ---: | ---: | ---: | ---: |
| RapidOCR default (min, 736) | 806.6 | 922.3 | 0.0181 | 279.7 MB |
| min, 960 | 1405.3 | 1564.2 | 0.0347 | 277.9 MB |
| max, 736 | 155.8 | 179.5 | 0.0181 | 268.3 MB |
| max, 960 | 148.3 | 168.9 | 0.0181 | 268.0 MB |
| **max, 1280 (TextJ default)** | 149.6 | 164.2 | 0.0181 | 268.0 MB |

Per case, default vs max 1280:

| Case | Tags | Size | default p50 | max1280 p50 | max1280 p95 | CER |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| en-ui-001 | EN UI S | 171×92 | 406.4 | 53.8 | 69.8 | 0.0000 |
| en-para-001 | EN M | 552×131 | 1008.2 | 169.6 | 175.1 | 0.0076 |
| en-url-001 | EN URL S | 551×92 | 1473.8 | 143.1 | 151.2 | 0.0000 |
| code-py-001 | CODE M | 465×113 | 973.4 | 157.4 | 165.9 | 0.0741 |
| term-dark-001 | TERM DARK M | 357×140 | 604.4 | 141.1 | 153.5 | 0.0000 |
| dark-ui-001 | DARK UI S | 229×92 | 547.7 | 60.1 | 85.2 | 0.0000 |
| tiny-en-001 | TINY EN S | 197×44 | 989.7 | 56.2 | 67.2 | 0.0000 |
| screen-en-001 | EN UI L | 1280×720 | 449.6 | 415.7 | 445.9 | 0.0632 |

Interpretation:

- RapidOCR's default `min` policy **upscales** the short side to 736 px. For
  wide, short screen crops this multiplies detector work (for a 900×140 crop
  the detector input's short side is scaled from 140 to 736 px).
- `max` keeps small crops at native size. On this corpus CER is identical for
  every case (`textj-bench-compare ... --max-cer-increase 0` passes).
- Decision: TextJ commands and `TextJRuntime` default to `max`, 1280. 1280 was
  chosen over 960 because it does not downscale screens up to 1280 px; the
  two were equal within noise here. Large screenshots (1440p/4K) were not
  measured yet; small text on large images is the main risk to re-check.

Known recognition failures in this corpus (same under every policy):

- `code-py-001`: leading indentation is lost (`    data = ...` → `data = ...`).
- `screen-en-001`: runs of spaces collapse (`File   Edit` → `File Edit`).
- `en-para-001`: `AI` recognized as `Al`.

### Request-to-response through the runtime and transports

```bash
textj-bench-runtime benchmarks/fixtures/images/<case>.png --language en \
  --profile ppocrv6-small --runs 20 --warmups 2 --burst-clients 4 --burst-requests 5
```

Runtime default config (max_inflight 1, max_queue 8, det max 1280).
Client-observed wall time; `input`/`detect`/`recognize` are server-reported means.

`en-para-001` (552×131). Runtime start 570.6 ms (construct 532.2, warmup 38.2).

| Path | p50 | p95 | max | input | detect | recognize |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Python API (`handle` dict) | 157.4 | 182.5 | 190.9 | 0.78 | 48.0 | 110.6 |
| `handle_json` | 171.6 | 183.1 | 204.9 | 0.81 | 47.4 | 121.8 |
| TCP daemon, path input | 168.1 | 199.8 | 203.9 | 0.82 | 48.0 | 119.7 |
| TCP daemon, base64 bytes | 168.9 | 182.4 | 183.6 | 0.69 | 49.8 | 117.5 |

`screen-en-001` (1280×720). Runtime start 575.9 ms.

| Path | p50 | p95 | max | input | detect | recognize |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Python API | 418.9 | 451.1 | 457.3 | 4.51 | 332.4 | 82.1 |
| `handle_json` | 420.7 | 443.3 | 467.6 | 4.53 | 336.2 | 82.4 |
| TCP daemon, path | 428.1 | 453.9 | 454.9 | 4.78 | 338.2 | 85.0 |
| TCP daemon, base64 | 413.5 | 440.4 | 441.5 | 4.39 | 327.7 | 80.7 |

Interpretation:

- Protocol parse, queue and decode are ≤ 5 ms; OCR inference dominates.
  Differences between the four paths are within run-to-run variation of the
  OCR stage itself (compare the server-side `recognize` column).
- On the 1280×720 screen, detection is ~80% of latency: next optimization target.

### Burst / concurrency

4 concurrent TCP clients × 10 requests, `en-para-001`:

| max_inflight | backend construct (all) | throughput | client p50 | client p95 | ok |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **1 (default)** | 565 ms | 5.91 req/s | 659.4 | 796.0 | 40/40 |
| 2 | 697 ms | 4.70 req/s | 839.8 | 1213.8 | 40/40 |
| 4 | 1000 ms | 4.36 req/s | 870.5 | 1230.8 | 40/40 |

Each ONNX Runtime session already uses all cores, so parallel sessions contend
on this 4-vCPU machine: more in-flight workers lowered throughput and raised
p95. Default stays `max_inflight = 1`. Re-measure on the target machine.

### ONNX Runtime intra-op threads (direct RapidOCR engine)

Direct `RapidOCR(...)` calls with `Det.limit_type=max, 1280`, PP-OCRv6 small,
2 warmups + 10 runs; p50 / max in ms. Ad-hoc script, not a TextJ command.

| intra_op_num_threads | en-para-001 552×131 | screen-en-001 1280×720 | en-ui-001 171×92 |
| ---: | ---: | ---: | ---: |
| -1 (all cores, default) | 165.4 / 187.5 | 419.8 / 444.9 | 60.8 / 64.8 |
| 1 | 325.7 / 344.6 | 1217.5 / 1295.3 | 64.7 / 83.3 |
| 2 | 181.1 / 190.6 | 681.9 / 742.3 | 38.8 / 46.4 |
| 4 | 163.6 / 214.8 | 436.3 / 561.9 | 65.6 / 111.8 |

Default kept. Small crops were faster with 2 threads here; a size-dependent
thread policy is a possible later experiment (needs more cases and runs).

### `preserve_indent` postprocess (accuracy only)

Runtime, PP-OCRv6 small, `options.preserve_indent` off vs on, CER:

| Case | off | on |
| --- | ---: | ---: |
| code-py-001 | 0.0741 | **0.0000** |
| term-dark-001 | 0.0000 | 0.0000 |
| screen-en-001 | 0.0632 | **1.4105** |
| other EN/DARK/TINY/URL cases | unchanged | unchanged |

Fixes code indentation; destroys scattered UI layouts. Therefore opt-in and
documented as code/terminal-only.

---

## Pending measurements

- Korean / mixed fixtures with `ppocrv5-mobile` (blocked: model download host
  unreachable from the development sandbox).
- Target Windows hardware.
- 1440p / 4K screenshots and detector side-length sweep for them.
- Idle RSS of a long-running daemon; RSS with `max_inflight > 1`.
- Recognizer thread settings (`intra_op_num_threads`) vs latency.
