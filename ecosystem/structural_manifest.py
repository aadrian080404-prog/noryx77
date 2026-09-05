"""Executable manifest for the four NORYX fronts.

The manifest is deliberately declarative: it verifies that the structural
entry points exist without importing or executing any front. This keeps the
structural gate independent from runtime behaviour.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final


FRONT_REQUIRED_PATHS: Final[dict[str, tuple[str, ...]]] = {
    "jarvis": (
        "jarvis/core/contracts.py",
        "jarvis/core/orchestrator.py",
        "jarvis/core/runtime.py",
        "jarvis/core/recovery.py",
        "jarvis/core/state.py",
        "jarvis/core/provider.py",
        "jarvis/core/decomposition.py",
        "jarvis/security",
        "jarvis/tools",
        "jarvis/memory",
    ),
    "browser": (
        "noryx-browser/settings.gradle.kts",
        "noryx-browser/build.gradle.kts",
        "noryx-browser/app/build.gradle.kts",
        "noryx-browser/app/src/main/AndroidManifest.xml",
        "noryx-browser/app/src/main/java/com/noryx/browser/MainActivity.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/BrowserController.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/NavigationState.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/NavigationPolicy.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/NoryxWebViewClient.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/NoryxWebChromeClient.kt",
        "noryx-browser/app/src/main/res/layout/activity_main.xml",
        "noryx-browser/app/src/test/java/com/noryx/browser/NavigationPolicyTest.kt",
    ),
    "hypersynth": (
        "core/hypersynth.py",
        "core/hypersynth_runtime.py",
        "core/reasoning.py",
        "core/metacognition.py",
        "core/planning.py",
        "core/verification.py",
        "core/memory.py",
        "core/secure_memory.py",
        "core/security.py",
        "core/recovery.py",
    ),
    "orchestration": (
        "core/runtime.py",
        "core/orchestration.py",
        "core/interaction_context.py",
        "core/user_understanding.py",
        "core/state.py",
        "core/security.py",
        "core/recovery.py",
        "core/evaluation.py",
        "ecosystem/boundaries.py",
    ),
}


def missing_paths(repository_root: str | Path | None = None) -> tuple[str, ...]:
    """Return every required structural path that is absent."""
    root = Path(repository_root).resolve() if repository_root is not None else Path(__file__).resolve().parents[1]
    missing: list[str] = []
    for paths in FRONT_REQUIRED_PATHS.values():
        for relative in paths:
            if not (root / relative).exists():
                missing.append(relative)
    return tuple(missing)


def require_complete(repository_root: str | Path | None = None) -> None:
    """Fail closed when any front is structurally incomplete."""
    missing = missing_paths(repository_root)
    if missing:
        raise RuntimeError("front_structure_incomplete:" + ",".join(missing))
