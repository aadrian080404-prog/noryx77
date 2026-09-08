import pytest

from .adapters import CapabilityAdapter
from .capabilities import Capability, CapabilityBroker
from .contracts import ActionEnvelope


def envelope(**overrides):
    values = {
        "execution_id": "exec-1",
        "principal_id": "principal-1",
        "step_id": "step-1",
        "action_type": "read",
        "target": "memory",
        "parameters": {},
        "nonce": "nonce-1",
    }
    values.update(overrides)
    return ActionEnvelope(**values)


def test_adapter_resolves_exactly_one_capability():
    seen = []
    broker = CapabilityBroker({
        "memory": Capability("memory", frozenset({"read"}), lambda item: seen.append(item) or "ok")
    })
    adapter = CapabilityAdapter(broker, agent_id="agent-1")

    assert adapter.execute(envelope()) == "ok"
    assert len(seen) == 1


def test_adapter_rejects_missing_identity_before_capability_resolution():
    broker = CapabilityBroker({
        "memory": Capability("memory", frozenset({"read"}), lambda item: "unsafe")
    })
    adapter = CapabilityAdapter(broker, agent_id="agent-1")

    with pytest.raises(PermissionError):
        adapter.execute(envelope(principal_id=""))


def test_adapter_fails_closed_when_capability_is_ambiguous():
    broker = CapabilityBroker({
        "one": Capability("one", frozenset({"read"}), lambda item: "one"),
        "two": Capability("two", frozenset({"read"}), lambda item: "two"),
    })
    adapter = CapabilityAdapter(broker, agent_id="agent-1")

    with pytest.raises(LookupError):
        adapter.execute(envelope())
