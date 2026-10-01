import json
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.http_provider import HttpProviderConfig, build_http_provider
from core.provider_router import Provider
from core.provider_resilience import ResilientProviderExecutor


@contextmanager
def _json_server(*, response, delay=0.0):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received.append(json.loads(self.rfile.read(length)))
            if delay:
                time.sleep(delay)
            body = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/provider", received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _authorize(principal, capability, target):
    return principal == "user" and capability == "provider_execute" and target == "provider:chat"


def test_http_provider_executes_json_through_resilience_boundary():
    with _json_server(response={"reply": "HTTP-OK"}) as (endpoint, received):
        runtime = ResilientProviderExecutor(max_attempts=2)
        runtime.register(
            build_http_provider(
                name="http-primary",
                capabilities=frozenset({"chat"}),
                config=HttpProviderConfig(endpoint=endpoint, timeout_seconds=2.0),
            )
        )

        result = runtime.execute(
            "chat",
            {"message": "NORYX7-HTTP-E2E"},
            principal_id="user",
            logical_target="provider:chat",
            authorize=_authorize,
        )

        assert result.provider == "http-primary"
        assert result.output == {"reply": "HTTP-OK"}
        assert len(result.attempts) == 1
        assert result.attempts[0].success is True
        assert received == [{"message": "NORYX7-HTTP-E2E"}]


def test_http_provider_timeout_is_bounded_and_failover_reaches_secondary():
    with _json_server(response={"reply": "too-late"}, delay=0.25) as (endpoint, _received):
        runtime = ResilientProviderExecutor(max_attempts=2)
        runtime.register(
            build_http_provider(
                name="http-primary",
                capabilities=frozenset({"chat"}),
                config=HttpProviderConfig(endpoint=endpoint, timeout_seconds=0.05),
            )
        )
        runtime.register(
            Provider(
                "secondary",
                frozenset({"chat"}),
                lambda parameters: {"reply": parameters["payload"]["message"]},
            )
        )

        result = runtime.execute(
            "chat",
            {"message": "NORYX7-TIMEOUT-E2E"},
            principal_id="user",
            logical_target="provider:chat",
            authorize=_authorize,
        )

        assert result.provider == "secondary"
        assert result.output == {"reply": "NORYX7-TIMEOUT-E2E"}
        assert tuple((a.provider, a.attempt, a.success, a.error) for a in result.attempts) == (
            ("http-primary", 1, False, "RuntimeError"),
            ("secondary", 2, True, None),
        )


def test_http_provider_does_not_accept_credentials_in_endpoint():
    try:
        HttpProviderConfig("https://user:secret@example.invalid/v1")
    except ValueError as exc:
        assert str(exc) == "http_provider_credentials_must_not_be_in_url"
    else:
        raise AssertionError("credentials in endpoint must be rejected")
