import os

import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis = aioredis.from_url(
            url,
            decode_responses=True,
            socket_timeout=None,         # no socket-level read timeout — blpop manages its own timeout
            socket_connect_timeout=5,    # fail fast on connection failures, not on long-running commands
        )
    return _redis
