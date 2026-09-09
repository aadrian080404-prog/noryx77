"""Shared, dependency-light boundaries for the NORYX ecosystem."""

from .closure_contract import CLOSURE_CONTRACTS, FrontClosure, require_contract_shape
from .global_fabric import GlobalIdentityAuthorizationFabric, GlobalMemoryFabric, IdentityAuthorization, MemoryLevel, MemoryRecord
from .global_scale import (
    Capacity, Cell, CellRegistry, DegradationController, DegradationMode, DisasterRecoveryPlan,
    ElasticComputeFabric, EventFabric, GlobalControlPlane, GlobalTrafficRouter, Health,
    LanguageContext, LanguageFabric, ObservabilityFabric, ResourceBudget, ResourceController,
    SelfHealingController, SyntheticScenario, SyntheticTestingGrid, WorkClass, WorkRequest,
)
from .operational_bridge import OperationalEcosystemBridge, OperationalFabricSnapshot

__all__ = [
    "CLOSURE_CONTRACTS", "FrontClosure", "require_contract_shape",
    "GlobalIdentityAuthorizationFabric", "GlobalMemoryFabric", "IdentityAuthorization", "MemoryLevel", "MemoryRecord",
    "Capacity", "Cell", "CellRegistry", "DegradationController", "DegradationMode", "DisasterRecoveryPlan",
    "ElasticComputeFabric", "EventFabric", "GlobalControlPlane", "GlobalTrafficRouter", "Health",
    "LanguageContext", "LanguageFabric", "ObservabilityFabric", "ResourceBudget", "ResourceController",
    "SelfHealingController", "SyntheticScenario", "SyntheticTestingGrid", "WorkClass", "WorkRequest",
    "OperationalEcosystemBridge", "OperationalFabricSnapshot",
]
