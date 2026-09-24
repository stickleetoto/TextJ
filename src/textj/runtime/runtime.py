"""Long-lived TextJ OCR runtime.

The runtime owns the warm OCR backend(s), admission control, the bounded work
queue, timeouts and lifecycle. Every transport (Python API, JSON stdio, local
daemon, MCP) calls :meth:`TextJRuntime.handle` or :meth:`TextJRuntime.submit`
so that OCR behavior cannot drift between interfaces.

Scheduling model
----------------
* ``max_inflight`` worker threads, each owning one backend instance (backends
  are not assumed to be thread-safe).
* At most ``max_inflight + max_queue`` requests are admitted at once. Further
  requests are rejected immediately with ``BUSY`` (retryable).
* Every request has a deadline (``timeout_ms`` or the default). A request
  still queued at its deadline is removed and answered with ``TIMEOUT``.
  A request already executing cannot be interrupted (ONNX inference is not
  cancellable); the caller receives ``TIMEOUT`` and the result is discarded
  when the worker finishes. Its slot stays occupied until then, so overload
  remains bounded.
* ``ocr_batch`` is one admission unit processed sequentially by one worker.
  Items whose turn comes after the deadline are answered with per-item
  ``TIMEOUT``; completed items are still returned.
"""

from __future__ import annotations

import io
import json
import logging
import threading
import time
from collections import deque
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, field
from enum import Enum
from time import perf_counter
from typing import Any, Callable, Mapping

import numpy as np

from textj import __version__
from textj.api.errors import ErrorCode, TextJError
from textj.api.image_loader import load_image
from textj.api.limits import Limits
from textj.api.request import (
    PROTOCOL_VERSION,
    BatchRequest,
    ImageInput,
    OCROptions,
    OCRRequest,
    StatusRequest,
    new_request_id,
    parse_options,
    parse_request,
    peek_request_id,
)
from textj.api.response import (
    encode_json,
    error_envelope,
    ocr_result_payload,
    round_timings,
    success_envelope,
)
from textj.backends.base import OCRBackend
from textj.backends.rapidocr_backend import DEFAULT_PROFILE
from textj.benchmark import percentile

log = logging.getLogger("textj.runtime")

BackendFactory = Callable[[], OCRBackend]


