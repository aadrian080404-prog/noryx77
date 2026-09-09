from __future__ import annotations

from fastapi.testclient import TestClient

from web import app as web_app


class _FakeGateway:
    def __init__(self):
        self.calls = []

    def create_session(self, *, bootstrap_token: str, client_id: str):
        self.calls.append(("session", bootstrap_token, client_id))
        return {"status": "authenticated", "client_id": client_id, "session_token": "fake-session"}

    def execute(self, *, session_token: str, text: str, execution_id: str | None = None):
        self.calls.append(("execute", session_token, text, execution_id))
        return {
            "status": "completed",
            "system_id": "NORYX7",
            "creator": "Adrian Aristodemo",
            "task_id": "browser:task",
            "execution_id": execution_id,
            "client_id": "noryx-web",
            "result": "WEB_GATEWAY_RUNTIME_PASS",
            "verification": {"stage": "runtime_result", "valid": True, "reason": "output_present"},
        }


class _FakeRuntime:
    class _Agents:
        def status(self):
            return [type("Agent", (), {"agent_id": "noryx7-llm", "role": "primary", "state": "ONLINE"})()]

    agent_runtime = _Agents()


def test_identity_endpoint_exposes_canonical_identity():
    client = TestClient(web_app.app)
    response = client.get("/api/identity")
    assert response.status_code == 200
    assert response.json()["system_id"] == "NORYX7"
    assert response.json()["creator"] == "Adrian Aristodemo"


def test_web_chat_uses_canonical_gateway(monkeypatch):
    fake_gateway = _FakeGateway()
    monkeypatch.setattr(web_app, "get_gateway", lambda: fake_gateway)
    monkeypatch.setattr(web_app, "get_runtime", lambda: _FakeRuntime())
    monkeypatch.setenv("NORYX_GATEWAY_BOOTSTRAP_TOKEN", "test-bootstrap")

    client = TestClient(web_app.app)
    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "WEB_GATEWAY_RUNTIME_PASS"
    assert payload["system_id"] == "NORYX7"
    assert payload["creator"] == "Adrian Aristodemo"
    assert fake_gateway.calls[0] == ("session", "test-bootstrap", "noryx-web")
    assert fake_gateway.calls[1][0] == "execute"
    assert fake_gateway.calls[1][1] == "fake-session"
    assert fake_gateway.calls[1][2] == "hello"
