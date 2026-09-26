from __future__ import annotations

import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROTOCOL = "NORYX7_PROVIDER_V1"
PROVIDER = "flights"
MAX_BODY = 65536

def _json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)

class ProviderHandler(BaseHTTPRequestHandler):
    server_version = "NORYX7ProviderE2E/1"

    def do_GET(self) -> None:
        if self.path == "/health":
            _json(self, 200, {"status": "healthy", "protocol": PROTOCOL, "provider": PROVIDER})
            return
        _json(self, 404, {"status": "rejected", "reason": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/provider":
            _json(self, 404, {"status": "rejected", "reason": "not_found"})
            return
        expected = os.environ.get("NORYX7_E2E_PROVIDER_TOKEN", "").strip()
        if not expected or self.headers.get("Authorization", "") != f"Bearer {expected}":
            _json(self, 401, {"status": "rejected", "reason": "authorization_required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("invalid_body")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("invalid_body")
        except (ValueError, json.JSONDecodeError):
            _json(self, 400, {"status": "rejected", "reason": "invalid_json"})
            return
        if payload.get("protocol") != PROTOCOL or payload.get("provider") != PROVIDER:
            _json(self, 400, {"status": "rejected", "reason": "provider_contract_rejected"})
            return
        execution_id = str(payload.get("execution_id") or "").strip()
        idempotency_key = str(payload.get("idempotency_key") or "").strip()
        operation = str(payload.get("operation") or "").strip()
        target = str(payload.get("target") or "").strip()
        parameters = payload.get("parameters")
        if not execution_id or execution_id != idempotency_key or not operation or not target or not isinstance(parameters, dict):
            _json(self, 400, {"status": "rejected", "reason": "execution_contract_rejected"})
            return
        receipt_id = "e2e-" + hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:32]
        _json(self, 200, {
            "protocol": PROTOCOL,
            "provider": PROVIDER,
            "status": "completed",
            "execution_id": execution_id,
            "idempotency_key": idempotency_key,
            "verified": True,
            "receipt": {"receipt_id": receipt_id},
            "effect": {"status": "applied", "operation": operation},
            "result": {
                "sandbox": True,
                "provider": PROVIDER,
                "target": target,
                "operation": operation,
                "parameters": parameters,
                "receipt_id": receipt_id,
            },
        })

    def log_message(self, *_args) -> None:
        return

def main() -> None:
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ProviderHandler)
    print(f"NORYX7 E2E provider listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()
