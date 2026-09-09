import pytest

from core.agents import DeterministicAgent
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.router import ResourceRouter
from core.system_fabric import CanonicalSystemFabric


def _router_with_agent(capabilities=("execute",)):
    registry = IdentityRegistry()
    identity, _ = AgentIdentityAuthority.generate("deterministic")
    registry.register(identity)
    router = ResourceRouter(identity_registry=registry)
    router.register(DeterministicAgent(identity=identity))
    fabric = CanonicalSystemFabric()
    fabric.bind_agent_identity(identity, capabilities=capabilities)
    router.attach_system_fabric(fabric)
    return router, fabric, identity


def test_router_requires_canonical_capability_before_dispatch():
    router, _, _ = _router_with_agent(("observe",))
    with pytest.raises(PermissionError, match="agent_route_not_authorized"):
        router.route("deterministic")


def test_router_authorization_isolated_by_agent_key():
    registry = IdentityRegistry()
    identity_a, _ = AgentIdentityAuthority.generate("deterministic")
    identity_b, _ = AgentIdentityAuthority.generate("deterministic")
    registry.register(identity_a)
    router = ResourceRouter(identity_registry=registry)
    router.register(DeterministicAgent(identity=identity_a))
    fabric = CanonicalSystemFabric()
    fabric.bind_agent_identity(identity_a, capabilities=("execute",))
    router.attach_system_fabric(fabric)

    assert router.route("deterministic").identity.public_key == identity_a.public_key
    with pytest.raises(PermissionError, match="agent_route_not_authorized"):
        fabric.authorize_agent(identity_b, "execute")


def test_router_route_provenance_is_digest_only_and_authorized():
    router, _, identity = _router_with_agent()
    agent = router.route("deterministic")
    provenance = router.route_provenance(agent)
    assert provenance["agent_id"] == "deterministic"
    assert provenance["capability"] == "execute"
    assert provenance["identity_digest"]
    assert len(provenance["identity_digest"]) == 64
    assert identity.public_key.hex() not in provenance.values()


def test_route_metadata_cannot_escalate_capability():
    router, _, _ = _router_with_agent(("observe",))
    with pytest.raises(PermissionError, match="agent_route_not_authorized"):
        router.route("deterministic", required_capability="execute")
