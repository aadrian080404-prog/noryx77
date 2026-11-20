import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.identity import AgentIdentityAuthority
from core.federation.memory_transfer_trust import build_memory_transfer_trust
from core.principal_identity import PrincipalIdentityAuthority
from core.sqlite_identity import SQLiteIdentityRegistry
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry


def _register_principal(registry, principal_id):
    identity, private_key = PrincipalIdentityAuthority.generate(principal_id)
    registry.register(identity)
    return identity, private_key


def _register_agent(registry, agent_id):
    identity, _private_key = AgentIdentityAuthority.generate(agent_id)
    registry.register(identity)
    return identity


def test_transfer_trust_resolves_live_principal_key_and_checks_agent_ownership(tmp_path):
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals.db")
    agents = SQLiteIdentityRegistry(tmp_path / "agents.db")
    try:
        source, source_private = _register_principal(principals, "principal-source")
        recipient, _ = _register_principal(principals, "principal-recipient")
        _register_agent(agents, "agent-source")
        _register_agent(agents, "agent-recipient")
        ownership = {
            ("principal-source", "agent-source"),
            ("principal-recipient", "agent-recipient"),
        }
        trust = build_memory_transfer_trust(
            principal_registry=principals,
            agent_registry=agents,
            is_agent_owned_by_principal=lambda principal, agent: (
                principal, agent
            ) in ownership,
        )

        payload = b"canonical federated memory statement"
        signature = source_private.sign(payload)
        assert trust.verify_signature(
            "principal-source", payload,
            __import__("base64").b64encode(signature).decode("ascii"),
        )
        assert trust.verify_source_principal("principal-source", "principal-source")
        assert not trust.verify_source_principal("principal-source", "principal-recipient")
        assert trust.verify_source_agent("principal-source", "agent-source")
        assert trust.verify_recipient_agent("principal-recipient", "agent-recipient")
        assert not trust.verify_source_agent("principal-recipient", "agent-source")
    finally:
        principals.close() if callable(getattr(principals, "close", None)) else None
        agents.close() if callable(getattr(agents, "close", None)) else None


def test_transfer_trust_fails_closed_after_principal_revocation(tmp_path):
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals-revoked.db")
    agents = SQLiteIdentityRegistry(tmp_path / "agents-revoked.db")
    try:
        _register_principal(principals, "principal-source")
        _register_agent(agents, "agent-source")
        trust = build_memory_transfer_trust(
            principal_registry=principals,
            agent_registry=agents,
            is_agent_owned_by_principal=lambda principal, agent: True,
        )
        principals.revoke("principal-source")
        assert not trust.verify_source_principal("principal-source", "principal-source")
        assert not trust.verify_signature("principal-source", b"payload", "invalid")
    finally:
        agents.close() if callable(getattr(agents, "close", None)) else None


def test_transfer_trust_fails_closed_after_agent_revocation_and_binding_failure(tmp_path):
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals-agent.db")
    agents = SQLiteIdentityRegistry(tmp_path / "agents-agent.db")
    try:
        _register_principal(principals, "principal-source")
        _register_agent(agents, "agent-source")
        ownership = {("principal-source", "agent-source")}
        trust = build_memory_transfer_trust(
            principal_registry=principals,
            agent_registry=agents,
            is_agent_owned_by_principal=lambda principal, agent: (
                principal, agent
            ) in ownership,
        )
        assert trust.verify_source_agent("principal-source", "agent-source")
        agents.revoke("agent-source")
        assert not trust.verify_source_agent("principal-source", "agent-source")
        assert not trust.verify_source_agent("principal-other", "agent-source")
    finally:
        agents.close() if callable(getattr(agents, "close", None)) else None


def test_transfer_trust_requires_explicit_principal_agent_binding_store(tmp_path):
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals-binding.db")
    agents = SQLiteIdentityRegistry(tmp_path / "agents-binding.db")
    try:
        with pytest.raises(TypeError, match="principal_agent_binding_verifier_required"):
            build_memory_transfer_trust(
                principal_registry=principals,
                agent_registry=agents,
                is_agent_owned_by_principal=None,
            )
    finally:
        agents.close() if callable(getattr(agents, "close", None)) else None


def test_source_agent_trust_fails_after_owner_principal_revocation(tmp_path):
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals-owner-revoked.db")
    agents = SQLiteIdentityRegistry(tmp_path / "agents-owner-revoked.db")
    try:
        _register_principal(principals, "principal-source")
        _register_agent(agents, "agent-source")
        trust = build_memory_transfer_trust(
            principal_registry=principals,
            agent_registry=agents,
            is_agent_owned_by_principal=lambda principal, agent: True,
        )
        assert trust.verify_source_agent("principal-source", "agent-source")
        principals.revoke("principal-source")
        assert not trust.verify_source_agent("principal-source", "agent-source")
    finally:
        agents.close() if callable(getattr(agents, "close", None)) else None


def test_transfer_trust_wires_durable_principal_agent_binding_registry(tmp_path):
    from core.sqlite_principal_agent_binding import SQLitePrincipalAgentBindingRegistry

    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals-bound.db")
    agents = SQLiteIdentityRegistry(tmp_path / "agents-bound.db")
    try:
        _register_principal(principals, "principal-source")
        _register_principal(principals, "principal-recipient")
        _register_agent(agents, "agent-source")
        _register_agent(agents, "agent-recipient")
        bindings = SQLitePrincipalAgentBindingRegistry(
            tmp_path / "principal-agent-bindings.db",
            principal_registry=principals,
            agent_registry=agents,
        )
        bindings.bind("principal-source", "agent-source")
        bindings.bind("principal-recipient", "agent-recipient")
        trust = build_memory_transfer_trust(
            principal_registry=principals,
            agent_registry=agents,
            binding_registry=bindings,
        )
        assert trust.verify_source_agent("principal-source", "agent-source")
        assert trust.verify_recipient_agent("principal-recipient", "agent-recipient")
        assert not trust.verify_source_agent("principal-recipient", "agent-source")
        bindings.revoke_binding("principal-source", "agent-source")
        assert not trust.verify_source_agent("principal-source", "agent-source")
    finally:
        agents.close() if callable(getattr(agents, "close", None)) else None