class RuntimeState(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    FAILED = "failed"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    language: str = "korean"
    profile: str = DEFAULT_PROFILE
    det_limit_type: str | None = None
    det_limit_side_len: int | None = None
    max_inflight: int = 1
    max_queue: int = 8
    warmup: bool = True
    # Extra time a caller waits past the deadline for a batch to return the
    # items finished so far.
    batch_grace_ms: int = 2_000
    limits: Limits = field(default_factory=Limits)

    def __post_init__(self) -> None:
        if self.max_inflight < 1:
            raise ValueError("max_inflight must be at least 1")
        if self.max_queue < 0:
            raise ValueError("max_queue cannot be negative")
        if self.batch_grace_ms < 0:
            raise ValueError("batch_grace_ms cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["limits"] = self.limits.to_dict()
        return payload


def rapidocr_factory(config: RuntimeConfig) -> BackendFactory:
    def build() -> OCRBackend:
        from textj.backends.rapidocr_backend import RapidOCRBackend

        # Score filtering happens per request in the runtime, so the engine
        # keeps every recognized line.
        return RapidOCRBackend(
            language=config.language,
            text_score=0.0,
            profile=config.profile,
            det_limit_type=config.det_limit_type,
            det_limit_side_len=config.det_limit_side_len,
        )

    return build


@dataclass(eq=False)
class _Job:
    request: OCRRequest | BatchRequest
    future: Future
    received_at: float
    accepted_at: float
    deadline: float
    parse_ms: float | None


def _warmup_input() -> ImageInput:
    """Encoded PNG with text, so warmup also initializes the decode path."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (192, 48), "white")
    ImageDraw.Draw(image).text((12, 14), "TextJ warmup 123", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return ImageInput.from_bytes(buffer.getvalue())


class TextJRuntime:
    """Resident OCR runtime. Thread-safe; construct once, reuse for all calls."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        backend_factory: BackendFactory | None = None,
    ) -> None:
        self.config = config or RuntimeConfig()
        self._factory = backend_factory or rapidocr_factory(self.config)

        self._cond = threading.Condition()
        self._pending: deque[_Job] = deque()
        self._admitted = 0
        self._inflight = 0
        self._state = RuntimeState.CREATED
        self._failure: str | None = None
        self._workers: list[threading.Thread] = []
        self._backends: list[OCRBackend] = []
        self._started_at: float | None = None
        self._startup: dict[str, float] = {}

        self._counters: dict[str, int] = {
            "requests": 0,
            "ok": 0,
            "errors": 0,
            "busy_rejects": 0,
            "timeouts": 0,
        }
        self._errors_by_code: dict[str, int] = {}
        self._latencies: deque[float] = deque(maxlen=1024)

    # ------------------------------------------------------------------ lifecycle

    @property
    def state(self) -> RuntimeState:
        return self._state

    def start(self) -> "TextJRuntime":
        """Construct and warm every backend, then start workers.

        Raises ``TextJError(BACKEND_NOT_READY)`` when construction or warmup
        fails; the runtime then stays in the ``failed`` state.
        """
        with self._cond:
            if self._state is not RuntimeState.CREATED:
                raise RuntimeError(f"runtime cannot start from state {self._state.value}")
            self._state = RuntimeState.STARTING

        construct_ms: list[float] = []
        warmup_ms: list[float] = []
        try:
            for _ in range(self.config.max_inflight):
                started = perf_counter()
                backend = self._factory()
                construct_ms.append((perf_counter() - started) * 1000.0)
                self._backends.append(backend)
                if self.config.warmup:
                    started = perf_counter()
                    backend.recognize(load_image(_warmup_input(), self.config.limits).array)
                    warmup_ms.append((perf_counter() - started) * 1000.0)
        except Exception as exc:
            log.exception("backend startup failed")
            with self._cond:
                self._state = RuntimeState.FAILED
                self._failure = f"{type(exc).__name__}: {exc}"
            self._close_backends()
            raise TextJError(
                ErrorCode.BACKEND_NOT_READY,
                f"OCR backend failed to start: {exc}",
                retryable=False,
            ) from exc

        self._startup = {
            "backend_construct_ms": round(sum(construct_ms), 3),
        }
        if warmup_ms:
            self._startup["warmup_ms"] = round(sum(warmup_ms), 3)

        # READY must be set before workers start: a worker exits as soon as it
        # sees a non-READY state with an empty queue.
        with self._cond:
            self._state = RuntimeState.READY
            self._started_at = time.monotonic()

        for index, backend in enumerate(self._backends):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(backend,),
                name=f"textj-ocr-{index}",
                daemon=True,
            )
            self._workers.append(worker)
            worker.start()
        return self

    def close(self, timeout: float | None = 10.0) -> None:
        """Stop accepting work, fail queued jobs, wait for running jobs."""
        with self._cond:
            if self._state in (RuntimeState.CLOSING, RuntimeState.CLOSED):
                return
            previous = self._state
            self._state = RuntimeState.CLOSING
            dropped = list(self._pending)
            self._pending.clear()
            self._admitted -= len(dropped)
            self._cond.notify_all()

        shutdown = TextJError(
            ErrorCode.BACKEND_NOT_READY, "runtime is shutting down", retryable=False
        )
        for job in dropped:
            if not job.future.done():
                job.future.set_exception(shutdown)

        deadline = None if timeout is None else time.monotonic() + timeout
        for worker in self._workers:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            worker.join(remaining)

        if previous is not RuntimeState.FAILED:
            self._close_backends()
        with self._cond:
            self._state = RuntimeState.CLOSED

    def _close_backends(self) -> None:
        for backend in self._backends:
            try:
                backend.close()
            except Exception:
                log.exception("backend close failed")

    def __enter__(self) -> "TextJRuntime":
        if self._state is RuntimeState.CREATED:
            self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ entry points

    def handle_json(self, raw: str | bytes) -> str:
        """Protocol entry for text transports: one JSON message in, one out."""
        received = perf_counter()
        size = len(raw.encode("utf-8") if isinstance(raw, str) else raw)
        if size > self.config.limits.max_request_bytes:
            error = TextJError(
                ErrorCode.REQUEST_TOO_LARGE,
                "request exceeds max_request_bytes",
                details={"max_request_bytes": self.config.limits.max_request_bytes},
            )
            self.record_error(error)
            return encode_json(error_envelope(None, error))
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            error = TextJError(ErrorCode.INVALID_REQUEST, f"request is not valid JSON: {exc}")
            self.record_error(error)
            return encode_json(error_envelope(None, error))
        return encode_json(self.handle(payload, received_at=received))

    def handle(self, payload: Any, *, received_at: float | None = None) -> dict[str, Any]:
        """Protocol entry for decoded messages. Never raises."""
        received = received_at if received_at is not None else perf_counter()
        request_id = peek_request_id(payload)
        try:
            request = parse_request(payload, self.config.limits)
        except TextJError as error:
            self.record_error(error)
            return error_envelope(request_id, error)
        except Exception as exc:  # defensive: parsing must never crash a transport
            log.exception("request parsing failed")
            error = TextJError(ErrorCode.INTERNAL_ERROR, f"internal error: {type(exc).__name__}")
            self.record_error(error)
            return error_envelope(request_id, error)

        parse_ms = (perf_counter() - received) * 1000.0
        if isinstance(request, StatusRequest):
            return success_envelope(request.request_id, self.status())
        return self.submit(request, received_at=received, parse_ms=parse_ms)

    def ocr(
        self,
        image: np.ndarray | bytes | str | Any,
        *,
        request_id: str | None = None,
        timeout_ms: int | None = None,
        **options: Any,
    ) -> dict[str, Any]:
        """Python API: OCR an ndarray (BGR/gray/BGRA uint8), encoded bytes, or path.

        Returns the same protocol v1 response envelope as every transport.
        """
        if isinstance(image, np.ndarray):
            image_input = ImageInput.from_array(image)
        elif isinstance(image, (bytes, bytearray, memoryview)):
            image_input = ImageInput.from_bytes(bytes(image))
        else:
            image_input = ImageInput.from_path(image)
        rid = request_id or new_request_id()
        try:
            parsed_options = parse_options(options) if options else OCROptions()
        except TextJError as error:
            self.record_error(error)
            return error_envelope(rid, error)
        request = OCRRequest(
            request_id=rid,
            image=image_input,
            options=parsed_options,
            timeout_ms=timeout_ms,
        )
        return self.submit(request)

    def submit(
        self,
        request: OCRRequest | BatchRequest,
        *,
        received_at: float | None = None,
        parse_ms: float | None = None,
    ) -> dict[str, Any]:
        """Admit, queue and execute a parsed request. Never raises."""
        accepted = perf_counter()
        received = received_at if received_at is not None else accepted
        try:
            self._validate_options(request.options)
            limits = self.config.limits
            timeout_ms = request.timeout_ms or limits.default_timeout_ms
            if not 1 <= timeout_ms <= limits.max_timeout_ms:
                raise TextJError(
                    ErrorCode.INVALID_REQUEST,
                    f"timeout_ms must be between 1 and {limits.max_timeout_ms}",
                    details={"field": "timeout_ms"},
                )
            job = _Job(
                request=request,
                future=Future(),
                received_at=received,
                accepted_at=accepted,
                deadline=received + timeout_ms / 1000.0,
                parse_ms=parse_ms,
            )
            self._admit(job)

            wait = job.deadline - perf_counter()
            if isinstance(request, BatchRequest):
                wait += self.config.batch_grace_ms / 1000.0
            try:
                response = job.future.result(timeout=max(0.0, wait))
            except FutureTimeout:
                self._abandon(job)
                raise TextJError(
                    ErrorCode.TIMEOUT,
                    f"request did not complete within {timeout_ms} ms",
                    details={"timeout_ms": timeout_ms},
                )
        except TextJError as error:
            self.record_error(error)
            return error_envelope(request.request_id, error)
        except Exception as exc:
            log.exception("request execution failed")
            error = TextJError(ErrorCode.INTERNAL_ERROR, f"internal error: {type(exc).__name__}")
            self.record_error(error)
            return error_envelope(request.request_id, error)

        with self._cond:
            self._counters["requests"] += 1
            self._counters["ok"] += 1
            self._latencies.append((perf_counter() - received) * 1000.0)
        return response

    # ------------------------------------------------------------------ status

    def status(self) -> dict[str, Any]:
        with self._cond:
            latencies = list(self._latencies)
            counters = dict(self._counters)
            errors_by_code = dict(sorted(self._errors_by_code.items()))
            state = self._state
            queued = len(self._pending)
            inflight = self._inflight
            started_at = self._started_at

        latency: dict[str, Any] = {"count": len(latencies)}
        if latencies:
            latency.update(
                p50=round(percentile(latencies, 0.5), 3),
                p95=round(percentile(latencies, 0.95), 3),
                max=round(max(latencies), 3),
            )

        backend = self._backends[0].describe() if self._backends else None
        return {
            "state": state.value,
            "ready": state is RuntimeState.READY,
            "protocol_version": PROTOCOL_VERSION,
            "textj_version": __version__,
            "backend": backend,
            "failure": self._failure,
            "uptime_s": (
                round(time.monotonic() - started_at, 3) if started_at is not None else None
            ),
            "startup_ms": dict(self._startup),
            "scheduler": {
                "max_inflight": self.config.max_inflight,
                "max_queue": self.config.max_queue,
                "inflight": inflight,
                "queued": queued,
            },
            "limits": self.config.limits.to_dict(),
            "counters": counters,
            "errors_by_code": errors_by_code,
            "latency_ms": latency,
        }

    # ------------------------------------------------------------------ internals

    def _validate_options(self, options: OCROptions) -> None:
        if options.language is not None and options.language != self.config.language:
            raise TextJError(
                ErrorCode.INVALID_REQUEST,
                f"language {options.language!r} is not loaded in this runtime",
                details={"field": "options.language", "supported": [self.config.language]},
            )

    def _admit(self, job: _Job) -> None:
        with self._cond:
            if self._state is not RuntimeState.READY:
                raise self._not_ready_error()
            capacity = self.config.max_inflight + self.config.max_queue
            if self._admitted >= capacity:
                self._counters["busy_rejects"] += 1
                raise TextJError(
                    ErrorCode.BUSY,
                    "runtime queue is full",
                    details={
                        "max_inflight": self.config.max_inflight,
                        "max_queue": self.config.max_queue,
                    },
                )
            self._admitted += 1
            self._pending.append(job)
            self._cond.notify()

    def _abandon(self, job: _Job) -> None:
        """Caller gave up: drop the job if it is still queued."""
        with self._cond:
            try:
                self._pending.remove(job)
            except ValueError:
                return  # already running; its slot frees when the worker ends
            self._admitted -= 1

    def _not_ready_error(self) -> TextJError:
        state = self._state
        if state in (RuntimeState.CREATED, RuntimeState.STARTING):
            return TextJError(
                ErrorCode.BACKEND_NOT_READY,
                f"runtime is {state.value}",
                retryable=True,
                details={"state": state.value},
            )
        return TextJError(
            ErrorCode.BACKEND_NOT_READY,
            f"runtime is {state.value}",
            retryable=False,
            details={"state": state.value, "failure": self._failure},
        )

    def record_error(self, error: TextJError) -> None:
        with self._cond:
            self._counters["requests"] += 1
            self._counters["errors"] += 1
            if error.code is ErrorCode.TIMEOUT:
                self._counters["timeouts"] += 1
            code = error.code.value
            self._errors_by_code[code] = self._errors_by_code.get(code, 0) + 1

    def _worker_loop(self, backend: OCRBackend) -> None:
        while True:
            with self._cond:
                while not self._pending and self._state is RuntimeState.READY:
                    self._cond.wait()
                if not self._pending:
                    return  # closing and nothing left
                job = self._pending.popleft()
                self._inflight += 1
            try:
                started = perf_counter()
                if started >= job.deadline:
                    raise TextJError(
                        ErrorCode.TIMEOUT,
                        "request timed out while queued",
                        details={"queue_ms": round((started - job.accepted_at) * 1000.0, 3)},
                    )
                if isinstance(job.request, BatchRequest):
                    response = self._run_batch(backend, job, started)
                else:
                    response = self._run_single(backend, job, started)
                if not job.future.done():
                    job.future.set_result(response)
            except TextJError as error:
                if not job.future.done():
                    job.future.set_exception(error)
            except Exception as exc:  # pragma: no cover - defensive
                log.exception("worker failure")
                if not job.future.done():
                    job.future.set_exception(
                        TextJError(ErrorCode.INTERNAL_ERROR, f"internal error: {type(exc).__name__}")
                    )
            finally:
                with self._cond:
                    self._inflight -= 1
                    self._admitted -= 1

    def _recognize(
        self, backend: OCRBackend, image: ImageInput, options: OCROptions
    ) -> tuple[dict[str, Any], dict[str, float]]:
        """Load + OCR + postprocess one image. Returns (result, timings)."""
        timings: dict[str, float] = {}

        started = perf_counter()
        loaded = load_image(image, self.config.limits)
        timings["input"] = (perf_counter() - started) * 1000.0

        started = perf_counter()
        try:
            backend_result = backend.recognize(loaded.array)
        except TextJError:
            raise
        except Exception as exc:
            log.exception("backend recognition failed")
            raise TextJError(
                ErrorCode.OCR_FAILED, f"OCR backend failed: {type(exc).__name__}: {exc}"
            )
        timings["ocr"] = (perf_counter() - started) * 1000.0
        engine_stages = backend_result.metadata.get("engine_stages_ms")
        if isinstance(engine_stages, Mapping):
            for key in ("detect", "recognize"):
                value = engine_stages.get(key)
                if isinstance(value, (int, float)):
                    timings[key] = float(value)

        started = perf_counter()
        lines = tuple(line for line in backend_result.lines if line.score >= options.min_score)
        result = ocr_result_payload(
            lines=lines,
            backend=backend.name,
            image_info=loaded.describe(),
            options=options,
            timings_ms=None,
        )
        timings["postprocess"] = (perf_counter() - started) * 1000.0
        return result, timings

    def _run_single(self, backend: OCRBackend, job: _Job, started: float) -> dict[str, Any]:
        request = job.request
        assert isinstance(request, OCRRequest)
        result, stages = self._recognize(backend, request.image, request.options)
        if request.options.include_timings:
            timings = self._base_timings(job, started)
            timings.update(stages)
            timings["total"] = (perf_counter() - job.received_at) * 1000.0
            result["timings_ms"] = round_timings(timings)
        return success_envelope(request.request_id, result)

    def _run_batch(self, backend: OCRBackend, job: _Job, started: float) -> dict[str, Any]:
        request = job.request
        assert isinstance(request, BatchRequest)
        items: list[dict[str, Any]] = []
        succeeded = 0
        for item in request.items:
            if item.error is not None:
                items.append({"id": item.item_id, "ok": False, "error": item.error.to_dict()})
                continue
            if perf_counter() >= job.deadline:
                error = TextJError(ErrorCode.TIMEOUT, "batch deadline reached before this item")
                items.append({"id": item.item_id, "ok": False, "error": error.to_dict()})
                continue
            assert item.image is not None
            try:
                result, stages = self._recognize(backend, item.image, request.options)
            except TextJError as error:
                items.append({"id": item.item_id, "ok": False, "error": error.to_dict()})
                continue
            if request.options.include_timings:
                result["timings_ms"] = round_timings(stages)
            items.append({"id": item.item_id, "ok": True, "result": result})
            succeeded += 1

        payload: dict[str, Any] = {
            "items": items,
            "item_count": len(items),
            "succeeded": succeeded,
            "failed": len(items) - succeeded,
            "backend": backend.name,
        }
        if request.options.include_timings:
            timings = self._base_timings(job, started)
            timings["total"] = (perf_counter() - job.received_at) * 1000.0
            payload["timings_ms"] = round_timings(timings)
        return success_envelope(request.request_id, payload)

    @staticmethod
    def _base_timings(job: _Job, started: float) -> dict[str, float]:
        timings: dict[str, float] = {}
        if job.parse_ms is not None:
            timings["parse"] = job.parse_ms
        timings["queue"] = (started - job.accepted_at) * 1000.0
        return timings
