"""
Run a compiled wrapper inside a sandbox container and decode what it printed.

Every language wrapper prints its JSON result between RESULT_START and
RESULT_END, so anything the user's code prints (debug output) is ignored
instead of corrupting the result. The JSON is one of:

    {"result": <value>}                         normal return
    {"result": null, "mutated": <first arg>}    function returned nothing
    {"results": [<value>, ...]}                 batch mode (several test cases)
    {"error": "<message>", "failed_test_case_index": <i>}
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from config.limits import MAX_STDOUT_BYTES
from execution.exceptions import ExecutionTimeoutError, RuntimeExecutionError

PIPE = asyncio.subprocess.PIPE

RESULT_START = "__JUDGE_RESULT_7f3a__"
RESULT_END = "__JUDGE_END_7f3a__"

MAX_ERROR_MESSAGE_CHARS = 1000

# Exit codes of a process killed by a signal, as reported by `docker exec`.
_SIGNAL_MESSAGES = {
    134: "Runtime error: aborted (SIGABRT)",
    136: "Runtime error: floating point exception (SIGFPE)",
    137: "Runtime error: killed (SIGKILL), possibly out of memory",
    139: "Runtime error: segmentation fault (SIGSEGV)",
}


@dataclass
class InPlaceResult:
    """A function that returned nothing; the judge may compare its mutated first argument."""
    value: Any
    mutated: Any


def parse_wrapper_output(stdout: str) -> dict | None:
    """Return the last result block the wrapper printed, or None if there is none."""
    start = stdout.rfind(RESULT_START)
    if start == -1:
        return None
    start += len(RESULT_START)
    end = stdout.find(RESULT_END, start)
    if end == -1:
        return None
    try:
        parsed = json.loads(stdout[start:end])
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_all_wrapper_outputs(stdout: str) -> list[dict]:
    """Return every result block, in order (used by streaming batch wrappers)."""
    blocks = []
    pos = 0
    while True:
        start = stdout.find(RESULT_START, pos)
        if start == -1:
            return blocks
        start += len(RESULT_START)
        end = stdout.find(RESULT_END, start)
        if end == -1:
            return blocks
        try:
            parsed = json.loads(stdout[start:end])
            if isinstance(parsed, dict):
                blocks.append(parsed)
        except ValueError:
            pass
        pos = end + len(RESULT_END)


def _truncate(message: str) -> str:
    message = message.strip()
    if len(message) > MAX_ERROR_MESSAGE_CHARS:
        return message[:MAX_ERROR_MESSAGE_CHARS] + "..."
    return message


def error_message(parsed: dict | None, stderr: str, returncode: int) -> str:
    if parsed and parsed.get("error"):
        return _truncate(str(parsed["error"]))
    if stderr.strip():
        return _truncate(stderr)
    if returncode in _SIGNAL_MESSAGES:
        return _SIGNAL_MESSAGES[returncode]
    if returncode != 0:
        return f"Runtime error (exit code {returncode})"
    return "Invalid output format"


async def run_in_sandbox(cmd: list[str], payload: bytes, timeout: float) -> tuple[str, str, int]:
    """Run `cmd` with `payload` on stdin. Raises on timeout or output overflow."""
    proc = await asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(payload), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise ExecutionTimeoutError()

    if len(stdout) > MAX_STDOUT_BYTES:
        raise RuntimeExecutionError("Output limit exceeded")

    return (
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        proc.returncode,
    )


def result_value(parsed: dict) -> Any:
    if "mutated" in parsed:
        return InPlaceResult(parsed.get("result"), parsed["mutated"])
    return parsed.get("result")


async def run_wrapper(cmd: list[str], payload: bytes, timeout: float) -> Any:
    """Run a single-test-case wrapper and return the function's result."""
    stdout, stderr, returncode = await run_in_sandbox(cmd, payload, timeout)
    parsed = parse_wrapper_output(stdout)
    if returncode != 0 or parsed is None or "error" in parsed or (
        "result" not in parsed and "mutated" not in parsed
    ):
        raise RuntimeExecutionError(error_message(parsed, stderr, returncode))
    return result_value(parsed)


async def run_batch_wrapper(cmd: list[str], payload: bytes, timeout: float, count: int) -> list[Any]:
    """
    Run a batch wrapper that prints one result block per test case as it goes
    ({"index": i, "result": ...}), so a crash part-way through still reports
    which test case failed.
    """
    proc = await asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out_buf, err_buf = bytearray(), bytearray()

    async def _drain(stream, buf):
        while chunk := await stream.read(65536):
            buf.extend(chunk)
            if len(buf) > MAX_STDOUT_BYTES:
                raise RuntimeExecutionError("Output limit exceeded")

    async def _communicate():
        proc.stdin.write(payload)
        await proc.stdin.drain()
        proc.stdin.close()
        await asyncio.gather(_drain(proc.stdout, out_buf), _drain(proc.stderr, err_buf))
        return await proc.wait()

    try:
        returncode = await asyncio.wait_for(_communicate(), timeout=timeout)
    except (asyncio.TimeoutError, RuntimeExecutionError) as exc:
        proc.kill()
        await proc.wait()
        if isinstance(exc, RuntimeExecutionError):
            raise
        # Test cases that already printed a result passed the time limit.
        done = len(parse_all_wrapper_outputs(out_buf.decode("utf-8", errors="replace")))
        raise ExecutionTimeoutError(failed_test_case_index=min(done, count - 1))

    stdout = out_buf.decode("utf-8", errors="replace")
    stderr = err_buf.decode("utf-8", errors="replace")
    blocks = parse_all_wrapper_outputs(stdout)
    results = []
    for block in blocks:
        if "error" in block:
            index = block.get("failed_test_case_index", len(results))
            raise RuntimeExecutionError(error_message(block, stderr, returncode), index)
        results.append(result_value(block))

    if returncode != 0 or len(results) != count:
        raise RuntimeExecutionError(error_message(None, stderr, returncode), len(results))
    return results
