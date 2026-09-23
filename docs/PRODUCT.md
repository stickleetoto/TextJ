# Product Definition

## 1. What is TextJ?

TextJ is a lightweight local OCR utility that turns visible text in an image or screen region into editable text as quickly as possible.

The intended experience is:

```text
press hotkey
-> drag over text
-> release mouse
-> text is already in clipboard
```

A conventional OCR application often makes the user open a window, import a file, wait for analysis, select output, and copy it.

TextJ should remove almost all of those steps.

---

## 2. Primary use cases

### Region OCR

The user presses a global hotkey and selects part of the screen.

TextJ recognizes only that region and places the result in the clipboard.

### Clipboard image OCR

If the clipboard already contains an image, TextJ should be able to OCR it directly.

### File OCR

The user passes an image file to TextJ through CLI, drag-and-drop, or the desktop shell.

### Batch OCR

A folder of screenshots can be processed into text files for debugging, archiving, dataset preparation, or note extraction.

---

## 3. Product principles

### 3.1 Latency first

The user should feel that TextJ is instant.

A slightly less accurate result that arrives immediately may be more useful than a perfect result that requires several seconds, provided the user can switch to a higher-accuracy mode when needed.

### 3.2 Local first

OCR should work without uploading screenshots to a remote server.

This improves privacy, removes network latency, and makes the utility usable offline.

### 3.3 Warm process

The default desktop mode should keep the OCR runtime and required models loaded.

Cold startup and model initialization are benchmarked separately from warm OCR latency.

### 3.4 Replaceable OCR backend

TextJ must not be permanently coupled to one OCR library.

Detection and recognition implementations should sit behind internal interfaces.

### 3.5 Korean + English first

The first language target is mixed Korean and English text because this covers the main intended environment while keeping the initial scope controlled.

### 3.6 Minimal interaction

The default successful path should require no confirmation dialog.

The output should be copied automatically.

---

## 4. Modes

### Fast mode

Optimized for UI text, code snippets, chat screenshots, menus, and ordinary screen text.

Characteristics:

- minimal preprocessing
- aggressive resize limits
- fast text detection
- short postprocessing path

### Accurate mode

Used when the first pass is uncertain or the source image is difficult.

Possible differences:

- larger detector input
- additional preprocessing
- orientation handling
- slower recognition backend
- second-pass recognition of low-confidence regions

Fast mode is the default.

---

## 5. Non-goals for v1

The following are intentionally outside the first release unless required by core OCR quality:

- full PDF document management
- cloud synchronization
- user accounts
- collaborative annotation
- document editor
- translation
- summarization
- handwriting-first recognition
- a custom foundation OCR model
- complex AI assistant features

These can be separate future projects or plugins.

---

## 6. Success criteria for v1

TextJ v1 is successful when:

- region capture is reliable,
- Korean/English OCR works locally,
- warm OCR feels immediate on ordinary screenshots,
- output reaches the clipboard automatically,
- benchmark results can be reproduced,
- OCR backend can be changed without rewriting the application,
- the app can stay running with acceptable memory usage.

The exact performance thresholds are defined in [PERFORMANCE.md](PERFORMANCE.md).
