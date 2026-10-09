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
from execution.process import run_wrapper, run_batch_wrapper
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
from .c_signature import parse_signature
from .c_wrapper import C_PRELUDE, C_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL

_SCALAR_TYPES = {
    "int": "int", "long": "long", "long long": "long long", "short": "short",
    "unsigned": "unsigned", "unsigned int": "unsigned int", "unsigned long": "unsigned long",
    "unsigned long long": "unsigned long long", "double": "double", "float": "float",
    "bool": "bool", "_Bool": "bool", "char": "char", "size_t": "size_t",
    "int32_t": "int32_t", "int64_t": "int64_t", "uint32_t": "uint32_t", "uint64_t": "uint64_t",
}
_ARRAY_TYPES = {f"{t}*": t for t in ("int", "long", "long long", "double", "float", "unsigned int", "int64_t")}


def _normalize(type_text: str) -> str:
    t = re.sub(r"\bconst\b", "", type_text)
    t = " ".join(t.split())
    return re.sub(r"\s*\*", "*", t)


class CExecutor(BaseExecutor):
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
                stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeExecutionError("Failed to start container")
            self.container_id = stdout.decode().strip()

        wrapped_code = self._generate_wrapper()

        # The submission is compiled as C (so e.g. `int* r = malloc(...)` works)
        # and linked with the C++ harness that reads JSON and calls it.
        files = {
            "judge_prelude.h": C_PRELUDE,
            "user.c": self.code,
            "solution.cpp": wrapped_code,
        }
        for name, content in files.items():
            with open(os.path.join(self.temp_dir, name), "w", encoding="utf-8") as f:
                f.write(content)
        self.file_path = os.path.join(self.temp_dir, "solution.cpp")

        build = (
            "gcc -std=gnu17 -O2 -include judge_prelude.h -c user.c -o user.o"
            f" && g++ -std=c++20 -pipe {CPP_COMPILE_OPT_LEVEL} solution.cpp user.o -o solution -lm"
        )
        compile_cmd = ["docker", "exec", self.container_id, "sh", "-c", build]

        async with compile_semaphore():
            proc = await asyncio.create_subprocess_exec(*compile_cmd, stdout=PIPE, stderr=PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=COMPILATION_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise CompileError("Compilation timed out")

        if proc.returncode != 0:
            raise CompileError(stderr.decode(errors="replace").strip()[:1000] or "Compilation failed")

    async def run(self, test_input: dict):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"keys": list(test_input), "values": list(test_input.values())}).encode()
        exec_cmd = ["docker", "exec", "-i", self.container_id, "./solution"]
        return await run_wrapper(exec_cmd, payload, EXECUTION_TIMEOUT_SECONDS)

    async def run_batch(self, test_cases: list[dict]):
        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({
            "test_cases": [
                {"keys": list(tc["input"]), "values": list(tc["input"].values())}
                for tc in test_cases
            ],
        }).encode()
        exec_cmd = ["docker", "exec", "-i", self.container_id, "./solution"]
        timeout = max(EXECUTION_TIMEOUT_SECONDS, EXECUTION_TIMEOUT_SECONDS * len(test_cases))
        return await run_batch_wrapper(exec_cmd, payload, timeout, len(test_cases))

    async def cleanup(self):
        if self.container_id:
            cid, td, htd = self.container_id, self.temp_dir, self.host_temp_dir
            self.container_id = None
            self.temp_dir = None
            self.host_temp_dir = None
            await container_pool.release(self.IMAGE_NAME, cid, td, htd)

    # ------------------------------------------------------------------
    # Wrapper generation
    #
    # LeetCode C conventions handled here:
    #   int* nums, int numsSize            array + its length (filled in)
    #   int** grid, int gridSize, int* gridColSize
    #   char* s / char** strs / char** grid (list of strings or char grid)
    #   int* returnSize, int** returnColumnSizes   output sizes
    #   struct ListNode* / struct TreeNode*
    #   void f(...)                        in place: the first argument is compared
    # ------------------------------------------------------------------

    def _generate_wrapper(self):
        sig = parse_signature(self.code, self.function_name)
        return_type = _normalize(sig.return_type)

        bindings: list[str] = []
        call_args: list[str] = []
        sized: dict | None = None      # last array-like argument, for numsSize / gridColSize
        first_input: dict | None = None
        has_return_size = has_return_cols = False
        json_index = 0

        for index, param in enumerate(sig.params):
            t = _normalize(param.type)
            var = f"_a{index}"
            name = param.name

            if t == "int*" and re.search(r"return.*size", name, re.IGNORECASE):
                bindings += ["int _returnSize = 0;", f"int* {var} = &_returnSize;"]
                has_return_size = True
            elif t == "int**" and re.search(r"return.*col", name, re.IGNORECASE):
                bindings += ["int* _returnCols = nullptr;", f"int** {var} = &_returnCols;"]
                has_return_cols = True
            elif t == "int*" and re.search(r"col(umn)?size", name, re.IGNORECASE) and sized and sized.get("cols"):
                bindings.append(f"int* {var} = {sized['cols']}.data();")
            elif t in ("int", "size_t") and re.search(r"size$", name, re.IGNORECASE) and sized:
                bindings.append(f"{t} {var} = {sized['size']};")
            else:
                arg = f'_in.arg("{name}", {json_index})'
                json_index += 1
                info = self._bind_input(t, var, arg, bindings)
                if info is None:
                    raise CompileError(f"Unsupported C parameter type: {param.type} {name}")
                if info.get("size"):
                    sized = info
                if first_input is None:
                    first_input = info

            call_args.append(var)

        call = f"::{self.function_name}({', '.join(call_args)})"
        lines = self._call_and_serialize(return_type, call, first_input, has_return_size, has_return_cols)

        declaration = f"{sig.return_type} {self.function_name}({sig.raw_params or 'void'});"
        indent = "\n    "
        return (
            C_WRAPPER_TEMPLATE
            .replace("__FUNCTION_DECLARATION_PLACEHOLDER__", declaration)
            .replace("__SKIP_POS_PLACEHOLDER__", "true" if any("ListNode" in p.type for p in sig.params) else "false")
            .replace("__PARAMETER_DESERIALIZATION_PLACEHOLDER__", indent.join(bindings))
            .replace("__CALL_AND_SERIALIZE_PLACEHOLDER__", indent.join(lines))
        )

    def _bind_input(self, t: str, var: str, arg: str, bindings: list[str]) -> dict | None:
        """Declare `var` from JSON; return how to size and re-serialize it."""
        if t in _SCALAR_TYPES:
            ctype = _SCALAR_TYPES[t]
            bindings.append(f"{ctype} {var} = judge::Arg<{ctype}>::get({arg});")
            return {"mutated": None}

        if t in _ARRAY_TYPES:
            elem = _ARRAY_TYPES[t]
            bindings += [
                f"vector<{elem}> {var}_v = judge::Arg<vector<{elem}>>::get({arg});",
                f"{elem}* {var} = {var}_v.data();",
            ]
            return {"size": f"(int){var}_v.size()", "mutated": f"json({var}_v)"}

        if t == "char*":
            bindings += [
                f"const json& {var}_j = {arg};",
                f"string {var}_s = judge_c::charsToString({var}_j);",
                f"vector<char> {var}_v({var}_s.begin(), {var}_s.end());",
                f"{var}_v.push_back('\\0');",
                f"char* {var} = {var}_v.data();",
            ]
            mutated = (
                f"({var}_j.is_array() ? judge_c::stringToChars({var}, (int){var}_s.size()) : json(string({var})))"
            )
            return {"size": f"(int){var}_s.size()", "mutated": mutated}

        if t == "char**":
            bindings += [
                f"judge_c::CharRows {var}_rows({arg});",
                f"char** {var} = {var}_rows.ptrs.data();",
            ]
            return {"size": f"(int){var}_rows.rows.size()", "cols": f"{var}_rows.cols", "mutated": f"{var}_rows.toJson()"}

        if t == "int**":
            bindings += [
                f"judge_c::IntRows {var}_rows({arg});",
                f"int** {var} = {var}_rows.ptrs.data();",
            ]
            return {"size": f"(int){var}_rows.rows.size()", "cols": f"{var}_rows.cols", "mutated": f"json({var}_rows.rows)"}

        if t in ("struct ListNode*", "ListNode*"):
            bindings.append(f"ListNode* {var} = judge::Arg<ListNode*>::get({arg});")
            return {"mutated": f"judge::toJson({var})"}

        if t in ("struct TreeNode*", "TreeNode*"):
            bindings.append(f"TreeNode* {var} = judge::Arg<TreeNode*>::get({arg});")
            return {"mutated": f"judge::toJson({var})"}

        return None

    def _call_and_serialize(self, return_type, call, first_input, has_return_size, has_return_cols):
        if return_type == "void":
            # In-place problems return nothing; the judge compares the mutated first argument.
            lines = [f"{call};", '_output["result"] = nullptr;']
            if first_input and first_input.get("mutated"):
                lines.append(f'_output["mutated"] = {first_input["mutated"]};')
            return lines

        lines = [f"auto _result = {call};"]
        if return_type in _SCALAR_TYPES:
            ctype = _SCALAR_TYPES[return_type]
            lines.append(f'_output["result"] = judge::toJson(static_cast<{ctype}>(_result));')
        elif return_type == "char*":
            lines.append('_output["result"] = _result ? json(string(_result)) : json(nullptr);')
        elif return_type in _ARRAY_TYPES:
            elem = _ARRAY_TYPES[return_type]
            size = "_returnSize" if has_return_size else (first_input or {}).get("size", "0")
            lines.append(f'_output["result"] = json(vector<{elem}>(_result, _result + {size}));')
        elif return_type == "char**":
            if not has_return_size:
                raise CompileError("char** return value needs an int* returnSize parameter")
            lines += [
                "json _arr = json::array();",
                "for (int _i = 0; _i < _returnSize; ++_i) _arr.push_back(string(_result[_i]));",
                '_output["result"] = _arr;',
            ]
        elif return_type == "int**":
            if not (has_return_size and has_return_cols):
                raise CompileError("int** return value needs returnSize and returnColumnSizes parameters")
            lines += [
                "json _arr = json::array();",
                "for (int _i = 0; _i < _returnSize; ++_i)",
                "    _arr.push_back(vector<int>(_result[_i], _result[_i] + _returnCols[_i]));",
                '_output["result"] = _arr;',
            ]
        elif return_type in ("struct ListNode*", "ListNode*", "struct TreeNode*", "TreeNode*"):
            lines.append('_output["result"] = judge::toJson(_result);')
        else:
            raise CompileError(f"Unsupported C return type: {return_type}")
        return lines
