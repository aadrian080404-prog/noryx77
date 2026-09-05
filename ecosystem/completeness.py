"""Single fail-closed structural gate for the complete four-front system."""
from __future__ import annotations

from core.architecture_registry import canonical_gate
from .structural_manifest import missing_paths


def evaluate() -> tuple[bool, tuple[str, ...]]:
    """Evaluate architecture definitions and concrete front structure."""
    architecture = canonical_gate().evaluate()
    missing = list(architecture.missing)
    invalid = list(architecture.invalid)
    invalid.extend(f"front_structure:{path}" for path in missing_paths())
    return not missing and not invalid, tuple(missing + invalid)


def require_complete() -> None:
    """Fail closed unless both abstract and concrete structure are complete."""
    complete, problems = evaluate()
    if not complete:
        raise RuntimeError("system_structurally_incomplete:" + ",".join(problems))
