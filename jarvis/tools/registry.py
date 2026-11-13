from __future__ import annotations

from typing import Callable, Optional
from functools import wraps


class CapabilityRegistry:
    """
    Canonical capability registry for JARVIS.

    When a core registry is supplied, JARVIS delegates registration
    and resolution to that registry instead of maintaining a second
    execution registry.
    """

    def __init__(self, core_registry=None):
        self._core_registry = core_registry
        self._tools = {}
        self._risks = {}

    def register(self, name: str, handler: Callable, *, risk_class: str = "normal"):
        if not isinstance(name, str) or not name.strip() or not callable(handler):
            raise ValueError("invalid_capability")
        if not isinstance(risk_class, str) or risk_class not in {"normal", "sensitive", "high"}:
            raise ValueError("invalid_capability_risk")

        if self._core_registry is not None:
            @wraps(handler)
            def core_handler(target, parameters):
                # The canonical Core ToolExecutor contract is:
                #     handler(target, parameters)
                #
                # JARVIS capabilities retain their native:
                #     handler(PlanStep)
                #
                # Reconstruct the JARVIS step at this boundary so both
                # layers share one registry without changing either
                # subsystem's public contract.
                from jarvis.core.contracts import ActionResult, PlanStep

                params = dict(parameters)
                step_id = params.pop("__jarvis_step_id", None)
                if step_id is None:
                    step_id = str(target)

                step = PlanStep(
                    step_id=str(step_id),
                    capability=name,
                    target=target,
                    parameters=params,
                    dependencies=(),
                )
                result = handler(step)
                if isinstance(result, ActionResult):
                    return result
                return ActionResult(
                    step_id=str(step_id),
                    success=True,
                    output=result,
                )

            self._core_registry.register(name, core_handler, risk_class=risk_class)
            return

        if name in self._tools:
            raise ValueError("capability_already_registered")

        self._tools[name] = handler
        self._risks[name] = risk_class

    def resolve(self, name: str) -> Optional[Callable]:
        if self._core_registry is not None:
            return self._core_registry.resolve(name)

        return self._tools.get(name)

    def risk(self, name: str):
        if self._core_registry is not None:
            return self._core_registry.risk(name)
        return self._risks.get(name)

    def names(self):
        if self._core_registry is not None:
            return self._core_registry.names()

        return tuple(sorted(self._tools))
