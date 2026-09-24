# AI Tool Protocol

Status: design target for TextJ protocol v1.

This document defines the machine-facing contract that future CLI/stdio, daemon, Python API, and MCP adapters should share.

---

## 1. Design goals

The protocol should be:

- local-first
- versioned
- deterministic
- easy to parse
- bounded
- backend-independent
- suitable for repeated AI-agent calls
- suitable for batch OCR

The protocol should not expose Python objects or arbitrary backend internals.

---

## 2. Request envelope

Conceptual request:

```json
{
  "protocol_version": "1",
  "request_id": "req-123",
  "operation": "ocr",
  "input": {
    "type": "path",
    "path": "C:/tmp/frame.png"
  },
  "options": {
    "language": "korean",
    "mode": "fast",
    "min_score": 0.5,
    "include_boxes": true,
    "include_timings": true
  }
}
```

Supported input types should evolve carefully.

Initial candidates:

- `path`
- `bytes_base64`
- internal Python ndarray API

Future candidates:

- shared memory handle
- memory-mapped region
- capture-handle adapter

---

## 3. Success response

```json
{
  "protocol_version": "1",
  "request_id": "req-123",
  "ok": true,
  "result": {
    "text": "안녕하세요 TextJ",
    "lines": [
      {
        "text": "안녕하세요 TextJ",
        "score": 0.97,
        "box": [[10, 10], [200, 10], [200, 40], [10, 40]]
      }
    ],
    "backend": "rapidocr-onnx",
    "input": {
      "width": 1920,
      "height": 1080
    },
    "timings_ms": {
      "queue": 0.2,
      "decode": 1.1,
      "ocr": 51.3,
      "serialize": 0.4,
      "total": 53.0
    }
  }
}
```

---

## 4. Error response

```json
{
  "protocol_version": "1",
  "request_id": "req-123",
  "ok": false,
  "error": {
    "code": "IMAGE_NOT_FOUND",
    "message": "Input image was not found.",
    "retryable": false
  }
}
```

The `message` is diagnostic.

Agents should primarily branch on `code`.

---

## 5. Initial error codes

Recommended v1 draft:

- `INVALID_REQUEST`
- `UNSUPPORTED_PROTOCOL`
- `UNSUPPORTED_OPERATION`
- `IMAGE_NOT_FOUND`
- `IMAGE_DECODE_FAILED`
- `UNSUPPORTED_IMAGE`
- `REQUEST_TOO_LARGE`
- `BACKEND_NOT_READY`
- `BUSY`
- `TIMEOUT`
- `OCR_FAILED`
- `INTERNAL_ERROR`

Do not casually rename codes after protocol use begins.

---

## 6. Batch OCR

Conceptual request:

```json
{
  "protocol_version": "1",
  "request_id": "batch-7",
  "operation": "ocr_batch",
  "items": [
    {"id": "crop-a", "input": {"type": "path", "path": "a.png"}},
    {"id": "crop-b", "input": {"type": "path", "path": "b.png"}}
  ]
}
```

Batch results should preserve item IDs and order.

One failed item should not necessarily destroy all successful items.

---

## 7. Limits

Daemon/service mode must define limits such as:

- maximum encoded payload size
- maximum image dimensions
- maximum pixels
- maximum batch count
- request timeout
- queue length
- concurrent request count

Reject oversized work early with a stable error code.

---

## 8. Ordering

TextJ should document how line order is produced.

Until advanced layout reconstruction exists:

- preserve backend order or
- apply one deterministic reading-order algorithm

Do not silently change ordering semantics without tests.

---

## 9. Transport independence

The core schema should be reusable over:

- JSON stdin/stdout
- local socket
- named pipe
- loopback HTTP if justified
- MCP adapter

Transport-specific metadata should stay outside OCR result semantics.

---

## 10. MCP adapter

MCP should be a thin adapter.

Likely tools:

- `ocr_image`
- `ocr_batch`
- `textj_status`

MCP is not the core runtime.

The MCP adapter should call the same resident TextJ runtime used by other interfaces.

---

## 11. Compatibility

Protocol responses should include `protocol_version`.

If future breaking changes are required:

- add a new protocol version,
- preserve the old version where practical,
- do not make agents guess response shape.
