"""Shared, dependency-light boundaries for the NORYX ecosystem."""

from .global_scale import (
    Capacity,
    Cell,
    CellRegistry,
    DegradationController,
    DegradationMode,
    DisasterRecoveryPlan,
    ElasticComputeFabric,
    EventFabric,
    GlobalControlPlane,
    GlobalTrafficRouter,
    Health,
    LanguageContext,
    LanguageFabric,
    ObservabilityFabric,
    ResourceBudget,
    ResourceController,
    SelfHealingController,
    SyntheticScenario,
    SyntheticTestingGrid,
    WorkClass,
    WorkRequest,
)

__all__ = [
    "Capacity", "Cell", "CellRegistry", "DegradationController", "DegradationMode",
    "DisasterRecoveryPlan", "ElasticComputeFabric", "EventFabric", "GlobalControlPlane",
    "GlobalTrafficRouter", "Health", "LanguageContext", "LanguageFabric", "ObservabilityFabric",
    "ResourceBudget", "ResourceController", "SelfHealingController", "SyntheticScenario",
    "SyntheticTestingGrid", "WorkClass", "WorkRequest",
]
