"""Bounded deterministic decomposition boundary for JARVIS."""
from __future__ import annotations

from .contracts import PlanStep, Request


class Decomposer:
    """Convert one request into an explicitly ordered, bounded plan."""

    def decompose(self, request: Request) -> tuple[PlanStep, ...]:
        if not isinstance(request, Request):
            raise TypeError("request_required")
        return (PlanStep("step-1", "compute", request.text, {}),)


class TaskDecomposer(Decomposer):
    pass


__all__ = ["Decomposer", "TaskDecomposer"]
