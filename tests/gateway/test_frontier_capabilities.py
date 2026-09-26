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


def test_external_provider_contract_binds_effect_to_execution_and_idempotency(monkeypatch):
    import json
    import core.frontier_capabilities as frontier

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self, _limit):
            return json.dumps({
                "protocol": "NORYX7_PROVIDER_V1",
                "provider": "flights",
                "status": "completed",
                "execution_id": "exec-123",
                "idempotency_key": "exec-123",
                "verified": True,
                "receipt": {"receipt_id": "provider-receipt-1"},
                "effect": {"status": "applied"},
                "result": {"booking_id": "ABC123"},
            }).encode()

    captured = {}
    def fake_urlopen(request, **_kwargs):
        captured["body"] = json.loads(request.data.decode())
        captured["headers"] = dict(request.header_items())
        return Response()

    monkeypatch.setenv("NORYX7_FLIGHTS_ENDPOINT", "https://provider.example.test/execute")
    monkeypatch.setenv("NORYX7_FLIGHTS_TOKEN", "secret-token")
    monkeypatch.setattr(frontier, "urlopen", fake_urlopen)

    result = frontier.ExternalProviderCapability("flights", "NORYX7_FLIGHTS")(
        "book", {"execution_id": "exec-123", "operation": "book", "passengers": [{"name": "Test"}]}
    )

    assert result["receipt"]["receipt_id"] == "provider-receipt-1"
    assert captured["body"]["protocol"] == "NORYX7_PROVIDER_V1"
    assert captured["body"]["execution_id"] == "exec-123"
    assert captured["body"]["idempotency_key"] == "exec-123"
    assert captured["body"]["provider"] == "flights"
    assert "Authorization" in captured["headers"]
    assert "secret-token" not in captured["body"]


@pytest.mark.parametrize("response_patch", [
    {"provider": "payments"},
    {"execution_id": "wrong"},
    {"idempotency_key": "wrong"},
    {"verified": False},
    {"receipt": {}},
    {"effect": {"status": "failed"}},
])
def test_external_provider_rejects_malformed_effect_contract(monkeypatch, response_patch):
    import json
    import core.frontier_capabilities as frontier

    response = {
        "protocol": "NORYX7_PROVIDER_V1",
        "provider": "flights",
        "status": "completed",
        "execution_id": "exec-123",
        "idempotency_key": "exec-123",
        "verified": True,
        "receipt": {"receipt_id": "receipt"},
        "effect": {"status": "applied"},
        "result": {},
    }
    response.update(response_patch)

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self, _limit):
            return json.dumps(response).encode()

    monkeypatch.setenv("NORYX7_FLIGHTS_ENDPOINT", "https://provider.example.test/execute")
    monkeypatch.setenv("NORYX7_FLIGHTS_TOKEN", "token")
    monkeypatch.setattr(frontier, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(frontier.CapabilityUnavailable):
        frontier.ExternalProviderCapability("flights", "NORYX7_FLIGHTS")(
            "book", {"execution_id": "exec-123", "operation": "book"}
        )


def test_external_provider_rejects_non_https_endpoint(monkeypatch):
    import core.frontier_capabilities as frontier
    monkeypatch.setenv("NORYX7_FLIGHTS_ENDPOINT", "http://provider.example.test/execute")
    monkeypatch.setenv("NORYX7_FLIGHTS_TOKEN", "token")
    with pytest.raises(frontier.CapabilityUnavailable, match="https_required"):
        frontier.ExternalProviderCapability("flights", "NORYX7_FLIGHTS")(
            "book", {"execution_id": "exec-123", "operation": "book"}
        )


def test_external_provider_rejects_sensitive_nested_credentials(monkeypatch):
    import core.frontier_capabilities as frontier
    monkeypatch.setenv("NORYX7_FLIGHTS_ENDPOINT", "https://provider.example.test/execute")
    monkeypatch.setenv("NORYX7_FLIGHTS_TOKEN", "token")
    with pytest.raises(frontier.CapabilityUnavailable, match="sensitive_parameter"):
        frontier.ExternalProviderCapability("flights", "NORYX7_FLIGHTS")(
            "book", {"execution_id": "exec-123", "payment": {"access_token": "should-not-cross"}}
        )


@pytest.mark.parametrize("capability", ["flights", "payments", "contracts", "bureaucracy", "insurance"])
def test_frontier_external_capabilities_lazy_register_as_high_risk(monkeypatch, capability):
    from core.frontier_capabilities import ExternalProviderCapability
    from core.tools import CapabilityRegistry

    registry = CapabilityRegistry()
    registry.register(capability, ExternalProviderCapability(capability, "NORYX7_" + capability.upper()), risk_class="high")
    assert registry.risk(capability) == "high"
    assert isinstance(registry.resolve(capability), ExternalProviderCapability)
