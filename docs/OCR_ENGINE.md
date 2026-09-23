# OCR Engine Strategy

## 1. Strategy

TextJ should begin by integrating an existing local OCR backend.

The initial engineering problem is not:

> Can we invent a new OCR model?

It is:

> How quickly can we turn arbitrary screen pixels into usable text?

A custom OCR model may become a later research track after the product pipeline and benchmark suite are stable.

---

## 2. Backend abstraction

Detection and recognition must be replaceable.

TextJ should be able to compare combinations such as:

```text
Detector A + Recognizer A
Detector A + Recognizer B
Detector B + Recognizer B
```

without changing capture, clipboard, UI, or benchmark code.

---

## 3. Initial backend characteristics

The first backend should preferably support:

- local inference,
- CPU execution,
- Korean and English,
- reusable model sessions,
- batch recognition,
- predictable model files,
- an inference runtime that can later use hardware acceleration.

ONNX-compatible OCR pipelines are a strong starting direction because they make runtime/provider experiments easier, but TextJ should not hard-code its architecture around a specific vendor implementation.

---

## 4. Detection optimization

Text detection is often performed on a reduced representation of the source image.

Proposed strategy:

1. inspect input dimensions,
2. resize to a bounded detector resolution,
3. detect text areas,
4. map boxes back to original coordinates,
5. crop original pixels for recognition.

Important variables to benchmark:

- detector long-side resolution,
- detector threshold,
- minimum text box size,
- box merge rules,
- orientation handling.

---

## 5. Recognition optimization

Recognition should operate only on useful text crops.

Potential optimizations:

- dynamic batching,
- bucket crops by similar width,
- cap maximum recognition width in fast mode,
- skip extremely low-confidence detector regions,
- avoid recognizing duplicate boxes,
- use one warm runtime session,
- separate short UI-text mode from document mode.

Batch size should be selected by measurement rather than assuming larger is always faster.

---

## 6. Korean + English handling

The first language policy is mixed `ko + en`.

Important cases:

- Korean sentence with English technical words,
- source code surrounded by Korean explanation,
- UI labels,
- numbers and punctuation,
- URLs,
- filenames,
- terminal output.

Postprocessing must avoid aggressively "correcting" technical text.

For example, a code identifier should not be automatically transformed into a natural-language word simply because it looks unusual.

---

## 7. Preprocessing policy

Preprocessing is conditional, not mandatory.

Default fast path:

- normalize image representation,
- resize only where required,
- no expensive enhancement unless needed.

Optional difficult-image path may include:

- contrast adjustment,
- grayscale conversion,
- thresholding,
- denoise,
- deskew,
- orientation correction.

Each preprocessing step must justify its latency cost through measured accuracy improvement.

---

## 8. Confidence-driven fallback

A future optimization path:

```text
fast recognition
      |
      v
confidence acceptable? ---- yes ---> return
      |
      no
      v
second-pass accurate recognition
```

This preserves fast common-case behavior without abandoning difficult images.

---

## 9. Custom TextJ model: future track

A custom model is intentionally not required for v1.

If TextJ later develops one, useful research targets include:

- Korean/English screen-text specialization,
- tiny UI text,
- anti-aliased fonts,
- terminal/code recognition,
- recognition model distillation,
- quantization,
- dynamic-width recognition,
- screen-specific synthetic datasets.

The product benchmark suite should exist before model research begins so a custom model can be judged against a real baseline.

---

## 10. Backend acceptance test

A backend is acceptable only if it can be wrapped behind the TextJ interfaces and measured on the same dataset.

Minimum comparison dimensions:

- cold startup time,
- warm inference time,
- Korean accuracy,
- English accuracy,
- mixed-text behavior,
- memory usage,
- model size,
- CPU latency,
- accelerated latency when available.

No backend should become permanent only because it was used first.
