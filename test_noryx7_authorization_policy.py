import pytest

from core.actions import ActionGate, AuthorizationAuthority
from core.contracts import ActionSpec, TaskSpec
from core.coordination import AgentCoordinator
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.limits import RuntimeLimits
from core.planning import Planner
from core.policy import PolicyEngine
from core.router import ResourceRouter
from core.security import SecurityBoundary
from core.tools import CapabilityRegistry, ToolExecutor
from core.verification import VerificationEngine


class PaymentAgent:
    agent_id = "payment-agent"

    def __init__(self):
        self.calls = []

    def run(self, task):
        self.calls.append(task)
        return None


def _high_risk_action(*, requires_authorization):
    return ActionSpec(
        action_id="payment-1",
        action_type="payments",
        target="wallet-1",
        parameters={"amount_minor": 5000, "currency": "EUR"},
        risk_class="high",
        requires_authorization=requires_authorization,
        execution_id="execution-1",
    )


def test_payment_action_is_denied_without_a_verified_grant():
    policy = PolicyEngine()
    security = SecurityBoundary(policy, VerificationEngine())
    gate = ActionGate(policy, security, RuntimeLimits())
    effects = []
    action = _high_risk_action(requires_authorization=False)

    decision, output = gate.authorize_and_execute(
        action,
        lambda: effects.append("paid") or "paid",
        execution_id="execution-1",
    )

    assert not decision.allowed
    assert output is None
    assert effects == []


def test_payment_action_requires_high_risk_classification():
    policy = PolicyEngine()
    action = ActionSpec(
        action_id="payment-2",
        action_type="payments",
        target="wallet-1",
        parameters={},
        risk_class="normal",
        requires_authorization=True,
        execution_id="execution-2",
    )

    assert not policy.allows(action, authorization_verified=True)


def test_valid_one_shot_grant_allows_one_payment_execution_only():
    identity, _ = AgentIdentityAuthority.generate("owner")
    registry = IdentityRegistry()
    registry.register(identity)
    authority = AuthorizationAuthority(b"noryx7-test-secret-material-32-bytes", identity_registry=registry)
    policy = PolicyEngine()
    security = SecurityBoundary(policy, VerificationEngine())
    gate = ActionGate(policy, security, RuntimeLimits(), authorization=authority)
    action = _high_risk_action(requires_authorization=True)
    grant = authority.issue(action, "execution-1", principal=identity)
    effects = []

    decision, output = gate.authorize_and_execute(
        action,
        lambda: effects.append("paid") or "paid",
        execution_id="execution-1",
        grant=grant,
        principal=identity,
    )
    replay_decision, replay_output = gate.authorize_and_execute(
        action,
        lambda: effects.append("replayed") or "replayed",
        execution_id="execution-1",
        grant=grant,
        principal=identity,
    )

    assert decision.allowed
    assert output == "paid"
    assert not replay_decision.allowed
    assert replay_output is None
    assert effects == ["paid"]


def test_planner_rejects_payment_task_without_high_risk_classification():
    planner = Planner()
    task = TaskSpec("task-payment", "payments", "transfer funds", None)
    plan = planner.build(task)

    check = planner.verify(plan, task)

    assert not check.valid
    assert check.reason == "high_risk_class_required"


def test_agent_coordinator_cannot_downgrade_payment_plan_to_compute():
    agent = PaymentAgent()
    router = ResourceRouter()
    router.register(agent)
    coordinator = AgentCoordinator(router, VerificationEngine())
    task = TaskSpec("task-payment", "payments", "transfer funds", None, risk_class="high")
    plan = Planner().build(task)

    with pytest.raises(RuntimeError, match="action_gate_denied"):
        coordinator.execute(task, plan)

    assert agent.calls == []


def test_capability_registry_rejects_unknown_risk_classes():
    registry = CapabilityRegistry()
    with pytest.raises(ValueError, match="invalid_capability_risk"):
        registry.register("danger", lambda target, params: "ok", risk_class="critical")


def test_tool_executor_rejects_capability_risk_downgrade():
    tool = ToolExecutor(PolicyEngine(), VerificationEngine())
    effects = []
    tool.capabilities.register(
        "danger",
        lambda target, params: effects.append("executed") or "ok",
        risk_class="high",
    )
    action = ActionSpec(
        "capability-call",
        "jarvis_capability",
        "system",
        {"__jarvis_capability": "danger"},
        risk_class="normal",
        execution_id="execution-3",
    )

    output, check = tool.execute(action, execution_id="execution-3")

    assert output is None
    assert not check.valid
    assert check.reason == "capability_risk_downgrade"
    assert effects == []


def test_high_risk_capability_requires_explicit_authorization_flag():
    tool = ToolExecutor(PolicyEngine(), VerificationEngine())
    tool.capabilities.register("danger", lambda target, params: "executed", risk_class="high")
    action = ActionSpec(
        "capability-call",
        "jarvis_capability",
        "system",
        {"__jarvis_capability": "danger"},
        risk_class="high",
        requires_authorization=False,
        execution_id="execution-4",
    )

    output, check = tool.execute(action, execution_id="execution-4")

    assert output is None
    assert not check.valid
    assert check.reason == "high_risk_capability_requires_authorization"


def test_high_risk_capability_executes_only_with_valid_one_shot_grant():
    identity, _ = AgentIdentityAuthority.generate("owner")
    registry = IdentityRegistry()
    registry.register(identity)
    authority = AuthorizationAuthority(b"noryx7-capability-secret-32-bytes!!", identity_registry=registry)
    policy = PolicyEngine()
    security = SecurityBoundary(policy, VerificationEngine())
    gate = ActionGate(policy, security, RuntimeLimits(), authorization=authority)
    tool = ToolExecutor(gate, VerificationEngine())
    effects = []
    tool.capabilities.register(
        "danger",
        lambda target, params: effects.append(target) or "executed",
        risk_class="high",
    )
    action = ActionSpec(
        "capability-call",
        "jarvis_capability",
        "system",
        {"__jarvis_capability": "danger"},
        risk_class="high",
        requires_authorization=True,
        execution_id="execution-5",
    )
    grant = authority.issue(action, "execution-5", principal=identity)

    output, check = tool.execute(
        action,
        execution_id="execution-5",
        grant=grant,
        principal=identity,
    )

    assert output == "executed"
    assert check.valid
    assert effects == ["system"]
