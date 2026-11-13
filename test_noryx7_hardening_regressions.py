import hashlib
import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authorization_replay import AuthorizationReplayGuard
from core.coordination import AgentCoordinator
from core.contracts import TaskSpec
from core.multiauth import SignedApprovalAuthority, SignedAuthorizationProof, sign_approval
from core.planning import Plan, PlanStep
from core.router import ResourceRouter
from core.verification import VerificationEngine
from noryx7_runtime.contracts import ExecutionStatus, Intent, PlanStep as RuntimePlanStep
from noryx7_runtime.engine import RuntimeEngine
from tests.million_scale_campaign import VERIFICATION_SCOPE, run_campaign, scenario_for


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id


def test_agent_coordinator_assigns_every_step_to_bounded_worker_pool():
    router = ResourceRouter()
    router.register(StubAgent("agent-a"))
    router.register(StubAgent("agent-b"))
    coordinator = AgentCoordinator(router, VerificationEngine(), max_agents=2)
    plan = Plan(
        "task-1",
        tuple(PlanStep(f"step-{index}", f"objective-{index}") for index in range(5)),
    )

    assignments = coordinator.assign(plan, "execution-1")

    assert len(assignments) == len(plan.steps)
    assert [item.agent_id for item in assignments] == [
        "agent-a", "agent-b", "agent-a", "agent-b", "agent-a"
    ]
    assert [item.step_id for item in assignments] == [
        step.step_id for step in plan.steps
    ]


def test_agent_coordinator_rejects_plan_for_different_task():
    router = ResourceRouter()
    router.register(StubAgent("agent-a"))
    coordinator = AgentCoordinator(router, VerificationEngine())
    task = TaskSpec("task-1", "compute", "do work", None)
    plan = Plan("different-task", (PlanStep("step-1", "do work"),))

    with pytest.raises(ValueError, match="plan_task_mismatch"):
        coordinator.execute(task, plan)


def test_high_risk_authorization_replay_is_rejected_across_runtime_retries(tmp_path):
    execution_id = "replay-execution"
    principal_id = "principal-1"
    step = RuntimePlanStep("step-1", "financial", "transfer", {})
    plan_payload = [{
        "step_id": step.step_id,
        "action_type": step.action_type,
        "target": step.target,
        "parameters": dict(step.parameters),
        "dependencies": sorted(step.dependencies),
        "risk_class": step.risk_class,
    }]
    plan_digest = hashlib.sha256(
        json.dumps(
            plan_payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    statement = {
        "execution_id": execution_id,
        "principal_id": principal_id,
        "step_id": step.step_id,
        "action_type": step.action_type,
        "target": step.target,
        "parameters": dict(step.parameters),
        "risk_class": step.risk_class,
        "plan_digest": plan_digest,
    }
    action_statement = bytes.fromhex(
        hashlib.sha256(
            json.dumps(
                statement,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    authority = SignedApprovalAuthority(
        required_threshold=1,
        trusted_keys={"approver-1": public_key},
    )
    proof_expiry = int(time.time()) + 60
    approval = sign_approval(
        "approver-1", private_key, action_id=execution_id, epoch=0,
        action_statement=action_statement, expires_at=proof_expiry,
    )
    proof = SignedAuthorizationProof(
        execution_id, 0, action_statement, (approval,), 1, proof_expiry,
    )
    engine = RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=lambda envelope, signed_statement: proof,
        high_risk_action_types={"financial"},
        replay_guard=AuthorizationReplayGuard(path=str(tmp_path / "runtime-replay.sqlite3")),
    )
    effects = []
    intent = Intent("execute a financial operation", principal_id)

    first = engine.execute(
        intent,
        (step,),
        executor=lambda envelope: effects.append(envelope.step_id) or {"ok": True},
        verifier=lambda envelope, output: True,
        execution_id=execution_id,
    )
    replay = engine.execute(
        intent,
        (step,),
        executor=lambda envelope: effects.append(envelope.step_id) or {"ok": True},
        verifier=lambda envelope, output: True,
        execution_id=execution_id,
    )

    assert first.status is ExecutionStatus.SUCCEEDED
    assert replay.status is ExecutionStatus.FAILED
    assert replay.error == "PermissionError"
    assert effects == ["step-1"]


def test_generated_campaign_reports_its_actual_evidence_scope():
    result = run_campaign(seed=20261113, cases=10_000)

    assert result["status"] == "passed"
    assert result["executed"] == 10_000
    assert result["verification_scope"] == VERIFICATION_SCOPE


@pytest.mark.parametrize(
    "call",
    [
        lambda: scenario_for(True, 0),
        lambda: scenario_for(1, True),
        lambda: run_campaign(True, 100),
        lambda: run_campaign(1, True),
        lambda: run_campaign(1, 100, shards="1"),
        lambda: run_campaign(1, 100, shard_index=True),
        lambda: run_campaign(1, 10_000_001),
    ],
)
def test_generated_campaign_rejects_invalid_bounds_and_boolean_integers(call):
    with pytest.raises(ValueError):
        call()



def test_durable_replay_guard_survives_runtime_restart(tmp_path):
    path = str(tmp_path / "persistent-replay.sqlite3")
    token = b"\x42" * 32
    first_process = AuthorizationReplayGuard(path=path)
    assert first_process.durable
    expiry = int(time.time()) + 60
    assert first_process.consume(token, expires_at=expiry, now=time.time())
    first_process.close()

    restarted_process = AuthorizationReplayGuard(path=path)
    assert restarted_process.durable
    assert restarted_process.contains(token, now=time.time())
    assert not restarted_process.consume(token, expires_at=expiry, now=time.time())


def test_runtime_rejects_in_memory_replay_guard_for_high_risk_actions():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    authority = SignedApprovalAuthority(
        required_threshold=1,
        trusted_keys={"approver-1": public_key},
    )
    engine = RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=lambda envelope, statement: None,
        replay_guard=AuthorizationReplayGuard(),
    )
    effects = []
    result = engine.execute(
        Intent("financial operation", "principal-1"),
        (RuntimePlanStep("step-1", "financial", "transfer", {}),),
        executor=lambda envelope: effects.append("executed"),
        verifier=lambda envelope, output: True,
        execution_id="volatile-replay",
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert effects == []


def test_runtime_treats_financial_actions_as_high_risk_by_default():
    engine = RuntimeEngine()
    effects = []
    result = engine.execute(
        Intent("financial operation", "principal-1"),
        (RuntimePlanStep("step-1", "financial", "transfer", {}),),
        executor=lambda envelope: effects.append("executed"),
        verifier=lambda envelope, output: True,
        execution_id="default-high-risk",
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert effects == []
