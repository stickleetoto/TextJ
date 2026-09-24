"""MCP (Model Context Protocol) adapter for TextJ.

A dependency-free MCP server speaking JSON-RPC 2.0 over stdio (one message per
line). It is a thin mapping layer: every tool call becomes a TextJ protocol v1
request handled by either

* an in-process :class:`TextJRuntime` (default; the MCP server process is
  itself long-lived, so the model is loaded once), or
* a running ``textj-serve --tcp`` daemon (``--daemon``), shared with other
  clients.

Tools: ``ocr_image``, ``ocr_batch``, ``textj_status``. Tool results carry the
protocol v1 envelope both as ``structuredContent`` and as JSON text.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, BinaryIO, Callable, Mapping

from textj import __version__
from textj.api.errors import ErrorCode, TextJError
from textj.api.request import PROTOCOL_VERSION
from textj.api.response import encode_json, error_envelope

log = logging.getLogger("textj.mcp")

Handler = Callable[[dict[str, Any]], dict[str, Any]]

SUPPORTED_MCP_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_MESSAGE_BYTES = 64 * 1024 * 1024

_OPTION_PROPERTIES: dict[str, Any] = {
    "min_score": {
        "type": "number", "minimum": 0, "maximum": 1,
        "description": "Drop lines with confidence below this value (default 0.5).",
    },
    "include_boxes": {
        "type": "boolean",
        "description": "Include 4-point pixel boxes per line (default true).",
    },
    "include_timings": {
        "type": "boolean",
        "description": "Include stage timings in milliseconds (default true).",
    },
    "preserve_indent": {
        "type": "boolean",
        "description": "Rebuild leading indentation from box positions (code/terminal text). Default false.",
    },
    "timeout_ms": {
        "type": "integer", "minimum": 1,
        "description": "Fail with TIMEOUT if not finished within this many ms (default 30000).",
    },
}

_IMAGE_PROPERTIES: dict[str, Any] = {
    "path": {
        "type": "string",
        "description": "Absolute path of a local image file (PNG, JPEG, BMP, WebP, ...).",
    },
    "image_base64": {
        "type": "string",
        "description": "Base64-encoded image file bytes. Use instead of path.",
    },
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "ocr_image",
        "description": (
            "Extract text from one image or screenshot with local OCR (Korean + English). "
            "Returns text, per-line confidence scores and pixel bounding boxes. "
            "Provide exactly one of 'path' or 'image_base64'. Line order is "
            "top-to-bottom, then left-to-right. On failure, error.code is a stable "
            "machine-readable code (e.g. IMAGE_NOT_FOUND, BUSY, TIMEOUT)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {**_IMAGE_PROPERTIES, **_OPTION_PROPERTIES},
            "additionalProperties": False,
        },
    },
    {
        "name": "ocr_batch",
        "description": (
            "Run local OCR on several images or crops in one call. Results keep item "
            "order and ids; one failed item does not fail the others."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Caller-chosen item id."},
                            **_IMAGE_PROPERTIES,
                        },
                        "additionalProperties": False,
                    },
                },
                **_OPTION_PROPERTIES,
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
    {
        "name": "textj_status",
        "description": (
            "Report TextJ runtime readiness, loaded backend/model, queue limits, "
            "counters and recent latency."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

_TOOL_NAMES = {tool["name"] for tool in TOOLS}


class ToolArgumentError(Exception):
    pass


def _image_input(args: Mapping[str, Any], where: str) -> dict[str, Any]:
    path = args.get("path")
    data = args.get("image_base64")
    if (path is None) == (data is None):
        raise ToolArgumentError(f"{where}: provide exactly one of 'path' or 'image_base64'")
    if path is not None:
        return {"type": "path", "path": path}
    return {"type": "bytes_base64", "data": data}


def _options(args: Mapping[str, Any]) -> dict[str, Any] | None:
    options = {
        key: args[key]
        for key in ("min_score", "include_boxes", "include_timings", "preserve_indent")
        if key in args
    }
    return options or None


def tool_request(name: str, args: Mapping[str, Any]) -> dict[str, Any]:
    """Translate MCP tool arguments into a protocol v1 request."""
    if not isinstance(args, Mapping):
        raise ToolArgumentError("arguments must be an object")
    allowed = set(TOOLS[[t["name"] for t in TOOLS].index(name)]["inputSchema"]["properties"])
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise ToolArgumentError(f"unknown argument(s): {', '.join(unknown)}")

    request: dict[str, Any] = {"protocol_version": PROTOCOL_VERSION}
    if name == "textj_status":
        request["operation"] = "status"
        return request

    if "timeout_ms" in args:
        request["timeout_ms"] = args["timeout_ms"]
    options = _options(args)
    if options is not None:
        request["options"] = options

    if name == "ocr_image":
        request["operation"] = "ocr"
        request["input"] = _image_input(args, "ocr_image")
        return request

    items = args.get("items")
    if not isinstance(items, list):
        raise ToolArgumentError("items must be an array")
    protocol_items = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ToolArgumentError(f"items[{index}] must be an object")
        extra = sorted(set(item) - {"id", "path", "image_base64"})
        if extra:
            raise ToolArgumentError(f"items[{index}]: unknown argument(s): {', '.join(extra)}")
        entry: dict[str, Any] = {"input": _image_input(item, f"items[{index}]")}
        if "id" in item:
            entry["id"] = item["id"]
        protocol_items.append(entry)
    request["operation"] = "ocr_batch"
    request["items"] = protocol_items
    return request


class MCPServer:
    def __init__(self, handler: Handler) -> None:
        self.handler = handler
        self.initialized = False

    def call_tool(self, name: str, args: Mapping[str, Any]) -> dict[str, Any]:
        try:
            envelope = self.handler(tool_request(name, args))
        except ToolArgumentError as exc:
            envelope = error_envelope(None, TextJError(ErrorCode.INVALID_REQUEST, str(exc)))
        except Exception as exc:  # daemon unreachable etc.
            log.exception("tool call failed")
            envelope = error_envelope(
                None,
                TextJError(
                    ErrorCode.BACKEND_NOT_READY,
                    f"TextJ runtime unavailable: {exc}",
                    retryable=True,
                ),
            )
        return {
            "content": [{"type": "text", "text": encode_json(envelope)}],
            "structuredContent": envelope,
            "isError": not envelope.get("ok", False),
        }

    def dispatch(self, message: Any) -> dict[str, Any] | None:
        """Handle one JSON-RPC message. Returns a response, or None for notifications."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _rpc_error(None, -32600, "Invalid Request")
        method = message.get("method")
        msg_id = message.get("id")
        is_notification = "id" not in message
        if not isinstance(method, str):
            return None if is_notification else _rpc_error(msg_id, -32600, "Invalid Request")
        params = message.get("params") or {}

        if is_notification:
            if method == "notifications/initialized":
                self.initialized = True
            return None

        if method == "initialize":
            requested = params.get("protocolVersion") if isinstance(params, dict) else None
            version = requested if requested in SUPPORTED_MCP_VERSIONS else SUPPORTED_MCP_VERSIONS[0]
            return _rpc_result(msg_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "textj", "version": __version__},
                "instructions": (
                    "Local OCR for images and screenshots. Use ocr_image for one image, "
                    "ocr_batch for several crops, textj_status to check readiness."
                ),
            })
        if method == "ping":
            return _rpc_result(msg_id, {})
        if method == "tools/list":
            return _rpc_result(msg_id, {"tools": TOOLS})
        if method == "tools/call":
            if not isinstance(params, dict):
                return _rpc_error(msg_id, -32602, "Invalid params")
            name = params.get("name")
            if name not in _TOOL_NAMES:
                return _rpc_error(msg_id, -32602, f"Unknown tool: {name}")
            return _rpc_result(msg_id, self.call_tool(name, params.get("arguments") or {}))
        return _rpc_error(msg_id, -32601, f"Method not found: {method}")

    def serve(self, stdin: BinaryIO, stdout: BinaryIO) -> None:
        from textj.transport.framing import LineTooLong, read_line

        while True:
            try:
                line = read_line(stdin, MAX_MESSAGE_BYTES)
            except LineTooLong:
                self._write(stdout, _rpc_error(None, -32600, "Message too large"))
                continue
            if line is None:
                return
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                self._write(stdout, _rpc_error(None, -32700, "Parse error"))
                continue
            response = self.dispatch(message)
            if response is not None:
                self._write(stdout, response)

    @staticmethod
    def _write(stdout: BinaryIO, payload: Mapping[str, Any]) -> None:
        stdout.write(encode_json(payload).encode("utf-8") + b"\n")
        stdout.flush()


