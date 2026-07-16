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
from .csharp_wrapper import CSHARP_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


def _strip_csharp_preamble(code: str) -> str:
    """Remove using directives and namespace declarations from user-submitted C# code.

    The wrapper already contains all necessary using directives at the top.
    If user code includes its own using/namespace statements and gets injected
    mid-file, the compiler rejects them as invalid at that position.
    """
    import re
    lines = code.splitlines()
    filtered = [
        line for line in lines
        if not re.match(r"^\s*(using\s+[\w.]+\s*;|namespace\s+)", line)
    ]
    return "\n".join(filtered)


class CSharpExecutor(BaseExecutor):
    IMAGE_NAME = "csharp-sandbox:latest"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.project_path = None

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
                "-w", "/app/SandboxApp",
                self.IMAGE_NAME,
            ] + CONTAINER_SLEEP_CMD

            async with docker_run_semaphore():
                proc = await asyncio.create_subprocess_exec(*run_cmd, stdout=PIPE, stderr=PIPE)
                stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeExecutionError("Failed to start execution container")
            self.container_id = stdout.decode().strip()

        self.project_path = os.path.join(self.temp_dir, "SandboxApp")
        os.makedirs(self.project_path, exist_ok=True)

        mkdir_proc = await asyncio.create_subprocess_exec(
            "docker", "exec", self.container_id,
            "mkdir", "-p", "/app/SandboxApp",
            stdout=DEVNULL, stderr=DEVNULL,
        )
        await mkdir_proc.wait()

        program_path = os.path.join(self.project_path, "Program.cs")
        # Strip using/namespace declarations from user code — the wrapper
        # already has them at the top and C# forbids using directives after
        # type declarations.
        cleaned_code = _strip_csharp_preamble(self.code)
        wrapped_code = CSHARP_WRAPPER_TEMPLATE.replace("{source_code}", cleaned_code)
        with open(program_path, "w") as f:
            f.write(wrapped_code)

        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
  </PropertyGroup>
</Project>
"""
        with open(os.path.join(self.project_path, "SandboxApp.csproj"), "w") as f:
            f.write(csproj_content)

        compile_cmd = [
            "docker", "exec", self.container_id,
            "dotnet", "build", "--configuration", "Release", "--nologo",
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
            # dotnet build writes errors to stdout, not stderr
            error_output = stdout.decode().strip() or stderr.decode().strip() or "Compilation failed"
            raise CompileError(error_output)

    async def run(self, test_input: dict):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"function_name": self.function_name, "input": test_input}).encode()
        exec_cmd = [
            "docker", "exec", "-i", self.container_id,
            "dotnet", "/app/SandboxApp/bin/Release/net8.0/SandboxApp.dll",
        ]

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

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)
