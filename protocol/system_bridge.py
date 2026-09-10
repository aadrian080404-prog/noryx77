"""Canonical adapter from the NORYX System Protocol into the runtime.

The bridge deliberately contains no model, capability, or provider logic. It
only validates the protocol envelope, binds the authenticated principal, and
hands the request to the existing canonical gateway execution path.
"""

from __future__ import annotations

from typing import Any, Mapping

from .envelope import SystemRequest, validate_request


class SystemBridge:
    """Transport-neutral bridge for first-party NORYX7 clients."""

    def __init__(self, gateway: Any):
        if gateway is None or not callable(getattr(gateway, "execute", None)):
            raise TypeError("gateway_required")
        self.gateway = gateway

    @staticmethod
    def _capability(request: SystemRequest) -> str | None:
        value = request.input.get("capability")
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("noryx_protocol_invalid_capability")
        return value.strip().lower()

    @staticmethod
    def _query(request: SystemRequest) -> str | None:
        value = request.input.get("query")
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("noryx_protocol_invalid_query")
        return value.strip()

    def execute(self, *, session_token: str, envelope: Mapping[str, Any]) -> dict[str, Any]:
        request = validate_request(envelope)
        capability = self._capability(request)
        query = self._query(request)
        text = request.input.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("noryx_protocol_input_text_required")

        result = self.gateway.execute(
            session_token=session_token,
            text=text,
            execution_id=request.execution_id,
            capability=capability,
            query=query,
        )
        if result.get("client_id") != request.principal_id:
            raise PermissionError("noryx_protocol_principal_mismatch")
        if result.get("execution_id") != request.execution_id:
            raise RuntimeError("noryx_protocol_execution_mismatch")

        return {
            "protocol": request.to_dict()["protocol"],
            "version": request.to_dict()["version"],
            "message_type": "execute_result",
            "request_id": request.request_id,
            "execution_id": request.execution_id,
            "session_id": request.session_id,
            "principal_id": request.principal_id,
            "client_id": request.client_id,
            "source": request.source,
            "result": result,
        }
