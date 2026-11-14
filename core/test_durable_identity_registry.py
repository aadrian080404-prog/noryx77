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
