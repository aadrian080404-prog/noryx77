"""Canonical recovery boundary for the JARVIS front.

JARVIS intentionally reuses the ecosystem recovery state machine instead of
maintaining a second, semantically divergent recovery controller.
"""
from __future__ import annotations

from core.recovery import RecoveryController, RecoveryState

__all__ = ["RecoveryController", "RecoveryState"]
