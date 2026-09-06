"""Executable manifest for the four NORYX fronts."""
from __future__ import annotations

from pathlib import Path
from typing import Final

FRONT_REQUIRED_PATHS: Final[dict[str, tuple[str, ...]]] = {
    "jarvis": (
        "jarvis/core/contracts.py", "jarvis/core/orchestrator.py", "jarvis/core/runtime.py", "jarvis/core/recovery.py",
        "jarvis/core/state.py", "jarvis/core/provider.py", "jarvis/core/decomposition.py", "jarvis/security", "jarvis/tools", "jarvis/memory",
    ),
    "browser": (
        "noryx-browser/settings.gradle.kts", "noryx-browser/build.gradle.kts", "noryx-browser/app/build.gradle.kts",
        "noryx-browser/app/src/main/AndroidManifest.xml", "noryx-browser/app/src/main/java/com/noryx/browser/MainActivity.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/BrowserController.kt", "noryx-browser/app/src/main/java/com/noryx/browser/NavigationState.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/NavigationPolicy.kt", "noryx-browser/app/src/main/java/com/noryx/browser/NoryxWebViewClient.kt",
        "noryx-browser/app/src/main/java/com/noryx/browser/NoryxWebChromeClient.kt", "noryx-browser/app/src/main/res/layout/activity_main.xml",
        "noryx-browser/app/src/test/java/com/noryx/browser/NavigationPolicyTest.kt",
    ),
    "hypersynth": (
        "core/agents.py", "core/agent_core.py", "core/agent_fabric.py", "core/agent_skills.py", "core/cyber_range.py", "core/hypersynth.py", "core/hypersynth_runtime.py", "core/reasoning.py", "core/metacognition.py", "core/metacognitive_challenge.py",
        "core/planning.py", "core/verification.py", "core/memory.py", "core/secure_memory.py", "core/security.py", "core/recovery.py",
        "core/offline.py", "core/offline_adapters.py", "core/multiauth.py", "core/control_plane.py", "core/defense.py", "core/observability.py",
        "core/security_integration.py", "core/authorization_replay.py", "core/supply_chain.py", "tests/test_metacognitive_challenge.py", "tests/test_offline.py", "core/test_agent_fabric.py", "core/test_cyber_range.py",
    ),
    "orchestration": (
        "core/agents.py", "core/agent_core.py", "core/agent_fabric.py", "core/agent_skills.py", "core/cyber_range.py", "core/runtime.py", "core/orchestration.py", "core/interaction_context.py", "core/user_understanding.py", "core/state.py",
        "core/security.py", "core/security_integration.py", "core/defense.py", "core/observability.py", "core/control_plane.py", "core/multiauth.py",
        "core/authorization_replay.py", "core/supply_chain.py", "core/recovery.py", "core/offline.py", "core/offline_adapters.py", "core/evaluation.py", "core/evaluation_campaign.py", "ecosystem/boundaries.py",
        "ecosystem/dispatch_contract.py", "ecosystem/isolation.py", "ecosystem/runtime_dispatch.py", "ecosystem/global_scale.py", "ecosystem/global_fabric.py",
        "ecosystem/closure_contract.py", "ecosystem/completeness.py", "ecosystem/structural_manifest.py", "tests/test_global_fabric.py", "tests/test_offline.py", "tests/test_runtime_offline.py", "tests/test_closure_contract.py",
    ),
}

FORBIDDEN_PATH_PREFIXES: Final[tuple[str, ...]] = ("core/core/",)


def missing_paths(repository_root: str | Path | None = None) -> tuple[str, ...]:
    root = Path(repository_root).resolve() if repository_root is not None else Path(__file__).resolve().parents[1]
    missing = [relative for paths in FRONT_REQUIRED_PATHS.values() for relative in paths if not (root / relative).exists()]
    for prefix in FORBIDDEN_PATH_PREFIXES:
        if any(path.as_posix().startswith(prefix) for path in root.rglob("*") if path.is_file()):
            missing.append(f"forbidden:{prefix}")
    return tuple(missing)


def require_complete(repository_root: str | Path | None = None) -> None:
    missing = missing_paths(repository_root)
    if missing:
        raise RuntimeError("front_structure_incomplete:" + ",".join(missing))
