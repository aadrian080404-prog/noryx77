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
