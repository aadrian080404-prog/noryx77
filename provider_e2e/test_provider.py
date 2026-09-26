from __future__ import annotations

import json
import os
import threading
from http.client import HTTPConnection
from unittest import mock

from provider_e2e.server import ProviderHandler, ThreadingHTTPServer

def test_provider_health_and_contract():
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with mock.patch.dict(os.environ, {"NORYX7_E2E_PROVIDER_TOKEN": "test-token"}, clear=False):
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            payload = {
                "protocol": "NORYX7_PROVIDER_V1",
                "provider": "flights",
                "operation": "sandbox_execute",
                "target": "test-target",
                "parameters": {"mode": "e2e"},
                "execution_id": "exec-provider-test-1",
                "idempotency_key": "exec-provider-test-1",
            }
            connection.request("POST", "/v1/provider", body=json.dumps(payload), headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token",
            })
            response = connection.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert body["protocol"] == "NORYX7_PROVIDER_V1"
            assert body["provider"] == "flights"
            assert body["verified"] is True
            assert body["execution_id"] == payload["execution_id"]
            assert body["idempotency_key"] == payload["execution_id"]
            assert body["effect"]["status"] == "applied"
            assert body["receipt"]["receipt_id"].startswith("e2e-")
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
