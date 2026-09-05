"""Canonical structural registry for the NORYX7 architecture."""
from __future__ import annotations

from .architecture_gate import ArchitectureCompletenessGate, ArchitecturePlane, PlaneDefinition


def _p(plane, contract, implementation, integration, trust, failure, budget, observability, recovery, verification, regression):
    return PlaneDefinition(plane, contract, implementation, integration, trust, failure, budget, observability, recovery, verification, regression)


CANONICAL_DEFINITIONS = {
    ArchitecturePlane.INGRESS: _p(ArchitecturePlane.INGRESS, "bounded TaskSpec/input", "contracts.py, limits.py", "runtime.py", "untrusted until contract verification", "reject malformed/oversized input", "input bounds", "audit rejection", "no mutation", "contract/adversarial tests", "ingress regression"),
    ArchitecturePlane.UNDERSTANDING: _p(ArchitecturePlane.UNDERSTANDING, "consent-bound understanding", "user_understanding.py, interaction_context.py", "runtime/orchestration", "raw content is not persistent authority", "deny without consent/bounds", "content/signal limits", "context audit", "discard transient content", "consent/isolation tests", "privacy regression"),
    ArchitecturePlane.COGNITION: _p(ArchitecturePlane.COGNITION, "bounded HYPERSYNTH phases", "hypersynth.py, reasoning.py, metacognition.py", "runtime/orchestration", "model output is untrusted proposal", "reject failed cognitive checks", "step/agent/deadline limits", "phase audit", "terminate without commit", "adversarial cognitive tests", "phase-order regression"),
    ArchitecturePlane.PLANNING: _p(ArchitecturePlane.PLANNING, "verified DAG plan", "planning.py, decomposition.py", "HYPERSYNTH/runtime", "plans cannot authorize themselves", "reject malformed/cyclic plans", "plan/action bounds", "plan audit", "discard invalid plan", "dependency/cycle tests", "planner regression"),
    ArchitecturePlane.ROUTING: _p(ArchitecturePlane.ROUTING, "policy-constrained resource selection", "router.py", "runtime/distribution", "router has no authorization authority", "deny invalid/unavailable route", "resource/latency bounds", "routing audit", "trusted fallback only", "routing-policy tests", "route regression"),
    ArchitecturePlane.AGENTS: _p(ArchitecturePlane.AGENTS, "identity-bound AgentResult", "agents.py, supervisor.py, coordination.py, agent_mesh.py", "router/execution gates", "agents receive scoped delegation", "reject identity/task/execution mismatch", "agent/execution bounds", "assignment/result audit", "stop/revoke agent", "agent isolation tests", "identity regression"),
    ArchitecturePlane.CAPABILITIES: _p(ArchitecturePlane.CAPABILITIES, "scoped capability grants", "tools.py, device.py", "action/tool gates", "least-privilege authority", "unknown/expired/revoked denied", "scope/expiry/call limits", "grant/use/revoke audit", "revoke and terminate", "escalation tests", "capability regression"),
    ArchitecturePlane.TOOLS: _p(ArchitecturePlane.TOOLS, "typed tool boundary", "tools.py, actions.py", "capability/policy gates", "adapters are untrusted surfaces", "reject malformed/unauthorized calls", "argument/output/call bounds", "tool audit", "sandbox/quarantine", "tool injection tests", "adapter regression"),
    ArchitecturePlane.MEMORY: _p(ArchitecturePlane.MEMORY, "bounded provenance-bearing memory", "memory.py, secure_memory.py", "runtime/HYPERSYNTH commit", "memory is data, never authority", "reject unsafe persistence", "item/count/retention limits", "memory provenance", "quarantine/restore trusted snapshot", "poisoning/isolation tests", "memory regression"),
    ArchitecturePlane.RUNTIME: _p(ArchitecturePlane.RUNTIME, "controlled lifecycle/execution identity", "runtime.py, limits.py", "all execution planes", "runtime cannot bypass policy", "fail closed on exceptions/deadlines", "time/action/output budgets", "lifecycle audit", "cancel/terminate/recover", "race/failure tests", "runtime regression"),
    ArchitecturePlane.SECURITY: _p(ArchitecturePlane.SECURITY, "zero-trust identity/channel/auth", "security.py, crypto.py, trust_chain.py, authorization_replay.py, multiauth.py", "every privileged boundary", "untrusted until identity/channel/policy/auth valid", "deny auth/replay/binding failures", "crypto/session/replay bounds", "security events", "lockdown/revoke/isolate", "protocol/adversarial tests", "security regression"),
    ArchitecturePlane.STATE: _p(ArchitecturePlane.STATE, "verified state transition/commit", "state.py, orchestration.py", "runtime/verification/memory", "only verified results commit", "reject stale/reordered/unverified commit", "journal/transaction bounds", "commit audit", "rollback/recovery snapshot", "tamper/order/replay tests", "state regression"),
    ArchitecturePlane.DISTRIBUTION: _p(ArchitecturePlane.DISTRIBUTION, "trusted node/shard topology", "distributed.py, device.py", "Device-Edge-Cloud", "remote nodes require trust evidence", "partition/trust failure degrades safely", "node/shard/message bounds", "partition telemetry", "offline/degraded/rejoin", "partition/identity tests", "distributed regression"),
    ArchitecturePlane.INTERFACES: _p(ArchitecturePlane.INTERFACES, "explicit surface contracts", "platform.py, JARVIS, NORYX Browser", "interaction/orchestration", "interfaces cannot bypass gates", "reject malformed/unauthorized requests", "request/response limits", "interface audit", "disable compromised surface", "boundary/permission tests", "interface regression"),
    ArchitecturePlane.AUDIT: _p(ArchitecturePlane.AUDIT, "tamper-evident provenance", "audit.py, observability.py", "security/runtime transitions", "audit is evidence, not authority", "integrity failure handled fail-closed where required", "event/chain bounds", "authenticated event chain", "trusted checkpoint restore", "tamper/completeness tests", "audit regression"),
    ArchitecturePlane.RECOVERY: _p(ArchitecturePlane.RECOVERY, "incident state/recovery contract", "recovery.py, defense.py", "security/runtime/distribution", "recovery controls outrank affected workloads", "contain/lockdown unsafe recovery", "attempt/time bounds", "incident audit", "offline restore/revocation/re-attestation", "lockdown/recovery tests", "recovery regression"),
    ArchitecturePlane.PERFORMANCE: _p(ArchitecturePlane.PERFORMANCE, "bounded resource/latency contract", "limits.py/runtime boundaries", "every pipeline stage", "exhaustion is unsafe", "terminate or degrade safely", "CPU/time/memory/output/action budgets", "resource metrics", "safe restart/degrade", "load/endurance tests", "performance regression"),
    ArchitecturePlane.UNIVERSAL_INTELLIGENCE: _p(ArchitecturePlane.UNIVERSAL_INTELLIGENCE, "domain evidence/uncertainty contracts", "domain fabrics/reasoning/evaluation", "HYPERSYNTH specialist routing", "specialists cannot self-authorize", "contradiction/uncertainty blocks unsafe commit", "domain/model/evidence bounds", "evidence/uncertainty audit", "safer fallback/human escalation", "cross-domain contradiction tests", "domain regression"),
}


def canonical_gate():
    return ArchitectureCompletenessGate(CANONICAL_DEFINITIONS)


def require_structural_completeness():
    canonical_gate().require_complete()
