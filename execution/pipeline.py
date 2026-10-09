import os
import shutil
import tempfile
import asyncio
import time

from execution.executor import ExecutorFactory
from execution.exceptions import (
    CompileError,
    ExecutionTimeoutError,
    RuntimeExecutionError,
)
from execution.process import InPlaceResult
from execution.sandbox_paths import build_host_temp_dir, get_sandbox_roots
from config.limits import (
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
)
from observability import metrics
from observability.tracing import span

_LANG_CONFIG = {
    "python":     {"image": "python-sandbox:latest",  "ext": ".py",  "cmd": ["python3", "main.py"]},
    "javascript": {"image": "js-sandbox:latest",      "ext": ".js",  "cmd": ["node", "main.js"]},
    "c":          {"image": "cpp-sandbox:latest",     "ext": ".c",   "cmd": ["sh", "-c", 'gcc -O2 main.c -o main && ./main "$@"', "sh"]},
    "cpp":        {"image": "cpp-sandbox:latest",     "ext": ".cpp", "cmd": ["sh", "-c", 'g++ -O2 main.cpp -o main && ./main "$@"', "sh"]},
    "java":       {"image": "java-sandbox:latest",    "ext": ".java","cmd": ["sh", "-c", 'javac Main.java && java Main "$@"', "sh"]},
    "kotlin":     {"image": "kotlin-sandbox:latest",  "ext": ".kt",  "cmd": ["sh", "-c", 'kotlinc main.kt -include-runtime -d main.jar && java -jar main.jar "$@"', "sh"]},
    "go":         {"image": "go-sandbox:latest",      "ext": ".go",  "cmd": ["sh", "-c", 'go build -o main main.go && ./main "$@"', "sh"]},
    "rust":       {"image": "rust-sandbox:latest",    "ext": ".rs",  "cmd": ["sh", "-c", 'rustc main.rs -o main && ./main "$@"', "sh"]},
    "typescript": {"image": "js-sandbox:latest",      "ext": ".ts",  "cmd": ["sh", "-c", 'tsc main.ts && node main.js "$@"', "sh"]},
    "csharp":     {"image": "csharp-sandbox:latest",  "ext": ".cs",  "cmd": ["sh", "-c", 'echo \'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>disable</Nullable></PropertyGroup></Project>\' > main.csproj && dotnet run -- "$@"', "sh"]},
}


FLOAT_TOLERANCE = 1e-5


def _floats_close(a: float, b: float) -> bool:
    return abs(a - b) <= FLOAT_TOLERANCE * max(1.0, abs(a), abs(b))


def _values_match(actual: object, expected: object) -> bool:
    """Structural comparison used inside lists/objects: exact, floats within tolerance."""
    if actual == expected:
        return True
    if (actual is None and expected == []) or (actual == [] and expected is None):
        return True
    if (
        (isinstance(actual, float) or isinstance(expected, float))
        and isinstance(actual, (int, float)) and isinstance(expected, (int, float))
        and not isinstance(actual, bool) and not isinstance(expected, bool)
    ):
        return _floats_close(float(actual), float(expected))
    if isinstance(actual, list) and isinstance(expected, list) and len(actual) == len(expected):
        return all(_values_match(a, e) for a, e in zip(actual, expected))
    if isinstance(actual, dict) and isinstance(expected, dict) and actual.keys() == expected.keys():
        return all(_values_match(actual[k], expected[k]) for k in actual)
    return False


def _outputs_match(actual: object, expected: object) -> bool:
    """Compare actual vs expected output with type coercion for common edge cases.

    Strict equality is tried first. If that fails we apply these relaxations:

    1. Numeric string / number equivalence: a function that returns the string
       "-1" should match expected_output: -1 (and vice-versa).  This avoids
       penalising users for the return type of string-returning functions when
       the value happens to be numeric.

    2. List-of-one vs scalar: some languages (e.g. Go wrappers) wrap a single
       return value in a list; [42] should equal 42.

    3. Floats match within a relative/absolute tolerance of 1e-5, also inside
       lists and objects (0.1 + 0.2 matches 0.3).

    4. null matches []: an empty tree or linked list is returned as null by
       most languages but written as [] in LeetCode-style expected output.
    """
    if isinstance(actual, InPlaceResult):
        return _outputs_match(actual.value, expected) or _outputs_match(actual.mutated, expected)

    # Exact, floats within tolerance, null vs [] - also inside lists and objects.
    # The looser rules below apply to the top-level value only.
    if _values_match(actual, expected):
        return True

    # Numeric string <-> number
    try:
        if str(actual) == str(expected):
            return True
        if float(str(actual)) == float(str(expected)):
            return True
    except (ValueError, TypeError):
        pass

    # [value] vs value
    if isinstance(actual, list) and len(actual) == 1:
        if _outputs_match(actual[0], expected):
            return True
    if isinstance(expected, list) and len(expected) == 1:
        if _outputs_match(actual, expected[0]):
            return True

    return False


