import asyncio
import json
import os
import re
import tempfile

from config.limits import (
    COMPILATION_TIMEOUT_SECONDS,
    CONTAINER_SLEEP_CMD,
    DOCKER_CPU_LIMIT,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_NOFILE_LIMIT,
    DOCKER_PIDS_LIMIT,
    EXECUTION_TIMEOUT_SECONDS,
)
from execution.base import BaseExecutor
from execution.exceptions import CompileError, RuntimeExecutionError
from execution.process import run_wrapper
from execution.sandbox_paths import build_host_temp_dir, get_sandbox_roots
from execution import container_pool
from execution.docker_semaphore import docker_run_semaphore, compile_semaphore

from .rust_wrapper import (
    LIST_NODE_DEFINITION,
    RUST_WRAPPER_TEMPLATE,
    SOLUTION_STRUCT,
    TREE_NODE_DEFINITION,
)

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class RustExecutor(BaseExecutor):
    IMAGE_NAME = "rust-sandbox:latest"
    VENDORED_SOURCE_DIR = "/opt/cache/runner/vendor"
    SHARED_TARGET_DIR = "/opt/cache/runner/target"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None

    async def compile(self):
        container_root, host_root = get_sandbox_roots()

        warm = await container_pool.acquire(self.IMAGE_NAME)
        if warm:
            self.container_id = warm["container_id"]
            self.temp_dir = warm["temp_dir"]
            self.host_temp_dir = warm["host_temp_dir"]
        else:
            self.temp_dir = tempfile.mkdtemp(dir=container_root)
            self.host_temp_dir = build_host_temp_dir(host_root, self.temp_dir)

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
                raise RuntimeExecutionError("Failed to start Rust container")
            self.container_id = stdout.decode().strip()

        wrapped_code = self._generate_wrapper()
        if "__PLACEHOLDER__" in wrapped_code or "__FUNCTION_" in wrapped_code:
            raise CompileError("Wrapper placeholder replacement failed")

        src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        with open(os.path.join(src_dir, "main.rs"), "w") as f:
            f.write(wrapped_code)

        cargo_toml = """
[package]
name = "runner"
version = "0.1.0"
edition = "2021"

[dependencies]
serde_json = "1"
"""
        with open(os.path.join(self.temp_dir, "Cargo.toml"), "w") as f:
            f.write(cargo_toml)

        cargo_config_dir = os.path.join(self.temp_dir, ".cargo")
        os.makedirs(cargo_config_dir, exist_ok=True)
        cargo_config = f"""[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "{self.VENDORED_SOURCE_DIR}"
"""
        with open(os.path.join(cargo_config_dir, "config.toml"), "w") as f:
            f.write(cargo_config)

        compile_cmd = [
            "docker", "exec", self.container_id,
            "cargo", "build", "--release", "--offline",
            "--target-dir", self.SHARED_TARGET_DIR,
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
            raise CompileError(stderr.decode().strip()[:1000])

    async def run(self, test_input: dict):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"keys": list(test_input), "values": list(test_input.values())}).encode()
        exec_cmd = [
            "docker", "exec", "-i", self.container_id,
            f"{self.SHARED_TARGET_DIR}/release/runner",
        ]
        return await run_wrapper(exec_cmd, payload, EXECUTION_TIMEOUT_SECONDS)

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)

    def _generate_wrapper(self):
        return_type, params = self._parse_signature()
        skip_pos = any("ListNode" in t for t, _ in params)

        bindings = []
        call_args = []
        first_mutable = None
        for index, (param_type, param_name) in enumerate(params):
            lines, call_arg, mutable_var = self._build_param_binding(
                self._normalize_type(param_type), index, param_name, skip_pos
            )
            bindings.extend(lines)
            call_args.append(call_arg)
            if index == 0 and mutable_var:
                first_mutable = (mutable_var, self._normalize_type(param_type))

        target = "Solution::" if re.search(r"\bimpl\s+Solution\b", self.code) else ""
        call = f"{target}{self.function_name}({', '.join(call_args)})"

        return_type = self._normalize_type(return_type)
        if return_type in ("", "()"):
            # In-place problems return nothing; the judge compares the mutated first argument.
            mutated = "serde_json::Value::Null"
            if first_mutable:
                mutated = self._to_json(first_mutable[1], f"&{first_mutable[0]}")
            body = [
                f"{call};",
                f'serde_json::json!({{"result": serde_json::Value::Null, "mutated": {mutated}}})',
            ]
        else:
            body = [
                f"let _result = {call};",
                f'serde_json::json!({{"result": {self._to_json(return_type, "&_result")}}})',
            ]

        definitions = []
        if not re.search(r"\bstruct\s+TreeNode\b", self.code):
            definitions.append(TREE_NODE_DEFINITION)
        if not re.search(r"\bstruct\s+ListNode\b", self.code):
            definitions.append(LIST_NODE_DEFINITION)
        has_solution = re.search(r"\bstruct\s+Solution\b", self.code)

        return (
            RUST_WRAPPER_TEMPLATE
            .replace("__SOLUTION_STRUCT_PLACEHOLDER__", "" if has_solution else SOLUTION_STRUCT)
            .replace("__NODE_DEFINITIONS_PLACEHOLDER__", "\n".join(definitions))
            .replace("__PARAMETER_DESERIALIZATION_PLACEHOLDER__", "\n    ".join(bindings))
            .replace("__CALL_AND_SERIALIZE_PLACEHOLDER__", "\n    ".join(body))
            .replace("__USER_CODE_PLACEHOLDER__", self.code)
        )

    def _to_json(self, type_name: str, expr: str) -> str:
        bare = type_name.lstrip("&").replace("mut ", "").strip()
        if "TreeNode" in bare:
            return f"__judge::tree_to_json({expr})"
        if "ListNode" in bare:
            return f"__judge::list_to_json({expr})"
        return f"serde_json::to_value({expr}).unwrap_or(serde_json::Value::Null)"

    def _parse_signature(self):
        pattern = f"fn\\s+{re.escape(self.function_name)}\\s*\\((.*?)\\)\\s*(?:->\\s*([^\\{{]+))?\\s*\\{{"
        match = re.search(pattern, self.code, re.DOTALL)
        if not match:
            raise CompileError("Could not parse Rust function signature")

        params_str = match.group(1).strip()
        return_type = (match.group(2) or "()").strip()
        params = []

        if params_str:
            raw_params = [p.strip() for p in self._split_top_level(params_str)]
            for param in raw_params:
                if ":" not in param:
                    raise CompileError(f"Invalid Rust parameter syntax: {param}")
                name, param_type = param.split(":", 1)
                clean_name = name.strip().replace("mut ", "")
                params.append((param_type.strip(), clean_name))

        return return_type, params

    def _split_top_level(self, content: str):
        segments = []
        current = []
        angle_depth = 0
        paren_depth = 0
        bracket_depth = 0

        for ch in content:
            if ch == "<":
                angle_depth += 1
            elif ch == ">":
                angle_depth = max(0, angle_depth - 1)
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)

            if ch == "," and angle_depth == 0 and paren_depth == 0 and bracket_depth == 0:
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

    def _build_param_binding(self, type_name: str, index: int, param_name: str, skip_pos: bool):
        """Return (binding lines, argument expression, owned variable name if passed by &mut)."""
        var = f"_a{index}"
        value = f'__judge::pick(&payload, "{param_name}", {index}, {"true" if skip_pos else "false"})'

        mutable = type_name.startswith("&mut ")
        borrowed = type_name.startswith("&")
        owned_type = type_name
        if mutable:
            owned_type = self._resolve_owned_reference_target(type_name[5:].strip())
        elif borrowed:
            owned_type = self._resolve_owned_reference_target(type_name[1:].strip())

        if "TreeNode" in owned_type:
            expr = f"__judge::build_tree(&{value})"
        elif "ListNode" in owned_type:
            expr = f"__judge::build_list(&{value})"
        else:
            expr = (
                f"serde_json::from_value::<{owned_type}>({value})"
                f'.unwrap_or_else(|e| panic!("invalid argument {param_name}: {{}}", e))'
            )

        lines = [f"let mut {var}: {owned_type} = {expr};"]
        if mutable:
            return lines, f"&mut {var}", var
        if borrowed:
            return lines, f"&{var}", None
        return lines, var, None

    def _resolve_owned_reference_target(self, borrowed_type: str) -> str:
        inner = borrowed_type.strip()
        if inner == "str":
            return "String"
        if inner.startswith("[") and inner.endswith("]"):
            return f"Vec<{inner[1:-1].strip()}>"
        return inner
