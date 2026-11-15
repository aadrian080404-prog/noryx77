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
        bootstrap_token="bootstrap-test-token-32-bytes-minimum",
        signing_secret="signing-test-secret-32-bytes-minimum",
    )

    session = gateway.create_session(
        bootstrap_token="bootstrap-test-token-32-bytes-minimum",
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
        bootstrap_token="bootstrap-test-token-32-bytes-minimum",
        signing_secret="signing-test-secret-32-bytes-minimum",
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
        bootstrap_token="bootstrap-test-token-32-bytes-minimum",
        signing_secret="signing-test-secret-32-bytes-minimum",
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
                    "bootstrap_token": "bootstrap-test-token-32-bytes-minimum",
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

import pytest


def test_session_authority_rejects_weak_secrets():
    from gateway.auth import SessionAuthority

    with pytest.raises(ValueError, match="bootstrap_token_too_weak"):
        SessionAuthority(bootstrap_token="short", signing_secret="s" * 32)
    with pytest.raises(ValueError, match="signing_secret_too_weak"):
        SessionAuthority(bootstrap_token="b" * 32, signing_secret="short")


def test_session_authority_revokes_one_session_and_all_sessions_for_client():
    from gateway.auth import SessionAuthority, SessionError

    authority = SessionAuthority(bootstrap_token="b" * 32, signing_secret="s" * 32)
    first = authority.issue("b" * 32, "client-a")
    second = authority.issue("b" * 32, "client-a")
    third = authority.issue("b" * 32, "client-b")
    authority.revoke(first)
    with pytest.raises(SessionError, match="session_token_revoked"):
        authority.verify(first)
    assert authority.verify(second)["client_id"] == "client-a"
    assert authority.revoke_client("client-a") == 1
    with pytest.raises(SessionError, match="session_token_revoked"):
        authority.verify(second)
    assert authority.verify(third)["client_id"] == "client-b"


def test_session_authority_rotation_invalidates_existing_tokens():
    from gateway.auth import SessionAuthority, SessionError

    authority = SessionAuthority(bootstrap_token="b" * 32, signing_secret="s" * 32)
    token = authority.issue("b" * 32, "client-a")
    authority.rotate_signing_secret("n" * 32)
    with pytest.raises(SessionError):
        authority.verify(token)
    with pytest.raises(SessionError, match="bootstrap_auth_failed"):
        authority.issue("b" * 32, "client-b")
    authority.rotate_bootstrap_token("r" * 32)
    assert authority.issue("r" * 32, "client-b")


def test_session_authority_bounds_capacity_and_rejects_noncanonical_tokens():
    from gateway.auth import SessionAuthority, SessionError

    authority = SessionAuthority(bootstrap_token="b" * 32, signing_secret="s" * 32, max_sessions=1)
    token = authority.issue("b" * 32, "client-a")
    with pytest.raises(SessionError, match="session_capacity_reached"):
        authority.issue("b" * 32, "client-b")
    with pytest.raises(SessionError):
        authority.verify(token + ".extra")
