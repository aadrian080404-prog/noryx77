import pytest

from core.identity import AgentIdentityAuthority
from core.principal_identity import PrincipalIdentityAuthority
from core.sqlite_identity import SQLiteIdentityRegistry
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry
from core.sqlite_principal_agent_binding import SQLitePrincipalAgentBindingRegistry


def _trusted_stores(tmp_path):
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals.sqlite3")
    agents = SQLiteIdentityRegistry(tmp_path / "agents.sqlite3")
    principal, _ = PrincipalIdentityAuthority.generate("principal-a")
    agent, _ = AgentIdentityAuthority.generate("agent-a")
    principals.register(principal)
    agents.register(agent)
    bindings = SQLitePrincipalAgentBindingRegistry(
        tmp_path / "bindings.sqlite3",
        principal_registry=principals,
        agent_registry=agents,
    )
    return principals, agents, bindings, principal, agent


def test_binding_is_durable_and_requires_both_trusted_identities(tmp_path):
    principals, agents, bindings, principal, agent = _trusted_stores(tmp_path)
    bindings.bind(principal.principal_id, agent.agent_id)
    reopened = SQLitePrincipalAgentBindingRegistry(
        tmp_path / "bindings.sqlite3",
        principal_registry=principals,
        agent_registry=agents,
    )
    assert reopened.is_agent_owned_by_principal(principal.principal_id, agent.agent_id)
    assert not reopened.is_agent_owned_by_principal("principal-other", agent.agent_id)


def test_agent_can_have_only_one_principal_owner(tmp_path):
    principals, agents, bindings, principal, agent = _trusted_stores(tmp_path)
    other, _ = PrincipalIdentityAuthority.generate("principal-b")
    principals.register(other)
    bindings.bind(principal.principal_id, agent.agent_id)
    with pytest.raises(PermissionError, match="agent_already_bound_to_another_principal"):
        bindings.bind(other.principal_id, agent.agent_id)


def test_binding_revocation_is_irreversible_and_does_not_revoke_identity(tmp_path):
    principals, agents, bindings, principal, agent = _trusted_stores(tmp_path)
    bindings.bind(principal.principal_id, agent.agent_id)
    bindings.revoke_binding(principal.principal_id, agent.agent_id)
    assert not bindings.is_agent_owned_by_principal(principal.principal_id, agent.agent_id)
    assert principals.is_registered(principal.principal_id)
    assert agents.is_registered(agent.agent_id)
    with pytest.raises(PermissionError, match="principal_agent_binding_permanently_revoked"):
        bindings.bind(principal.principal_id, agent.agent_id)


def test_identity_revocation_invalidates_existing_binding(tmp_path):
    principals, agents, bindings, principal, agent = _trusted_stores(tmp_path)
    bindings.bind(principal.principal_id, agent.agent_id)
    agents.revoke(agent.agent_id)
    assert not bindings.is_agent_owned_by_principal(principal.principal_id, agent.agent_id)


def test_principal_revocation_invalidates_existing_binding(tmp_path):
    principals, agents, bindings, principal, agent = _trusted_stores(tmp_path)
    bindings.bind(principal.principal_id, agent.agent_id)
    principals.revoke(principal.principal_id)
    assert not bindings.is_agent_owned_by_principal(principal.principal_id, agent.agent_id)


def test_binding_registry_rejects_in_memory_database(tmp_path):
    principals, agents, _bindings, _principal, _agent = _trusted_stores(tmp_path)
    with pytest.raises(ValueError, match="persistent_binding_database_required"):
        SQLitePrincipalAgentBindingRegistry(
            ":memory:", principal_registry=principals, agent_registry=agents
        )
