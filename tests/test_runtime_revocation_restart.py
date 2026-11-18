import pytest

from core.identity import AgentIdentityAuthority
from core.runtime import NORYXRuntime
from core.sqlite_identity import SQLiteIdentityRegistry


def test_runtime_refuses_permanently_revoked_agent_identity_after_restart(tmp_path):
    database_path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("deterministic")

    first_registry = SQLiteIdentityRegistry(database_path)
    first_registry.register(identity)
    provider = lambda agent_id: identity if agent_id == "deterministic" else None

    # The runtime can start while the identity is trusted.
    NORYXRuntime(
        identity_registry=first_registry,
        agent_identity_provider=provider,
    )

    # Revoke, then reopen the durable registry as a fresh process would.
    first_registry.revoke("deterministic")
    reopened_registry = SQLiteIdentityRegistry(database_path)

    assert reopened_registry.is_trusted(identity) is False
    with pytest.raises(PermissionError, match="agent_identity_permanently_revoked"):
        reopened_registry.register(identity)

    # Runtime initialization must consult the durable trust registry rather
    # than accepting an identity merely because the provider still returns it.
    with pytest.raises(PermissionError, match="persistent_agent_identity_untrusted"):
        NORYXRuntime(
            identity_registry=reopened_registry,
            agent_identity_provider=provider,
        )
