"""Safe, local-only test runner for NORYX7 development.

This module deliberately executes a fixed allow-list of repository checks. It does
not accept arbitrary shell commands and is never imported by the production runtime.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from dataclasses import asdict, dataclass

MAX_OUTPUT = 120_000
DEFAULT_TIMEOUT = 900


@dataclass(frozen=True)
class TestResult:
    __test__ = False
    name: str
    command: tuple[str, ...]
    returncode: int
    duration_seconds: float
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True)
class TestReport:
    __test__ = False
    passed: bool
    started_at: int
    duration_seconds: float
    results: tuple[TestResult, ...]

    def to_dict(self) -> dict:
        return {
            "schema": "noryx7/test-lab/v1",
            "passed": self.passed,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "results": [asdict(result) for result in self.results],
        }


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def allowed_commands(root: Path) -> dict[str, tuple[str, ...]]:
    return {
        "compile": (sys.executable, "-m", "compileall", "-q", "core", "ecosystem", "jarvis", "noryx7_runtime"),
        "pytest": (sys.executable, "-m", "pytest", "core", "noryx7_runtime", "ecosystem", "jarvis", "tests", "-q"),
        "closure": (sys.executable, "-c", "from ecosystem.global_closure import require_closed; require_closed()"),
        "completeness": (sys.executable, "-c", "from ecosystem.completeness import require_complete; require_complete()"),
    }


def run_one(root: Path, name: str, command: tuple[str, ...], timeout: int) -> TestResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command), cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout, check=False,
            env={k: v for k, v in os.environ.items() if k not in {"NORYX_PRODUCTION", "NORYX_PROD_KEYS"}},
        )
        output = completed.stdout[-MAX_OUTPUT:]
        return TestResult(name, command, completed.returncode, time.monotonic() - started, output)
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + "\nTIMEOUT").encode() if isinstance(exc.stdout, bytes) else ((exc.stdout or "") + "\nTIMEOUT")
        return TestResult(name, command, 124, time.monotonic() - started, str(output)[-MAX_OUTPUT:])


def run_suite(selected: tuple[str, ...] = ("compile", "closure", "completeness", "pytest"), timeout: int = DEFAULT_TIMEOUT) -> TestReport:
    root = repository_root()
    commands = allowed_commands(root)
    unknown = [name for name in selected if name not in commands]
    if unknown:
        raise ValueError("unknown_test_target:" + ",".join(unknown))
    started_at = int(time.time())
    started = time.monotonic()
    results: list[TestResult] = []
    for name in selected:
        result = run_one(root, name, commands[name], timeout)
        results.append(result)
        if not result.passed:
            break
    return TestReport(all(result.passed for result in results) and len(results) == len(selected), started_at, time.monotonic() - started, tuple(results))


def main() -> int:
    parser = argparse.ArgumentParser(description="NORYX7 local test lab")
    parser.add_argument("--suite", nargs="+", choices=("compile", "closure", "completeness", "pytest"), default=["compile", "closure", "completeness", "pytest"])
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_suite(tuple(args.suite), timeout=max(1, min(args.timeout, 3600)))
    payload = json.dumps(report.to_dict(), indent=2)
    print(payload if args.json else payload)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
