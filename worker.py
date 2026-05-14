"""
Execution worker — pull jobs from Redis and run them.

Usage:
    WORKER_CONCURRENCY=30 python worker.py

Each worker process runs WORKER_CONCURRENCY async slots.  To scale,
run multiple processes (or containers) pointing at the same Redis instance.
Each slot independently BRPOPs from the queue, so there is no central
coordination needed.
"""

import asyncio
import json
import logging
import os
import signal
import time

from prometheus_client import start_http_server

from jobqueue.redis_client import get_redis
from jobqueue.job import (
    JOB_MAX_AGE,
    LANGUAGE_QUEUES,
    mark_done,
    mark_running,
    queue_depths,
    queue_keys_for_languages,
)
from execution.pipeline import ExecutionPipeline
from execution.container_pool import reaper_loop, ensure_pool_target
from config.limits import (
    WORKER_CONCURRENCY as _DEFAULT_CONCURRENCY,
    CPP_PREWARM_TARGET,
)
from observability.logging import configure_logging
from observability import metrics
from observability.tracing import configure_tracing, extract_context, span

configure_logging()
configure_tracing("execution-engine-worker")
log = logging.getLogger(__name__)

WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", str(_DEFAULT_CONCURRENCY)))
WORKER_METRICS_PORT = int(os.getenv("WORKER_METRICS_PORT", "9101"))
WORKER_LANGUAGES = tuple(
    language.strip()
    for language in os.getenv("WORKER_LANGUAGES", ",".join(LANGUAGE_QUEUES)).split(",")
    if language.strip()
)
BRPOP_TIMEOUT = 2   # seconds; short so shutdown is responsive

_shutdown = False


def _on_signal(signum, frame):
    global _shutdown
    log.info(f"Signal {signum} received — finishing in-flight jobs then exiting")
    _shutdown = True


async def _process(job_data: str) -> None:
    try:
        job = json.loads(job_data)
    except Exception:
        metrics.worker_errors_total.labels("decode_job", "malformed_json").inc()
        log.error("Received malformed job JSON, discarding", extra={"error_type": "malformed_json"})
        return

    job_id: str = job.get("job_id", "unknown")
    payload: dict = job.get("payload", {})
    language = metrics.language_from_payload(payload)
    mode = metrics.mode_from_payload(payload)
    age: float = time.time() - job.get("enqueued_at", 0.0)

    if age > JOB_MAX_AGE:
        metrics.worker_job_expired_total.labels(language, mode).inc()
        log.warning(
            "Job expired in queue, skipping",
            extra={
                "job_id": job_id,
                "language": language,
                "mode": mode,
                "queue_wait_seconds": round(age, 3),
            },
        )
        await mark_done(job_id, {
            "verdict": "error",
            "error_message": f"Job expired after {age:.0f}s in queue",
        })
        return

    await mark_running(job_id)
    metrics.worker_queue_wait_seconds.labels(language, mode).observe(age)
    log.info(
        "Job started",
        extra={
            "job_id": job_id,
            "language": language,
            "mode": mode,
            "queue_wait_seconds": round(age, 3),
        },
    )

    started = time.perf_counter()
    verdict = "error"
    context = extract_context(payload)
    try:
        metrics.worker_active_slots.labels(language).inc()
        with span(
            "worker.process_job",
            context=context,
            attributes={"job_id": job_id, "language": language, "mode": mode},
        ):
            pipeline = ExecutionPipeline(payload)
            result = await pipeline.execute()
        await mark_done(job_id, result)
        verdict = result.get("verdict", "completed")
        log.info(
            "Job done",
            extra={
                "job_id": job_id,
                "language": language,
                "mode": mode,
                "verdict": verdict,
                "duration_seconds": round(time.perf_counter() - started, 3),
            },
        )
    except ValueError as e:
        verdict = "error"
        await mark_done(job_id, {"verdict": "error", "error_message": str(e)})
        metrics.worker_errors_total.labels("process_job", type(e).__name__).inc()
        log.warning(
            "Job rejected",
            extra={
                "job_id": job_id,
                "language": language,
                "mode": mode,
                "error_type": type(e).__name__,
            },
        )
    except Exception:
        verdict = "error"
        metrics.worker_errors_total.labels("process_job", "unexpected_exception").inc()
        log.exception(
            "Job unexpected error",
            extra={
                "job_id": job_id,
                "language": language,
                "mode": mode,
                "error_type": "unexpected_exception",
            },
        )
        await mark_done(job_id, {
            "verdict": "error",
            "error_message": "Internal execution error",
        })
    finally:
        elapsed = time.perf_counter() - started
        metrics.worker_active_slots.labels(language).dec()
        metrics.worker_jobs_total.labels(language, mode, verdict).inc()
        metrics.worker_job_duration_seconds.labels(language, mode, verdict).observe(elapsed)


async def _slot(slot_id: int) -> None:
    """
    One async worker slot.  Loops forever pulling one job at a time from Redis
    until the shutdown flag is set and the queue is drained.
    """
    r = get_redis()
    queue_keys = queue_keys_for_languages(WORKER_LANGUAGES)
    log.info("Worker slot ready", extra={"operation": "slot_ready"})

    while not _shutdown:
        try:
            item = await r.brpop(queue_keys, timeout=BRPOP_TIMEOUT)
        except Exception as e:
            metrics.worker_errors_total.labels("brpop", type(e).__name__).inc()
            log.error(
                "Worker Redis error, retrying",
                extra={"operation": "brpop", "error_type": type(e).__name__},
            )
            await asyncio.sleep(1)
            continue

        if item is None:
            # Timeout — loop back and check _shutdown
            continue

        _, job_data = item
        await _process(job_data)

    log.info("Worker slot exited", extra={"operation": "slot_exit"})


async def _queue_depth_reporter() -> None:
    while not _shutdown:
        try:
            depths = await queue_depths()
            for language, depth in depths.items():
                metrics.queue_depth.labels(language).set(depth)
        except Exception as exc:
            metrics.worker_errors_total.labels("queue_depth_reporter", type(exc).__name__).inc()
        await asyncio.sleep(5)


async def _main() -> None:
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    invalid_languages = sorted(set(WORKER_LANGUAGES) - set(LANGUAGE_QUEUES))
    if invalid_languages:
        raise ValueError(f"Unsupported worker languages: {', '.join(invalid_languages)}")

    start_http_server(WORKER_METRICS_PORT)
    log.info(
        "Starting worker",
        extra={"operation": "worker_start"},
    )

    await asyncio.gather(
        reaper_loop(),
        ensure_pool_target("cpp-sandbox:latest", CPP_PREWARM_TARGET),
        _queue_depth_reporter(),
        *[_slot(i) for i in range(WORKER_CONCURRENCY)],
        return_exceptions=True,
    )
    log.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(_main())
