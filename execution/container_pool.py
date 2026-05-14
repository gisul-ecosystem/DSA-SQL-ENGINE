"""
Redis-backed warm container pool.

After a job finishes, instead of killing the container it is sanitized
(stray processes killed, /app wiped) and pushed into a per-image list in
Redis.  The next job for the same image pops it atomically and skips the
docker-run spinup cost entirely.

A background reaper task runs every 30 s and kills containers that have
been idle longer than WARM_CONTAINER_TTL_SECONDS.
"""

import asyncio
import json
import logging
import shutil
import tempfile
import time

from jobqueue.redis_client import get_redis
from jobqueue.job import queue_depth
from config.limits import (
    WARM_CONTAINER_TTL_SECONDS,
    WARM_POOL_MAX_PER_IMAGE,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    CONTAINER_SLEEP_CMD,
)
from execution.docker_semaphore import docker_run_semaphore
from execution.sandbox_paths import build_host_temp_dir, get_sandbox_roots
from observability import metrics
from observability.tracing import span

log = logging.getLogger(__name__)

POOL_KEY_PREFIX = "warm_pool:"   # warm_pool:<image_name>
DEVNULL = asyncio.subprocess.DEVNULL
PIPE = asyncio.subprocess.PIPE
_PREWARM_SPECS = {
    "cpp-sandbox:latest":    {"workdir": "/app"},
    "python-sandbox:latest": {"workdir": "/app"},
    "js-sandbox:latest":     {"workdir": "/app"},
    "java-sandbox:latest":   {"workdir": "/app"},
    "kotlin-sandbox:latest": {"workdir": "/app"},
    "go-sandbox:latest":     {"workdir": "/app"},
    "rust-sandbox:latest":   {"workdir": "/app"},
    "csharp-sandbox:latest": {"workdir": "/app"},
}

