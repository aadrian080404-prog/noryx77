"""Single fail-closed structural gate for the complete four-front system."""
from __future__ import annotations

from core.architecture_registry import canonical_gate
from .browser_isolation import scan_browser_isolation
from .structural_manifest import missing_paths


def evaluate() -> tuple[bool, tuple[str, ...]]:
    """Evaluate architecture, concrete structure and browser isolation."""
    architecture = canonical_gate().evaluate()
    problems = list(architecture.missing) + list(architecture.invalid)
    problems.extend(f"front_structure:{path}" for path in missing_paths())
    problems.extend(f"browser_isolation:{item}" for item in scan_browser_isolation())
    return not problems, tuple(problems)


def require_complete() -> None:
    """Fail closed unless all structural and browser-isolation gates pass."""
    complete, problems = evaluate()
    if not complete:
        raise RuntimeError("system_structurally_incomplete:" + ",".join(problems))
