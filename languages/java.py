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
    COMPILATION_TIMEOUT_SECONDS,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    MAX_STDOUT_BYTES,
    CONTAINER_SLEEP_CMD,
)
from .java_wrapper import JAVA_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


def _strip_java_preamble(code: str) -> str:
    """Normalise user-submitted Java code for injection into the wrapper (Main.java).

    Three transformations applied in order:

    1. Drop import / package declarations — the wrapper already has all needed
       imports and they cannot appear after class declarations in the same file.

    2. Demote 'public class Solution' → 'class Solution' — only one public
       top-level class is allowed per file and it must match the filename
       (Main.java).

    3. Wrap bare methods — if the code has no class declaration at all (user
       submitted just a method body) wrap it in 'class Solution { ... }' so
       javac doesn't treat it as an unnamed class (preview feature, disabled
       by default on JDK 21).
    """
    import re
    lines = code.splitlines()
    filtered = []
    for line in lines:
        # Drop import / package lines
        if re.match(r"^\s*(import|package)\s+", line):
            continue
        # Demote 'public class Solution' -> 'class Solution'
        line = re.sub(r"\bpublic\s+(class\s+Solution\b)", r"\1", line)
        filtered.append(line)

    result = "\n".join(filtered)

    # If there is no class declaration, wrap the whole thing in Solution{}
    if not re.search(r"\bclass\s+\w+", result):
        result = "class Solution {\n" + result + "\n}"

    return result

class JavaBatchRuntimeError(RuntimeExecutionError):
    def __init__(self, message: str, failed_test_case_index: int | None = None):
        super().__init__(message)
        self.failed_test_case_index = failed_test_case_index


class JavaExecutor(BaseExecutor):
    IMAGE_NAME = "java-sandbox:latest"

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
                stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeExecutionError("Failed to start execution container")
            self.container_id = stdout.decode().strip()

        self.file_path = os.path.join(self.temp_dir, "Main.java")
        # Strip any import/package statements from user code — the wrapper
        # already imports everything needed, and Java forbids imports after
        # class/type declarations.
        cleaned_code = _strip_java_preamble(self.code)
        wrapped_code = JAVA_WRAPPER_TEMPLATE.replace("{source_code}", cleaned_code)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        compile_cmd = [
            "docker", "exec", self.container_id,
            "javac", "-cp", ".:/opt/libs/*", "Main.java",
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
        exec_cmd = self._java_exec_cmd()

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
                message = stderr.decode() or "Runtime error"
            raise RuntimeExecutionError(message)

        try:
            return json.loads(stdout_str)["result"]
        except Exception:
            raise RuntimeExecutionError("Invalid output format")

    async def run_batch(self, test_cases: list[dict]):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({
            "function_name": self.function_name,
            "test_cases": [{"input": tc["input"]} for tc in test_cases],
        }).encode()
        exec_cmd = self._java_exec_cmd()

        proc = await asyncio.create_subprocess_exec(*exec_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        timeout = max(EXECUTION_TIMEOUT_SECONDS, EXECUTION_TIMEOUT_SECONDS * len(test_cases))
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(payload), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise JavaBatchRuntimeError("Execution timed out", 0)

        stdout_str = stdout.decode()

        if len(stdout_str.encode("utf-8")) > MAX_STDOUT_BYTES:
            raise RuntimeExecutionError("Output limit exceeded")

        if proc.returncode != 0:
            try:
                response = json.loads(stdout_str)
                message = response.get("error", "Runtime error")
                failed_index = response.get("failed_test_case_index")
            except Exception:
                message = stderr.decode() or "Runtime error"
                failed_index = None
            raise JavaBatchRuntimeError(message, failed_index)

        try:
            return json.loads(stdout_str)["results"]
        except Exception:
            raise RuntimeExecutionError("Invalid output format")

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)

    def _java_exec_cmd(self):
        return [
            "docker", "exec", "-i", self.container_id,
            "java",
            "-Xms16m", "-Xmx256m",
            "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1",
            "-cp", ".:/opt/libs/*",
            "Main",
        ]