def _reported(actual: object, expected: object) -> object:
    """The value shown to the user: for in-place functions, the mutated argument."""
    if isinstance(actual, InPlaceResult):
        if actual.value is not None or _outputs_match(actual.value, expected):
            return actual.value
        return actual.mutated
    return actual


def _failure(exc: Exception, index: int) -> dict:
    if isinstance(exc, ExecutionTimeoutError):
        return {"verdict": "timeout", "failed_test_case_index": index}
    return {
        "verdict": "runtime_error",
        "failed_test_case_index": index,
        "error_message": str(exc) or "Runtime error",
    }


class ExecutionPipeline:

    def __init__(self, request: dict):
        self.request = request
        self.executor = None
        self.is_raw = request.get("is_raw", False)

    def _apply_in_place(self, result: object) -> object:
        """Drop the mutated-argument result when the caller says the problem is not in place."""
        if isinstance(result, InPlaceResult) and self.request.get("in_place") is False:
            return result.value
        return result

    async def _execute_raw(self) -> dict:
        started = time.perf_counter()
        container_root, host_root = get_sandbox_roots()
        temp_dir = tempfile.mkdtemp(dir=container_root)
        host_temp_dir = build_host_temp_dir(host_root, temp_dir)

        language = self.request["language"]
        source_code = self.request["source_code"]
        args = self.request.get("args", [])
        stdin = self.request.get("stdin", "")

        config = _LANG_CONFIG[language]
        file_name = f"main{config['ext']}"
        if language == "java":
            file_name = "Main.java"

        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, "w") as f:
            f.write(source_code)

        run_cmd = [
            "docker", "run", "-i", "--rm",
            "--memory", DOCKER_MEMORY_LIMIT,
            "--memory-swap", DOCKER_MEMORY_SWAP,
            "--cpus", DOCKER_CPU_LIMIT,
            "--pids-limit", DOCKER_PIDS_LIMIT,
            "--ulimit", f"nofile={DOCKER_NOFILE_LIMIT}:{DOCKER_NOFILE_LIMIT}",
            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-v", f"{host_temp_dir}:/app",
            "-w", "/app",
            config["image"]
        ] + config["cmd"] + args

        try:
            with span("pipeline.raw_execute", attributes={"language": language, "mode": "raw"}):
                proc = await asyncio.create_subprocess_exec(
                    *run_cmd,
                    stdin=asyncio.subprocess.PIPE if stdin else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    input_bytes = stdin.encode('utf-8') if stdin else None
                    stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_bytes), timeout=30)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    metrics.raw_executions_total.labels(language, "124").inc()
                    return {"stdout": "", "stderr": "Execution timed out", "exit_code": 124}

                metrics.raw_executions_total.labels(language, str(proc.returncode)).inc()
                return {
                    "stdout": stdout.decode(errors='replace')[:10000],
                    "stderr": stderr.decode(errors='replace')[:10000],
                    "exit_code": proc.returncode
                }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            metrics.pipeline_duration_seconds.labels(language, "raw", "completed").observe(
                time.perf_counter() - started
            )

    async def execute(self) -> dict:
        if self.is_raw:
            return await self._execute_raw()

        language = self.request["language"]
        started = time.perf_counter()
        verdict = "error"

        def finish(result: dict) -> dict:
            nonlocal verdict
            verdict = result.get("verdict", "error")
            metrics.pipeline_verdicts_total.labels(language, "judge", verdict).inc()
            metrics.pipeline_duration_seconds.labels(language, "judge", verdict).observe(
                time.perf_counter() - started
            )
            return result

        try:
            with span("pipeline.execute", attributes={"language": language, "mode": "judge"}):
                metrics.pipeline_test_cases.labels(language).observe(len(self.request["test_cases"]))
                self.executor = ExecutorFactory.get_executor(
                    language,
                    self.request["source_code"],
                    self.request["function_name"],
                )

                compile_started = time.perf_counter()
                try:
                    with span("pipeline.compile", attributes={"language": language}):
                        await self.executor.compile()
                    metrics.pipeline_compile_duration_seconds.labels(language, "success").observe(
                        time.perf_counter() - compile_started
                    )
                except CompileError as e:
                    metrics.pipeline_compile_duration_seconds.labels(language, "error").observe(
                        time.perf_counter() - compile_started
                    )
                    return finish({
                        "verdict": "compilation_error",
                        "error_message": str(e),
                    })
                except RuntimeExecutionError as e:
                    # The sandbox could not be prepared (container start, Docker
                    # daemon, configuration) - not a problem with the user's code.
                    metrics.pipeline_compile_duration_seconds.labels(language, "error").observe(
                        time.perf_counter() - compile_started
                    )
                    return finish({
                        "verdict": "error",
                        "error_message": f"Execution environment error: {e}",
                    })

                actual_outputs = []
                if hasattr(self.executor, "run_batch"):
                    run_started = time.perf_counter()
                    try:
                        with span("pipeline.run_batch", attributes={"language": language}):
                            actual_outputs = await self.executor.run_batch(self.request["test_cases"])
                        metrics.pipeline_run_duration_seconds.labels(language, "batch", "success").observe(
                            time.perf_counter() - run_started
                        )
                    except Exception as exc:
                        metrics.pipeline_run_duration_seconds.labels(language, "batch", "error").observe(
                            time.perf_counter() - run_started
                        )
                        return finish(_failure(exc, getattr(exc, "failed_test_case_index", None) or 0))

                    if len(actual_outputs) != len(self.request["test_cases"]):
                        return finish({
                            "verdict": "runtime_error",
                            "failed_test_case_index": 0,
                            "error_message": "Invalid batch output format",
                        })

                    actual_outputs = [self._apply_in_place(r) for r in actual_outputs]
                    for index, (result, tc) in enumerate(zip(actual_outputs, self.request["test_cases"])):
                        if not _outputs_match(result, tc["expected_output"]):
                            return finish({
                                "verdict": "wrong_answer",
                                "failed_test_case_index": index,
                                "actual_output": _reported(result, tc["expected_output"]),
                                "expected_output": tc["expected_output"],
                            })
                    actual_outputs = [
                        _reported(result, tc["expected_output"])
                        for result, tc in zip(actual_outputs, self.request["test_cases"])
                    ]
                else:
                    for index, tc in enumerate(self.request["test_cases"]):
                        run_started = time.perf_counter()
                        try:
                            with span(
                                "pipeline.run_test_case",
                                attributes={"language": language, "test_case_index": index},
                            ):
                                result = self._apply_in_place(await self.executor.run(tc["input"]))
                            metrics.pipeline_run_duration_seconds.labels(language, "single", "success").observe(
                                time.perf_counter() - run_started
                            )
                        except Exception as exc:
                            metrics.pipeline_run_duration_seconds.labels(language, "single", "error").observe(
                                time.perf_counter() - run_started
                            )
                            return finish(_failure(exc, index))

                        if not _outputs_match(result, tc["expected_output"]):
                            return finish({
                                "verdict": "wrong_answer",
                                "failed_test_case_index": index,
                                "actual_output": _reported(result, tc["expected_output"]),
                                "expected_output": tc["expected_output"],
                            })
                        actual_outputs.append(_reported(result, tc["expected_output"]))

                return finish({
                    "verdict": "accepted",
                    "actual_outputs": actual_outputs,
                })

        finally:
            if self.executor:
                try:
                    # Run cleanup shielded so that even if the request/worker cancels,
                    # the pool release finishes successfully in the background.
                    await asyncio.shield(self.executor.cleanup())
                except asyncio.CancelledError:
                    pass
