from dataclasses import dataclass

import pytest

from .jarvis import JarvisAssistant, JarvisCapabilities, JarvisRequest


@dataclass
class StubRuntime:
    runtime_id: str = "runtime-test"
    response: dict | None = None

    def run_hypersynth(self, task):
        assert task.task_type == "jarvis_request"
        assert task.execution_id
        return self.response or {
            "status": "completed",
            "result": {"ok": True},
            "verified": True,
        }


def test_request_binds_to_noryx7_task():
    request = JarvisRequest("req-1", "Organize the task")
    task = request.to_task()
    assert task.task_id == "req-1"
    assert task.task_type == "jarvis_request"
    assert task.execution_id


def test_jarvis_delegates_to_runtime_and_preserves_verification():
    assistant = JarvisAssistant(StubRuntime())
    response = assistant.handle(JarvisRequest("req-2", "Do work"))
    assert response.status == "completed"
    assert response.verified is True
    assert response.result == {"ok": True}


def test_jarvis_rejects_malformed_runtime_result():
    assistant = JarvisAssistant(StubRuntime(response=None))
    assistant.runtime.response = []
    response = assistant.handle(JarvisRequest("req-3", "Do work"))
    assert response.status == "rejected"
    assert response.reason == "malformed_runtime_result"


def test_jarvis_rejects_invalid_runtime_status():
    assistant = JarvisAssistant(StubRuntime(response={"status": "unknown"}))
    response = assistant.handle(JarvisRequest("req-4", "Do work"))
    assert response.status == "rejected"
    assert response.reason == "invalid_runtime_status"


def test_invalid_request_is_rejected_before_runtime():
    assistant = JarvisAssistant(StubRuntime())
    with pytest.raises(ValueError, match="invalid objective"):
        assistant.handle(JarvisRequest("req-5", ""))


def test_capabilities_are_explicit_and_platform_neutral():
    assistant = JarvisAssistant(
        StubRuntime(),
        JarvisCapabilities(multimodal=True, proactive=True),
    )
    snapshot = assistant.capability_snapshot()
    assert snapshot["multimodal"] is True
    assert snapshot["proactive"] is True
    assert snapshot["verification"] is True
