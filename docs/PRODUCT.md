# Product Definition

## 1. What is TextJ?

TextJ is a **local, low-latency OCR primitive for AI agents and automated systems**.

It is designed to answer requests such as:

```text
"Extract every visible line of text from this screenshot."
"Read this UI state and return boxes + confidence."
"Run OCR on these 20 image crops."
"Give my computer-use agent machine-readable text from the latest frame."
```

The canonical interaction is not a human clicking buttons.

It is:

```text
AI/worker
  -> sends image
  -> TextJ processes locally
  -> returns structured OCR result
```

---

## 2. Primary users

TextJ is built for software callers:

- LLM agents
- local autonomous agents
- computer-use systems
- MCP servers/tools
- automation pipelines
- screenshot analyzers
- testing systems
- vision preprocessing pipelines

A human may use the CLI for testing, but human desktop UX is secondary.

---

## 3. Primary inputs

TextJ should support machine-friendly inputs.

Priority order:

1. in-memory image array inside Python
2. local file path
3. encoded image bytes
4. daemon request containing or referencing image data
5. batch of images
6. optional capture adapters

Temporary files should not be required for normal programmatic use.

---

## 4. Primary outputs

Structured output is first-class.

Minimum useful result:

```json
{
  "protocol_version": "1",
  "request_id": "abc",
  "text": "hello",
  "lines": [
    {
      "text": "hello",
      "score": 0.98,
      "box": [[12, 20], [80, 20], [80, 40], [12, 40]]
    }
  ],
  "backend": "rapidocr-onnx",
  "timings_ms": {
    "total": 42.1
  }
}
```

Optional future fields can include:

- orientation
- language hints
- region grouping
- word-level boxes
- input dimensions
- model/provider metadata

Machine-readable stability matters more than pretty console formatting.

---

## 5. Product principles

### 5.1 Fast warm calls

AI tools may invoke OCR repeatedly.

Model construction should happen once, not once per request.

### 5.2 Deterministic behavior

The caller should be able to depend on:

- schema
- error codes
- timeout behavior
- size limits
- ordering rules
- version negotiation

### 5.3 Local by default

Do not upload agent screenshots to remote OCR services by default.

### 5.4 In-memory by default

Avoid encode/decode/disk cycles when an image is already available in memory.

### 5.5 Structured, not conversational

TextJ is a tool.

It should return OCR evidence, not invent explanations or interpret the image semantically.

### 5.6 Backend independence

The public API must not expose unnecessary RapidOCR-specific concepts.

---

## 6. Core use cases

### Agent screenshot OCR

A computer-use agent captures a frame and sends a crop to TextJ.

### Batch crop OCR

An upstream detector provides multiple image crops and TextJ recognizes them efficiently.

### UI parsing support

An agent combines TextJ boxes/text with accessibility or vision data.

### Code/terminal extraction

TextJ preserves exact-ish technical strings for another model to reason over.

### MCP tool

An MCP server exposes TextJ as an OCR tool to compatible agents.

---

## 7. Non-goals for v1

Not required:

- tray UI
- global keyboard shortcut
- drag-to-select overlay
- human OCR history
- cloud account
- sync
- document editor
- translation
- summarization
- semantic image reasoning
- custom foundation OCR model

A human-facing desktop wrapper may exist later, but it must remain an adapter around the AI-facing core.

---

## 8. v1 success criteria

TextJ v1 is successful when:

- a local agent can call OCR repeatedly without model reload,
- request/response schema is versioned and stable,
- path/bytes/in-memory inputs are supported by clear adapters,
- structured text/box/confidence output is available,
- batch requests are supported,
- concurrent calls have defined behavior,
- overload is bounded,
- errors are machine-readable,
- benchmark results are reproducible,
- Korean/English mixed OCR is useful,
- the backend can be replaced without changing the public contract.
