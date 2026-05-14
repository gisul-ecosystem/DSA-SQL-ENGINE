import asyncio
import json
import os
import re
import tempfile
from typing import List, Tuple

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
from .go_wrapper import GO_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class GoExecutor(BaseExecutor):
    IMAGE_NAME = "go-sandbox:latest"

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
                raise RuntimeExecutionError("Failed to start execution container")
            self.container_id = stdout.decode().strip()

        self.file_path = os.path.join(self.temp_dir, "main.go")
        wrapped_code = self._generate_wrapper()
        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

        compile_cmd = [
            "docker", "exec", "-e", "CGO_ENABLED=0", self.container_id,
            "go", "build", "-buildvcs=false", "-o", "main", "main.go",
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
        exec_cmd = ["docker", "exec", "-i", self.container_id, "./main"]

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

    def _generate_wrapper(self) -> str:
        signature = self._parse_signature()
        params = self._parse_params(signature["params"])
        returns = self._parse_returns(signature["returns"])

        param_lines = []
        for param_name, param_type in params:
            if self._is_listnode_type(param_type):
                if self._is_pointer_type(param_type):
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f"    pos_{param_name} := -1",
                            f'    if rawPos_{param_name}, ok := input["pos"]; ok {{',
                            f'        if err := json.Unmarshal(rawPos_{param_name}, &pos_{param_name}); err != nil {{',
                            '            return nil, fmt.Errorf("invalid parameter pos: %w", err)',
                            "        }",
                            "    }",
                            f'    {param_name} := buildLinkedList({param_name}_arr, pos_{param_name})',
                            "",
                        ]
                    )
                else:
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f"    pos_{param_name} := -1",
                            f'    if rawPos_{param_name}, ok := input["pos"]; ok {{',
                            f'        if err := json.Unmarshal(rawPos_{param_name}, &pos_{param_name}); err != nil {{',
                            '            return nil, fmt.Errorf("invalid parameter pos: %w", err)',
                            "        }",
                            "    }",
                            f'    tmp_{param_name} := buildLinkedList({param_name}_arr, pos_{param_name})',
                            f"    var {param_name} ListNode",
                            f"    if tmp_{param_name} != nil {{",
                            f"        {param_name} = *tmp_{param_name}",
                            "    }",
                            "",
                        ]
                    )
            elif self._is_treenode_type(param_type):
                if self._is_pointer_type(param_type):
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []interface{{}}',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    {param_name} := buildTree({param_name}_arr)',
                            "",
                        ]
                    )
                else:
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []interface{{}}',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    tmp_{param_name} := buildTree({param_name}_arr)',
                            f"    var {param_name} TreeNode",
                            f"    if tmp_{param_name} != nil {{",
                            f"        {param_name} = *tmp_{param_name}",
                            "    }",
                            "",
                        ]
                    )
            elif self._is_graph_node_type(param_type):
                if self._is_pointer_type(param_type):
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_adj [][]int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_adj); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    {param_name} := buildGraph({param_name}_adj)',
                            "",
                        ]
                    )
                else:
                    raise CompileError("Go graph node parameters must be pointers")
            else:
                go_type = self._normalize_type(param_type)
                param_lines.extend(
                    [
                        f'    raw_{param_name}, ok := input["{param_name}"]',
                        f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                        f"    var {param_name} {go_type}",
                        f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}); err != nil {{',
                        f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                        "    }",
                        "",
                    ]
                )

        invocation_args = ", ".join(param_name for param_name, _ in params)
        call_lines = self._build_call_lines(invocation_args, returns)

        return (
            GO_WRAPPER_TEMPLATE
            .replace("{source_code}", self.code)
            .replace("__PARAM_BINDINGS_PLACEHOLDER__", "\n".join(param_lines).rstrip())
            .replace("__INVOKER_SETUP_PLACEHOLDER__", "")
            .replace("__CALL_PLACEHOLDER__", call_lines)
            .replace("__FUNCTION_NAME_PLACEHOLDER__", self.function_name)
        )

    def _parse_signature(self) -> dict:
        match = re.search(
            rf"func\s+{re.escape(self.function_name)}\s*\((.*?)\)\s*(\([^\)]*\)|[^\s\{{]+)?\s*\{{",
            self.code,
            re.DOTALL,
        )
        if not match:
            raise CompileError("Could not parse Go function signature")

        return {
            "params": match.group(1).strip(),
            "returns": (match.group(2) or "").strip(),
        }

    def _parse_params(self, params_str: str) -> List[Tuple[str, str]]:
        if not params_str:
            return []

        params: List[Tuple[str, str]] = []
        pending_names: List[str] = []

        for segment in self._split_top_level(params_str):
            parts = segment.split()
            if not parts:
                continue

            if len(parts) == 1:
                pending_names.append(parts[0])
                continue

            param_type = " ".join(parts[1:])
            names = pending_names + [parts[0]]
            pending_names = []
            for param_name in names:
                params.append((param_name, param_type))

        if pending_names:
            raise CompileError(f"Invalid Go parameter syntax: {params_str}")

        return params

    def _parse_returns(self, returns_str: str) -> List[str]:
        if not returns_str:
            return []
        if returns_str.startswith("(") and returns_str.endswith(")"):
            inner = returns_str[1:-1].strip()
            if not inner:
                return []
            return [self._normalize_type(piece) for piece in self._split_top_level(inner)]
        return [self._normalize_type(returns_str)]

    def _split_top_level(self, content: str) -> List[str]:
        segments: List[str] = []
        current: List[str] = []
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0

        for ch in content:
            if ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)
            elif ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth = max(0, brace_depth - 1)

            if ch == "," and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                piece = "".join(current).strip()
                if piece:
                    segments.append(piece)
                current = []
                continue

            current.append(ch)

        tail = "".join(current).strip()
        if tail:
            segments.append(tail)
        return segments

    def _normalize_type(self, type_name: str) -> str:
        return " ".join(type_name.strip().split())

    def _is_pointer_type(self, type_name: str) -> bool:
        return self._normalize_type(type_name).startswith("*")

    def _strip_pointer(self, type_name: str) -> str:
        return self._normalize_type(type_name).lstrip("*").strip()

    def _is_listnode_type(self, type_name: str) -> bool:
        return self._strip_pointer(type_name) == "ListNode"

    def _is_treenode_type(self, type_name: str) -> bool:
        return self._strip_pointer(type_name) == "TreeNode"

    def _is_graph_node_type(self, type_name: str) -> bool:
        return self._strip_pointer(type_name) == "Node"

    def _build_call_lines(self, invocation_args: str, returns: List[str]) -> str:
        if not returns:
            return f"    {self.function_name}({invocation_args})\n    return nil, nil"

        if len(returns) != 1:
            raise CompileError("Multiple Go return values are not supported")

        return (
            f"    result := {self.function_name}({invocation_args})\n"
            "    return autoConvertOutput(result), nil"
        )
