from fastapi.testclient import TestClient

from core.contracts import VerificationResult
from gateway.runtime_adapter import RuntimeAdapter
from gateway.server import NoryxGateway
from web import app as web_app


class FakeAgent:
    def __init__(self, agent_id, role):
        self.agent_id = agent_id
        self.role = role
        self.state = "ONLINE"


class FakeOperationalRuntime:
    online = True

    def __init__(self):
        self.agents = (
            FakeAgent("noryx7-llm", "primary"),
            FakeAgent("noryx7-secondary", "secondary"),
        )

    def heartbeat_agents(self):
        return self.agents

    def run_hypersynth(self, task):
        return {
            "status": "completed",
            "task_id": task.task_id,
            "execution_id": task.execution_id,
            "result": "NORYX7 HOSTED: " + task.input,
            "verification": VerificationResult(
                True,
                "runtime_result",
                "hosted_gateway_e2e_verified",
            ),
        }


def test_hosted_gateway_http_e2e(monkeypatch):
    runtime = FakeOperationalRuntime()
    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(runtime),
        bootstrap_token="hosted-bootstrap-test",
        signing_secret="hosted-signing-test",
    )
    monkeypatch.setattr(web_app, "get_gateway", lambda: gateway)
    client = TestClient(web_app.app)

    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["agents"][0]["state"] == "ONLINE"

    session = client.post(
        "/v1/session",
        json={
            "bootstrap_token": "hosted-bootstrap-test",
            "client_id": "noryx-browser-android",
        },
    )
    assert session.status_code == 200
    token = session.json()["session_token"]

    execution = client.post(
        "/v1/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "input": "hello from hosted browser",
            "execution_id": "browser-e2e-001",
        },
    )
    assert execution.status_code == 200
    payload = execution.json()
    assert payload["status"] == "completed"
    assert payload["execution_id"] == "browser-e2e-001"
    assert payload["result"] == "NORYX7 HOSTED: hello from hosted browser"
    assert payload["verification"]["valid"] is True


def test_hosted_gateway_rejects_missing_authorization(monkeypatch):
    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(FakeOperationalRuntime()),
        bootstrap_token="hosted-bootstrap-test",
        signing_secret="hosted-signing-test",
    )
    monkeypatch.setattr(web_app, "get_gateway", lambda: gateway)
    client = TestClient(web_app.app)

    response = client.post(
        "/v1/execute",
        json={"input": "must reject"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "authorization_required"
