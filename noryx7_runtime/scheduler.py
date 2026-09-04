from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import PlanStep


@dataclass(frozen=True)
class ScheduledStep:
    index: int
    step: PlanStep


class Scheduler:
    """Deterministic scheduler for dependency-safe plan execution."""

    def schedule(self, steps: Sequence[PlanStep]) -> tuple[ScheduledStep, ...]:
        by_id = {step.step_id: step for step in steps}
        if len(by_id) != len(steps):
            raise ValueError("duplicate step id")
        known = set(by_id)
        for step in steps:
            unknown = set(step.dependencies) - known
            if unknown:
                raise ValueError("unknown step dependency")
        remaining = set(by_id)
        result: list[ScheduledStep] = []
        while remaining:
            ready = sorted(
                step_id for step_id in remaining
                if all(dep not in remaining for dep in by_id[step_id].dependencies)
            )
            if not ready:
                raise ValueError("cyclic plan dependencies")
            for step_id in ready:
                result.append(ScheduledStep(len(result), by_id[step_id]))
            remaining.difference_update(ready)
        return tuple(result)
