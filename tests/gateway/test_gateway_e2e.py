import json
import threading
from urllib.request import Request, urlopen

from gateway.runtime_adapter import RuntimeAdapter
from gateway.server import NoryxGateway


class FakeRuntime:
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
            "result": "NORYX7: " + task.input,
            "verification": VerificationResult(
                True,
                "runtime_result",
                "gateway_e2e_verified",
            ),
        }


def test_gateway_session_and_runtime_e2e():
    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(FakeRuntime()),
        bootstrap_token="bootstrap-test",
        signing_secret="signing-test",
    )

    session = gateway.create_session(
        bootstrap_token="bootstrap-test",
        client_id="noryx-browser-test",
    )

    result = gateway.execute(
        session_token=session["session_token"],
        text="test browser request",
    )

    assert result["status"] == "completed"
    assert result["result"] == "NORYX7: test browser request"


def test_gateway_rejects_invalid_session():
    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(FakeRuntime()),
        bootstrap_token="bootstrap-test",
        signing_secret="signing-test",
    )

    try:
        gateway.execute(
            session_token="invalid",
            text="test",
        )
    except PermissionError as exc:
        assert str(exc) in {
            "session_token_required",
            "session_token_invalid",
        }
    else:
        raise AssertionError("invalid session was accepted")


def test_gateway_http_e2e():
    gateway = NoryxGateway(
        runtime_adapter=RuntimeAdapter(FakeRuntime()),
        bootstrap_token="bootstrap-test",
        signing_secret="signing-test",
    )

    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        gateway.handler_class(),
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    base = f"http://127.0.0.1:{server.server_port}"

    try:
        request = Request(
            base + "/v1/session",
            data=json.dumps(
                {
                    "bootstrap_token": "bootstrap-test",
                    "client_id": "browser-e2e",
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(request) as response:
            session = json.loads(
                response.read().decode()
            )

        request = Request(
            base + "/v1/execute",
            data=json.dumps(
                {
                    "input": "hello from browser",
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": (
                    "Bearer "
                    + session["session_token"]
                ),
            },
            method="POST",
        )

        with urlopen(request) as response:
            result = json.loads(
                response.read().decode()
            )

        assert result["status"] == "completed"
        assert result["result"] == "NORYX7: hello from browser"

    finally:
        server.shutdown()
        server.server_close()
