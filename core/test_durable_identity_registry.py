import concurrent.futures
import threading

import pytest

from core.identity import (
    AgentIdentityAuthority,
    SQLiteIdentityRegistry,
)


def test_trust_registry_survives_restart_and_persists_revocation(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-1")
    registry = SQLiteIdentityRegistry(path)
    registry.register(identity)
    assert registry.is_trusted(identity)
    registry.close()

    reopened = SQLiteIdentityRegistry(path)
    assert reopened.is_trusted(identity)
    reopened.revoke("agent-1")
    reopened.close()

    restored = SQLiteIdentityRegistry(path)
    assert not restored.is_trusted(identity)
    assert restored.snapshot() == ()
    restored.close()


def test_registry_rejects_duplicate_and_malformed_identities(tmp_path):
    registry = SQLiteIdentityRegistry(str(tmp_path / "identity.sqlite"))
    identity, _ = AgentIdentityAuthority.generate("agent-1")
    registry.register(identity)
    with pytest.raises(ValueError, match="already_registered"):
        registry.register(identity)
    malformed = type(identity)("agent-2", b"x")
    with pytest.raises(ValueError, match="invalid_agent_identity"):
        registry.register(malformed)
    registry.close()


def test_registry_rejects_trust_after_close(tmp_path):
    registry = SQLiteIdentityRegistry(str(tmp_path / "identity.sqlite"))
    registry.close()
    with pytest.raises(RuntimeError, match="identity_registry_closed"):
        registry.snapshot()


def test_revocation_waits_for_trusted_critical_section_across_connections(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-1")
    first = SQLiteIdentityRegistry(path)
    second = SQLiteIdentityRegistry(path)
    first.register(identity)

    entered = threading.Event()
    release = threading.Event()

    def critical_section(verified_identity):
        assert verified_identity == identity
        entered.set()
        assert release.wait(timeout=5)
        return "verified"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        verified = pool.submit(first.with_trusted_identity, "agent-1", critical_section)
        assert entered.wait(timeout=5)
        revoked = pool.submit(second.revoke, "agent-1")
        assert not revoked.done()
        release.set()
        assert verified.result(timeout=5) == "verified"
        revoked.result(timeout=5)

    assert not first.is_trusted(identity)
    first.close()
    second.close()


def test_unknown_or_revoked_identity_cannot_enter_critical_section(tmp_path):
    registry = SQLiteIdentityRegistry(str(tmp_path / "identity.sqlite"))
    with pytest.raises(PermissionError, match="not_trusted"):
        registry.with_trusted_identity("missing", lambda identity: True)
    identity, _ = AgentIdentityAuthority.generate("agent-1")
    registry.register(identity)
    registry.revoke("agent-1")
    with pytest.raises(PermissionError, match="not_trusted"):
        registry.with_trusted_identity("agent-1", lambda item: True)
    registry.close()


def test_durable_registry_is_compatible_with_agent_fabric(tmp_path):
    from core.agent_core import AgentCore, AgentInput, AgentPlan, AgentResponse
    from core.agent_fabric import AgentBinding, AgentFabric
    from core.agent_skills import AgentSkill, AgentSkillRegistry

    class Brain:
        def understand(self, request):
            return type("Context", (), {
                "objective": request.content, "input": request, "facts": {}
            })()
        def plan(self, context):
            return AgentPlan(("answer",))
        def act(self, step, context):
            return "ok"
        def verify(self, step, result, context):
            return True
        def reflect(self, context, results):
            return "verified"
        def respond(self, context, reflection, results):
            return AgentResponse("ok", context.input.mode, verified=True)

    registry = SQLiteIdentityRegistry(str(tmp_path / "identity.sqlite"))
    identity, _ = AgentIdentityAuthority.generate("fabric-agent")
    registry.register(identity)
    skills = AgentSkillRegistry()
    skills.register(AgentSkill("general", "general capability"))
    agent = AgentCore("fabric-agent", Brain())
    fabric = AgentFabric(skills, registry, lambda principal, binding, request: principal == "owner")
    fabric.register(AgentBinding(agent, identity, ("general",)))

    assert fabric.dispatch("owner", AgentInput("hello"), "general").verified
    registry.revoke("fabric-agent")
    with pytest.raises(PermissionError, match="no_authorized_agent"):
        fabric.dispatch("owner", AgentInput("hello"), "general")
    registry.close()



def test_trust_generation_survives_restart_and_advances_on_reregistration(tmp_path):
    path = str(tmp_path / "identity-epochs.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-epoch")
    first = SQLiteIdentityRegistry(path)
    first.register(identity)
    assert first.generation(identity) == 1
    first.close()

    second = SQLiteIdentityRegistry(path)
    assert second.generation(identity) == 1
    second.revoke("agent-epoch")
    assert second.generation(identity) is None
    second.register(identity)
    assert second.generation(identity) == 3
    second.close()

    restored = SQLiteIdentityRegistry(path)
    assert restored.is_trusted(identity)
    assert restored.generation(identity) == 3
    restored.close()


def test_legacy_registry_schema_migrates_to_initial_trust_generation(tmp_path):
    import sqlite3

    path = str(tmp_path / "legacy-identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("legacy-agent")
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE agent_identity_trust ("
            "agent_id TEXT PRIMARY KEY, public_key BLOB NOT NULL, "
            "version INTEGER NOT NULL, state TEXT NOT NULL "
            "CHECK(state IN ('active','revoked')))"
        )
        db.execute(
            "INSERT INTO agent_identity_trust(agent_id,public_key,version,state) "
            "VALUES(?,?,?,'active')",
            (identity.agent_id, identity.public_key, identity.version),
        )

    registry = SQLiteIdentityRegistry(path)
    assert registry.is_trusted(identity)
    assert registry.generation(identity) == 1
    registry.close()


def test_durable_registry_rejects_malformed_utf8_agent_identifiers(tmp_path):
    registry = SQLiteIdentityRegistry(str(tmp_path / "identity-unicode.sqlite"))
    malformed, _ = AgentIdentityAuthority.generate("valid-agent")
    malformed = type(malformed)("\ud800", malformed.public_key)
    assert not malformed.is_well_formed()
    with pytest.raises(ValueError, match="invalid_agent_identity"):
        registry.register(malformed)
    with pytest.raises(ValueError, match="invalid_agent_id"):
        registry.revoke("\ud800")
    with pytest.raises(ValueError, match="invalid_agent_id"):
        registry.with_trusted_identity("\ud800", lambda _identity: None)
    registry.close()
