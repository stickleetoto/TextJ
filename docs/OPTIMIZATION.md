# Optimization Strategy

## 1. Performance philosophy

TextJ optimizes **time-to-clipboard**, not benchmark theater.

The useful equation is:

```text
T_total =
T_trigger
+ T_capture
+ T_convert
+ T_detect
+ T_crop
+ T_recognize
+ T_layout
+ T_clipboard
```

Reducing a 50 ms model to 30 ms is irrelevant if image capture and conversion consume 300 ms.

---

## 2. Optimization levels

### Level 0 — eliminate accidental work

Before model optimization:

- never reload models per request
- do not repeatedly import heavy packages
- avoid repeated image encode/decode
- avoid saving temporary PNG/JPEG files
- avoid converting RGB <-> BGR multiple times
- avoid copying full screenshots unless necessary

### Level 1 — reduce pixels

OCR cost strongly depends on image size.

Detector path:

```text
native screenshot
-> downscaled detector view
-> detect boxes
-> map boxes to native screenshot
-> recognize original-resolution crops
```

This keeps detection cheap without throwing away recognition detail.

### Level 2 — reduce regions

Before recognition:

- reject tiny noise boxes
- merge near-duplicate boxes
- suppress strongly overlapping boxes
- drop impossible aspect ratios when safe
- skip invisible/transparent regions where relevant

### Level 3 — batch intelligently

Recognition crops have varying widths.

Instead of:

```text
[a very short crop, a huge crop, a medium crop]
```

bucket by dimensions:

```text
small-width batch
medium-width batch
large-width batch
```

This reduces padding waste in batched models.

### Level 4 — adaptive quality

Run cheap work first.

```text
FAST
 |
 +-- high confidence --> output
 |
 +-- uncertain -------> targeted retry
```

Only ambiguous regions should pay for the slow path.

---

## 3. Model warm-up

A resident process should:

1. create inference sessions,
2. allocate common buffers,
3. run one or more dummy inferences,
4. enter ready state.

Benchmark separately:

- process cold start
- model cold inference
- warm steady-state inference

The global hotkey should only be enabled after the normal runtime is ready, or the app should clearly expose readiness.

---

## 4. Buffer and copy policy

A hidden source of OCR latency is memory movement.

Track:

- capture buffer -> CPU buffer
- BGRA -> BGR/RGB conversion
- resize output
- crop allocation
- tensor conversion
- CPU -> GPU upload
- GPU -> CPU result synchronization

Possible future optimization:

```text
capture frame
  ↓
shared/reused native buffer
  ↓
resize/crop
  ↓
inference tensor
```

Avoid:

```text
capture
-> PNG encode
-> bytes
-> PNG decode
-> NumPy copy
-> color copy
-> tensor copy
```

---

## 5. Crop recognition cache

Screens often contain repeated text.

A future optional cache could fingerprint normalized crops:

```text
crop
-> tiny perceptual hash
-> cache lookup
-> unchanged? reuse OCR
```

Possible use cases:

- repeated UI labels
- repeated game HUD
- monitoring tools

Do not add this before the uncached path is reliable.

Cache correctness rules:

- bounded memory
- short TTL
- confidence-aware
- no persistence by default
- collision-safe verification for suspicious hits

---

## 6. Dirty-region OCR

For continuous/rapid OCR modes, full-screen reprocessing is wasteful.

DXGI Desktop Duplication exposes frame-change metadata such as dirty regions.

Possible future pipeline:

```text
new frame
-> changed rectangles
-> intersection with OCR watch area
-> OCR only changed areas
```

This is especially useful for:

- subtitles
- chat windows
- game UI
- live terminal output

It is not required for one-shot region OCR.

---

## 7. Detector bypass

Some inputs do not require general text detection.

Examples:

### Single selected line

If the user captures a thin horizontal region, directly recognize it.

### Clipboard crop with strong heuristics

If the image shape strongly resembles a single text line, detector bypass can be attempted.

Pipeline:

```text
input
-> classify layout cheaply
-> single-line?
   -> recognizer directly
-> otherwise
   -> detector
```

This should be benchmarked carefully because wrong bypass decisions damage accuracy.

---

## 8. Downscale search

The detector does not always need a fixed resolution.

Potential adaptive strategy:

```text
small region  -> near-native / moderate scale
1080p screen  -> capped scale
4K screen     -> aggressively capped detector view
```

Benchmark dimensions such as:

- 640
- 768
- 960
- 1280

for the detector longest side.

Choose based on latency/recall Pareto frontier.

---

## 9. Quantization

Potential variants:

- FP32
- FP16 where provider supports it well
- INT8 dynamic
- INT8 static/calibrated

Quantization is not automatically faster.

Measure:

- model load time
- detector latency
- recognizer latency
- CER
- memory
- provider compatibility

A quantized model that is 2x smaller but slower on the target provider is not a win.

---

## 10. Thread tuning

CPU inference should benchmark:

- ORT intra-op thread count
- inter-op thread count
- sequential vs parallel execution
- physical-core-oriented values
- system responsiveness during OCR

Fastest absolute throughput is not necessarily best for a desktop utility.

TextJ should avoid freezing the user's system just to save a few milliseconds.

---

## 11. Latency classes

TextJ can use workload-aware paths.

```text
Class S
tiny crop / single line
-> direct or tiny detector path

Class M
normal selected region
-> default fast OCR

Class L
large screenshot/document
-> bounded detector + batched recognition

Class X
difficult/low-confidence
-> accurate fallback
```

This avoids forcing every request through one universal configuration.

---

## 12. Optimization evidence

Every optimization PR should include:

```text
before:
p50
p95
CER
RSS

after:
p50
p95
CER
RSS

dataset/config:
...
```

A change described as "faster" without measurements should be considered unverified.
