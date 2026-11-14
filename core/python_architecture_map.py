"""Non-executing, bounded Python architecture and dependency mapper."""
from __future__ import annotations

import ast
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys

MAX_MAP_FILES = 5000
MAX_MAP_FILE_BYTES = 2 * 1024 * 1024
MAX_MAP_TOTAL_BYTES = 64 * 1024 * 1024
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
RISK_SURFACES = {
    "ctypes": "native_ffi",
    "importlib": "dynamic_import",
    "marshal": "binary_deserialization",
    "os": "process_and_filesystem",
    "pickle": "object_deserialization",
    "socket": "network",
    "ssl": "tls",
    "subprocess": "process_execution",
    "urllib": "network",
    "requests": "network",
    "httpx": "network",
}


@dataclass(frozen=True, order=True)
class ModuleRecord:
    path: str
    module: str
    imports: tuple[str, ...]
    definitions: tuple[str, ...]
    entrypoint: bool
    capability_surfaces: tuple[str, ...]


@dataclass(frozen=True)
class PythonArchitectureMap:
    modules: tuple[ModuleRecord, ...]
    internal_edges: tuple[tuple[str, str], ...]
    standard_library: tuple[str, ...]
    third_party: tuple[str, ...]
    parse_errors: tuple[str, ...]
    files_scanned: int
    bytes_scanned: int


class _Definitions(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.names: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_definition(node)

    def _visit_definition(self, node) -> None:
        name = ".".join((*self.stack, node.name))
        self.names.add(name)
        self.stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self.stack.pop()


def _module_for(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or "__root__"


def _package_for(module: str, is_package: bool) -> list[str]:
    parts = [] if module == "__root__" else module.split(".")
    return parts if is_package else parts[:-1]


def _relative_import(package: list[str], level: int, module: str | None) -> str:
    if level <= 0:
        return module or ""
    base = package[: max(0, len(package) - level + 1)]
    suffix = module.split(".") if module else []
    return ".".join((*base, *suffix))


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        left, right = test.left, test.comparators[0]
        return (
            isinstance(left, ast.Name) and left.id == "__name__"
            and isinstance(right, ast.Constant) and right.value == "__main__"
        ) or (
            isinstance(right, ast.Name) and right.id == "__name__"
            and isinstance(left, ast.Constant) and left.value == "__main__"
        )
    return False


class PythonArchitectureMapper:
    """Build a deterministic module/import/entrypoint map without importing code."""

    def __init__(self, *, max_files: int = MAX_MAP_FILES,
                 max_file_bytes: int = MAX_MAP_FILE_BYTES,
                 max_total_bytes: int = MAX_MAP_TOTAL_BYTES) -> None:
        for name, value, maximum in (
            ("max_files", max_files, MAX_MAP_FILES),
            ("max_file_bytes", max_file_bytes, MAX_MAP_FILE_BYTES),
            ("max_total_bytes", max_total_bytes, MAX_MAP_TOTAL_BYTES),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValueError("invalid_architecture_map_limit:" + name)
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes

    def inspect(self, root: str | os.PathLike[str]) -> PythonArchitectureMap:
        root_path = Path(root)
        if root_path.is_symlink():
            raise ValueError("architecture_root_must_not_be_symlink")
        root_path = root_path.resolve(strict=True)
        if not root_path.is_dir():
            raise ValueError("architecture_root_must_be_directory")

        parsed: list[tuple[str, str, ast.Module]] = []
        errors: list[str] = []
        total_bytes = 0
        for current, dirs, filenames in os.walk(root_path, topdown=True, followlinks=False):
            dirs[:] = sorted(
                name for name in dirs
                if name not in SKIP_DIRS and not (Path(current) / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = Path(current) / filename
                if path.suffix != ".py" or path.is_symlink():
                    continue
                if len(parsed) >= self.max_files:
                    errors.append("file_limit_reached")
                    return self._build(parsed, errors, total_bytes)
                relative = path.relative_to(root_path).as_posix()
                try:
                    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    try:
                        metadata = os.fstat(descriptor)
                        if not stat.S_ISREG(metadata.st_mode):
                            continue
                        if metadata.st_size > self.max_file_bytes or total_bytes + metadata.st_size > self.max_total_bytes:
                            errors.append("size_limit_skipped:" + relative)
                            continue
                        with os.fdopen(descriptor, "rb", closefd=False) as stream:
                            raw = stream.read(self.max_file_bytes + 1)
                    finally:
                        os.close(descriptor)
                    if len(raw) > self.max_file_bytes or total_bytes + len(raw) > self.max_total_bytes:
                        errors.append("size_limit_skipped:" + relative)
                        continue
                    tree = ast.parse(raw.decode("utf-8"), filename=relative)
                except (OSError, UnicodeError, SyntaxError) as exc:
                    errors.append(f"parse_error:{relative}:{type(exc).__name__}")
                    continue
                total_bytes += len(raw)
                parsed.append((relative, _module_for(Path(relative)), tree))
        return self._build(parsed, errors, total_bytes)

    @staticmethod
    def _build(parsed, errors, total_bytes) -> PythonArchitectureMap:
        internal = {module for _, module, _ in parsed}
        records: list[ModuleRecord] = []
        edges: set[tuple[str, str]] = set()
        stdlib: set[str] = set()
        third_party: set[str] = set()

        for path, module, tree in parsed:
            package = _package_for(module, path.endswith("__init__.py"))
            imports: set[str] = set()
            surfaces: set[str] = set()
            entrypoint = False
            definitions = _Definitions()
            definitions.visit(tree)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    base = _relative_import(package, node.level, node.module)
                    imported = [base] if base else []
                    if base:
                        imported.extend(base + "." + alias.name for alias in node.names if alias.name != "*")
                else:
                    if isinstance(node, ast.If) and _is_main_guard(node):
                        entrypoint = True
                    continue

                for name in imported:
                    if not name:
                        continue
                    imports.add(name)
                    top = name.split(".", 1)[0]
                    surface = RISK_SURFACES.get(top)
                    if surface:
                        surfaces.add(surface)
                    if name in internal and name != module:
                        edges.add((module, name))
                    elif top in sys.stdlib_module_names:
                        stdlib.add(top)
                    else:
                        third_party.add(top)

            records.append(ModuleRecord(
                path, module, tuple(sorted(imports)),
                tuple(sorted(definitions.names)), entrypoint,
                tuple(sorted(surfaces)),
            ))

        return PythonArchitectureMap(
            tuple(sorted(records)), tuple(sorted(edges)),
            tuple(sorted(stdlib)), tuple(sorted(third_party)),
            tuple(sorted(errors)), len(parsed), total_bytes,
        )
