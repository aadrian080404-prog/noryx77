import pytest

from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.router import ResourceRouter
from core.system_fabric import CanonicalSystemFabric


class FakeAgent:
    def __init__(self, identity):
        self.agent_id = identity.agent_id
        self.identity = identity


def _router():
    registry = IdentityRegistry()
    identity, _ = AgentIdentityAuthority.generate("route-agent")
    registry.register(identity)
    fabric = CanonicalSystemFabric()
    fabric.bind_agent_identity(identity, capabilities=("execute", "model:execute"))
    router = ResourceRouter(identity_registry=registry, system_fabric=fabric)
    router.register(FakeAgent(identity))
    return router, identity


def test_protected_route_requires_canonical_capability():
    router, _ = _router()
    assert router.route("route-agent", required_capability="model:execute").agent_id == "route-agent"


def test_protected_route_denies_unbound_capability():
    router, _ = _router()
    with pytest.raises(PermissionError):
        router.route("route-agent", required_capability="admin:execute")


def test_protected_route_requires_canonical_fabric():
    registry = IdentityRegistry()
    identity, _ = AgentIdentityAuthority.generate("unbound-route-agent")
    registry.register(identity)
    router = ResourceRouter(identity_registry=registry)
    router.register(FakeAgent(identity))
    with pytest.raises(PermissionError, match="canonical_system_fabric_required"):
        router.route("unbound-route-agent", required_capability="execute")
