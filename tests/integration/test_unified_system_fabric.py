from core.identity import AgentIdentityAuthority
from core.system_fabric import CanonicalSystemFabric


def test_system_fabric_binds_and_authorizes_session():
    fabric = CanonicalSystemFabric()
    binding = fabric.bind_session(
        session_id="session:test",
        client_id="noryx-web",
        device_id="gateway",
        role="client",
    )
    assert binding.identity_id == "noryx-web"
    authorized = fabric.authorize("session:test", "execute")
    assert authorized.identity_id == "noryx-web"
    assert authorized.session_id == "session:test"


def test_system_fabric_records_digest_only_execution_metadata():
    fabric = CanonicalSystemFabric()
    record = fabric.record_execution(
        execution_id="exec:test",
        client_id="noryx-web",
        phase="gateway_completed",
        metadata={"verified": True},
    )
    assert record.record_id == "execution:exec:test:gateway_completed"
    assert record.level.value == "l3_distributed"
    assert len(record.payload_digest) == 64
    assert len(record.provenance_digest) == 64


def test_system_fabric_health_is_canonical():
    fabric = CanonicalSystemFabric()
    health = fabric.health()
    assert health["system_id"] == "NORYX7"
    assert health["creator"] == "Adrian Aristodemo"
    assert health["provenance"] == "OFFICIAL_NORYX7"


def test_system_fabric_binds_and_authorizes_agent_identity():
    fabric = CanonicalSystemFabric()
    identity, _ = AgentIdentityAuthority.generate("agent-test")
    binding = fabric.bind_agent_identity(identity)
    assert binding.identity_id == "agent-test"
    assert binding.role == "agent"
    assert binding.capabilities == ("execute",)
    authorized = fabric.authorize_agent(identity, "execute")
    assert authorized.session_id == fabric.agent_session_id(identity)


def test_system_fabric_agent_binding_is_key_bound():
    fabric = CanonicalSystemFabric()
    first, _ = AgentIdentityAuthority.generate("agent-test")
    second, _ = AgentIdentityAuthority.generate("agent-test")
    first_binding = fabric.bind_agent_identity(first)
    second_binding = fabric.bind_agent_identity(second)
    assert first_binding.session_id != second_binding.session_id
    assert fabric.authorize_agent(first, "execute").authorization_digest != fabric.authorize_agent(second, "execute").authorization_digest


def test_system_fabric_agent_capability_denial_is_fail_closed():
    fabric = CanonicalSystemFabric()
    identity, _ = AgentIdentityAuthority.generate("agent-test")
    fabric.bind_agent_identity(identity, capabilities=("observe",))
    try:
        fabric.authorize_agent(identity, "execute")
    except PermissionError as exc:
        assert str(exc) == "capability_not_granted"
    else:
        raise AssertionError("agent capability unexpectedly authorized")
