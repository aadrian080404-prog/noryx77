import os
import tempfile
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.multiauth import SignedApprovalAuthority, SignedAuthorizationProof, sign_approval
import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.runtime import JarvisRuntime


def _durable_runtime():
    directory = tempfile.mkdtemp(prefix="noryx7-replay-")
    return JarvisRuntime(authorization_replay_path=os.path.join(directory, "replay.sqlite3"))


def test_runtime_requires_explicit_grant_and_registered_capability():
    runtime = _durable_runtime(); request = Request("run", "user"); step = PlanStep("a", "tool", "target", {}); plan = Plan(request.request_id, (step,)); runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    with pytest.raises(PermissionError, match="capability_denied"): runtime.execute(request, plan)
    runtime.grant("user", "tool", "target"); result = runtime.execute(request, plan)
    assert result[0].success and result[0].output == "ok"


def test_runtime_rejects_plan_from_another_request():
    runtime = _durable_runtime(); first = Request("one", "user"); second = Request("two", "user"); plan = Plan(first.request_id, (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(PermissionError, match="request_identity_mismatch"): runtime.execute(second, plan)


def test_runtime_reserves_execution_before_side_effect_and_blocks_replay():
    runtime = _durable_runtime(); request = Request("run", "user"); plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),)); calls = []
    runtime.registry.register("tool", lambda s: calls.append(s.step_id) or ActionResult(s.step_id, True, "ok")); runtime.grant("user", "tool", "target")
    first = runtime.execute(request, plan); second = runtime.execute(request, plan)
    assert first[0].success and second == () and calls == ["a"]
    assert runtime.state.get(request.request_id) is not None


def test_unauthorized_request_does_not_consume_execution_reservation():
    runtime = _durable_runtime(); request = Request("run", "user"); plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),)); runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    with pytest.raises(PermissionError, match="capability_denied"): runtime.execute(request, plan)
    assert runtime.state.reservation(request.request_id) is None
    runtime.grant("user", "tool", "target")
    assert runtime.execute(request, plan)[0].success



def test_high_risk_capability_requires_independent_threshold_approval(tmp_path):
    runtime = _durable_runtime()
    effects = []
    runtime.registry.register(
        "bank.transfer",
        lambda step: effects.append(step.parameters["amount"]) or ActionResult(step.step_id, True, "settled"),
        risk_class="high",
    )
    request = Request("transfer", "user")
    plan = Plan(request.request_id, (PlanStep("transfer-1", "bank.transfer", "bank:account-1", {"amount": 100}),))
    runtime.grant("user", "bank.transfer", "bank:account-1")

    result = runtime.execute(request, plan)

    assert result == ()
    assert effects == []


def test_high_risk_capability_executes_only_after_signed_threshold_approval(tmp_path):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    authority = SignedApprovalAuthority(required_threshold=1, trusted_keys={"approver": public})

    def proof_provider(envelope, statement):
        expires_at = int(time.time()) + 60
        approval = sign_approval(
            "approver", private, action_id=envelope.execution_id,
            epoch=0, action_statement=statement, expires_at=expires_at,
        )
        return SignedAuthorizationProof(
            envelope.execution_id, 0, statement, (approval,), 1, expires_at,
        )

    directory = tempfile.mkdtemp(prefix="noryx7-replay-")
    runtime = JarvisRuntime(
        authorization_replay_path=os.path.join(directory, "replay.sqlite3"),
        multi_auth_authority=authority,
        authorization_provider=proof_provider,
    )
    effects = []
    runtime.registry.register(
        "bank.transfer",
        lambda step: effects.append(step.parameters["amount"]) or ActionResult(step.step_id, True, "settled"),
        risk_class="high",
    )
    request = Request("transfer", "user")
    plan = Plan(request.request_id, (PlanStep("transfer-1", "bank.transfer", "bank:account-1", {"amount": 100}),))
    runtime.grant("user", "bank.transfer", "bank:account-1")

    result = runtime.execute(request, plan)

    assert len(result) == 1
    assert result[0].success is True
    assert result[0].output == "settled"
    assert effects == [100]