def _rpc_result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _rpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def build_parser() -> argparse.ArgumentParser:
    from textj.app.common import add_model_arguments, add_model_store_arguments

    parser = argparse.ArgumentParser(
        prog="textj-mcp",
        description="MCP stdio server exposing TextJ OCR tools (ocr_image, ocr_batch, textj_status).",
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="Forward to a running textj-serve --tcp daemon instead of loading models in-process.",
    )
    parser.add_argument("--state-file", help="Daemon state file for --daemon.")
    parser.add_argument("--config", help="TOML config file (see textj.config); flags override it.")
    add_model_arguments(parser)
    add_model_store_arguments(parser)
    parser.add_argument("--max-inflight", type=int, default=1)
    parser.add_argument("--max-queue", type=int, default=8)
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--log-level", default="WARNING")
    return parser


def main(argv: list[str] | None = None) -> int:
    from textj.app.serve import parse_with_config
    from textj.config import ConfigError

    try:
        args, limits = parse_with_config(build_parser(), argv)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr,
                        format="[textj-mcp] %(levelname)s %(name)s: %(message)s")
    protocol_out = sys.stdout.buffer
    sys.stdout = sys.stderr  # stdout is reserved for JSON-RPC

    runtime = None
    if args.daemon:
        from textj.transport.client import TextJClient

        client = TextJClient.from_state_file(args.state_file)
        handler: Handler = client.request
    else:
        from textj.runtime import RuntimeConfig, TextJRuntime

        runtime = TextJRuntime(RuntimeConfig(
            language=args.language,
            profile=args.profile,
            det_limit_type=args.det_limit_type,
            det_limit_side_len=args.det_limit_side_len,
            max_inflight=args.max_inflight,
            max_queue=args.max_queue,
            warmup=not args.no_warmup,
            model_download="never" if args.offline else "missing",
            model_dir=args.model_dir,
            limits=limits,
        ))
        try:
            runtime.start()
        except TextJError as exc:
            # Keep serving so the agent sees BACKEND_NOT_READY instead of a dead server.
            log.error("runtime failed to start: %s", exc.message)
        handler = runtime.handle

    try:
        MCPServer(handler).serve(sys.stdin.buffer, protocol_out)
    except KeyboardInterrupt:
        return 130
    finally:
        if runtime is not None:
            runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
