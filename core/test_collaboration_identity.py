import pytest

from core.collaboration import AgentCollaboration
from core.contracts import AgentResult, TaskSpec, VerificationResult
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.verification import VerificationEngine


class CollaboratingAgent:
    def __init__(self, agent_id, identity, outputs, on_run=None):
        self.agent_id = agent_id
        self.identity = identity
        self.outputs = list(outputs)
        self.on_run = on_run
        self.calls = 0

    def run(self, task):
        self.calls += 1
        if self.on_run:
            self.on_run(self, task)
        output = self.outputs.pop(0)
        return AgentResult(self.agent_id, task.task_id, "completed", output,
                           VerificationResult(True, "agent_result", "verified"),
                           task.execution_id)


def make_agents(registry, primary_hook=None):
    primary_id, _ = AgentIdentityAuthority.generate("primary")
    secondary_id, _ = AgentIdentityAuthority.generate("secondary")
    registry.register(primary_id)
    registry.register(secondary_id)
    primary = CollaboratingAgent("primary", primary_id, ["proposal", "reconciled answer"], primary_hook)
    secondary = CollaboratingAgent("secondary", secondary_id, ["APPROVE\nEvidence supports the proposal"])
    return primary, secondary


def test_collaboration_revalidates_trusted_agents_for_each_turn():
    registry = IdentityRegistry()
    primary, secondary = make_agents(registry)
    result, check = AgentCollaboration(VerificationEngine(), identity_registry=registry).run(
        TaskSpec("task-1", "compute", "objective", "input", execution_id="exec-1"),
        primary, secondary,
    )
    assert check.valid
    assert result.output == "reconciled answer"
    assert primary.calls == 2
    assert secondary.calls == 1


def test_revocation_during_primary_inference_discards_agent_output():
    registry = IdentityRegistry()
    def revoke_during_call(agent, task):
        registry.revoke(agent.agent_id)
    primary, secondary = make_agents(registry, revoke_during_call)
    collaboration = AgentCollaboration(VerificationEngine(), identity_registry=registry)
    with pytest.raises(PermissionError, match="collaboration_agent_identity_untrusted"):
        collaboration.run(TaskSpec("task-2", "compute", "objective", "input", execution_id="exec-2"),
                          primary, secondary)
    assert primary.calls == 1
    assert secondary.calls == 0


def test_untrusted_secondary_is_rejected_before_critique_call():
    registry = IdentityRegistry()
    primary, secondary = make_agents(registry)
    registry.revoke("secondary")
    collaboration = AgentCollaboration(VerificationEngine(), identity_registry=registry)
    with pytest.raises(PermissionError, match="collaboration_agent_identity_untrusted"):
        collaboration.run(TaskSpec("task-3", "compute", "objective", "input", execution_id="exec-3"),
                          primary, secondary)
    assert primary.calls == 1
    assert secondary.calls == 0


def test_agent_id_must_match_registered_identity_before_inference():
    registry = IdentityRegistry()
    mismatched_identity, _ = AgentIdentityAuthority.generate("registered-primary")
    secondary_identity, _ = AgentIdentityAuthority.generate("secondary")
    registry.register(mismatched_identity)
    registry.register(secondary_identity)
    primary = CollaboratingAgent(
        "primary", mismatched_identity, ["proposal", "reconciled answer"]
    )
    secondary = CollaboratingAgent(
        "secondary", secondary_identity, ["APPROVE\\nEvidence supports the proposal"]
    )

    collaboration = AgentCollaboration(VerificationEngine(), identity_registry=registry)
    with pytest.raises(PermissionError, match="identity_untrusted"):
        collaboration.run(
            TaskSpec("task-4", "compute", "objective", "input", execution_id="exec-4"),
            primary,
            secondary,
        )
    assert primary.calls == 0


def test_replacing_agent_with_another_trusted_identity_discards_result():
    registry = IdentityRegistry()
    replacement_identity, _ = AgentIdentityAuthority.generate("replacement")
    registry.register(replacement_identity)

    def replace_during_call(agent, task):
        agent.identity = replacement_identity
        agent.agent_id = replacement_identity.agent_id

    primary, secondary = make_agents(registry, replace_during_call)
    collaboration = AgentCollaboration(VerificationEngine(), identity_registry=registry)

    with pytest.raises(PermissionError, match="identity_changed"):
        collaboration.run(
            TaskSpec("task-5", "compute", "objective", "input", execution_id="exec-5"),
            primary,
            secondary,
        )
    assert primary.calls == 1
    assert secondary.calls == 0


def test_revoke_and_reregister_same_identity_during_inference_is_rejected():
    registry = IdentityRegistry()
    def revoke_and_reregister(agent, task):
        registry.revoke(agent.agent_id)
        registry.register(agent.identity)
    primary, secondary = make_agents(registry, revoke_and_reregister)
    collaboration = AgentCollaboration(VerificationEngine(), identity_registry=registry)
    with pytest.raises(PermissionError, match="identity_changed"):
        collaboration.run(
            TaskSpec("task-epoch", "compute", "objective", "input", execution_id="exec-epoch"),
            primary,
            secondary,
        )
    assert primary.calls == 1
    assert secondary.calls == 0
