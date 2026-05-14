import asyncio
import json
import time
import uuid

from jobqueue.redis_client import get_redis
from observability import metrics

QUEUE_KEY_PREFIX = "exec:queue:"
JOB_PREFIX = "exec:job:"
LANGUAGE_QUEUES = (
    "python",
    "javascript",
    "c",
    "java",
    "kotlin",
    "go",
    "rust",
    "typescript",
    "cpp",
    "csharp",
)

RESULT_TTL = 3600     # seconds — clients have 1 hour to poll before result expires
JOB_MAX_AGE = 300     # seconds — matches API timeout, abandon jobs older than 5 min
MAX_QUEUE_DEPTH = 10_000  # refuse new jobs above this; keeps memory bounded


def queue_key_for_language(language: str) -> str:
    if language not in LANGUAGE_QUEUES:
        raise ValueError("Unsupported language")
    return f"{QUEUE_KEY_PREFIX}{language}"


def queue_keys_for_languages(languages: list[str] | tuple[str, ...] | None = None) -> list[str]:
    selected = languages or LANGUAGE_QUEUES
    return [queue_key_for_language(language) for language in selected]


async def enqueue(payload: dict) -> str:
    r = get_redis()
    queue_key = queue_key_for_language(payload["language"])

    depth = await r.llen(queue_key)
    metrics.queue_depth.labels(payload["language"]).set(depth)
    if depth >= MAX_QUEUE_DEPTH:
        raise OverflowError("Queue at capacity")

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "payload": payload,
        "enqueued_at": time.time(),
    }

    pipe = r.pipeline()
    pipe.lpush(queue_key, json.dumps(job))
    pipe.set(f"{JOB_PREFIX}{job_id}", json.dumps({"status": "queued"}), ex=RESULT_TTL)
    await pipe.execute()
    metrics.queue_depth.labels(payload["language"]).set(depth + 1)

    return job_id


async def mark_running(job_id: str) -> None:
    r = get_redis()
    await r.set(
        f"{JOB_PREFIX}{job_id}",
        json.dumps({"status": "running"}),
        ex=RESULT_TTL,
    )


async def mark_done(job_id: str, result: dict) -> None:
    r = get_redis()
    pipe = r.pipeline()
    pipe.set(
        f"{JOB_PREFIX}{job_id}",
        json.dumps({"status": "done", "result": result}),
        ex=RESULT_TTL,
    )
    pipe.lpush(f"{JOB_PREFIX}result:{job_id}", json.dumps(result))
    pipe.expire(f"{JOB_PREFIX}result:{job_id}", RESULT_TTL)
    await pipe.execute()


async def get_job_status(job_id: str) -> dict | None:
    r = get_redis()
    val = await r.get(f"{JOB_PREFIX}{job_id}")
    if val is None:
        return None
    return json.loads(val)


async def wait_for_job_result(job_id: str, timeout: int) -> dict | None:
    r = get_redis()
    res = await r.blpop(f"{JOB_PREFIX}result:{job_id}", timeout=timeout)
    if not res:
        return None
    _, val = res
    return json.loads(val)


async def queue_depth() -> int:
    r = get_redis()
    depths = await asyncio.gather(
        *(r.llen(key) for key in queue_keys_for_languages()),
    )
    return sum(depths)


async def queue_depths() -> dict[str, int]:
    r = get_redis()
    keys = queue_keys_for_languages()
    depths = await asyncio.gather(*(r.llen(key) for key in keys))
    result = {
        language: depth
        for language, depth in zip(LANGUAGE_QUEUES, depths)
    }
    result["total"] = sum(result.values())
    for language, depth in result.items():
        metrics.queue_depth.labels(language).set(depth)
    return result
