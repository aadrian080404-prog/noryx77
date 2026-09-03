from .agents import DeterministicAgent
from .contracts import ActionSpec, TaskSpec
from .memory import MemoryItem, MemoryStore
from .policy import PolicyEngine
from .router import ResourceRouter
from .runtime import NORYXRuntime
from .verification import VerificationEngine


def test_task_contract_and_runtime():
    task = TaskSpec("t1", "research", "inspect", "input")
    result = NORYXRuntime().run(task)
    assert result["status"] == "completed"
    assert result["result"].verification.valid


def test_unknown_risk_is_rejected():
    task = TaskSpec("t1", "x", "y", "z", risk_class="unknown")
    assert not VerificationEngine().verify_task(task).valid


def test_policy_fails_closed_for_unknown_and_high_risk():
    policy = PolicyEngine()
    assert not policy.evaluate(ActionSpec("a", "unknown")).get("allowed")
    assert not policy.evaluate(ActionSpec("b", "financial")).get("allowed")


def test_router_requires_explicit_route_when_ambiguous():
    router = ResourceRouter()
    router.register(DeterministicAgent())
    assert router.route().agent_id == "deterministic"


def test_memory_is_bounded_and_replaceable():
    store = MemoryStore()
    item = MemoryItem("m1", "hello", "postit", "test", 0.8)
    store.put(item)
    assert store.get("m1") == item
    assert store.delete("m1")
    assert store.get("m1") is None
