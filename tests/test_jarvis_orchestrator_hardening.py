import pytest

from jarvis.core.contracts import Plan, PlanStep, Request
from jarvis.core.orchestrator import JarvisOrchestrator


def test_jarvis_rejects_dependency_on_future_step():
    request = Request("run", "principal")
    plan = Plan(request.request_id, (
        PlanStep("a", "cap", "target", {}, dependencies=("b",)),
        PlanStep("b", "cap", "target", {}),
    ))
    with pytest.raises(ValueError, match="dependency_order_violation"):
        JarvisOrchestrator().execute(request, plan, lambda step: None)


def test_jarvis_authorization_failure_is_fail_closed():
    request = Request("run", "principal")
    plan = Plan(request.request_id, (PlanStep("a", "cap", "target", {}),))
    with pytest.raises(PermissionError, match="capability_denied"):
        JarvisOrchestrator().execute(request, plan, lambda step: None)


def test_jarvis_rejects_self_dependency():
    request = Request("run", "principal")
    plan = Plan(request.request_id, (PlanStep("a", "cap", "target", {}, dependencies=("a",)),))
    with pytest.raises(ValueError, match="self_dependency"):
        JarvisOrchestrator().execute(request, plan, lambda step: None)
