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

# Exit codes of a process killed by a signal, as reported by `podman exec` (same as Docker).
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


def _exec_container(cmd: list[str]) -> str | None:
    """The container id in a `<cli> exec [options] <container> ...` command, else None."""
    if len(cmd) < 3 or cmd[1] != "exec":
        return None
    i = 2
    while i < len(cmd) and cmd[i].startswith("-"):
        # Options that take a separate value (-e VAR=1, -w /dir, -u user).
        i += 2 if cmd[i] in ("-e", "--env", "-w", "--workdir", "-u", "--user") else 1
    return cmd[i] if i < len(cmd) else None


async def _abort(proc: asyncio.subprocess.Process, cmd: list[str]) -> None:
    """
    Stop a run that timed out or flooded its output.

    Killing the `podman exec` client does not stop the program inside the
    container, and the exec session keeps the pipes open, so waiting on the
    client alone can block forever while the program keeps running. Removing
    the container kills everything in it; the pool then discards it on
    release instead of handing a polluted container to the next submission.
    """
    try:
        proc.kill()
    except ProcessLookupError:
        pass
    container_id = _exec_container(cmd)
    if container_id:
        from execution.container_pool import force_remove_cmd

        rm = await asyncio.create_subprocess_exec(
            *force_remove_cmd(cmd[0], container_id),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(rm.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            rm.kill()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pass
    # Close the pipes now rather than leaving them to garbage collection,
    # which can run after the event loop has closed.
    transport = getattr(proc, "_transport", None)
    if transport is not None:
        transport.close()


async def _run_capped(cmd: list[str], payload: bytes, timeout: float) -> tuple[bytes, bytes, int]:
    """
    Run `cmd` with `payload` on stdin, reading stdout/stderr as they arrive.

    Raises ExecutionTimeoutError (with `partial_stdout`) after `timeout` seconds,
    and RuntimeExecutionError once either stream exceeds MAX_STDOUT_BYTES, so a
    print loop is stopped instead of being buffered without bound.
    """
    proc = await asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out_buf, err_buf = bytearray(), bytearray()

    async def _drain(stream, buf):
        while chunk := await stream.read(65536):
            buf.extend(chunk)
            if len(buf) > MAX_STDOUT_BYTES:
                raise RuntimeExecutionError("Output limit exceeded")

    async def _communicate():
        try:
            proc.stdin.write(payload)
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        proc.stdin.close()
        await asyncio.gather(_drain(proc.stdout, out_buf), _drain(proc.stderr, err_buf))
        return await proc.wait()

    try:
        returncode = await asyncio.wait_for(_communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        await _abort(proc, cmd)
        exc = ExecutionTimeoutError()
        exc.partial_stdout = bytes(out_buf)
        raise exc
    except RuntimeExecutionError:
        await _abort(proc, cmd)
        raise
    return bytes(out_buf), bytes(err_buf), returncode


async def run_in_sandbox(cmd: list[str], payload: bytes, timeout: float) -> tuple[str, str, int]:
    """Run `cmd` with `payload` on stdin. Raises on timeout or output overflow."""
    stdout, stderr, returncode = await _run_capped(cmd, payload, timeout)
    return (
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        returncode,
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
    try:
        out, err, returncode = await _run_capped(cmd, payload, timeout)
    except ExecutionTimeoutError as exc:
        # Test cases that already printed a result passed the time limit.
        partial = getattr(exc, "partial_stdout", b"").decode("utf-8", errors="replace")
        done = len(parse_all_wrapper_outputs(partial))
        raise ExecutionTimeoutError(failed_test_case_index=min(done, count - 1))

    stdout = out.decode("utf-8", errors="replace")
    stderr = err.decode("utf-8", errors="replace")
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
