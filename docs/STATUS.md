# Development Status

Last updated: 2026-09-23

## Current milestone

**v0.1 OCR Core implemented; v0.2 Benchmark Foundation in progress**

The code path for local image OCR is present. Real Windows screenshot validation is still required before v0.1 is considered field-validated.

## Implemented

### OCR core

- Python package layout
- `textj` console entry point
- backend abstraction
- RapidOCR backend
- PP-OCRv5 mobile configuration
- Korean recognition model selection
- ONNX Runtime CPU baseline
- backend-independent `OCRLine` / `OCRResult`
- plain-text CLI output
- JSON output
- confidence threshold option
- end-to-end timing
- RapidOCR internal detector/classifier/recognizer timing export when available
- backend-independent model and pipeline tests

### In-memory and clipboard path

- OCRPipeline accepts NumPy image arrays
- RapidOCR backend accepts in-memory arrays directly
- Pillow clipboard image acquisition
- RGB -> contiguous BGR conversion for RapidOCR
- no temporary image file on clipboard path
- native Win32 CF_UNICODETEXT output
- `textj-clipboard` command
- `--no-copy`, JSON and timing modes
- array/clipboard conversion tests

### Benchmark foundation

- `textj-bench` single-image benchmark
- warm-up runs separated from measured runs
- min / mean / p50 / p95 / max latency
- sampled process RSS memory
- UTF-8 ground-truth comparison
- character error rate (CER)
- result JSON persistence
- system/runtime metadata
- ONNX Runtime provider metadata
- benchmark manifest format
- `textj-bench-suite` multi-image regression runner
- per-case latency and CER
- aggregate mean p50 / p95 / CER
- benchmark utility tests
- `benchmarks/` fixture layout documentation

## Commands

OCR:

```bash
textj image.png --timing
```

Single-image benchmark:

```bash
textj-bench image.png --runs 20 --warmups 2
```

Accuracy benchmark:

```bash
textj-bench image.png --expected expected.txt --output benchmarks/results/image.json
```

Regression suite:

```bash
textj-bench-suite benchmarks/manifest.json \
  --runs 10 \
  --warmups 1 \
  --output benchmarks/results/baseline.json
```

## Remaining validation

- install on target Windows machine
- validate RapidOCR model acquisition/cache behavior
- run Korean screenshot baseline
- run English screenshot baseline
- run Korean/English mixed screenshot baseline
- record cold process/model startup separately
- collect real p50/p95 values
- build the first committed synthetic/safe fixture set
- verify line ordering failures
- decide whether orientation classification stays disabled by default

## Next engineering work

After baseline numbers exist:

1. detector input-size sweep
2. fast-path image-size policy
3. box filtering/merge experiments
4. recognizer batching experiments
5. optimize the new clipboard path under a resident runtime
6. Windows screen-region capture

## Known limitations

- clipboard OCR currently starts a fresh process/model each invocation
- no screen-region capture yet
- no resident process yet
- each CLI invocation is a new Python process
- first invocation can include model acquisition/loading cost
- line ordering currently follows backend output
- orientation classifier is intentionally disabled in the fast baseline
- RSS metric is sampled after runs, not a continuous true peak-memory profiler
