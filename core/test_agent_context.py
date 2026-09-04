import pytest

from .agent_context import AgentContext
from .contracts import TaskSpec


def make_task(**constraints):
    return TaskSpec("task-1", "analysis", "solve", "input", constraints=constraints)


def test_context_binds_runtime_principal_and_execution():
    context = AgentContext("runtime-a", "exec-a", "principal-a")
    bound = context.bind_task(make_task())
    assert bound.execution_id == "exec-a"
    assert bound.constraints["runtime_id"] == "runtime-a"
    assert bound.constraints["principal_id"] == "principal-a"


def test_context_rejects_cross_runtime_task():
    context = AgentContext("runtime-a", "exec-a", "principal-a")
    with pytest.raises(PermissionError, match="runtime identity mismatch"):
        context.bind_task(make_task(runtime_id="runtime-b"))


def test_context_rejects_cross_principal_task():
    context = AgentContext("runtime-a", "exec-a", "principal-a")
    with pytest.raises(PermissionError, match="principal identity mismatch"):
        context.bind_task(make_task(principal_id="principal-b"))


def test_context_rejects_cross_execution_task():
    context = AgentContext("runtime-a", "exec-a", "principal-a")
    task = TaskSpec("task-1", "analysis", "solve", "input", execution_id="exec-b")
    with pytest.raises(PermissionError, match="execution identity mismatch"):
        context.bind_task(task)


def test_context_is_immutable():
    context = AgentContext("runtime-a", "exec-a", "principal-a")
    with pytest.raises(AttributeError):
        context.runtime_id = "runtime-b"
