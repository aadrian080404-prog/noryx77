from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .auth import SessionAuthority, SessionError
from .runtime_adapter import RuntimeAdapter


class NoryxGateway:
    """HTTP API boundary. Production deployment must terminate TLS."""

    def __init__(
        self,
        *,
        runtime_adapter: RuntimeAdapter | None = None,
        bootstrap_token: str | None = None,
        signing_secret: str | None = None,
    ):
        bootstrap_token = (
            bootstrap_token
            if bootstrap_token is not None
            else os.environ.get("NORYX_GATEWAY_BOOTSTRAP_TOKEN", "")
        )
        signing_secret = (
            signing_secret
            if signing_secret is not None
            else os.environ.get("NORYX_GATEWAY_SIGNING_SECRET", "")
        )

        self.auth = SessionAuthority(
            bootstrap_token=bootstrap_token,
            signing_secret=signing_secret,
        )
        self.runtime = runtime_adapter or RuntimeAdapter()

    def health(self) -> dict:
        return {
            "status": "ok",
            "service": "noryx7-gateway",
            "runtime": "connected",
            "auth": "enabled",
        }

    def create_session(
        self,
        *,
        bootstrap_token: str,
        client_id: str,
    ) -> dict:
        token = self.auth.issue(
            bootstrap_token,
            client_id,
        )
        return {
            "status": "authenticated",
            "client_id": client_id,
            "session_token": token,
        }

    def execute(
        self,
        *,
        session_token: str,
        text: str,
    ) -> dict:
        identity = self.auth.verify(session_token)

        return self.runtime.execute(
            client_id=identity["client_id"],
            text=text,
        )

    def handler_class(self):
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "NORYX7Gateway/1"

            def _json(self, status: int, payload: dict):
                data = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")

                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(data)),
                )
                self.send_header(
                    "Cache-Control",
                    "no-store",
                )
                self.end_headers()
                self.wfile.write(data)

            def _body(self):
                try:
                    length = int(
                        self.headers.get(
                            "Content-Length",
                            "0",
                        )
                    )
                    if length <= 0 or length > 16384:
                        raise ValueError("invalid_json_body")

                    body = json.loads(
                        self.rfile.read(length).decode("utf-8")
                    )

                    if not isinstance(body, dict):
                        raise ValueError("invalid_json_body")

                    return body

                except ValueError as exc:
                    if str(exc) == "invalid_json_body":
                        raise
                    raise ValueError("invalid_json_body") from exc

                except Exception as exc:
                    raise ValueError("invalid_json_body") from exc

            def do_GET(self):
                if self.path == "/v1/health":
                    self._json(
                        200,
                        gateway.health(),
                    )
                    return

                self._json(
                    404,
                    {"status": "rejected", "reason": "not_found"},
                )

            def do_POST(self):
                try:
                    body = self._body()

                    if self.path == "/v1/session":
                        result = gateway.create_session(
                            bootstrap_token=str(
                                body.get(
                                    "bootstrap_token",
                                    "",
                                )
                            ),
                            client_id=str(
                                body.get(
                                    "client_id",
                                    "",
                                )
                            ),
                        )
                        self._json(200, result)
                        return

                    if self.path == "/v1/execute":
                        authorization = self.headers.get(
                            "Authorization",
                            "",
                        )

                        if not authorization.startswith(
                            "Bearer "
                        ):
                            raise SessionError(
                                "authorization_required"
                            )

                        result = gateway.execute(
                            session_token=authorization[7:],
                            text=body.get("input", ""),
                        )
                        self._json(200, result)
                        return

                    self._json(
                        404,
                        {
                            "status": "rejected",
                            "reason": "not_found",
                        },
                    )

                except SessionError as exc:
                    self._json(
                        401,
                        {
                            "status": "rejected",
                            "reason": str(exc),
                        },
                    )

                except ValueError as exc:
                    self._json(
                        400,
                        {
                            "status": "rejected",
                            "reason": str(exc),
                        },
                    )

                except PermissionError as exc:
                    self._json(
                        403,
                        {
                            "status": "rejected",
                            "reason": str(exc),
                        },
                    )

                except Exception:
                    self._json(
                        500,
                        {
                            "status": "rejected",
                            "reason": "gateway_runtime_failure",
                        },
                    )

            def log_message(self, *_args):
                return

        return Handler

    def serve(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8787,
    ):
        server = ThreadingHTTPServer(
            (host, port),
            self.handler_class(),
        )

        print(
            f"NORYX7 Gateway listening on {host}:{port}"
        )
        server.serve_forever()
