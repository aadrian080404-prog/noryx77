"""Cross-front structural closure contract.

This module is deliberately declarative: it defines the seams that must exist
before the project can enter the final verification phase. It does not claim
that those seams are already runtime-verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .boundaries import Front


@dataclass(frozen=True)
class FrontClosure:
    front: Front
    required_boundaries: tuple[str, ...]
    security_invariants: tuple[str, ...]


CLOSURE_CONTRACTS: Final[tuple[FrontClosure, ...]] = (
    FrontClosure(
        Front.JARVIS,
        ("contracts", "orchestrator", "runtime", "recovery", "state", "policy", "provider", "tools", "memory"),
        ("deny_by_default", "verified_result_before_commit", "recovery_gate", "state_identity_binding"),
    ),
    Front.BROWSER,
        ("android_webview", "https_only_navigation", "lifecycle_restore", "browser_isolation"),
        ("no_ai_boundary", "no_tracking_boundary", "cleartext_denied", "no_javascript_bridge"),
    ),
    Front.HYPERSYNTH,
        ("cognition", "planning", "reasoning", "metacognition", "challenge_verification", "memory", "offline", "recovery"),
        ("verified_execution", "independent_verification", "capability_gate", "offline_security_continuity"),
    ),
    Front.ORCHESTRATION,
        ("understanding", "interaction_context", "orchestration", "dispatch", "isolation", "global_fabric", "offline"),
        ("consent_bound_understanding", "topology_enforced_dispatch", "identity_authorization", "offline_fail_closed"),
    ),
)


def require_contract_shape() -> None:
    """Fail closed if the declarative closure contract itself is malformed."""
    seen: set[Front] = set()
    for contract in CLOSURE_CONTRACTS:
        if contract.front in seen:
            raise RuntimeError("duplicate_front_closure")
        seen.add(contract.front)
        if not contract.required_boundaries or not contract.security_invariants:
            raise RuntimeError("incomplete_front_closure")
        if any(not isinstance(item, str) or not item.strip() for item in (*contract.required_boundaries, *contract.security_invariants)):
            raise RuntimeError("invalid_front_closure_entry")
    if seen != set(Front):
        raise RuntimeError("front_closure_set_incomplete")
