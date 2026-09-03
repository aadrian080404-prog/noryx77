from concurrent.futures import ThreadPoolExecutor

import pytest

from .capabilities import Capability, CapabilityBroker
from .contracts import ActionEnvelope


def envelope(action_type="tool.call"):
    return ActionEnvelope("exec-1", "principal-1", "step-1", action_type, "target", {}, "nonce-1")


def test_capability_rejects_malformed_definition():
    with pytest.raises(ValueError):
        Capability("", frozenset({"tool.call"}), lambda action: None)
    with pytest.raises(ValueError):
        Capability("tool", frozenset({""}), lambda action: None)
    with pytest.raises(TypeError):
        Capability("tool", frozenset({"tool.call"}), None)


def test_broker_rejects_duplicate_name():
    broker = CapabilityBroker()
    capability = Capability("tool", frozenset({"tool.call"}), lambda action: "ok")
    broker.register(capability)
    with pytest.raises(ValueError, match="already registered"):
        broker.register(capability)


def test_broker_rejects_ambiguous_action_type():
    broker = CapabilityBroker()
    broker.register(Capability("one", frozenset({"tool.call"}), lambda action: "one"))
    broker.register(Capability("two", frozenset({"other"}), lambda action: "two"))
    with pytest.raises(LookupError):
        broker.resolve(envelope("missing"))


def test_broker_does_not_call_handler_during_resolution():
    called = []
    broker = CapabilityBroker()
    broker.register(Capability("tool", frozenset({"tool.call"}), lambda action: called.append(True) or "ok"))
    assert broker.resolve(envelope()).name == "tool"
    assert called == []


def test_concurrent_registration_has_single_winner():
    broker = CapabilityBroker()

    def register():
        try:
            broker.register(Capability("tool", frozenset({"tool.call"}), lambda action: "ok"))
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: register(), range(32)))
    assert sum(results) == 1
    assert broker.resolve(envelope()).name == "tool"


def test_resolution_is_stable_under_concurrent_reads():
    broker = CapabilityBroker({"tool": Capability("tool", frozenset({"tool.call"}), lambda action: "ok")})
    with ThreadPoolExecutor(max_workers=16) as pool:
        resolved = list(pool.map(lambda _: broker.resolve(envelope()).name, range(64)))
    assert resolved == ["tool"] * 64
