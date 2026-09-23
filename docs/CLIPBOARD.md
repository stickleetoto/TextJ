# Clipboard OCR

TextJ now has an early in-memory clipboard OCR path.

## Flow

```text
clipboard image
  -> Pillow ImageGrab
  -> RGB image
  -> contiguous BGR ndarray
  -> OCRPipeline
  -> RapidOCR
  -> recognized text
  -> Win32 CF_UNICODETEXT
```

No temporary PNG/JPEG file is required.

## Command

```powershell
textj-clipboard --timing
```

Behavior:

1. read the current clipboard image,
2. initialize the OCR backend,
3. recognize text directly from memory,
4. replace the clipboard with recognized text,
5. print the recognized text.

To inspect OCR without overwriting the clipboard:

```powershell
textj-clipboard --no-copy
```

Structured output:

```powershell
textj-clipboard --json
```

## Current limitation

This is still a command-line prototype.

Every invocation creates a new Python process and initializes the OCR model again. The final low-latency UX requires the resident runtime planned for v0.6.

The important architectural change is already present: `OCRPipeline` and the backend can now accept a NumPy image directly, so screen capture and clipboard capture do not need image encode/decode or temporary files.
