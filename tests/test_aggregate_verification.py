from core.contracts import AgentResult, VerificationResult
from core.verification import VerificationEngine


def _result(task_id, execution_id="exec-1", agent_id="deterministic", valid=True):
    return AgentResult(
        agent_id=agent_id,
        task_id=task_id,
        status="completed",
        output=f"output-{task_id}",
        verification=VerificationResult(valid, "agent_result", "ok" if valid else "bad"),
        execution_id=execution_id,
    )


def test_aggregate_verification_accepts_complete_ordered_result_set():
    engine = VerificationEngine()
    checks = engine.verify_agent_results(
        [_result("a"), _result("b")],
        expected_agent_id="deterministic",
        expected_execution_id="exec-1",
        expected_task_ids=("a", "b"),
    )
    assert checks and all(check.valid for check in checks)


def test_aggregate_verification_rejects_identity_mismatch():
    engine = VerificationEngine()
    checks = engine.verify_agent_results(
        [_result("a"), _result("b", execution_id="other")],
        expected_agent_id="deterministic",
        expected_execution_id="exec-1",
        expected_task_ids=("a", "b"),
    )
    assert any(check.reason == "execution_identity_mismatch" for check in checks)
    assert not all(check.valid for check in checks)


def test_aggregate_verification_rejects_missing_or_extra_results():
    engine = VerificationEngine()
    checks = engine.verify_agent_results(
        [_result("a")],
        expected_agent_id="deterministic",
        expected_execution_id="exec-1",
        expected_task_ids=("a", "b"),
    )
    assert checks[0].reason == "result_count_mismatch"


def test_aggregate_verification_rejects_unverified_child_result():
    engine = VerificationEngine()
    checks = engine.verify_agent_results(
        [_result("a", valid=False)],
        expected_agent_id="deterministic",
        expected_execution_id="exec-1",
        expected_task_ids=("a",),
    )
    assert any(check.reason == "unverified_agent_result" for check in checks)
    assert not all(check.valid for check in checks)
