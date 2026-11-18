import pytest

from core.identity import AgentIdentityAuthority
from core.runtime import NORYXRuntime
from core.sqlite_identity import SQLiteIdentityRegistry


def test_runtime_reuses_persisted_agent_identity_across_restarts(tmp_path):
    registry = SQLiteIdentityRegistry(tmp_path / "runtime-identities.sqlite3")
    identity, _private_key = AgentIdentityAuthority.generate("deterministic")
    registry.register(identity)
    provider = lambda agent_id: identity if agent_id == "deterministic" else None

    first = NORYXRuntime(
        identity_registry=registry,
        agent_identity_provider=provider,
    )
    second = NORYXRuntime(
        identity_registry=registry,
        agent_identity_provider=provider,
    )

    first_agent = first.router.get("deterministic")
    second_agent = second.router.get("deterministic")
    assert first_agent.identity == identity
    assert second_agent.identity == identity
    assert first.identity_registry is registry
    assert second.identity_registry is registry


def test_runtime_rejects_untrusted_persisted_agent_identity(tmp_path):
    registry = SQLiteIdentityRegistry(tmp_path / "untrusted-identities.sqlite3")
    identity, _private_key = AgentIdentityAuthority.generate("deterministic")

    with pytest.raises(PermissionError, match="persistent_agent_identity_untrusted"):
        NORYXRuntime(
            identity_registry=registry,
            agent_identity_provider=lambda _agent_id: identity,
        )


def test_runtime_requires_identity_provider_with_external_registry(tmp_path):
    registry = SQLiteIdentityRegistry(tmp_path / "provider-required.sqlite3")
    with pytest.raises(ValueError, match="persistent_agent_identity_registry_and_provider_required"):
        NORYXRuntime(identity_registry=registry)


def test_runtime_rejects_provider_returning_wrong_agent_id(tmp_path):
    registry = SQLiteIdentityRegistry(tmp_path / "wrong-id.sqlite3")
    wrong, _private_key = AgentIdentityAuthority.generate("other-agent")
    registry.register(wrong)

    with pytest.raises(TypeError, match="persistent_agent_identity_invalid"):
        NORYXRuntime(
            identity_registry=registry,
            agent_identity_provider=lambda _agent_id: wrong,
        )


def test_runtime_rejects_revoked_persistent_agent_identity(tmp_path):
    registry = SQLiteIdentityRegistry(tmp_path / "revoked-identities.sqlite3")
    identity, _private_key = AgentIdentityAuthority.generate("deterministic")
    registry.register(identity)
    registry.revoke(identity.agent_id)

    with pytest.raises(PermissionError, match="persistent_agent_identity_untrusted"):
        NORYXRuntime(
            identity_registry=registry,
            agent_identity_provider=lambda _agent_id: identity,
        )
