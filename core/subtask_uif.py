from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import TaskSpec, VerificationResult
from .decomposition import Subtask
from .universal_intelligence import SpecialistRoute, UniversalIntelligenceFabric


@dataclass(frozen=True)
class SubtaskRoute:
    subtask_id: str
    route: SpecialistRoute
    route_authority: bool = False

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.subtask_id, str)
            and bool(self.subtask_id.strip())
            and isinstance(self.route, SpecialistRoute)
            and self.route.is_well_formed()
            and isinstance(self.route_authority, bool)
            and self.route_authority is False
        )


@dataclass(frozen=True)
class SubtaskRouteSet:
    task_id: str
    routes: tuple[SubtaskRoute, ...]
    verification: VerificationResult


class SubtaskUIFRouter:
    """Route each bounded subtask independently; routing never grants authority."""

    def __init__(self, fabric: UniversalIntelligenceFabric | None = None):
        self.fabric = fabric or UniversalIntelligenceFabric()
        if not isinstance(self.fabric, UniversalIntelligenceFabric):
            raise TypeError("invalid_universal_intelligence_fabric")

    def route(self, task: TaskSpec, subtasks: tuple[Subtask, ...]) -> SubtaskRouteSet:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return SubtaskRouteSet("", (), VerificationResult(False, "subtask_routing", "invalid_task"))
        if not isinstance(subtasks, tuple) or not subtasks:
            return SubtaskRouteSet(task.task_id, (), VerificationResult(False, "subtask_routing", "invalid_subtasks"))
        routes: list[SubtaskRoute] = []
        seen: set[str] = set()
        for subtask in subtasks:
            if not isinstance(subtask, Subtask):
                return SubtaskRouteSet(task.task_id, tuple(routes), VerificationResult(False, "subtask_routing", "invalid_subtask"))
            if subtask.subtask_id in seen or not subtask.subtask_id.startswith(task.task_id + ":"):
                return SubtaskRouteSet(task.task_id, tuple(routes), VerificationResult(False, "subtask_routing", "subtask_identity_invalid"))
            child = TaskSpec(
                subtask.subtask_id,
                subtask.task_type,
                subtask.objective,
                task.input,
                task.constraints,
                task.verification_requirements,
                task.risk_class,
                task.execution_id,
            )
            try:
                route = self.fabric.route(child)
            except Exception:
                return SubtaskRouteSet(task.task_id, tuple(routes), VerificationResult(False, "subtask_routing", "subtask_route_failure"))
            routes.append(SubtaskRoute(subtask.subtask_id, route, False))
            seen.add(subtask.subtask_id)
        return SubtaskRouteSet(task.task_id, tuple(routes), VerificationResult(True, "subtask_routing", "subtask_routes_ok"))

    @staticmethod
    def constraints_for(task: TaskSpec, route: SubtaskRoute) -> dict[str, Any]:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        if not isinstance(route, SubtaskRoute) or not route.is_well_formed():
            raise ValueError("invalid_subtask_route")
        constraints = dict(task.constraints)
        constraints.update(
            {
                "_noryx7_subtask_id": route.subtask_id,
                "_noryx7_specialist_domain": route.route.domain,
                "_noryx7_cognitive_strategy": route.route.strategy,
                "_noryx7_cognitive_budget": route.route.budget,
                "_noryx7_route_authority": False,
            }
        )
        return constraints
