import time

import pytest

from noryx7_runtime.contracts import ActionEnvelope
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
