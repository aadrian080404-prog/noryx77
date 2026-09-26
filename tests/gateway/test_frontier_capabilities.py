import pytest

from gateway.runtime_adapter import RuntimeAdapter
from gateway.server import NoryxGateway


class _CapabilityRuntime:
    def heartbeat_agents(self):
        return {
            "deterministic": "ONLINE",
            "noryx7-llm": "ONLINE",
            "noryx7-secondary": "ONLINE",
        }

    def run_hypersynth(self, task):
        from core.contracts import VerificationResult

        return {
            "status": "completed",
            "task_id": task.task_id,
            "execution_id": task.execution_id,
            "result": "ok",
            "verification": VerificationResult(True, "runtime_result", "verified"),
        }


def test_frontier_capability_is_exposed_to_authenticated_browser_when_provider_is_configured(monkeypatch):
    monkeypatch.setenv("NORYX7_FLIGHTS_ENDPOINT", "https://provider.example.test/execute")
    monkeypatch.setenv("NORYX7_FLIGHTS_TOKEN", "configured-token")

    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(_CapabilityRuntime()),
        bootstrap_token="bootstrap-test",
        signing_secret="signing-test",
    )
    session = gateway.create_session(
        bootstrap_token="bootstrap-test",
        client_id="browser-frontier",
    )

    authorization = gateway.system_fabric.authorize(session["session_id"], "flights")
    assert authorization.identity_id == "browser-frontier"


def test_unconfigured_frontier_capability_is_not_authorized(monkeypatch):
    monkeypatch.delenv("NORYX7_FLIGHTS_ENDPOINT", raising=False)
    monkeypatch.delenv("NORYX7_FLIGHTS_TOKEN", raising=False)

    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(_CapabilityRuntime()),
        bootstrap_token="bootstrap-test",
        signing_secret="signing-test",
    )
    session = gateway.create_session(
        bootstrap_token="bootstrap-test",
        client_id="browser-frontier-denied",
    )

    with pytest.raises(PermissionError):
        gateway.execute(
            session_token=session["session_token"],
            text="prenota un volo",
            capability="flights",
        )
