from pathlib import Path

from scripts.validate_integration_manifest import validate_manifest


def _module(module_id, *, paths=None, dependencies=None, status="implemented_partial"):
    return {
        "id": module_id,
        "plane": "test",
        "status": status,
        "paths": paths or [],
        "depends_on": dependencies or [],
        "integration_tests": [],
        **({"candidate": "PR #999"} if status == "candidate_only" else {}),
    }


def test_manifest_accepts_existing_sources_and_acyclic_dependencies(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "unit.py").write_text("# source", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "modules": [
            _module("base", paths=["core/unit.py"]),
            _module("api", dependencies=["base"], paths=["core"]),
        ],
    }
    assert validate_manifest(tmp_path, manifest) == []


def test_manifest_rejects_missing_source_path(tmp_path):
    manifest = {
        "schema_version": 1,
        "modules": [_module("base", paths=["core/missing.py"])],
    }
    assert "source_path_missing:base:core/missing.py" in validate_manifest(
        tmp_path, manifest
    )


def test_manifest_rejects_unknown_dependency_and_cycle(tmp_path):
    manifest = {
        "schema_version": 1,
        "modules": [
            _module("a", dependencies=["b"]),
            _module("b", dependencies=["a", "missing"]),
        ],
    }
    errors = validate_manifest(tmp_path, manifest)
    assert "unknown_dependency:b:missing" in errors
    assert any(error.startswith("dependency_cycle:") for error in errors)


def test_manifest_rejects_path_traversal(tmp_path):
    manifest = {
        "schema_version": 1,
        "modules": [_module("escape", paths=["../outside.py"])],
    }
    assert "unsafe_path:escape:../outside.py" in validate_manifest(
        tmp_path, manifest
    )


def test_candidate_requires_branch_or_pr_reference(tmp_path):
    module = _module("candidate", status="candidate_only")
    module.pop("candidate")
    manifest = {"schema_version": 1, "modules": [module]}
    assert "candidate_reference_missing:candidate" in validate_manifest(
        tmp_path, manifest
    )
