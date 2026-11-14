from core.collaboration import AgentCollaboration
from core.contracts import AgentResult, TaskSpec, VerificationResult


class _Verifier:
    def verify_output(self, output, *, stage):
        return VerificationResult(True, stage, "ok")


class _Agent:
    def __init__(self, agent_id, outputs):
        self.agent_id = agent_id
        self.outputs = list(outputs)

    def run(self, task):
        output = self.outputs.pop(0)
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.task_id,
            status="completed",
            output=output,
            verification=VerificationResult(True, "agent", "ok"),
            execution_id=task.execution_id,
        )


def _task():
    return TaskSpec(
        task_id="task-1",
        task_type="analysis",
        objective="analyze",
        input={"value": "x"},
        execution_id="exec-1",
    )


def test_approve_verdict_is_preserved():
    primary = _Agent("primary", ["proposal", "reconciled"])
    secondary = _Agent("secondary", ["APPROVE\nsupported"])
    reconciliation, verification = AgentCollaboration(_Verifier()).run(
        _task(), primary, secondary
    )
    assert reconciliation.accepted is True
    assert verification.valid is True


def test_reject_verdict_is_preserved():
    primary = _Agent("primary", ["proposal", "reconciled"])
    secondary = _Agent("secondary", ["REJECT\nunsupported claim"])
    reconciliation, verification = AgentCollaboration(_Verifier()).run(
        _task(), primary, secondary
    )
    assert reconciliation.accepted is False
    assert verification.valid is True


def test_unstructured_verdict_fails_closed():
    primary = _Agent("primary", ["proposal"])
    secondary = _Agent("secondary", ["the proposal looks good"])
    try:
        AgentCollaboration(_Verifier()).run(_task(), primary, secondary)
    except RuntimeError as exc:
        assert str(exc) == "unstructured_critique"
    else:
        raise AssertionError("unstructured critique must fail closed")
