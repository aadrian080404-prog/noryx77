from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import AgentResult, TaskSpec, VerificationResult
from .decomposition import Subtask
from .universal_intelligence import SpecialistRoute, UniversalIntelligenceFabric


@dataclass(frozen=True)
class SubtaskRoute:
    subtask_id: str
    route: SpecialistRoute

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.subtask_id, str)
            and bool(self.subtask_id.strip())
            and isinstance(self.route, SpecialistRoute)
            and self.route.is_well_formed()
        )


@dataclass(frozen=True)
class SubtaskRouteSet:
    task_id: str
    routes: tuple[SubtaskRoute, ...]
    verification: VerificationResult

    def route_for(self, subtask_id: str) -> SubtaskRoute | None:
        for item in self.routes:
            if item.subtask_id == subtask_id:
                return item
        return None


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
            routes.append(SubtaskRoute(subtask.subtask_id, route))
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

    @staticmethod
    def aggregate_verification(task: TaskSpec, routes: SubtaskRouteSet, results: tuple[AgentResult, ...]) -> VerificationResult:
        """Fail closed unless every routed subtask has one verified result."""
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return VerificationResult(False, "subtask_aggregate", "invalid_task")
        if not isinstance(routes, SubtaskRouteSet) or routes.task_id != task.task_id or not routes.verification.valid:
            return VerificationResult(False, "subtask_aggregate", "subtask_routes_not_verified")
        if not isinstance(results, tuple) or len(results) != len(routes.routes):
            return VerificationResult(False, "subtask_aggregate", "subtask_result_count_mismatch")
        expected = tuple(item.subtask_id for item in routes.routes)
        actual = tuple(getattr(item, "task_id", "") for item in results)
        if actual != expected:
            return VerificationResult(False, "subtask_aggregate", "subtask_result_order_mismatch")
        for result in results:
            if not isinstance(result, AgentResult):
                return VerificationResult(False, "subtask_aggregate", "subtask_result_invalid")
            if result.execution_id != task.execution_id:
                return VerificationResult(False, "subtask_aggregate", "subtask_execution_identity_mismatch")
            if result.status != "completed":
                return VerificationResult(False, "subtask_aggregate", "subtask_not_completed")
            if not isinstance(result.verification, VerificationResult) or not result.verification.is_well_formed() or not result.verification.valid:
                return VerificationResult(False, "subtask_aggregate", "subtask_verification_failed")
        return VerificationResult(True, "subtask_aggregate", "subtask_aggregate_verified")
