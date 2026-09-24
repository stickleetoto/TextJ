# AI Tool Protocol — v1

Status: **implemented** (`protocol_version: "1"`), 2026-09-24.

Source of truth in code:

| Concern | Module |
| --- | --- |
| request model + validation | `src/textj/api/request.py` |
| error codes | `src/textj/api/errors.py` |
| limits | `src/textj/api/limits.py` |
| image decode/normalize | `src/textj/api/image_loader.py` |
| response construction | `src/textj/api/response.py` |
| execution, queue, timeouts | `src/textj/runtime/runtime.py` |

Every interface — Python API, JSON stdio, loopback daemon, MCP — builds the
same request objects and returns the same response envelope. Changes to the
shapes below require tests in `tests/test_protocol.py` / `tests/test_runtime.py`
to change too; backward-incompatible changes require a new protocol version.

---

## 1. Framing

Text transports (stdio, TCP daemon) use **newline-delimited JSON**: one UTF-8
JSON object per line, one response line per request line, in order.

- Lines longer than `max_request_bytes` are discarded and answered with
  `REQUEST_TOO_LARGE`; the connection stays usable.
- Invalid JSON is answered with `INVALID_REQUEST` (`request_id: null`).
- Empty lines are ignored.
- stdout of `textj-serve --stdio` / `textj-mcp` carries protocol messages
  only; diagnostics go to stderr.

---

## 2. Request envelope

```json
{
  "protocol_version": "1",
  "request_id": "req-123",
  "operation": "ocr",
  "input": {"type": "path", "path": "C:/tmp/frame.png"},
  "options": {
    "mode": "fast",
    "min_score": 0.5,
    "include_boxes": true,
    "include_timings": true
  },
  "timeout_ms": 5000
}
```

| Field | Required | Rules |
| --- | --- | --- |
| `protocol_version` | yes | must be the string `"1"`; other values → `UNSUPPORTED_PROTOCOL`, missing → `INVALID_REQUEST` |
| `request_id` | no | string, 1–128 chars; echoed back. Generated (32 hex chars) if absent |
| `operation` | yes | `ocr`, `ocr_batch`, `status`; unknown → `UNSUPPORTED_OPERATION` |
| `input` | `ocr` | image descriptor (§3) |
| `items` | `ocr_batch` | array of `{"id"?: str, "input": {...}}` (§6) |
| `options` | no | §4 |
| `timeout_ms` | no | integer 1..`max_timeout_ms`; default `default_timeout_ms` |
| `auth_token` | daemon | transport field (§8); ignored by OCR semantics |

Parsing is **strict**: unknown fields at any level → `INVALID_REQUEST` with
`details.unknown`. This catches caller typos instead of silently ignoring them.

---

## 3. Image input

