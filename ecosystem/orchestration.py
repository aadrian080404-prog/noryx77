"""Canonical ecosystem orchestration boundary re-export.

Execution authority remains in the core orchestration/security layers; this module
exists only as the stable ecosystem-facing import surface.
"""
from core.orchestration import (
    OrchestrationCoordinator,
    OrchestrationEnvelope,
    OrchestrationStage,
    OrchestrationTransition,
)

__all__ = [
    "OrchestrationCoordinator",
    "OrchestrationEnvelope",
    "OrchestrationStage",
    "OrchestrationTransition",
]
