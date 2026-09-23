# Performance Targets

## 1. Primary metric

TextJ optimizes **end-to-end warm latency**.

For region capture:

```text
mouse release
-> image available
-> OCR complete
-> clipboard updated
```

The measurement ends only when the extracted text is usable.

---

## 2. Target classes

These are engineering targets, not guarantees.

### Small region

Example:

- button labels
- terminal error line
- short chat message
- small paragraph

Target:

- **stretch:** <= 150 ms
- **v1 target:** <= 250 ms warm

### Ordinary screenshot region

Example:

- several lines of UI text
- medium chat area
- code snippet
- article paragraph

Target:

- **stretch:** <= 300 ms
- **v1 target:** <= 500 ms warm

### Full document-like image

Example:

- 1080p screenshot with many text regions
- photographed page under reasonable conditions

Target:

- **v1 target:** <= 1.0 s warm on reference hardware when the selected backend permits it

These targets must be revised using real measurements.

---

## 3. Cold vs warm benchmarks

Always report both.

### Cold

Includes:

- process start,
- imports,
- model initialization,
- inference-session creation,
- first-run warm-up.

### Warm

Assumes:

- process alive,
- model loaded,
- runtime initialized.

Desktop UX is judged mainly by warm latency.

---

## 4. Stage timing

Every benchmark record should include:

| Stage | Meaning |
| --- | --- |
| input | file decode, clipboard read, or screen capture |
| normalize | image format conversion and basic preparation |
| detect | text detection |
| map/crop | coordinate mapping and region extraction |
| recognize | text recognition |
| postprocess | ordering, joining, cleanup |
| output | clipboard/stdout/file |
| total | end-to-end latency |

---

## 5. Percentiles

Do not optimize around one lucky run.

At minimum report:

- median / p50
- p95
- max during benchmark run

p95 is especially important for perceived responsiveness.

A tool that usually takes 150 ms but randomly takes 2 seconds is not fast in practice.

---

## 6. Benchmark dataset

The initial benchmark pack should contain at least:

### UI text

- Windows settings
- browser UI
- application dialogs

### Korean

- Korean paragraphs
- Korean UI
- mixed Hangul + numbers

### English

- documentation
- ordinary paragraphs
- menus

### Mixed technical

- Korean explanation with English library names
- code screenshots
- terminal output
- URLs and paths

### Hard cases

- low contrast
- dark mode
- tiny text
- scaled screenshots
- colored backgrounds
- compressed images

---

## 7. Accuracy metrics

Latency alone is insufficient.

Recommended metrics:

- CER: Character Error Rate
- exact-line match rate
- normalized text match rate
- text detection recall on selected benchmark images

For practical screen OCR, manually curated expected text files are acceptable during early development.

---

## 8. Reference benchmark protocol

For each backend/configuration:

1. restart for cold measurement,
2. record cold first-run latency,
3. execute warm-up,
4. run each sample multiple times,
5. record stage timings,
6. report p50 and p95,
7. record peak/RSS memory,
8. save configuration and runtime provider.

A result without configuration metadata should not be used for comparisons.

---

## 9. Performance budget

Example budget for a 250 ms small-region target:

```text
capture/input       15 ms
normalize            5 ms
detect               60 ms
crop/map             5 ms
recognize           150 ms
postprocess           5 ms
clipboard             2 ms
budget reserve        8 ms
-------------------------
total               250 ms
```

This is only an initial budget.

The real budget will be rewritten after the first benchmark.

---

## 10. Optimization order

Optimize in this order unless profiling proves otherwise:

1. eliminate repeated model loading,
2. reduce unnecessary image resolution,
3. reduce image copies/conversions,
4. batch recognition intelligently,
5. tune detector input size,
6. tune runtime provider/threading,
7. add confidence-based second pass,
8. only then consider lower-level rewrites.

Do not rewrite the application in a lower-level language before profiling identifies Python/runtime overhead as a significant part of total latency.
