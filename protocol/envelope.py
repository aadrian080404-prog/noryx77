"""Transport-neutral NORYX7 system envelopes.

This module contains only protocol validation. Execution remains owned by the
NORYX7 runtime and security fabric.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from . import PROTOCOL_NAME, PROTOCOL_VERSION


_REQUIRED_REQUEST_FIELDS = (
    "protocol",
    "version",
    "message_type",
    "request_id",
    "execution_id",
    "session_id",
    "principal_id",
    "client_id",
    "source",
    "input",
)


@dataclass(frozen=True)
class SystemRequest:
    request_id: str
    execution_id: str
    session_id: str
    principal_id: str
    client_id: str
    source: str
    input: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": PROTOCOL_NAME,
            "version": PROTOCOL_VERSION,
            "message_type": "execute",
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "session_id": self.session_id,
            "principal_id": self.principal_id,
            "client_id": self.client_id,
            "source": self.source,
            "input": dict(self.input),
        }


def validate_request(envelope: Mapping[str, Any]) -> SystemRequest:
    """Validate a canonical execute envelope and reject malformed input."""
    missing = [field for field in _REQUIRED_REQUEST_FIELDS if field not in envelope]
    if missing:
        raise ValueError(f"noryx_protocol_missing_fields:{','.join(missing)}")

    if envelope["protocol"] != PROTOCOL_NAME:
        raise ValueError("noryx_protocol_invalid_protocol")
    if envelope["version"] != PROTOCOL_VERSION:
        raise ValueError("noryx_protocol_unsupported_version")
    if envelope["message_type"] != "execute":
        raise ValueError("noryx_protocol_invalid_message_type")

    values = {
        field: envelope[field]
        for field in (
            "request_id",
            "execution_id",
            "session_id",
            "principal_id",
            "client_id",
            "source",
        )
    }
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("noryx_protocol_invalid_identity")

    if not isinstance(envelope["input"], Mapping):
        raise ValueError("noryx_protocol_invalid_input")

    return SystemRequest(input=dict(envelope["input"]), **values)