# Atomically push an entry only if the list is below the cap.
# Returns 1 if pushed, 0 if the pool was already at capacity.
_LUA_CAPPED_PUSH = """
local current = redis.call('LLEN', KEYS[1])
if current >= tonumber(ARGV[1]) then
    return 0
end
redis.call('LPUSH', KEYS[1], ARGV[2])
return 1
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pool_key(image: str) -> str:
    return f"{POOL_KEY_PREFIX}{image}"


async def _docker_is_running(container_id: str) -> bool:
    """Quick liveness check — ~10 ms."""
    proc = await asyncio.create_subprocess_exec(
        "docker", "inspect", "--format", "{{.State.Running}}", container_id,
        stdout=PIPE, stderr=DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() == "true"


async def _sanitize(container_id: str) -> bool:
    """
    Kill all user processes inside the container and wipe /app in a single
    docker exec round-trip. Returns False if the container is no longer alive.
    Uses /proc to find PIDs — works on all Linux-based sandbox images.
    """
    proc = await asyncio.create_subprocess_exec(
        "docker", "exec", container_id,
        "sh", "-c",
        "for pid in $(ls /proc | grep -E '^[0-9]+$'); do [ $pid -gt 1 ] && kill -9 $pid 2>/dev/null; done; rm -rf /app/* /app/.[!.]* 2>/dev/null; true",
        stdout=DEVNULL, stderr=DEVNULL,
    )
    await proc.wait()
    return await _docker_is_running(container_id)


async def _kill_container(container_id: str, temp_dir: str | None = None) -> None:
    proc = await asyncio.create_subprocess_exec(
        "docker", "rm", "-f", container_id,
        stdout=DEVNULL, stderr=DEVNULL,
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=15.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def acquire(image: str) -> dict | None:
    """
    Pop a warm container for *image* from Redis.
    Returns a dict with keys: container_id, temp_dir, host_temp_dir
    or None if no warm container is available.

    Stale / dead containers are discarded automatically.
    """
    r = get_redis()
    key = _pool_key(image)

    while True:
        with span("docker_pool.acquire", attributes={"image": image}):
            raw = await r.rpop(key)
        if raw is None:
            metrics.docker_pool_events_total.labels(image, "miss").inc()
            metrics.docker_pool_size.labels(image).set(0)
            return None  # pool empty

        entry = json.loads(raw)

        # Discard if TTL already exceeded (reaper may not have run yet)
        age = time.time() - entry["born_at"]
        if age > WARM_CONTAINER_TTL_SECONDS:
            metrics.docker_pool_events_total.labels(image, "stale_discard").inc()
            asyncio.create_task(_kill_container(entry["container_id"], entry.get("temp_dir")))
            continue

        # Liveness check
        if not await _docker_is_running(entry["container_id"]):
            metrics.docker_pool_events_total.labels(image, "dead_discard").inc()
            if entry.get("temp_dir"):
                shutil.rmtree(entry["temp_dir"], ignore_errors=True)
            continue

        # Containers are sanitized before they are pushed into the pool.
        # Avoid repeating that expensive cleanup on every acquire.
        metrics.docker_pool_events_total.labels(image, "hit").inc()
        log.debug("pool hit image=%s container=%s", image, entry["container_id"][:12])
        return entry


async def release(image: str, container_id: str, temp_dir: str, host_temp_dir: str) -> None:
    """
    Return a container to the pool after a job finishes.
    Sanitizes first; if the container is dead it is discarded instead.
    """
    sanitize_started = time.perf_counter()
    alive = await _sanitize(container_id)
    sanitize_outcome = "success" if alive else "dead"
    metrics.docker_sanitize_duration_seconds.labels(image, sanitize_outcome).observe(
        time.perf_counter() - sanitize_started
    )
    if not alive:
        metrics.docker_pool_events_total.labels(image, "release_dead").inc()
        shutil.rmtree(temp_dir, ignore_errors=True)
        return

    r = get_redis()
    key = _pool_key(image)
    entry = json.dumps({
        "container_id": container_id,
        "temp_dir": temp_dir,
        "host_temp_dir": host_temp_dir,
        "born_at": time.time(),
    })
    # Atomically cap pool size and push — prevents exceeding max under concurrency.
    pushed = await r.eval(_LUA_CAPPED_PUSH, 1, key, WARM_POOL_MAX_PER_IMAGE, entry)
    if not pushed:
        metrics.docker_pool_events_total.labels(image, "release_pool_full").inc()
        asyncio.create_task(_kill_container(container_id, temp_dir))
        return
    metrics.docker_pool_events_total.labels(image, "release").inc()
    metrics.docker_pool_size.labels(image).set(await r.llen(key))
    log.debug("pool release image=%s container=%s", image, container_id[:12])


async def ensure_pool_target(image: str, target: int) -> None:
    """
    Best-effort startup prewarm. One process per image takes a Redis lock and
    tops the pool up to the requested target.
    """
    if target <= 0:
        return

    spec = _PREWARM_SPECS.get(image)
    if not spec:
        log.warning("prewarm skipped for image=%s: no spec configured", image)
        return

    r = get_redis()
    key = _pool_key(image)
    lock_key = f"{key}:prewarm_lock"
    lock_value = str(time.time())

    got_lock = await r.set(lock_key, lock_value, ex=900, nx=True)
    if not got_lock:
        log.info("prewarm skipped for image=%s: another worker owns the lock", image)
        return

    try:
        container_sandbox_root, host_sandbox_root = get_sandbox_roots()
        workdir = spec["workdir"]
        current = await r.llen(key)

        if current >= target:
            log.info("prewarm not needed for image=%s current=%d target=%d", image, current, target)
            return

        log.info("prewarming image=%s current=%d target=%d", image, current, target)

        while current < target:
            queued = await queue_depth()
            if queued > 0:
                await asyncio.sleep(1)
                current = await r.llen(key)
                continue

            temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
            host_temp_dir = build_host_temp_dir(host_sandbox_root, temp_dir)
            run_cmd = [
                "docker", "run",
                "-d", "--rm",
                "--memory", DOCKER_MEMORY_LIMIT,
                "--memory-swap", DOCKER_MEMORY_SWAP,
                "--cpus", DOCKER_CPU_LIMIT,
                "--pids-limit", DOCKER_PIDS_LIMIT,
                "--ulimit", f"nofile={DOCKER_NOFILE_LIMIT}:{DOCKER_NOFILE_LIMIT}",
                "--network", "none",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "-v", f"{host_temp_dir}:/app",
                "-w", workdir,
                image,
            ] + CONTAINER_SLEEP_CMD

            try:
                async with docker_run_semaphore():
                    started = time.perf_counter()
                    proc = await asyncio.create_subprocess_exec(*run_cmd, stdout=PIPE, stderr=PIPE)
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            except Exception:
                metrics.docker_cold_start_duration_seconds.labels(image, "prewarm", "error").observe(
                    time.perf_counter() - started if "started" in locals() else 0
                )
                shutil.rmtree(temp_dir, ignore_errors=True)
                log.exception("prewarm failed while starting image=%s", image)
                break

            if proc.returncode != 0:
                metrics.docker_cold_start_duration_seconds.labels(image, "prewarm", "error").observe(
                    time.perf_counter() - started
                )
                shutil.rmtree(temp_dir, ignore_errors=True)
                log.error(
                    "prewarm failed image=%s rc=%s stderr=%s",
                    image,
                    proc.returncode,
                    stderr.decode(errors="replace").strip(),
                )
                break

            container_id = stdout.decode().strip()
            metrics.docker_cold_start_duration_seconds.labels(image, "prewarm", "success").observe(
                time.perf_counter() - started
            )
            # Push directly — no need to sanitize a freshly started container.
            entry = json.dumps({
                "container_id": container_id,
                "temp_dir": temp_dir,
                "host_temp_dir": host_temp_dir,
                "born_at": time.time(),
            })
            pushed = await r.eval(_LUA_CAPPED_PUSH, 1, key, WARM_POOL_MAX_PER_IMAGE, entry)
            if not pushed:
                metrics.docker_pool_events_total.labels(image, "prewarm_pool_full").inc()
                asyncio.create_task(_kill_container(container_id, temp_dir))
            else:
                metrics.docker_pool_events_total.labels(image, "prewarm").inc()
            current = await r.llen(key)
            metrics.docker_pool_size.labels(image).set(current)

        log.info("prewarm complete image=%s final_pool_size=%d target=%d", image, current, target)
    finally:
        current_lock_value = await r.get(lock_key)
        if current_lock_value == lock_value:
            await r.delete(lock_key)


# ---------------------------------------------------------------------------
# Reaper — run as a background task in worker.py
# ---------------------------------------------------------------------------

async def reaper_loop() -> None:
    """
    Periodically scan all warm pool keys and evict containers that have
    exceeded WARM_CONTAINER_TTL_SECONDS.  Runs forever.
    """
    log.info("Container pool reaper started (TTL=%ds)", WARM_CONTAINER_TTL_SECONDS)
    while True:
        await asyncio.sleep(30)
        try:
            await _reap_once()
        except Exception:
            log.exception("Reaper error (will retry)")


async def _reap_once() -> None:
    r = get_redis()
    now = time.time()

    async for key in r.scan_iter(f"{POOL_KEY_PREFIX}*"):
        # Snapshot the list — we'll rebuild it without expired entries
        raw_entries = await r.lrange(key, 0, -1)
        if not raw_entries:
            continue

        keep = []
        for raw in raw_entries:
            entry = json.loads(raw)
            age = now - entry["born_at"]
            if age > WARM_CONTAINER_TTL_SECONDS:
                image = key.removeprefix(POOL_KEY_PREFIX)
                metrics.docker_reaper_evictions_total.labels(image).inc()
                metrics.docker_pool_events_total.labels(image, "reaper_evict").inc()
                log.debug("reaper evicting container=%s age=%.0fs", entry["container_id"][:12], age)
                asyncio.create_task(_kill_container(entry["container_id"], entry.get("temp_dir")))
            else:
                keep.append(raw)

        # Atomically replace the list with only the live entries
        pipe = r.pipeline()
        pipe.delete(key)
        if keep:
            pipe.rpush(key, *keep)
        await pipe.execute()
        image = key.removeprefix(POOL_KEY_PREFIX)
        metrics.docker_pool_size.labels(image).set(len(keep))
