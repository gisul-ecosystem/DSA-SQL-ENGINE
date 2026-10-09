import asyncio
import tempfile
import os
import json
import re

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
    CPP_COMPILE_OPT_LEVEL,
)
from .cpp_wrapper import CPP_WRAPPER_TEMPLATE
from .c_signature import parse_signature

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class CppExecutor(BaseExecutor):
    IMAGE_NAME = "cpp-sandbox:latest"

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
                try:
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    raise RuntimeExecutionError("Docker daemon timed out and hung while starting the container")

            if proc.returncode != 0:
                raise RuntimeExecutionError("Failed to start C++ container")
            self.container_id = stdout.decode().strip()

        wrapped_code = self._generate_wrapper()
        if "__PLACEHOLDER__" in wrapped_code or "__FUNCTION_" in wrapped_code:
            raise CompileError("Wrapper placeholder replacement failed")

        self.file_path = os.path.join(self.temp_dir, "solution.cpp")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        compile_cmd = [
            "docker", "exec", self.container_id,
            "g++", "solution.cpp", "-pipe", CPP_COMPILE_OPT_LEVEL, "-std=c++20", "-o", "solution",
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
            raise CompileError(stderr.decode())

    async def run(self, test_input: dict):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"keys": list(test_input), "values": list(test_input.values())}).encode()
        exec_cmd = ["docker", "exec", "-i", self.container_id, "./solution"]
        return await run_wrapper(exec_cmd, payload, EXECUTION_TIMEOUT_SECONDS)

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)

    def _generate_wrapper(self):
        sig = parse_signature(self.code, self.function_name)

        bindings = []
        arg_names = []
        for index, param in enumerate(sig.params):
            # Declare a plain value; it binds to `T&`, `const T&` and `T` parameters.
            value_type = re.sub(r"\bconst\b", "", param.type).replace("&", "").strip()
            var = f"_a{index}"
            bindings.append(
                f'{value_type} {var} = judge::Arg<{value_type}>::get(_in.arg("{param.name}", {index}));'
            )
            arg_names.append(var)

        indent = "\n        "
        setup = f"Solution _solution;{indent}" if sig.in_solution_class else ""
        target = "_solution." if sig.in_solution_class else ""
        call = f"{target}{self.function_name}({', '.join(arg_names)})"

        if sig.return_type.strip() == "void":
            # In-place problems return nothing; the judge compares the mutated first argument.
            lines = [f"{setup}{call};", '_output["result"] = nullptr;']
            if arg_names:
                lines.append(f'_output["mutated"] = judge::toJson({arg_names[0]});')
        else:
            lines = [f"{setup}auto _result = {call};", '_output["result"] = judge::toJson(_result);']

        skip_pos = any("ListNode" in p.type for p in sig.params)
        return (
            CPP_WRAPPER_TEMPLATE
            .replace("__USER_CODE_PLACEHOLDER__", self.code)
            .replace("__SKIP_POS_PLACEHOLDER__", "true" if skip_pos else "false")
            .replace("__PARAMETER_DESERIALIZATION_PLACEHOLDER__", indent.join(bindings))
            .replace("__CALL_AND_SERIALIZE_PLACEHOLDER__", indent.join(lines))
        )