| `type` | Fields | Notes |
| --- | --- | --- |
| `path` | `path` | Local file path. Daemon callers should send absolute paths (relative paths resolve against the server's working directory). |
| `bytes_base64` | `data` | Standard base64 of an encoded image file (PNG, JPEG, BMP, WebP, TIFF, GIF first frame, ...). Size is checked before decoding. |
| ndarray | — | Python API only: `runtime.ocr(array)`. `uint8`/`uint16`, shapes `(H,W)`, `(H,W,1)`, `(H,W,3)` **BGR**, `(H,W,4)` **BGRA**. |

Processing:

1. size check (`max_image_bytes`) from file size / base64 length
2. header probe (Pillow) → dimension checks (`max_image_side`, `max_image_pixels`)
3. single decode (OpenCV, Pillow fallback) — no temporary files, no re-encode
4. normalize to contiguous `uint8 (H, W, 3)` BGR; alpha is composited onto
   a background that contrasts with the visible pixels; 16-bit is scaled.

URLs are **not** accepted as input.

---

## 4. Options

| Option | Type | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | string | `"fast"` | Only `fast` exists in v1. Other values → `INVALID_REQUEST`. |
| `language` | string | runtime's | If given, must equal the runtime's loaded language, else `INVALID_REQUEST` with `details.supported`. |
| `min_score` | number 0..1 | `0.5` | Lines with confidence below this are dropped. |
| `include_boxes` | bool | `true` | Emit `box` per line. |
| `include_timings` | bool | `true` | Emit `timings_ms`. |
| `preserve_indent` | bool | `false` | Rebuild leading indentation in `text` from line box positions. Use for **code/terminal** (monospace) crops only; on scattered UI layouts it inserts large bogus indents. `lines[].text` is never modified. |

---

## 5. Success response (`ocr`)

```json
{
  "protocol_version": "1",
  "request_id": "req-123",
  "ok": true,
  "result": {
    "text": "안녕하세요 TextJ",
    "lines": [
      {"text": "안녕하세요 TextJ", "score": 0.97, "box": [[10,10],[200,10],[200,40],[10,40]]}
    ],
    "line_count": 1,
    "mean_score": 0.97,
    "backend": "rapidocr-onnx",
    "input": {"width": 1920, "height": 1080, "source": "path", "format": "PNG", "bytes": 81234},
    "timings_ms": {
      "parse": 0.1, "queue": 0.04, "input": 0.8, "ocr": 150.2,
      "detect": 48.0, "recognize": 101.0, "postprocess": 0.03, "total": 151.4
    }
  }
}
```

- Key order is fixed (tested).
- `text` = non-empty line texts joined with `\n`.
- **Line order** = backend order. RapidOCR sorts boxes top-to-bottom, then
  left-to-right. No further layout reconstruction in v1.
- `box`: 4 points `[x, y]` in **original image pixels**, clockwise from
  top-left, rounded to 2 decimals; `null` if the backend gave no box.
- `score` rounded to 6 decimals; `mean_score` is over returned lines (0.0 if none).
- `input.source`: `path` | `bytes` | `ndarray`. `format`/`bytes` absent for ndarray.
- No text found → `ok: true`, `text: ""`, `lines: []`.

### Timings (`timings_ms`)

| Key | Meaning |
| --- | --- |
| `parse` | request validation (and JSON decode for text transports) |
| `queue` | admission → worker start |
| `input` | file read / base64-decoded bytes → decoded, normalized ndarray |
| `ocr` | backend call |
| `detect`, `recognize` | engine-reported sub-stages of `ocr`, when available |
| `postprocess` | score filtering + result construction |
| `total` | request received → response object built |

JSON encoding of the response and transport round-trip are not inside
`total`; measure them client-side (`textj-bench-runtime`).

---

## 6. Batch (`ocr_batch`)

```json
{
  "protocol_version": "1",
  "request_id": "batch-7",
  "operation": "ocr_batch",
  "items": [
    {"id": "crop-a", "input": {"type": "path", "path": "a.png"}},
    {"id": "crop-b", "input": {"type": "bytes_base64", "data": "..."}}
  ],
  "options": {"min_score": 0.6}
}
```

Response:

```json
{
  "protocol_version": "1", "request_id": "batch-7", "ok": true,
  "result": {
    "items": [
      {"id": "crop-a", "ok": true, "result": { ...same as ocr result... }},
      {"id": "crop-b", "ok": false, "error": {"code": "IMAGE_DECODE_FAILED", "message": "...", "retryable": false}}
    ],
    "item_count": 2, "succeeded": 1, "failed": 1,
    "backend": "rapidocr-onnx",
    "timings_ms": {"parse": 0.2, "queue": 0.1, "total": 310.0}
  }
}
```

- Item `id` defaults to the item's index as a string; ids must be unique.
- Item order is preserved.
- Per-item problems (bad input, missing file, decode error, OCR failure,
  deadline reached) are reported per item; the batch itself stays `ok: true`.
- Structural problems (not an array, empty, duplicate ids, more than
  `max_batch_items`) fail the whole request.
- Options apply to every item. Items run sequentially in one worker slot.
- Per-item `timings_ms` omit `parse`/`queue`/`total` (batch-level).

---

## 7. Errors

```json
{
  "protocol_version": "1",
  "request_id": "req-123",
  "ok": false,
  "error": {
    "code": "IMAGE_NOT_FOUND",
    "message": "input image was not found",
    "retryable": false,
    "details": {"path": "C:/tmp/frame.png"}
  }
}
```

Agents branch on `code`. `message` is diagnostic. `details` is optional and
code-specific. `request_id` is `null` only when the request could not be parsed
far enough to read it.

| Code | retryable | When |
| --- | --- | --- |
| `INVALID_REQUEST` | no | malformed JSON, missing/invalid/unknown fields, bad base64, language mismatch, bad batch structure |
| `UNSUPPORTED_PROTOCOL` | no | `protocol_version` ≠ `"1"` (`details.supported`) |
| `UNSUPPORTED_OPERATION` | no | unknown `operation` (`details.supported`) |
| `IMAGE_NOT_FOUND` | no | path missing, not a file, unreadable |
| `IMAGE_DECODE_FAILED` | no | bytes are not a decodable image |
| `UNSUPPORTED_IMAGE` | no | zero-size image, bad dtype/channel count |
| `REQUEST_TOO_LARGE` | no | message, encoded image, pixels, side, or batch size over limit |
| `BACKEND_NOT_READY` | starting: yes / failed or closing: no | runtime not ready (`details.state`) |
| `BUSY` | yes | admission capacity full (`details.max_inflight`, `details.max_queue`) |
| `TIMEOUT` | yes | deadline passed while queued or running (`details.timeout_ms`) |
| `OCR_FAILED` | no | backend raised during recognition |
| `UNAUTHORIZED` | no | daemon: missing or wrong `auth_token` |
| `INTERNAL_ERROR` | no | unexpected TextJ bug; details are logged to stderr |

The code list is frozen by `tests/test_protocol.py::test_error_code_values_are_frozen`.

---

## 8. Limits, timeouts and concurrency

Defaults (`textj.api.Limits`, reported by `status`):

| Limit | Default |
| --- | --- |
| `max_request_bytes` | 64 MiB per protocol message |
| `max_image_bytes` | 32 MiB encoded image |
| `max_image_pixels` | 50,000,000 |
| `max_image_side` | 16,384 px |
| `max_batch_items` | 64 |
| `default_timeout_ms` | 30,000 |
| `max_timeout_ms` | 600,000 |

Scheduling (`RuntimeConfig`):

- `max_inflight` workers (default **1**), each owning its own backend instance.
- At most `max_inflight + max_queue` requests admitted (default queue **8**).
  Beyond that: immediate `BUSY`. Nothing grows without bound.
- Deadline = receive time + `timeout_ms`.
  - still queued at the deadline → removed, `TIMEOUT`, never executed;
  - executing at the deadline → caller gets `TIMEOUT` immediately; the
    inference cannot be interrupted, so its slot stays busy until it ends
    and the result is discarded.
- Batch: the caller waits up to deadline + `batch_grace_ms` (2 s); items
  reached after the deadline get per-item `TIMEOUT`.
- `status` requests bypass the queue.

Daemon transport (`textj-serve --tcp`):

- binds loopback only (non-loopback addresses are refused);
- requires `auth_token` by default; the random token, host, port and pid are
  written with owner-only permissions to `~/.textj/daemon.json`
  (override: `--state-file` or `TEXTJ_STATE_FILE`);
- at most `--max-connections` (16) concurrent connections; extra connections
  receive one `BUSY` line and are closed; idle connections close after 300 s.

---

## 9. `status`

```json
{"protocol_version": "1", "operation": "status", "request_id": "s"}
```

Result fields: `state` (`created|starting|ready|failed|closing|closed`),
`ready`, `protocol_version`, `textj_version`, `backend` (name, profile,
language, detector limits), `failure`, `uptime_s`, `startup_ms`
(`backend_construct_ms`, `warmup_ms`), `scheduler` (`max_inflight`,
`max_queue`, `inflight`, `queued`), `limits`, `counters` (`requests`, `ok`,
`errors`, `busy_rejects`, `timeouts`), `errors_by_code`, `latency_ms`
(`count`, `p50`, `p95`, `max` over the last 1024 successful requests).

---

## 10. Interfaces

| Interface | Entry | Notes |
| --- | --- | --- |
| Python API | `TextJRuntime(RuntimeConfig(...)).start()`; `runtime.ocr(image, **options)`; `runtime.handle(dict)`; `runtime.handle_json(str)` | returns the envelope dict |
| JSON stdio | `textj-serve --stdio` | sequential; EOF stops the server |
| Local daemon | `textj-serve --tcp [--port 0]` | `TextJClient.from_state_file()`, `textj-client` |
| MCP | `textj-mcp` (in-process runtime) or `textj-mcp --daemon` | tools below |

MCP tools (JSON-RPC 2.0 over stdio, MCP versions 2025-06-18 / 2025-03-26 / 2024-11-05):

| Tool | Arguments | Maps to |
| --- | --- | --- |
| `ocr_image` | exactly one of `path` / `image_base64`; `min_score`, `include_boxes`, `include_timings`, `timeout_ms` | `ocr` |
| `ocr_batch` | `items: [{id?, path? , image_base64?}]` + the options above | `ocr_batch` |
| `textj_status` | — | `status` |

Tool results contain the protocol envelope as `structuredContent` and as JSON
text content; `isError` is `true` when `ok` is `false`.

---

## 11. Compatibility rules

- Additive fields in `result` or `details` are allowed within v1.
- Renaming/removing fields, changing types, changing error code strings, or
  changing line-order semantics requires `protocol_version: "2"`.
- Old versions should keep working where practical once v2 exists.
