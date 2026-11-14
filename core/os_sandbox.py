"""Linux OS-backed sandbox runner using Bubblewrap; no unsafe fallback.

The existing core.sandbox module is a control-plane state machine. This module
provides an optional execution boundary that fails closed when Bubblewrap or
required Linux isolation features are unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SandboxLimits:
    cpu_seconds: int = 10
    memory_bytes: int = 256 * 1024 * 1024
    file_size_bytes: int = 8 * 1024 * 1024
    open_files: int = 32
    processes: int = 16
    wall_seconds: int = 15
    output_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        bounds = {
            "cpu_seconds": (1, 300),
            "memory_bytes": (16 * 1024 * 1024, 4 * 1024 * 1024 * 1024),
            "file_size_bytes": (1, 1024 * 1024 * 1024),
            "open_files": (8, 1024),
            "processes": (1, 256),
            "wall_seconds": (1, 600),
            "output_bytes": (1, 16 * 1024 * 1024),
        }
        for name, (minimum, maximum) in bounds.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise ValueError("invalid_sandbox_limit:" + name)


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    output_truncated: bool


class BubblewrapSandboxRunner:
    """Execute one argv vector inside a networkless Linux mount/PID namespace.

    Only the caller-provided workspace is writable. System runtime directories
    are mounted read-only. Host environment variables and file descriptors are
    not inherited. No shell is involved. Bubblewrap is a mandatory dependency:
    absence or namespace failure is an error, never a request to run unsandboxed.
    """

    def __init__(
        self,
        *,
        bwrap_path: str | None = None,
        prlimit_path: str | None = None,
        setpriv_path: str | None = None,
    ) -> None:
        if sys.platform != "linux":
            raise RuntimeError("linux_sandbox_required")

        def resolve_executable(explicit: str | None, command: str, error: str) -> str:
            resolved = explicit or shutil.which(command)
            if not isinstance(resolved, str) or not os.path.isabs(resolved):
                raise RuntimeError(error)
            if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
                raise RuntimeError(error)
            return resolved

        self._bwrap = resolve_executable(bwrap_path, "bwrap", "bubblewrap_not_available")
        self._prlimit = resolve_executable(prlimit_path, "prlimit", "prlimit_not_available")
        self._setpriv = resolve_executable(setpriv_path, "setpriv", "setpriv_not_available")

    @staticmethod
    def _validate_argv(argv: Sequence[str]) -> tuple[str, ...]:
        if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence) or not argv or len(argv) > 128:
            raise ValueError("sandbox_argv_required")
        result = []
        total = 0
        for item in argv:
            if not isinstance(item, str) or not item or "\x00" in item:
                raise ValueError("invalid_sandbox_argument")
            total += len(item.encode("utf-8"))
            if total > 65536:
                raise ValueError("sandbox_argv_too_large")
            result.append(item)
        executable = result[0]
        if not executable.startswith("/") or ".." in Path(executable).parts:
            raise ValueError("sandbox_executable_must_be_absolute")
        return tuple(result)

    @staticmethod
    def _workspace_path(workspace: str | os.PathLike[str]) -> str:
        path = Path(workspace)
        if path.is_symlink():
            raise ValueError("sandbox_workspace_must_not_be_symlink")
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError("sandbox_workspace_must_be_directory")
        return str(resolved)

    def _command(self, argv: tuple[str, ...], workspace: str, limits: SandboxLimits) -> list[str]:
        if not os.path.isdir("/usr"):
            raise RuntimeError("sandbox_runtime_directory_missing")
        command = [
            self._prlimit,
            f"--cpu={limits.cpu_seconds}:{limits.cpu_seconds + 1}",
            f"--as={limits.memory_bytes}:{limits.memory_bytes}",
            f"--fsize={limits.file_size_bytes}:{limits.file_size_bytes}",
            f"--nofile={limits.open_files}:{limits.open_files}",
            "--core=0:0",
            "--",
            self._setpriv,
            "--no-new-privs",
            "--",
            self._bwrap,
            "--die-with-parent",
            "--new-session",
            "--unshare-user",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-ipc",
            "--unshare-uts",
            "--ro-bind", "/usr", "/usr",
        ]
        for source, target in (("/bin", "/bin"), ("/sbin", "/sbin"),
                               ("/lib", "/lib"), ("/lib64", "/lib64")):
            if not os.path.exists(source):
                continue
            if os.path.islink(source):
                link_target = os.readlink(source)
                if link_target.startswith("/"):
                    link_target = link_target.lstrip("/")
                command.extend(("--symlink", link_target, target))
            else:
                command.extend(("--ro-bind", source, target))
        for source in ("/etc/ld.so.cache", "/etc/ssl/certs"):
            if os.path.exists(source):
                command.extend(("--ro-bind", source, source))
        command.extend((
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--dir", "/workspace",
            "--bind", workspace, "/workspace",
            "--chdir", "/workspace",
            "--clearenv",
            "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
            "--setenv", "HOME", "/nonexistent",
            "--setenv", "LANG", "C.UTF-8",
            "--",
            self._prlimit,
            f"--nproc={limits.processes}:{limits.processes}",
            "--",
            *argv,
        ))
        return command

    @staticmethod
    def _read_bounded(stream, limit: int) -> tuple[bytes, bool]:
        stream.seek(0)
        data = stream.read(limit + 1)
        return data[:limit], len(data) > limit

    def run(
        self,
        argv: Sequence[str],
        *,
        workspace: str | os.PathLike[str],
        limits: SandboxLimits = SandboxLimits(),
    ) -> SandboxResult:
        if not isinstance(limits, SandboxLimits):
            raise TypeError("sandbox_limits_required")
        checked_argv = self._validate_argv(argv)
        checked_workspace = self._workspace_path(workspace)
        command = self._command(checked_argv, checked_workspace, limits)

        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    cwd="/",
                    env={"PATH": "/usr/bin:/bin"},
                    close_fds=True,
                    start_new_session=True,
                )
            except OSError as exc:
                raise RuntimeError("sandbox_process_start_failed") from exc

            timed_out = False
            try:
                exit_code = process.wait(timeout=limits.wall_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                exit_code = process.wait()

            stdout, stdout_cut = self._read_bounded(stdout_file, limits.output_bytes)
            stderr, stderr_cut = self._read_bounded(stderr_file, limits.output_bytes)
            return SandboxResult(
                exit_code=int(exit_code),
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
                output_truncated=stdout_cut or stderr_cut,
            )
