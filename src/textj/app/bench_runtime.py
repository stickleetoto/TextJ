"""textj-bench-runtime: measure request-to-response latency through TextJ layers.

Starts one warm TextJRuntime in-process and measures, for the same image:

* ``python_api``   runtime.handle(dict) with a path input
* ``json``         runtime.handle_json(str) with a path input (adds JSON parse/encode)
* ``tcp_path``     loopback daemon round trip with a path input
* ``tcp_bytes``    loopback daemon round trip with a bytes_base64 input
* ``burst``        C concurrent TCP clients x N requests each: throughput,
                   p50/p95 client latency, BUSY/TIMEOUT counts

Latencies are client-observed wall-clock times. Server-side stage timings are
averaged from response ``timings_ms``.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any, Callable

from textj.app.common import add_model_arguments
from textj.benchmark import percentile
from textj.result_io import write_json
from textj.system_info import collect_system_info


def _summary(samples: list[float]) -> dict[str, float]:
    return {
        "count": len(samples),
        "p50": round(percentile(samples, 0.5), 3),
        "p95": round(percentile(samples, 0.95), 3),
        "max": round(max(samples), 3),
        "mean": round(fmean(samples), 3),
    }


def _measure(call: Callable[[], dict[str, Any]], runs: int, warmups: int) -> dict[str, Any]:
    for _ in range(warmups):
        call()
    samples: list[float] = []
    stages: dict[str, list[float]] = {}
    errors = 0
    for _ in range(runs):
        started = perf_counter()
        response = call()
        samples.append((perf_counter() - started) * 1000.0)
        if not response.get("ok"):
            errors += 1
            continue
        for key, value in response["result"].get("timings_ms", {}).items():
            stages.setdefault(key, []).append(value)
    return {
        "latency_ms": _summary(samples),
        "server_stage_mean_ms": {k: round(fmean(v), 3) for k, v in stages.items()},
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="textj-bench-runtime", description=__doc__.split("\n")[0])
    parser.add_argument("image", type=Path)
    add_model_arguments(parser)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--max-inflight", type=int, default=1)
    parser.add_argument("--max-queue", type=int, default=8)
    parser.add_argument("--burst-clients", type=int, default=4)
    parser.add_argument("--burst-requests", type=int, default=5, help="Requests per burst client.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from textj.runtime import RuntimeConfig, TextJRuntime
    from textj.transport.client import TextJClient
    from textj.transport.server import TextJServer

    image = args.image.resolve()
    if not image.is_file():
        print(f"error: image not found: {image}", file=sys.stderr)
        return 1
    data_b64 = base64.b64encode(image.read_bytes()).decode("ascii")

    config = RuntimeConfig(
        language=args.language,
        profile=args.profile,
        det_limit_type=args.det_limit_type,
        det_limit_side_len=args.det_limit_side_len,
        max_inflight=args.max_inflight,
        max_queue=args.max_queue,
    )
    runtime = TextJRuntime(config)
    started = perf_counter()
    runtime.start()
    start_ms = (perf_counter() - started) * 1000.0

    path_request = {
        "protocol_version": "1",
        "operation": "ocr",
        "input": {"type": "path", "path": str(image)},
    }
    bytes_request = {
        "protocol_version": "1",
        "operation": "ocr",
        "input": {"type": "bytes_base64", "data": data_b64},
    }
    path_json = json.dumps(path_request)

    server = TextJServer(runtime, host="127.0.0.1", port=0, token=None,
                         max_connections=args.burst_clients + 2)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()

    results: dict[str, Any] = {}
    try:
        results["python_api"] = _measure(lambda: runtime.handle(path_request), args.runs, args.warmups)
        results["json"] = _measure(lambda: json.loads(runtime.handle_json(path_json)), args.runs, args.warmups)
        with TextJClient("127.0.0.1", server.port) as client:
            results["tcp_path"] = _measure(lambda: client.request(path_request), args.runs, args.warmups)
            results["tcp_bytes"] = _measure(lambda: client.request(bytes_request), args.runs, args.warmups)
        results["burst"] = _burst(server.port, path_request, args.burst_clients, args.burst_requests)
        status = runtime.status()
    finally:
        server.shutdown()
        server.server_close()
        runtime.close()

    payload = {
        "image": str(image),
        "runtime_start_ms": round(start_ms, 3),
        "startup_ms": status["startup_ms"],
        "backend": status["backend"],
        "scheduler": {"max_inflight": config.max_inflight, "max_queue": config.max_queue},
        "runs": args.runs,
        "warmups": args.warmups,
        "results": results,
        "system": collect_system_info(),
    }
    if args.output is not None:
        write_json(args.output, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("TextJ runtime benchmark")
    print(f"  runtime start:      {start_ms:.1f} ms ({status['startup_ms']})")
    for name in ("python_api", "json", "tcp_path", "tcp_bytes"):
        lat = results[name]["latency_ms"]
        print(f"  {name:<18}  p50 {lat['p50']:8.1f}  p95 {lat['p95']:8.1f}  max {lat['max']:8.1f} ms"
              f"  errors {results[name]['errors']}")
    burst = results["burst"]
    print(f"  burst {burst['clients']}x{burst['requests_per_client']}: "
          f"{burst['throughput_rps']:.2f} req/s, ok {burst['ok']}, codes {burst['error_codes']}, "
          f"p50 {burst['latency_ms']['p50']:.1f} p95 {burst['latency_ms']['p95']:.1f} ms")
    return 0


def _burst(port: int, request: dict[str, Any], clients: int, per_client: int) -> dict[str, Any]:
    from textj.transport.client import TextJClient

    lock = threading.Lock()
    samples: list[float] = []
    codes: dict[str, int] = {}
    ok = 0
    barrier = threading.Barrier(clients)

    def worker() -> None:
        nonlocal ok
        with TextJClient("127.0.0.1", port) as client:
            barrier.wait()
            for _ in range(per_client):
                started = perf_counter()
                response = client.request(request)
                elapsed = (perf_counter() - started) * 1000.0
                with lock:
                    samples.append(elapsed)
                    if response.get("ok"):
                        ok += 1
                    else:
                        code = response["error"]["code"]
                        codes[code] = codes.get(code, 0) + 1

    threads = [threading.Thread(target=worker) for _ in range(clients)]
    started = perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    wall = perf_counter() - started
    return {
        "clients": clients,
        "requests_per_client": per_client,
        "ok": ok,
        "error_codes": codes,
        "throughput_rps": round(ok / wall, 3) if wall > 0 else 0.0,
        "latency_ms": _summary(samples),
    }


if __name__ == "__main__":
    raise SystemExit(main())
