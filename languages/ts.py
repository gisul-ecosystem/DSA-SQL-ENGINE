import asyncio
import tempfile
import os
import json

from execution.base import BaseExecutor
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
)
from execution.sandbox_paths import (
    build_host_temp_dir,
    get_sandbox_roots,
)
from execution import container_pool
from execution.docker_semaphore import docker_run_semaphore, compile_semaphore

from config.limits import (
    EXECUTION_TIMEOUT_SECONDS,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    MAX_STDOUT_BYTES,
    MAX_COMPILE_ERROR_BYTES,
    CONTAINER_SLEEP_CMD,
    TS_CPU_LIMIT,
    TS_COMPILE_TIMEOUT_SECONDS,
)
from .ts_wrapper import TS_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class TypeScriptExecutor(BaseExecutor):
    IMAGE_NAME = "js-sandbox:latest"

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
                "--memory-swap", "1024m",
                "--cpus", TS_CPU_LIMIT,
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
                stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeExecutionError("Failed to start execution container")
            self.container_id = stdout.decode().strip()

        self.file_path = os.path.join(self.temp_dir, "main.ts")
        wrapped_code = TS_WRAPPER_TEMPLATE.replace("{source_code}", self.code)
        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

        compile_cmd = [
            "docker", "exec", self.container_id,
            "tsc", "main.ts",
            "--target", "ES2020",
            "--module", "commonjs",
            "--lib", "ES2020",
            "--skipLibCheck",
        ]

        async with compile_semaphore():
            proc = await asyncio.create_subprocess_exec(*compile_cmd, stdout=PIPE, stderr=PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TS_COMPILE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                await self.cleanup()
                raise CompileError("Compilation timed out")

        if proc.returncode != 0:
            error_message = (stderr.decode() or stdout.decode() or "").strip()
            if len(error_message) > MAX_COMPILE_ERROR_BYTES:
                error_message = error_message[:MAX_COMPILE_ERROR_BYTES]
            await self.cleanup()
            raise CompileError(error_message or "TypeScript compilation failed")

        check_proc = await asyncio.create_subprocess_exec(
            "docker", "exec", self.container_id, "test", "-f", "main.js",
            stdout=DEVNULL, stderr=DEVNULL,
        )
        await check_proc.wait()
        if check_proc.returncode != 0:
            await self.cleanup()
            raise CompileError("Compilation failed: main.js not generated")

    async def run(self, test_input: dict):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"function_name": self.function_name, "input": test_input}).encode()
        exec_cmd = ["docker", "exec", "-i", self.container_id, "node", "main.js"]

        proc = await asyncio.create_subprocess_exec(*exec_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(payload), timeout=EXECUTION_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeExecutionError("Execution timed out")

        stdout_str = stdout.decode()

        if len(stdout_str.encode("utf-8")) > MAX_STDOUT_BYTES:
            raise RuntimeExecutionError("Output limit exceeded")

        if proc.returncode != 0:
            try:
                message = json.loads(stdout_str).get("error", "Runtime error")
            except Exception:
                message = stderr.decode().strip() or "Runtime error"
            raise RuntimeExecutionError(message)

        try:
            return json.loads(stdout_str)["result"]
        except Exception:
            raise RuntimeExecutionError("Invalid output format")

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)
