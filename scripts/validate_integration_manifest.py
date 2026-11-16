#!/usr/bin/env python3
"""Validate NORYX7's machine-readable module/dependency graph.

This is a structural planning gate. It does not claim that a module is
production-ready merely because its source path exists.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {
    "implemented_partial",
    "implemented",
    "candidate_only",
    "specification_only",
}


def validate_manifest(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    modules = manifest.get("modules")
    if manifest.get("schema_version") != 1 or not isinstance(modules, list):
        return ["manifest_schema_invalid"]

    by_id: dict[str, dict[str, Any]] = {}
    for index, module in enumerate(modules):
        if not isinstance(module, dict):
            errors.append(f"module_{index}_not_object")
            continue
        module_id = module.get("id")
        if not isinstance(module_id, str) or not module_id.strip():
            errors.append(f"module_{index}_id_invalid")
            continue
        if module_id in by_id:
            errors.append(f"duplicate_module:{module_id}")
            continue
        by_id[module_id] = module
        if module.get("status") not in ALLOWED_STATUSES:
            errors.append(f"invalid_status:{module_id}")
        paths = module.get("paths")
        deps = module.get("depends_on")
        tests = module.get("integration_tests")
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            errors.append(f"paths_invalid:{module_id}")
            continue
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            errors.append(f"dependencies_invalid:{module_id}")
        if not isinstance(tests, list) or not all(isinstance(t, str) for t in tests):
            errors.append(f"integration_tests_invalid:{module_id}")
        if module.get("status") in {"implemented", "implemented_partial"} and not paths:
            errors.append(f"implemented_without_paths:{module_id}")
        if module.get("status") == "candidate_only" and not module.get("candidate"):
            errors.append(f"candidate_reference_missing:{module_id}")
        for relative in paths:
            candidate = Path(relative)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"unsafe_path:{module_id}:{relative}")
                continue
            if not (root / candidate).exists():
                errors.append(f"source_path_missing:{module_id}:{relative}")

    for module_id, module in by_id.items():
        for dependency in module.get("depends_on", []):
            if dependency not in by_id:
                errors.append(f"unknown_dependency:{module_id}:{dependency}")

    # Three-colour DFS detects dependency cycles without third-party packages.
    state: dict[str, int] = {}

    def visit(module_id: str, trail: tuple[str, ...] = ()) -> None:
        mark = state.get(module_id, 0)
        if mark == 1:
            errors.append("dependency_cycle:" + "->".join(trail + (module_id,)))
            return
        if mark == 2:
            return
        state[module_id] = 1
        module = by_id[module_id]
        for dependency in module.get("depends_on", []):
            if dependency in by_id:
                visit(dependency, trail + (module_id,))
        state[module_id] = 2

    for module_id in by_id:
        if state.get(module_id, 0) == 0:
            visit(module_id)
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "architecture" / "noryx7_integration_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INTEGRATION_MANIFEST_INVALID: {type(exc).__name__}: {exc}")
        return 2
    errors = validate_manifest(root, manifest)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        print(f"INTEGRATION_GRAPH_REJECTED errors={len(errors)}")
        return 1
    counts: dict[str, int] = {}
    for module in manifest["modules"]:
        status = module["status"]
        counts[status] = counts.get(status, 0) + 1
    print(
        "INTEGRATION_GRAPH_VALID "
        f"modules={len(manifest['modules'])} "
        + " ".join(f"{key}={counts[key]}" for key in sorted(counts))
    )
    print("NOTE: structural validity is not end-to-end or production verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
