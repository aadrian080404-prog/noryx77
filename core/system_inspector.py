"""Non-executing Python source inspector for authorized system review.

The inspector parses bounded source files into ASTs; it never imports or runs
the inspected program. Findings are review leads, not exploitability claims.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import os
from pathlib import Path
import stat

from .elf_inspector import ELFInspectionReport, ELF_MAGIC, inspect_elf_bytes

MAX_FILES = 5000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 20000
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}


@dataclass(frozen=True, order=True)
class InspectionFinding:
    path: str
    line: int
    rule_id: str
    severity: str
    evidence: str


@dataclass(frozen=True)
class InspectionReport:
    files_scanned: int
    bytes_scanned: int
    findings: tuple[InspectionFinding, ...]
    parse_errors: tuple[str, ...]
    binary_reports: tuple[ELFInspectionReport, ...] = ()


def _dotted_name(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


class _RuleVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.findings: list[InspectionFinding] = []

    def _add(self, node: ast.AST, rule: str, severity: str, evidence: str) -> None:
        self.findings.append(InspectionFinding(
            self.path, int(getattr(node, "lineno", 1)), rule, severity, evidence[:240]
        ))

    def visit_Call(self, node: ast.Call) -> None:
        name = _dotted_name(node.func) or ""
        if name in {"eval", "exec"}:
            self._add(node, "DYN-001", "high", f"dynamic execution call: {name}")
        elif name in {"os.system", "os.popen"}:
            self._add(node, "PROC-001", "high", f"shell-oriented process API: {name}")
        elif name in {"subprocess.run", "subprocess.call", "subprocess.Popen",
                      "subprocess.check_call", "subprocess.check_output"}:
            if any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant)
                   and keyword.value.value is True for keyword in node.keywords):
                self._add(node, "PROC-002", "high", f"subprocess shell=True: {name}")
        elif name in {"pickle.load", "pickle.loads", "marshal.loads"}:
            self._add(node, "DESER-001", "high", f"unsafe deserialization primitive: {name}")
        elif name == "yaml.load":
            self._add(node, "DESER-002", "medium", "yaml.load requires an explicitly safe loader")
        elif name in {"hashlib.md5", "hashlib.sha1"}:
            self._add(node, "CRYPTO-001", "medium", f"legacy hash primitive: {name}")
        elif name == "ssl._create_unverified_context":
            self._add(node, "TLS-001", "high", "TLS certificate verification bypass helper")
        elif name in {"requests.get", "requests.post", "requests.put",
                      "requests.patch", "requests.delete", "httpx.get", "httpx.post"}:
            if any(keyword.arg == "verify" and isinstance(keyword.value, ast.Constant)
                   and keyword.value.value is False for keyword in node.keywords):
                self._add(node, "TLS-002", "high", f"TLS verification disabled: {name}")
        self.generic_visit(node)


class PythonSystemInspector:
    """Bounded AST scanner that emits deterministic, source-located findings."""

    def __init__(self, *, max_files: int = MAX_FILES,
                 max_file_bytes: int = MAX_FILE_BYTES,
                 max_total_bytes: int = MAX_TOTAL_BYTES,
                 max_entries: int = MAX_ENTRIES) -> None:
        for name, value, maximum in (
            ("max_files", max_files, MAX_FILES),
            ("max_file_bytes", max_file_bytes, MAX_FILE_BYTES),
            ("max_total_bytes", max_total_bytes, MAX_TOTAL_BYTES),
            ("max_entries", max_entries, MAX_ENTRIES),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValueError("invalid_inspector_limit:" + name)
        self.max_files, self.max_file_bytes, self.max_total_bytes = max_files, max_file_bytes, max_total_bytes
        self.max_entries = max_entries

    def inspect(self, root: str | os.PathLike[str]) -> InspectionReport:
        root_path = Path(root)
        if root_path.is_symlink():
            raise ValueError("inspection_root_must_not_be_symlink")
        root_path = root_path.resolve(strict=True)
        if not root_path.is_dir():
            raise ValueError("inspection_root_must_be_directory")
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise RuntimeError("descriptor_relative_traversal_unsupported")

        findings: list[InspectionFinding] = []
        errors: list[str] = []
        binary_reports: list[ELFInspectionReport] = []
        files_scanned = total_bytes = visited_entries = 0
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
        root_fd = os.open(root_path, directory_flags)
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            os.close(root_fd)
            raise ValueError("inspection_root_must_be_directory")

        # Keep directory descriptors, not path strings, in the traversal
        # queue. Child opens are relative to the already-open parent, so a
        # concurrent rename/replacement cannot redirect a later path lookup.
        pending_dirs: list[tuple[int, Path]] = [(root_fd, Path("."))]
        entry_limit_reached = False
        try:
            while pending_dirs:
                current_fd, relative_dir = pending_dirs.pop()
                try:
                    scan_fd = os.dup(current_fd)
                    entries = []
                    try:
                        with os.scandir(scan_fd) as iterator:
                            for entry in iterator:
                                if visited_entries >= self.max_entries:
                                    entry_limit_reached = True
                                    break
                                visited_entries += 1
                                entries.append(entry)
                    finally:
                        os.close(scan_fd)

                    child_dirs: list[tuple[int, Path]] = []
                    for entry in sorted(entries, key=lambda item: item.name):
                        relative_path = relative_dir / entry.name
                        relative = relative_path.as_posix()
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                if entry.name not in SKIP_DIRS:
                                    child_fd = os.open(
                                        entry.name, directory_flags, dir_fd=current_fd
                                    )
                                    if stat.S_ISDIR(os.fstat(child_fd).st_mode):
                                        child_dirs.append((child_fd, relative_path))
                                    else:
                                        os.close(child_fd)
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue

                            path = Path(entry.name)
                            is_python = path.suffix == ".py"
                            descriptor = os.open(entry.name, file_flags, dir_fd=current_fd)
                            try:
                                metadata = os.fstat(descriptor)
                                if not stat.S_ISREG(metadata.st_mode):
                                    continue
                                size = metadata.st_size
                                if (
                                    size > self.max_file_bytes
                                    or total_bytes + size > self.max_total_bytes
                                ):
                                    if is_python:
                                        errors.append(f"size_limit_skipped:{relative}")
                                    continue
                                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                                    remaining_total = self.max_total_bytes - total_bytes
                                    read_limit = min(self.max_file_bytes, remaining_total)
                                    if read_limit < (1 if is_python else len(ELF_MAGIC)):
                                        errors.append(f"size_limit_skipped:{relative}")
                                        continue
                                    if not is_python:
                                        prefix = stream.read(len(ELF_MAGIC))
                                        if prefix != ELF_MAGIC:
                                            continue
                                    if files_scanned >= self.max_files:
                                        errors.append("file_limit_reached")
                                        for child_fd, _child_path in child_dirs:
                                            os.close(child_fd)
                                        return InspectionReport(
                                            files_scanned, total_bytes, tuple(sorted(findings)),
                                            tuple(sorted(errors)), tuple(binary_reports),
                                        )
                                    stream.seek(0)
                                    raw = stream.read(read_limit + 1)
                                if len(raw) > read_limit:
                                    errors.append(f"size_limit_skipped:{relative}")
                                    continue
                            finally:
                                os.close(descriptor)

                            # Account before parsing: malformed inputs still
                            # consume I/O, CPU and aggregate byte budgets.
                            files_scanned += 1
                            total_bytes += len(raw)
                            if is_python:
                                source = raw.decode("utf-8")
                                tree = ast.parse(source, filename=relative)
                                visitor = _RuleVisitor(relative)
                                visitor.visit(tree)
                                findings.extend(visitor.findings)
                            else:
                                binary_report = inspect_elf_bytes(raw)
                                binary_reports.append(binary_report)
                                findings.extend(
                                    InspectionFinding(
                                        relative, 0, finding.rule_id, finding.severity,
                                        finding.evidence,
                                    )
                                    for finding in binary_report.findings
                                )
                        except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
                            errors.append(f"parse_error:{relative}:{type(exc).__name__}")
                            continue

                    # Reverse before extending a LIFO stack to preserve lexical
                    # directory order. Each queued descriptor is already pinned.
                    pending_dirs.extend(reversed(child_dirs))
                    if entry_limit_reached:
                        errors.append("entry_limit_reached")
                        break
                finally:
                    os.close(current_fd)
        finally:
            for pending_fd, _pending_path in pending_dirs:
                try:
                    os.close(pending_fd)
                except OSError:
                    pass

        return InspectionReport(
            files_scanned, total_bytes, tuple(sorted(findings)),
            tuple(sorted(errors)), tuple(binary_reports),
        )
