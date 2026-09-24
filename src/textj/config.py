"""TOML configuration for long-running TextJ commands.

Example (all keys optional)::

    config_version = 1

    [runtime]
    language = "korean"
    profile = "ppocrv5-mobile"
    det_limit_type = "max"
    det_limit_side_len = 1280
    max_inflight = 1
    max_queue = 8
    warmup = true

    [limits]
    max_request_bytes = 67108864
    max_image_bytes = 33554432
    max_image_pixels = 50000000
    max_image_side = 16384
    max_batch_items = 64
    default_timeout_ms = 30000
    max_timeout_ms = 600000

    [server]
    host = "127.0.0.1"
    port = 47631
    max_connections = 16
    auth = true
    state_file = "C:/Users/me/.textj/daemon.json"

Unknown sections or keys are rejected so typos do not silently fall back to
defaults. Command-line flags override file values.
"""

from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path
from typing import Any, Mapping

from textj.api.limits import Limits

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

CONFIG_VERSION = 1

RUNTIME_KEYS = {
    "language": str,
    "profile": str,
    "det_limit_type": str,
    "det_limit_side_len": int,
    "max_inflight": int,
    "max_queue": int,
    "warmup": bool,
}
SERVER_KEYS = {
    "host": str,
    "port": int,
    "max_connections": int,
    "auth": bool,
    "state_file": str,
}
LIMIT_KEYS = {field.name: int for field in fields(Limits)}


class ConfigError(ValueError):
    pass


def _section(data: Mapping[str, Any], name: str, schema: Mapping[str, type]) -> dict[str, Any]:
    raw = data.get(name, {})
    if not isinstance(raw, Mapping):
        raise ConfigError(f"[{name}] must be a table")
    unknown = sorted(set(raw) - set(schema))
    if unknown:
        raise ConfigError(f"unknown key(s) in [{name}]: {', '.join(unknown)}")
    for key, value in raw.items():
        expected = schema[key]
        # bool is a subclass of int; keep them distinct.
        if expected is int and isinstance(value, bool) or not isinstance(value, expected):
            raise ConfigError(f"[{name}] {key} must be {expected.__name__}")
    return dict(raw)


def load_config(path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse and validate a config file into ``runtime``/``limits``/``server`` dicts."""
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    version = data.get("config_version", CONFIG_VERSION)
    if version != CONFIG_VERSION:
        raise ConfigError(f"unsupported config_version {version!r}; expected {CONFIG_VERSION}")
    unknown = sorted(set(data) - {"config_version", "runtime", "limits", "server"})
    if unknown:
        raise ConfigError(f"unknown top-level key(s): {', '.join(unknown)}")

    config = {
        "runtime": _section(data, "runtime", RUNTIME_KEYS),
        "limits": _section(data, "limits", LIMIT_KEYS),
        "server": _section(data, "server", SERVER_KEYS),
    }
    try:
        Limits(**{**Limits().to_dict(), **config["limits"]})
    except ValueError as exc:
        raise ConfigError(f"[limits] {exc}") from exc
    return config


def parser_defaults(config: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Map config values to argparse destination names."""
    defaults: dict[str, Any] = {}
    runtime = config.get("runtime", {})
    for key, value in runtime.items():
        if key == "warmup":
            defaults["no_warmup"] = not value
        else:
            defaults[key] = value
    server = config.get("server", {})
    for key, value in server.items():
        if key == "auth":
            defaults["no_auth"] = not value
        else:
            defaults[key] = value
    return defaults


def preparse_config(argv: list[str] | None) -> dict[str, dict[str, Any]] | None:
    """Find ``--config PATH`` before full argument parsing."""
    import argparse

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config")
    known, _ = pre.parse_known_args(argv)
    return load_config(known.config) if known.config else None
