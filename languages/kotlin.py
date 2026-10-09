import asyncio
import tempfile
import os
import json

from execution.base import BaseExecutor
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
)
from execution.process import run_wrapper
from execution.sandbox_paths import (
    build_host_temp_dir,
    get_sandbox_roots,
)
from execution import container_pool
from execution.docker_semaphore import docker_run_semaphore, compile_semaphore

from config.limits import (
    EXECUTION_TIMEOUT_SECONDS,
    COMPILATION_TIMEOUT_SECONDS,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    CONTAINER_SLEEP_CMD,
)
from .kotlin_wrapper import KOTLIN_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


def _split_kotlin_imports(code: str) -> tuple[str, str]:
    """Kotlin only allows imports at the top of the file, before the wrapper's code."""
    imports, body = [], []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            imports.append(stripped)
        elif stripped.startswith("package "):
            continue
        else:
            body.append(line)
    return "\n".join(imports), "\n".join(body)


class KotlinExecutor(BaseExecutor):
    IMAGE_NAME = "kotlin-sandbox:latest"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.file_path = None

    async def compile(self):
        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        warm = await container_pool.acquire(self.IMAGE_NAME)
        if warm:
            self.container_id = warm["container_id"]
            self.temp_dir = warm["temp_dir"]
            self.host_temp_dir = warm["host_temp_dir"]
        else:
            self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
            self.host_temp_dir = build_host_temp_dir(host_sandbox_root, self.temp_dir)

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
                "-v", f"{self.host_temp_dir}:/app",
                "-w", "/app",
                self.IMAGE_NAME,
            ] + CONTAINER_SLEEP_CMD

            async with docker_run_semaphore():
                proc = await asyncio.create_subprocess_exec(*run_cmd, stdout=PIPE, stderr=PIPE)
                stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                message = stderr.decode().strip() or "Failed to start execution container"
                raise RuntimeExecutionError(message)
            self.container_id = stdout.decode().strip()

        self.file_path = os.path.join(self.temp_dir, "Main.kt")
        user_imports, body = _split_kotlin_imports(self.code)
        wrapped_code = (
            KOTLIN_WRAPPER_TEMPLATE
            .replace("{user_imports}", user_imports)
            .replace("{source_code}", body)
        )
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        compile_cmd = [
            "docker", "exec", self.container_id,
            "kotlinc", "Main.kt",
            "-cp", "/opt/libs/jackson-core.jar:/opt/libs/jackson-databind.jar:/opt/libs/jackson-annotations.jar",
            "-d", ".",
            "-J-Xms64m", "-J-Xmx256m",
            "-J-XX:+UseSerialGC", "-J-XX:TieredStopAtLevel=1",
        ]

        async with compile_semaphore():
            proc = await asyncio.create_subprocess_exec(*compile_cmd, stdout=PIPE, stderr=PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=COMPILATION_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise CompileError("Compilation timed out")

        if proc.returncode != 0:
            raise CompileError(stderr.decode().strip() or "Compilation failed")

    async def run(self, test_input: dict):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"function_name": self.function_name, "input": test_input}).encode()
        exec_cmd = [
            "docker", "exec", "-i", self.container_id,
            "java", "-Xms16m", "-Xmx256m", "-Xss256m",
            "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1",
            "-cp", ".:/opt/kotlinc/lib/kotlin-stdlib.jar:/opt/libs/jackson-core.jar:/opt/libs/jackson-databind.jar:/opt/libs/jackson-annotations.jar",
            "Main",
        ]
        return await run_wrapper(exec_cmd, payload, EXECUTION_TIMEOUT_SECONDS)

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)
