"""Scientific-computing capability boundary for NORYX7.

Navier-Stokes is exposed as a bounded numerical capability. The fabric does
not claim a numerical simulation solves the mathematical 3-D existence and
regularity problem; verification remains an independent admission boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .contracts import TaskSpec, VerificationResult


@dataclass(frozen=True)
class PDEProblem:
    equation: str
    dimension: int
    density: float
    viscosity: float
    boundary_conditions: tuple[str, ...]
    initial_conditions: tuple[str, ...]
    time_step: float
    spatial_resolution: int

    def is_well_formed(self) -> bool:
        return (
            self.equation in {"navier_stokes_incompressible", "navier_stokes_compressible"}
            and self.dimension in {2, 3}
            and self.density > 0.0
            and self.viscosity > 0.0
            and self.time_step > 0.0
            and self.spatial_resolution >= 2
            and bool(self.boundary_conditions)
            and bool(self.initial_conditions)
        )


@dataclass(frozen=True)
class SimulationResult:
    method: str
    residual: float
    divergence_error: float
    conservation_error: float
    converged: bool
    field_digest: str


class ScientificFabric:
    """Route scientific simulations through the same contract/verification model."""

    CAPABILITIES = (
        "symbolic_mathematics",
        "linear_algebra",
        "differential_equations",
        "numerical_pde",
        "fluid_dynamics",
        "navier_stokes",
    )

    def classify(self, task: TaskSpec) -> str:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        text = f"{task.objective} {task.input or ''}".lower()
        if "navier-stokes" in text or "navier stokes" in text:
            return "navier_stokes"
        if any(token in text for token in ("fluid", "flow", "reynolds")):
            return "fluid_dynamics"
        if any(token in text for token in ("pde", "partial differential", "differential equation")):
            return "numerical_pde"
        return "scientific_research"

    def verify_simulation(self, task: TaskSpec, result: SimulationResult) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return VerificationResult(False, "scientific_simulation", "invalid_task")
        if not isinstance(result, SimulationResult):
            return VerificationResult(False, "scientific_simulation", "invalid_simulation_result")
        if result.residual < 0.0 or result.divergence_error < 0.0 or result.conservation_error < 0.0:
            return VerificationResult(False, "scientific_simulation", "negative_error_metric")
        valid = result.converged and result.residual <= 1e-3 and result.divergence_error <= 1e-3 and result.conservation_error <= 1e-2
        return VerificationResult(valid, "scientific_simulation", "independent_numerical_checks_passed" if valid else "numerical_checks_failed", (f"method={result.method}", f"residual={result.residual:.3e}", f"divergence={result.divergence_error:.3e}", f"conservation={result.conservation_error:.3e}"))

    def execute(self, task: TaskSpec, problem: PDEProblem, solver: Callable[[PDEProblem], SimulationResult]) -> tuple[SimulationResult, VerificationResult]:
        capability = self.classify(task)
        if capability != "navier_stokes":
            raise ValueError("unsupported_scientific_capability")
        if not problem.is_well_formed():
            return SimulationResult("none", float("inf"), float("inf"), float("inf"), False, ""), VerificationResult(False, "scientific_simulation", "invalid_pde_problem")
        result = solver(problem)
        return result, self.verify_simulation(task, result)
