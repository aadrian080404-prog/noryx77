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
                 max_total_bytes: int = MAX_TOTAL_BYTES) -> None:
        for name, value, maximum in (
            ("max_files", max_files, MAX_FILES),
            ("max_file_bytes", max_file_bytes, MAX_FILE_BYTES),
            ("max_total_bytes", max_total_bytes, MAX_TOTAL_BYTES),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValueError("invalid_inspector_limit:" + name)
        self.max_files, self.max_file_bytes, self.max_total_bytes = max_files, max_file_bytes, max_total_bytes

    def inspect(self, root: str | os.PathLike[str]) -> InspectionReport:
        root_path = Path(root)
        if root_path.is_symlink():
            raise ValueError("inspection_root_must_not_be_symlink")
        root_path = root_path.resolve(strict=True)
        if not root_path.is_dir():
            raise ValueError("inspection_root_must_be_directory")
        findings: list[InspectionFinding] = []
        errors: list[str] = []
        binary_reports: list[ELFInspectionReport] = []
        files_scanned = total_bytes = 0
        for current, dirs, filenames in os.walk(root_path, topdown=True, followlinks=False):
            dirs[:] = sorted(
                name for name in dirs
                if name not in SKIP_DIRS and not (Path(current) / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = Path(current) / filename
                if path.is_symlink():
                    continue
                is_python = path.suffix == ".py"
                relative = path.relative_to(root_path).as_posix()
                try:
                    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    descriptor = os.open(path, flags)
                    try:
                        metadata = os.fstat(descriptor)
                        if not stat.S_ISREG(metadata.st_mode):
                            continue
                        size = metadata.st_size
                        if size > self.max_file_bytes or total_bytes + size > self.max_total_bytes:
                            if is_python:
                                errors.append(f"size_limit_skipped:{relative}")
                            continue
                        with os.fdopen(descriptor, "rb", closefd=False) as stream:
                            prefix = stream.read(4)
                            if not is_python and prefix != ELF_MAGIC:
                                continue
                            if files_scanned >= self.max_files:
                                errors.append("file_limit_reached")
                                return InspectionReport(
                                    files_scanned, total_bytes, tuple(sorted(findings)),
                                    tuple(sorted(errors)), tuple(binary_reports),
                                )
                            stream.seek(0)
                            raw = stream.read(self.max_file_bytes + 1)
                        if len(raw) > self.max_file_bytes:
                            errors.append(f"size_limit_skipped:{relative}")
                            continue
                    finally:
                        os.close(descriptor)

                    # Account for every candidate before parsing. Malformed files
                    # still consume CPU and I/O and must not bypass either budget.
                    files_scanned += 1
                    total_bytes += len(raw)
                    if is_python:
                        source = raw.decode("utf-8")
                        tree = ast.parse(source, filename=str(path))
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
        return InspectionReport(
            files_scanned, total_bytes, tuple(sorted(findings)),
            tuple(sorted(errors)), tuple(binary_reports),
        )
