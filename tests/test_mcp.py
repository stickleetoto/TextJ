import io
import json

from conftest import b64, png_bytes
from textj.adapters.mcp_server import TOOLS, MCPServer, tool_request


def rpc(method, params=None, msg_id=1):
    message = {"jsonrpc": "2.0", "method": method}
    if msg_id is not None:
        message["id"] = msg_id
    if params is not None:
        message["params"] = params
    return message


def test_tool_request_mapping() -> None:
    assert tool_request("ocr_image", {"path": "/a.png", "min_score": 0.3, "timeout_ms": 10}) == {
        "protocol_version": "1",
        "timeout_ms": 10,
        "options": {"min_score": 0.3},
        "operation": "ocr",
        "input": {"type": "path", "path": "/a.png"},
    }
    batch = tool_request("ocr_batch", {"items": [{"id": "k", "image_base64": "QQ=="}]})
    assert batch["items"] == [{"input": {"type": "bytes_base64", "data": "QQ=="}, "id": "k"}]
    assert tool_request("textj_status", {}) == {"protocol_version": "1", "operation": "status"}


def test_initialize_list_and_call(make_runtime, png_path) -> None:
    server = MCPServer(make_runtime().handle)
    init = server.dispatch(rpc("initialize", {"protocolVersion": "2025-06-18"}))
    assert init["result"]["protocolVersion"] == "2025-06-18"
    assert init["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert server.dispatch(rpc("notifications/initialized", msg_id=None)) is None

    names = [tool["name"] for tool in server.dispatch(rpc("tools/list"))["result"]["tools"]]
    assert names == ["ocr_image", "ocr_batch", "textj_status"]

    call = server.dispatch(rpc("tools/call", {"name": "ocr_image", "arguments": {"path": str(png_path)}}))
    result = call["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["result"]["text"] == "안녕하세요 TextJ"
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]

    batch = server.dispatch(rpc("tools/call", {"name": "ocr_batch", "arguments": {
        "items": [{"id": "p", "path": str(png_path)}, {"id": "b", "image_base64": b64(png_bytes())}],
    }}))
    assert batch["result"]["structuredContent"]["result"]["succeeded"] == 2

    status = server.dispatch(rpc("tools/call", {"name": "textj_status", "arguments": {}}))
    assert status["result"]["structuredContent"]["result"]["ready"] is True


def test_tool_errors_are_structured(make_runtime) -> None:
    server = MCPServer(make_runtime().handle)
    both = server.dispatch(rpc("tools/call", {"name": "ocr_image", "arguments": {"path": "a", "image_base64": "QQ=="}}))
    assert both["result"]["isError"] is True
    assert both["result"]["structuredContent"]["error"]["code"] == "INVALID_REQUEST"

    missing = server.dispatch(rpc("tools/call", {"name": "ocr_image", "arguments": {"path": "/nope.png"}}))
    assert missing["result"]["structuredContent"]["error"]["code"] == "IMAGE_NOT_FOUND"

    unknown_arg = server.dispatch(rpc("tools/call", {"name": "ocr_image", "arguments": {"path": "a", "x": 1}}))
    assert unknown_arg["result"]["structuredContent"]["error"]["code"] == "INVALID_REQUEST"

    assert server.dispatch(rpc("tools/call", {"name": "nope"}))["error"]["code"] == -32602
    assert server.dispatch(rpc("resources/list"))["error"]["code"] == -32601
    assert server.dispatch([])["error"]["code"] == -32600


def test_unreachable_handler_maps_to_backend_not_ready() -> None:
    def broken(_request):
        raise ConnectionError("daemon down")

    result = MCPServer(broken).call_tool("textj_status", {})
    assert result["isError"] is True
    assert result["structuredContent"]["error"]["code"] == "BACKEND_NOT_READY"


def test_stdio_serve_loop(make_runtime) -> None:
    server = MCPServer(make_runtime().handle)
    stdin = io.BytesIO(b"\n".join([
        json.dumps(rpc("initialize", {"protocolVersion": "1999-01-01"})).encode(),
        json.dumps(rpc("notifications/initialized", msg_id=None)).encode(),
        b"{bad json",
        json.dumps(rpc("ping", msg_id=7)).encode(),
    ]) + b"\n")
    stdout = io.BytesIO()
    server.serve(stdin, stdout)
    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert len(responses) == 3
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"
    assert responses[1]["error"]["code"] == -32700
    assert responses[2] == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_tool_schemas_are_objects() -> None:
    for tool in TOOLS:
        assert tool["inputSchema"]["type"] == "object"
        assert tool["description"]
