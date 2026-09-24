"""TextJ protocol v1: request/response model shared by every transport."""

from textj.api.errors import ErrorCode, TextJError
from textj.api.limits import Limits
from textj.api.request import (
    OPERATIONS,
    PROTOCOL_VERSION,
    BatchItem,
    BatchRequest,
    ImageInput,
    OCROptions,
    OCRRequest,
    StatusRequest,
    parse_request,
)
from textj.api.response import encode_json, error_envelope, success_envelope

__all__ = [
    "OPERATIONS",
    "PROTOCOL_VERSION",
    "BatchItem",
    "BatchRequest",
    "ErrorCode",
    "ImageInput",
    "Limits",
    "OCROptions",
    "OCRRequest",
    "StatusRequest",
    "TextJError",
    "encode_json",
    "error_envelope",
    "parse_request",
    "success_envelope",
]
