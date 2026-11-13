import time

import pytest

from noryx7_runtime.contracts import ActionEnvelope
from noryx7_runtime.attestation import Ed25519AttestationSigner
from noryx7_runtime.contracts import Intent, PlanStep, ExecutionStatus
from noryx7_runtime.engine import RuntimeEngine
from noryx7_runtime.process_executor import (
    ProcessExecutionAdapter,
    ProcessExecutionError,
    ProcessExecutionTimeout,
)


def echo_handler(envelope):
    return {"step": envelope.step_id, "target": envelope.target}


def slow_handler(envelope):
    time.sleep(5)
    return {"done": True}


def bad_handler(envelope):
    raise ValueError("private exception details must not cross process boundary")


def make_envelope():
    return ActionEnvelope(
        execution_id="exec-1",
        principal_id="principal-1",
        step_id="step-1",
        action_type="test",
        target="local",
        parameters={},
        nonce="nonce-1",
    )


def test_process_executor_returns_json_result():
    adapter = ProcessExecutionAdapter(echo_handler, agent_id="isolated-worker", timeout_seconds=10)
    assert adapter.execute(make_envelope()) == {"step": "step-1", "target": "local"}


def test_process_executor_terminates_timed_out_child():
    adapter = ProcessExecutionAdapter(
        slow_handler, agent_id="isolated-worker", timeout_seconds=2, terminate_grace_seconds=0.1
    )
    with pytest.raises(ProcessExecutionTimeout, match="deadline_exceeded"):
        adapter.execute(make_envelope())


def test_process_executor_reports_only_exception_type():
    adapter = ProcessExecutionAdapter(bad_handler, agent_id="isolated-worker", timeout_seconds=10)
    with pytest.raises(ProcessExecutionError, match="ValueError") as error:
        adapter.execute(make_envelope())
    assert "private exception details" not in str(error.value)


def test_process_executor_rejects_non_picklable_or_invalid_configuration():
    with pytest.raises(ValueError, match="agent_id_required"):
        ProcessExecutionAdapter(echo_handler, agent_id=" ")
    with pytest.raises(ValueError, match="timeout_seconds"):
        ProcessExecutionAdapter(echo_handler, agent_id="worker", timeout_seconds=0)



def test_runtime_deadline_overrides_longer_adapter_timeout():
    adapter = ProcessExecutionAdapter(
        slow_handler,
        agent_id="isolated-worker",
        timeout_seconds=20,
        terminate_grace_seconds=0.1,
    )
    engine = RuntimeEngine(
        adapter=adapter,
        attestation_signer=Ed25519AttestationSigner.generate(),
    )
    result = engine.execute(
        Intent("deadline test", "principal-1"),
        [PlanStep("step-1", "test", "local", {})],
        verifier=lambda envelope, output: True,
        timeout_seconds=1.5,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "ProcessExecutionTimeout"



def test_executor_rejects_non_finite_deadlines():
    with pytest.raises(ValueError, match="timeout_seconds"):
        ProcessExecutionAdapter(echo_handler, agent_id="worker", timeout_seconds=float("nan"))
    adapter = ProcessExecutionAdapter(echo_handler, agent_id="worker", timeout_seconds=10)
    with pytest.raises(ValueError, match="timeout_seconds"):
        adapter.execute_with_timeout(make_envelope(), float("nan"))


def test_runtime_rejects_non_finite_deadline():
    engine = RuntimeEngine()
    with pytest.raises(ValueError, match="timeout_seconds"):
        engine.execute(
            Intent("deadline validation", "principal-1"),
            [PlanStep("step-1", "test", "local", {})],
            executor=echo_handler,
            verifier=lambda envelope, output: True,
            timeout_seconds=float("nan"),
        )
