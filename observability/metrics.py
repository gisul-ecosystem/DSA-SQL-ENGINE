import os
import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, multiprocess


SERVICE_NAME = os.getenv("SERVICE_NAME", "execution-engine")

LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
    900.0,
)

COUNT_BUCKETS = (1, 2, 5, 10, 20, 50, 100)


api_requests_total = Counter(
    "execution_engine_api_requests_total",
    "API requests by route, method, and status.",
    ("route", "method", "status_code"),
)
api_request_duration_seconds = Histogram(
    "execution_engine_api_request_duration_seconds",
    "API request latency.",
    ("route", "method"),
    buckets=LATENCY_BUCKETS,
)
api_enqueue_duration_seconds = Histogram(
    "execution_engine_api_enqueue_duration_seconds",
    "Time spent enqueueing jobs.",
    ("language", "mode"),
    buckets=LATENCY_BUCKETS,
)
api_result_wait_duration_seconds = Histogram(
    "execution_engine_api_result_wait_duration_seconds",
    "Time spent waiting for queued job results.",
    ("language", "mode", "outcome"),
    buckets=LATENCY_BUCKETS,
)
api_redis_fallbacks_total = Counter(
    "execution_engine_api_redis_fallbacks_total",
    "Requests that fell back to direct execution because Redis was unavailable.",
    ("language", "mode"),
)
api_queue_rejections_total = Counter(
    "execution_engine_api_queue_rejections_total",
    "Requests rejected because a queue was at capacity.",
    ("language", "mode"),
)
api_direct_executions_total = Counter(
    "execution_engine_api_direct_executions_total",
    "Requests executed directly by the API process.",
    ("language", "mode"),
)
api_direct_inflight = Gauge(
    "execution_engine_api_direct_inflight",
    "Direct API executions currently in flight.",
    ("mode",),
)

queue_depth = Gauge(
    "execution_engine_queue_depth",
    "Redis queue depth by language.",
    ("language",),
)
worker_active_slots = Gauge(
    "execution_engine_worker_active_slots",
    "Worker slots currently processing a job.",
    ("language",),
)
worker_jobs_total = Counter(
    "execution_engine_worker_jobs_total",
    "Jobs completed by workers.",
    ("language", "mode", "verdict"),
)
worker_job_duration_seconds = Histogram(
    "execution_engine_worker_job_duration_seconds",
    "Worker job processing duration.",
    ("language", "mode", "verdict"),
    buckets=LATENCY_BUCKETS,
)
worker_queue_wait_seconds = Histogram(
    "execution_engine_worker_queue_wait_seconds",
    "Time jobs spent waiting in Redis before a worker started them.",
    ("language", "mode"),
    buckets=LATENCY_BUCKETS,
)
worker_job_expired_total = Counter(
    "execution_engine_worker_job_expired_total",
    "Jobs skipped by workers because they exceeded max queue age.",
    ("language", "mode"),
)
worker_errors_total = Counter(
    "execution_engine_worker_errors_total",
    "Worker errors by operation and error type.",
    ("operation", "error_type"),
)

pipeline_compile_duration_seconds = Histogram(
    "execution_engine_pipeline_compile_duration_seconds",
    "Executor compile phase duration.",
    ("language", "outcome"),
    buckets=LATENCY_BUCKETS,
)
pipeline_run_duration_seconds = Histogram(
    "execution_engine_pipeline_run_duration_seconds",
    "Single test case or batch run duration.",
    ("language", "mode", "outcome"),
    buckets=LATENCY_BUCKETS,
)
pipeline_duration_seconds = Histogram(
    "execution_engine_pipeline_duration_seconds",
    "Full pipeline execution duration.",
    ("language", "mode", "verdict"),
    buckets=LATENCY_BUCKETS,
)
pipeline_verdicts_total = Counter(
    "execution_engine_pipeline_verdicts_total",
    "Pipeline verdicts by language and mode.",
    ("language", "mode", "verdict"),
)
pipeline_test_cases = Histogram(
    "execution_engine_pipeline_test_cases",
    "Number of test cases per judged request.",
    ("language",),
    buckets=COUNT_BUCKETS,
)
raw_executions_total = Counter(
    "execution_engine_raw_executions_total",
    "Raw executions by language and exit code.",
    ("language", "exit_code"),
)

docker_pool_events_total = Counter(
    "execution_engine_docker_pool_events_total",
    "Warm pool events by image and event.",
    ("image", "event"),
)
docker_pool_size = Gauge(
    "execution_engine_docker_pool_size",
    "Warm pool list size by image.",
    ("image",),
)
docker_cold_start_duration_seconds = Histogram(
    "execution_engine_docker_cold_start_duration_seconds",
    "Cold docker container start duration.",
    ("image", "operation", "outcome"),
    buckets=LATENCY_BUCKETS,
)
docker_sanitize_duration_seconds = Histogram(
    "execution_engine_docker_sanitize_duration_seconds",
    "Warm container sanitize duration.",
    ("image", "outcome"),
    buckets=LATENCY_BUCKETS,
)
docker_reaper_evictions_total = Counter(
    "execution_engine_docker_reaper_evictions_total",
    "Warm containers evicted by the reaper.",
    ("image",),
)
semaphore_wait_duration_seconds = Histogram(
    "execution_engine_semaphore_wait_duration_seconds",
    "Time spent waiting for Redis-backed semaphore slots.",
    ("semaphore", "outcome"),
    buckets=LATENCY_BUCKETS,
)


def mode_from_payload(payload: dict) -> str:
    return "raw" if payload.get("is_raw") else "judge"


def language_from_payload(payload: dict) -> str:
    return payload.get("language") or "unknown"


def observe_duration(histogram, *labels):
    return _Timer(histogram.labels(*labels))


class _Timer:
    def __init__(self, metric):
        self.metric = metric
        self.started = time.perf_counter()

    def observe(self) -> float:
        elapsed = time.perf_counter() - self.started
        self.metric.observe(elapsed)
        return elapsed


@contextmanager
def inflight(gauge, *labels):
    metric = gauge.labels(*labels)
    metric.inc()
    try:
        yield
    finally:
        metric.dec()


def latest_metrics() -> bytes:
    registry = CollectorRegistry()
    multiproc_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir and os.path.isdir(multiproc_dir):
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest()
