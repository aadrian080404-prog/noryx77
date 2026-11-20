from core.identity import AgentIdentityAuthority
from core.principal_identity import PrincipalIdentityAuthority
from core.sqlite_identity import SQLiteIdentityRegistry
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry
from core.sqlite_principal_agent_binding import SQLitePrincipalAgentBindingRegistry


def test_binding_provisioning_uses_agent_then_principal_lock_order(tmp_path):
    principal, _ = PrincipalIdentityAuthority.generate("lock-order-principal")
    agent, _ = AgentIdentityAuthority.generate("lock-order-agent")
    principal_store = SQLitePrincipalIdentityRegistry(tmp_path / "principals.sqlite")
    agent_store = SQLiteIdentityRegistry(tmp_path / "agents.sqlite")
    principal_store.register(principal)
    agent_store.register(agent)
    calls = []

    class RecordingPrincipalStore:
        def with_trusted_principal(self, principal_id, callback):
            calls.append("principal")
            return principal_store.with_trusted_principal(principal_id, callback)

    class RecordingAgentStore:
        def with_trusted_identity(self, agent_id, callback):
            calls.append("agent")
            return agent_store.with_trusted_identity(agent_id, callback)

    bindings = SQLitePrincipalAgentBindingRegistry(
        tmp_path / "bindings.sqlite",
        principal_registry=RecordingPrincipalStore(),
        agent_registry=RecordingAgentStore(),
    )
    bindings.bind(principal.principal_id, agent.agent_id)
    assert calls == ["agent", "principal"]
    assert bindings.is_agent_owned_by_principal(
        principal.principal_id, agent.agent_id
    )
