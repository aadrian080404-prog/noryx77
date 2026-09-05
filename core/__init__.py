from .actions import ActionDecision, ActionGate
from .adversarial import AdversarialEngine, AttackOutcome, AttackScenario
from .agents import Agent, DeterministicAgent
from .alerting import AlertChannel, AlertRouter, AlertSeverity, EscalationPolicy, SecurityAlert
from .audit import AuditLog
from .authorization_replay import AuthorizationReplayGuard
from .context import ContextManager, ContextSnapshot
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .coordination import AgentAssignment, AgentCoordinator
from .defense import (
    AccessRequest, DefenseController, DefenseDecision, DefenseMode,
    ImmutableCoreManifest, OfflineArtifact, OfflineRecoveryCatalog,
    SegmentationPolicy, SecurityEvent, TrustDecision,
)
from .decomposition import Subtask, TaskDecomposer
from .device import CapabilityGrant, DeviceAction, DeviceCapabilityGate, DeviceIdentity, DeviceRole, DeviceRuntimeBoundary, DeviceTrust
from .distributed import DistributedTopology, NodeDescriptor, NodeRole, ShardDescriptor
from .egress import EgressPolicy, EgressRequest
from .errors import ContractViolation, NORYXError, PolicyDenied, RouteError, VerificationFailure
from .evaluation import EvaluationDimension, EvaluationMatrix, EvaluationResult
from .hypersynth import CognitiveState, Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .memory import MemoryStore
from .metacognition import MetacognitiveReflection
from .multiauth import AuthorizationProof, SignedApproval, SignedApprovalAuthority, SignedAuthorizationProof, ThresholdAuthorizer, action_digest, sign_approval
from .observability import EventKind, ObservedEvent, SecurityEventBus
from .personality import ApollonianPersonality, PersonalityProfile
from .perimeter import PerimeterPolicy, TrafficDirection, TrafficRequest
from .planning import Plan, PlanStep, Planner
from .platform import AssistantIntegrationBoundary, InteractionKind, PlatformAction, PlatformAdapter, PlatformKind, PlatformRequest
from .policy import PolicyEngine
from .reasoning import CrossChecker, Hypothesis, HypothesisEngine, InternalSimulator, SimulationResult
from .recovery_plane import RecoveryController, RecoveryState
from .router import ResourceRouter
from .runtime import NORYXRuntime
from .sandbox import Sandbox, SandboxProfile, SandboxState
from .secure_boot import SecureBootChain, TrustAnchor
from .security import SecurityBoundary, SecurityDecision
from .self_improvement import ImprovementPipeline, ImprovementProposal, ImprovementStage
from .supervisor import AgentDecision, AgentSupervisor
from .supply_chain import ArtifactManifest, SupplyChainVerifier, manifest_digest
from .tools import CapabilityRegistry, ToolExecutor
from .verification import VerificationEngine

__all__ = [
    "AccessRequest", "ActionDecision", "ActionGate", "ActionSpec", "AdversarialEngine", "Agent", "AgentAssignment",
    "AgentCoordinator", "AgentDecision", "AgentResult", "AgentSupervisor", "AlertChannel", "AlertRouter", "AlertSeverity",
    "ApollonianPersonality", "ArtifactManifest", "AttackOutcome", "AttackScenario", "AuditLog", "AuthorizationProof",
    "AuthorizationReplayGuard", "CapabilityGrant", "CapabilityRegistry", "ContextManager", "ContextSnapshot", "ContractViolation",
    "CognitiveState", "CrossChecker", "DefenseController", "DefenseDecision", "DefenseMode", "DeterministicAgent",
    "DeviceAction", "DeviceCapabilityGate", "DeviceIdentity", "DeviceRole", "DeviceRuntimeBoundary", "DeviceTrust",
    "DistributedTopology", "EgressPolicy", "EgressRequest", "EvaluationDimension", "EvaluationMatrix", "EvaluationResult",
    "EventKind", "EscalationPolicy", "Hypersynth", "HypersynthRuntime", "Hypothesis", "HypothesisEngine", "ImmutableCoreManifest",
    "ImprovementPipeline", "ImprovementProposal", "ImprovementStage", "InteractionKind", "InternalSimulator", "MemoryStore",
    "MetacognitiveReflection", "NodeDescriptor", "NodeRole", "NORYXError", "NORYXRuntime", "ObservedEvent", "OfflineArtifact",
    "OfflineRecoveryCatalog", "PersonalityProfile", "PerimeterPolicy", "Plan", "PlanStep", "Planner", "PlatformAction",
    "PlatformAdapter", "PlatformKind", "PlatformRequest", "PolicyDenied", "PolicyEngine", "RecoveryController", "RecoveryState",
    "ResourceRouter", "RouteError", "RuntimeLimits", "Sandbox", "SandboxProfile", "SandboxState", "SecureBootChain",
    "SecurityAlert", "SecurityBoundary", "SecurityDecision", "SecurityEvent", "SecurityEventBus", "SegmentationPolicy",
    "ShardDescriptor", "SignedApproval", "SignedApprovalAuthority", "SignedAuthorizationProof", "SimulationResult", "Subtask",
    "SupplyChainVerifier", "TaskDecomposer", "TaskSpec", "ThresholdAuthorizer", "ToolExecutor", "TrafficDirection", "TrafficRequest",
    "TrustAnchor", "TrustDecision", "VerificationEngine", "VerificationFailure", "VerificationResult", "action_digest", "manifest_digest",
    "sign_approval",
]

# Architecture expansion marker: hierarchical memory is represented by MemoryStore + policy tiers pending dedicated module consolidation.
