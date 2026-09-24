"""Resident TextJ runtime: warm backend, bounded scheduling, lifecycle."""

from textj.runtime.runtime import (
    BackendFactory,
    RuntimeConfig,
    RuntimeState,
    TextJRuntime,
    rapidocr_factory,
)

__all__ = [
    "BackendFactory",
    "RuntimeConfig",
    "RuntimeState",
    "TextJRuntime",
    "rapidocr_factory",
]
