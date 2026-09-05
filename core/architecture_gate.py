"""Executable structural-completeness gate for NORYX7.

The gate is intentionally independent of runtime execution. It verifies that
all mandatory architectural planes have an explicit implementation boundary,
trust boundary, failure semantics, recovery path, observability contract and
verification target before the system can be frozen.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ArchitecturePlane(str, Enum):
    INGRESS = "ingress"
    UNDERSTANDING = "understanding"
    COGNITION = "cognition"
    PLANNING = "planning"
    ROUTING = "routing"
    AGENTS = "agents"
    CAPABILITIES = "capabilities"
    TOOLS = "tools"
    MEMORY = "memory"
    RUNTIME = "runtime"
    SECURITY = "security"
    STATE = "state"
    DISTRIBUTION = "distribution"
    INTERFACES = "interfaces"
    AUDIT = "audit"
    RECOVERY = "recovery"
    PERFORMANCE = "performance"
    UNIVERSAL_INTELLIGENCE = "universal_intelligence"


REQUIRED_ATTRIBUTES = (
    "contract",
    "implementation_boundary",
    "integration_boundary",
    "trust_boundary",
    "failure_semantics",
    "resource_budget",
    "observability",
    "recovery_path",
    "verification_target",
    "regression_target",
)


@dataclass(frozen=True)
class PlaneDefinition:
    plane: ArchitecturePlane
    contract: str
    implementation_boundary: str
    integration_boundary: str
    trust_boundary: str
    failure_semantics: str
    resource_budget: str
    observability: str
    recovery_path: str
    verification_target: str
    regression_target: str

    def validate(self) -> None:
        for name in REQUIRED_ATTRIBUTES:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"missing_{name}:{self.plane.value}")


@dataclass(frozen=True)
class ArchitectureGateResult:
    complete: bool
    missing: tuple[str, ...]
    invalid: tuple[str, ...]


class ArchitectureCompletenessGate:
    """Fail-closed structural gate; it never performs execution or authorization."""

    def __init__(self, definitions: Mapping[ArchitecturePlane, PlaneDefinition]):
        if not isinstance(definitions, Mapping):
            raise TypeError("definitions_mapping_required")
        self._definitions = dict(definitions)

    def evaluate(self) -> ArchitectureGateResult:
        missing = tuple(p.value for p in ArchitecturePlane if p not in self._definitions)
        invalid = []
        for plane, definition in self._definitions.items():
            if not isinstance(plane, ArchitecturePlane) or not isinstance(definition, PlaneDefinition):
                invalid.append(str(getattr(plane, "value", plane)))
                continue
            try:
                definition.validate()
            except (TypeError, ValueError) as exc:
                invalid.append(f"{plane.value}:{exc}")
        return ArchitectureGateResult(not missing and not invalid, missing, tuple(invalid))

    def require_complete(self) -> None:
        result = self.evaluate()
        if not result.complete:
            raise RuntimeError(
                "architecture_incomplete:" + ",".join(result.missing + result.invalid)
            )


# Canonical structural registry. Concrete implementations remain responsible
# for their own runtime behavior; this registry prevents undocumented planes.
CANONICAL_PLANES = tuple(ArchitecturePlane)
