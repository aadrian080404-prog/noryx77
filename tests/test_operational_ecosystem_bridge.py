from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.memory import MemoryStore
from ecosystem.global_fabric import MemoryLevel
from ecosystem.operational_bridge import OperationalEcosystemBridge


def test_operational_bridge_binds_trusted_agent_and_indexes_verified_result():
    registry = IdentityRegistry()
    identity, _ = AgentIdentityAuthority.generate("agent-test")
    registry.register(identity)
    bridge = OperationalEcosystemBridge(
        runtime_id="runtime-test",
        identity_registry=registry,
        memory=MemoryStore(),
    )

    bridge.bind_agent(
        agent_id="agent-test",
        role="primary",
        capabilities=("agent_execution",),
    )
    bridge.record_result(
        task_id="task-test",
        execution_id="exec-test",
        agent_id="agent-test",
        output="verified output",
    )

    authorization = bridge.identity.authorize(
        "agent-test",
        "agent_execution",
        bridge._policy_digest(),
    )
    record = bridge.memory_index.get("execution:exec-test")

    assert authorization.identity_id == "agent-test"
    assert authorization.role == "primary"
    assert record.level is MemoryLevel.L3_DISTRIBUTED
    assert record.replicas == ("runtime:runtime-test", "agent:agent-test")


def test_operational_bridge_never_indexes_empty_or_untrusted_execution():
    registry = IdentityRegistry()
    bridge = OperationalEcosystemBridge(
        runtime_id="runtime-test",
        identity_registry=registry,
        memory=MemoryStore(),
    )

    try:
        bridge.bind_agent(agent_id="missing-agent", role="primary")
    except PermissionError as exc:
        assert str(exc) == "agent_identity_not_trusted"
    else:
        raise AssertionError("untrusted agent must not be bound")

    try:
        bridge.record_result(
            task_id="task-test",
            execution_id="exec-test",
            agent_id="agent-test",
            output="",
        )
    except ValueError as exc:
        assert str(exc) == "verified_output_required"
    else:
        raise AssertionError("empty output must not be indexed")
