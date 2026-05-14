import asyncio
import logging
import time

import redis.exceptions
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from .schemas import ExecuteRequest, RawExecuteRequest, RawExecuteResponse
from jobqueue.job import enqueue, queue_depths, wait_for_job_result
from execution.pipeline import ExecutionPipeline
from config.limits import (
    FALLBACK_MAX_CONCURRENT,
    QUEUE_RESULT_TIMEOUT_SECONDS,
)
from observability.logging import configure_logging
from observability import metrics
from observability.tracing import inject_context, instrument_fastapi, span

configure_logging()
log = logging.getLogger(__name__)

app = FastAPI(title="Ephemeral Code Execution & Judging API")
instrument_fastapi(app, "execution-engine-api")

_fallback_sem = asyncio.Semaphore(FALLBACK_MAX_CONCURRENT)

_REDIS_ERRORS = (
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
    ConnectionRefusedError,
    OSError,
)


@app.middleware("http")
async def observe_http_requests(request: Request, call_next):
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    method = request.method
    started = time.perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        log.exception(
            "API request failed",
            extra={"route": route_path, "error_type": "unhandled_exception"},
        )
        raise
    finally:
        elapsed = time.perf_counter() - started
        metrics.api_requests_total.labels(route_path, method, status_code).inc()
        metrics.api_request_duration_seconds.labels(route_path, method).observe(elapsed)


async def _wait_for_queued_result(payload: dict):
    language = metrics.language_from_payload(payload)
    mode = metrics.mode_from_payload(payload)
    payload = inject_context(dict(payload))

    try:
        timer = metrics.observe_duration(metrics.api_enqueue_duration_seconds, language, mode)
        with span("queue.enqueue", attributes={"language": language, "mode": mode}):
            job_id = await enqueue(payload)
        timer.observe()
    except OverflowError:
        metrics.api_queue_rejections_total.labels(language, mode).inc()
        raise HTTPException(
            status_code=503,
            detail="Queue at capacity — try again shortly",
            headers={"Retry-After": "5"},
        )
    except _REDIS_ERRORS as exc:
        metrics.api_redis_fallbacks_total.labels(language, mode).inc()
        log.warning(
            "Redis unavailable, falling back to direct execution",
            extra={"language": language, "mode": mode, "error_type": type(exc).__name__},
        )
        return None

    wait_started = time.perf_counter()
    wait_outcome = "success"
    try:
        with span(
            "queue.wait_for_result",
            attributes={"job_id": job_id, "language": language, "mode": mode},
        ):
            result = await wait_for_job_result(job_id, timeout=QUEUE_RESULT_TIMEOUT_SECONDS)
    except _REDIS_ERRORS as exc:
        wait_outcome = "redis_error"
        log.warning(
            "Redis unavailable while waiting for job result",
            extra={
                "job_id": job_id,
                "language": language,
                "mode": mode,
                "error_type": type(exc).__name__,
            },
        )
        metrics.api_result_wait_duration_seconds.labels(language, mode, wait_outcome).observe(
            time.perf_counter() - wait_started
        )
        raise HTTPException(status_code=503, detail="Result store unavailable")

    if result is None:
        wait_outcome = "timeout"
        metrics.api_result_wait_duration_seconds.labels(language, mode, wait_outcome).observe(
            time.perf_counter() - wait_started
        )
        raise HTTPException(status_code=504, detail="Execution timed out")

    metrics.api_result_wait_duration_seconds.labels(language, mode, wait_outcome).observe(
        time.perf_counter() - wait_started
    )
    return JSONResponse(status_code=200, content=result)


async def _execute_direct(req, is_raw: bool = False) -> JSONResponse:
    payload = req.model_dump()
    if is_raw:
        payload["is_raw"] = True
    language = metrics.language_from_payload(payload)
    mode = metrics.mode_from_payload(payload)

    try:
        await asyncio.wait_for(_fallback_sem.acquire(), timeout=30)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Server busy — Redis is unavailable and the fallback queue is full",
            headers={"Retry-After": "10"},
        )

    try:
        metrics.api_direct_executions_total.labels(language, mode).inc()
        with metrics.inflight(metrics.api_direct_inflight, mode):
            with span("api.direct_execute", attributes={"language": language, "mode": mode}):
                pipeline = ExecutionPipeline(payload)
                result = await pipeline.execute()
        return JSONResponse(status_code=200, content=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        _fallback_sem.release()


@app.post("/execute")
async def execute(req: ExecuteRequest):
    response = await _wait_for_queued_result(req.model_dump())
    if response is not None:
        return response
    return await _execute_direct(req)


@app.post("/execute/raw", response_model=RawExecuteResponse)
async def execute_raw(req: RawExecuteRequest):
    payload = req.model_dump()
    payload["is_raw"] = True

    response = await _wait_for_queued_result(payload)
    if response is not None:
        return response
    return await _execute_direct(req, is_raw=True)


@app.get("/health")
async def health():
    try:
        depths = await queue_depths()
        for language, depth in depths.items():
            metrics.queue_depth.labels(language).set(depth)
        return {"ok": True, "redis": "up", "queue_depth": depths["total"], "queue_depths": depths}
    except _REDIS_ERRORS:
        return JSONResponse(
            status_code=200,
            content={"ok": True, "redis": "down", "fallback": "direct execution"},
        )


@app.get("/metrics")
async def prometheus_metrics():
    return Response(
        content=metrics.latest_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
