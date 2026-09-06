"""Executable cross-layer closure gate for NORYX7.

This gate separates structural presence from runtime evidence. It verifies that
critical persistence, orchestration, identity, security, recovery, verification,
and browser seams are wired at import/interface level. It does not pretend that
external KMS/HSM, hardware monotonic counters, Android devices, or CI runners
have been validated locally.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClosureReport:
    passed: bool
    problems: tuple[str, ...]


_REQUIRED_MODULES = (
    "core.state",
    "core.state_journal",
    "core.runtime",
    "core.offline",
    "core.offline_anchor",
    "core.attestation",
    "core.key_lifecycle",
    "core.crypto",
    "core.control_plane",
    "core.observability",
    "core.security",
    "core.recovery",
    "core.verification",
    "ecosystem.completeness",
)

_REQUIRED_SYMBOLS = {
    "core.state": ("NORYXState", "StateCommit", "StateStore"),
    "core.state_journal": ("StateJournal",),
    "core.runtime": ("NORYXRuntime",),
    "core.offline": ("OfflineRuntime", "OfflineSnapshot", "OfflineExecution"),
    "core.offline_anchor": ("MonotonicAnchor",),
    "core.attestation": ("Attestation", "AttestationVerifier", "RuntimeIdentity"),
    "core.key_lifecycle": ("KeyLifecycle", "KeyState", "ExternalKeyBoundary"),
    "core.crypto": ("AuthenticatedCipher", "KeyProvider"),
    "core.control_plane": ("Noryx7ControlPlane",),
    "core.observability": ("SecurityEventBus",),
    "core.recovery": ("RecoveryController",),
    "core.verification": ("VerificationEngine",),
}

_REQUIRED_PATHS = (
    "core/state.py",
    "core/state_journal.py",
    "core/runtime.py",
    "core/offline.py",
    "core/offline_anchor.py",
    "core/attestation.py",
    "core/key_lifecycle.py",
    "core/crypto.py",
    "core/control_plane.py",
    "core/observability.py",
    "core/security.py",
    "core/recovery.py",
    "core/verification.py",
    "noryx-browser/settings.gradle.kts",
    "noryx-browser/app/build.gradle.kts",
    "noryx-browser/app/src/main/AndroidManifest.xml",
    "devtools/test_lab/runner.py",
)


def evaluate(repository_root: str | Path | None = None) -> ClosureReport:
    problems: list[str] = []
    for module_name in _REQUIRED_MODULES:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            problems.append(f"import:{module_name}:{type(exc).__name__}")
            continue
        for symbol in _REQUIRED_SYMBOLS.get(module_name, ()):
            if not hasattr(module, symbol):
                problems.append(f"symbol:{module_name}:{symbol}")

    root = Path(repository_root).resolve() if repository_root is not None else Path(__file__).resolve().parents[1]
    problems.extend(f"path:{path}" for path in _REQUIRED_PATHS if not (root / path).exists())
    return ClosureReport(not problems, tuple(problems))


def require_closed(repository_root: str | Path | None = None) -> None:
    report = evaluate(repository_root)
    if not report.passed:
        raise RuntimeError("global_infrastructure_not_closed:" + ",".join(report.problems))


def main() -> int:
    report = evaluate()
    print("NORYX7 GLOBAL CLOSURE: " + ("PASS" if report.passed else "FAIL"))
    for problem in report.problems:
        print(problem)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
