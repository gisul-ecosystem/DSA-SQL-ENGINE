import os


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _str_env(name: str, default: str) -> str:
    return os.getenv(name, default)


# Time limits (seconds)
EXECUTION_TIMEOUT_SECONDS = _int_env("EXECUTION_TIMEOUT_SECONDS", 10)

# Compilation timeouts (seconds)
COMPILATION_TIMEOUT_SECONDS = _int_env("COMPILATION_TIMEOUT_SECONDS", 120)
TS_COMPILE_TIMEOUT_SECONDS = _int_env("TS_COMPILE_TIMEOUT_SECONDS", 30)

# How long the API waits for a queued job result before returning 504.
QUEUE_RESULT_TIMEOUT_SECONDS = _int_env("QUEUE_RESULT_TIMEOUT_SECONDS", 900)

# Docker resource limits
DOCKER_MEMORY_LIMIT = _str_env("DOCKER_MEMORY_LIMIT", "1024m")
DOCKER_MEMORY_SWAP = _str_env("DOCKER_MEMORY_SWAP", "1024m")
DOCKER_CPU_LIMIT = _str_env("DOCKER_CPU_LIMIT", "2")
DOCKER_PIDS_LIMIT = _str_env("DOCKER_PIDS_LIMIT", "1536")
DOCKER_NOFILE_LIMIT = _str_env("DOCKER_NOFILE_LIMIT", "65535")

TS_CPU_LIMIT = _str_env("TS_CPU_LIMIT", "2")
CPP_COMPILE_OPT_LEVEL = _str_env("CPP_COMPILE_OPT_LEVEL", "-O0")

# Output limits
MAX_STDOUT_BYTES = _int_env("MAX_STDOUT_BYTES", 1_000_000)
MAX_COMPILE_ERROR_BYTES = _int_env("MAX_COMPILE_ERROR_BYTES", 1000)

# Container behavior
CONTAINER_SLEEP_CMD = ["sleep", os.getenv("CONTAINER_SLEEP_SECONDS", "infinity")]

# Worker concurrency — slots per worker process
WORKER_CONCURRENCY = _int_env("WORKER_CONCURRENCY", 30)

# Fallback concurrency used when Redis is unavailable.
FALLBACK_MAX_CONCURRENT = _int_env("FALLBACK_MAX_CONCURRENT", 20)

# Warm container pool
WARM_CONTAINER_TTL_SECONDS = _int_env("WARM_CONTAINER_TTL_SECONDS", 60)
WARM_POOL_MAX_PER_IMAGE = _int_env("WARM_POOL_MAX_PER_IMAGE", 50)
CPP_PREWARM_TARGET = _int_env("CPP_PREWARM_TARGET", 1)

# Max simultaneous docker run calls across all worker slots.
DOCKER_RUN_CONCURRENCY = _int_env("DOCKER_RUN_CONCURRENCY", 20)

# Max simultaneous compiler invocations (g++, javac, rustc, etc.) across all worker slots.
# Keeping this at ~CPU core count prevents compilation CPU contention under burst load.
COMPILE_CONCURRENCY = _int_env("COMPILE_CONCURRENCY", 8)
