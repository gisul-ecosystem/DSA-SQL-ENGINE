"""
Cross-process semaphores for limiting simultaneous Docker operations.

Both use a Redis list as a counting semaphore shared across all worker processes:
- BRPOP to acquire a slot (blocks if none available)
- LPUSH to release a slot

docker_run_semaphore  — gates cold container spinups (docker run -d).
compile_semaphore     — gates compiler invocations (g++, javac, rustc, etc.).
                        Limits concurrent compilers to ~CPU core count so each
                        compile gets meaningful CPU time instead of thrashing.
"""

import logging
import time
from contextlib import asynccontextmanager

from jobqueue.redis_client import get_redis
from config.limits import DOCKER_RUN_CONCURRENCY, COMPILE_CONCURRENCY
from observability import metrics

log = logging.getLogger(__name__)

_RUN_KEY     = "docker_run_semaphore"
_COMPILE_KEY = "compile_semaphore"
_ACQUIRE_TIMEOUT = 120  # seconds

_run_initialized     = False
_compile_initialized = False


def _make_semaphore(key: str, concurrency: int, initialized_flag_name: str):
    """Factory that returns a context-manager using a named Redis semaphore."""

    @asynccontextmanager
    async def _semaphore():
        import sys
        mod = sys.modules[__name__]
        r = get_redis()

        if not getattr(mod, initialized_flag_name):
            if await r.setnx(f"{key}:init", "1"):
                await r.delete(key)
                await r.rpush(key, *["t"] * concurrency)
                log.info("%s: initialized with %d slots", key, concurrency)
            setattr(mod, initialized_flag_name, True)

        started = time.perf_counter()
        result = await r.brpop(key, timeout=_ACQUIRE_TIMEOUT)
        if result is None:
            metrics.semaphore_wait_duration_seconds.labels(key, "timeout").observe(
                time.perf_counter() - started
            )
            raise RuntimeError(f"Timed out waiting for {key} slot after {_ACQUIRE_TIMEOUT}s")
        metrics.semaphore_wait_duration_seconds.labels(key, "success").observe(
            time.perf_counter() - started
        )

        try:
            yield
        finally:
            await r.lpush(key, "t")

    return _semaphore


docker_run_semaphore = _make_semaphore(_RUN_KEY,     DOCKER_RUN_CONCURRENCY, "_run_initialized")
compile_semaphore    = _make_semaphore(_COMPILE_KEY, COMPILE_CONCURRENCY,    "_compile_initialized")
