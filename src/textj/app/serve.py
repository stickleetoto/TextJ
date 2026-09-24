"""textj-serve: run the resident TextJ runtime behind a machine-facing transport."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading

from textj.api.errors import TextJError
from textj.api.limits import Limits
from textj.app.common import add_model_arguments
from textj.config import ConfigError, parser_defaults, preparse_config
from textj.runtime import RuntimeConfig, TextJRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textj-serve",
        description=(
            "Run a warm TextJ OCR runtime. Protocol v1, newline-delimited JSON. "
            "--stdio: requests on stdin, responses on stdout. "
            "--tcp (default): loopback daemon with token auth."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stdio", action="store_true", help="Serve on stdin/stdout.")
    mode.add_argument("--tcp", action="store_true", help="Serve on loopback TCP (default).")
    parser.add_argument("--config", help="TOML config file (see textj.config); flags override it.")
    add_model_arguments(parser)
    parser.add_argument("--max-inflight", type=int, default=1,
                        help="Concurrent OCR executions; one backend each (default: 1).")
    parser.add_argument("--max-queue", type=int, default=8,
                        help="Requests allowed to wait; beyond this BUSY (default: 8).")
    parser.add_argument("--no-warmup", action="store_true", help="Skip startup warmup inference.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback bind address.")
    parser.add_argument("--port", type=int, default=47631, help="TCP port; 0 picks a free port.")
    parser.add_argument("--state-file", help="Where to write host/port/token (default: ~/.textj/daemon.json).")
    parser.add_argument("--no-auth", action="store_true", help="Do not require auth_token (TCP only).")
    parser.add_argument("--max-connections", type=int, default=16)
    parser.add_argument("--log-level", default="WARNING", help="stderr log level.")
    return parser


def runtime_config(args: argparse.Namespace, limits: Limits | None = None) -> RuntimeConfig:
    return RuntimeConfig(
        language=args.language,
        profile=args.profile,
        det_limit_type=args.det_limit_type,
        det_limit_side_len=args.det_limit_side_len,
        max_inflight=args.max_inflight,
        max_queue=args.max_queue,
        warmup=not args.no_warmup,
        limits=limits or Limits(),
    )


def parse_with_config(
    parser: argparse.ArgumentParser, argv: list[str] | None
) -> tuple[argparse.Namespace, Limits]:
    """Apply ``--config`` values as defaults, then parse flags (flags win)."""
    config = preparse_config(argv)
    limits = Limits()
    if config is not None:
        parser.set_defaults(**parser_defaults(config))
        limits = Limits(**{**Limits().to_dict(), **config["limits"]})
    return parser.parse_args(argv), limits


def main(argv: list[str] | None = None) -> int:
    try:
        args, limits = parse_with_config(build_parser(), argv)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr,
                        format="[textj] %(levelname)s %(name)s: %(message)s")

    # stdout belongs to the protocol in stdio mode: stray prints go to stderr.
    protocol_out = sys.stdout.buffer
    sys.stdout = sys.stderr

    try:
        runtime = TextJRuntime(runtime_config(args, limits))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        runtime.start()
    except TextJError as exc:
        print(f"error: {exc.code.value}: {exc.message}", file=sys.stderr)
        return 1

    try:
        if args.stdio:
            from textj.transport.stdio import serve_stdio

            serve_stdio(runtime, sys.stdin.buffer, protocol_out)
            return 0
        return _serve_tcp(runtime, args)
    except KeyboardInterrupt:
        return 130
    finally:
        runtime.close()


def _serve_tcp(runtime: TextJRuntime, args: argparse.Namespace) -> int:
    from pathlib import Path

    from textj.transport.server import TextJServer, default_state_file, new_token, write_state_file

    token = None if args.no_auth else new_token()
    try:
        server = TextJServer(
            runtime,
            host=args.host,
            port=args.port,
            token=token,
            max_connections=args.max_connections,
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    state_file = Path(args.state_file) if args.state_file else default_state_file()
    write_state_file(state_file, server.state_payload())

    def stop(*_: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    print(
        f"[textj] listening on {server.host}:{server.port} "
        f"(state file: {state_file}, auth: {'on' if token else 'off'})",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        try:
            state_file.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
