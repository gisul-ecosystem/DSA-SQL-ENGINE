"""
Run every pattern in tests/patterns.py through the real ExecutionPipeline.

Needs Redis, Docker and the sandbox images, the same as a worker. Example
(Docker Desktop on Windows, from the repo root):

    docker run --rm --network judgetest \
      -v //var/run/docker.sock:/var/run/docker.sock \
      -v C:/judge-sandbox:/sandbox -v "$PWD":/app \
      -e REDIS_URL=redis://judge-redis:6379/0 \
      -e HOST_SANDBOX_ROOT=/run/desktop/mnt/host/c/judge-sandbox \
      -e EXECUTION_TIMEOUT_SECONDS=4 \
      judge-local python tests/run_patterns.py [--lang cpp,go] [--pattern two_sum]

Exits non-zero when any case does not get the expected verdict.
"""

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.pipeline import ExecutionPipeline  # noqa: E402
from tests.patterns import LANGUAGES, PATTERNS  # noqa: E402


def _function_name(function: dict, language: str) -> str:
    return function.get(language) or function["default"]


async def _run_case(sem, name: str, spec: dict, language: str) -> dict:
    request = {
        "language": language,
        "source_code": spec["code"][language],
        "function_name": _function_name(spec["function"], language),
        "test_cases": spec["tests"],
    }
    async with sem:
        started = time.perf_counter()
        try:
            result = await ExecutionPipeline(request).execute()
        except Exception as exc:  # the pipeline itself should never raise
            result = {"verdict": "pipeline_exception", "error_message": repr(exc)}
        elapsed = time.perf_counter() - started

    expected = spec["expect"] if isinstance(spec["expect"], tuple) else (spec["expect"],)
    ok = result.get("verdict") in expected
    if ok and spec["failed_index"] is not None:
        ok = result.get("failed_test_case_index") == spec["failed_index"]
    return {
        "pattern": name,
        "language": language,
        "ok": ok,
        "expected": spec["expect"],
        "result": result,
        "seconds": round(elapsed, 2),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default=",".join(LANGUAGES))
    parser.add_argument("--pattern", default="")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--json", default="", help="write full results to this file")
    args = parser.parse_args()

    languages = [l for l in args.lang.split(",") if l]
    patterns = [p for p in args.pattern.split(",") if p] or list(PATTERNS)

    sem = asyncio.Semaphore(args.concurrency)
    jobs = [
        _run_case(sem, name, PATTERNS[name], language)
        for name in patterns
        for language in languages
        if language in PATTERNS[name]["code"]
    ]
    results = await asyncio.gather(*jobs)

    by_key = {(r["pattern"], r["language"]): r for r in results}
    width = max(len(p) for p in patterns) + 2
    print("pattern".ljust(width) + "".join(l[:6].ljust(7) for l in languages))
    for name in patterns:
        row = name.ljust(width)
        for language in languages:
            r = by_key.get((name, language))
            row += ("-" if r is None else "ok" if r["ok"] else "FAIL").ljust(7)
        print(row)

    failures = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(failures)}/{len(results)} passed")
    for r in failures:
        detail = dict(r["result"])
        if "error_message" in detail:
            detail["error_message"] = str(detail["error_message"])[:300]
        print(f"\n[{r['pattern']} / {r['language']}] expected {r['expected']}, got:")
        print("  " + json.dumps(detail)[:600])

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
