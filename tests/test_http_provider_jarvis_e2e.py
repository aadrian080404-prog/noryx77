import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.http_provider import HttpProviderConfig
from jarvis.core.contracts import Plan, PlanStep
from jarvis.core.runtime import JarvisRuntime
from jarvis.runtime_facade import JarvisFacade
from jarvis.agent.front_end import JarvisInteractionFrontEnd
from jarvis.interaction.session import SessionController
from jarvis.perception.audio import ClapDetector


@contextmanager
def _server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            json.loads(self.rfile.read(length))
            body = json.dumps({"provider_reply": "JARVIS-HTTP-OK"}).encode()
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
        yield f"http://127.0.0.1:{server.server_port}/v1/chat"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _frontend():
    detector = ClapDetector()
    frontend = JarvisInteractionFrontEnd(SessionController())
    assert detector.register_clap(100, 0.95) is None
    frontend.on_wake(detector.register_clap(300, 0.95), session_id="http-runtime")
    return frontend


def test_full_jarvis_http_provider_path_reaches_commit_and_trace():
    with _server() as endpoint:
        runtime = JarvisRuntime()
        runtime.register_http_provider(
            name="http-provider",
            capabilities=frozenset({"chat"}),
            config=HttpProviderConfig(endpoint=endpoint, timeout_seconds=2.0, allow_insecure_http=True),
        )
        runtime.grant("user", "provider_execute", "provider:chat")

        request_id = "jarvis-http-runtime-001"
        plan = Plan(
            request_id=request_id,
            steps=(
                PlanStep(
                    step_id="http-step",
                    capability="provider_execute",
                    target="provider:chat",
                    parameters={
                        "provider_capability": "chat",
                        "payload": {"message": "NORYX7-FULL-HTTP"},
                    },
                ),
            ),
        )

        frontend = _frontend()
        result = JarvisFacade(runtime=runtime, frontend=frontend).accept_input(
            frontend.build_input("usa il provider HTTP"),
            plan,
        )

        assert result.accepted is True
        assert result.reason == "executed"
        assert result.results[0].output["provider"] == "http-provider"
        assert result.results[0].output["output"] == {"provider_reply": "JARVIS-HTTP-OK"}

        events = runtime.execution_traces[request_id].events()
        assert any(e.event_type == "provider_attempt_succeeded" for e in events)
        assert runtime.execution_traces[request_id].verify() is True
        committed = runtime.state.get(request_id, principal_id="user")
        assert committed is not None
        assert committed.state.status == "committed"
