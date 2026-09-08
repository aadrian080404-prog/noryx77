"""Fail-closed provider boundary for the JARVIS front.

Providers are adapters, not authorities: they may produce proposals/results but
cannot grant capabilities or bypass the orchestrator policy gate.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import ActionResult, PlanStep, Request


@runtime_checkable
class Provider(Protocol):
    def execute(self, request: Request, step: PlanStep) -> ActionResult: ...


class CallableProvider:
    """Small adapter for a trusted caller-supplied execution function."""

    def __init__(self, handler):
        if not callable(handler):
            raise TypeError("provider_handler_required")
        self._handler = handler

    def execute(self, request: Request, step: PlanStep) -> ActionResult:
        if not isinstance(request, Request) or not isinstance(step, PlanStep):
            raise TypeError("request_and_step_required")
        result = self._handler(request, step)
        if not isinstance(result, ActionResult):
            raise TypeError("provider_result_required")
        if result.step_id != step.step_id:
            raise ValueError("provider_result_step_mismatch")
        return result


__all__ = ["Provider", "CallableProvider"]
