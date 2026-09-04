from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any


_DOMAIN = b"NORYX7/provenance/v2/"


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_default(value: Any):
    if hasattr(value, "__dict__"):
        return {key: value for key, value in vars(value).items() if not key.startswith("_")}
    raise TypeError(f"unsupported provenance value: {type(value).__name__}")


@dataclass(frozen=True)
class ProvenanceContext:
    runtime_id: str
    execution_id: str
    principal_id: str
    memory_digest: str
    route_digest: str
    request_digest: str
    result_digest: str = ""
    model_request_digest: str = ""
    model_result_digest: str = ""

    def is_well_formed(self) -> bool:
        ids = (self.runtime_id, self.execution_id, self.principal_id)
        digests = (self.memory_digest, self.route_digest, self.request_digest, self.result_digest, self.model_request_digest, self.model_result_digest)
        return (
            all(isinstance(v, str) and bool(v) and len(v.encode("utf-8")) <= 256 for v in ids)
            and all(isinstance(v, str) and (v == "" or len(v) == 64) and (v == "" or _is_hex(v)) for v in digests)
        )

    def digest(self) -> str:
        if not self.is_well_formed():
            raise ValueError("invalid provenance context")
        return canonical_digest({
            "runtime_id": self.runtime_id,
            "execution_id": self.execution_id,
            "principal_id": self.principal_id,
            "memory_digest": self.memory_digest,
            "route_digest": self.route_digest,
            "request_digest": self.request_digest,
            "result_digest": self.result_digest,
            "model_request_digest": self.model_request_digest,
            "model_result_digest": self.model_result_digest,
        })

    def bind_result(self, result: Any) -> "ProvenanceContext":
        return ProvenanceContext(
            self.runtime_id, self.execution_id, self.principal_id,
            self.memory_digest, self.route_digest, self.request_digest,
            canonical_digest(result), self.model_request_digest, self.model_result_digest,
        )

    def bind_model(self, request_digest: str, result: Any, *, result_digest: str = "") -> "ProvenanceContext":
        if not isinstance(request_digest, str) or len(request_digest) != 64 or not _is_hex(request_digest):
            raise ValueError("invalid model request digest")
        if not isinstance(result_digest, str) or (result_digest and (len(result_digest) != 64 or not _is_hex(result_digest))):
            raise ValueError("invalid model result digest")
        result_request_digest = getattr(result, "request_digest", None)
        if result_request_digest is not None and result_request_digest != request_digest:
            raise ValueError("model request digest mismatch")
        bound_result_digest = result_digest or canonical_digest(result)
        return ProvenanceContext(
            self.runtime_id, self.execution_id, self.principal_id,
            self.memory_digest, self.route_digest, self.request_digest,
            self.result_digest, request_digest, bound_result_digest,
        )


def _is_hex(value: str) -> bool:
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def seal_provenance(context: ProvenanceContext, key: bytes) -> bytes:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("provenance key must contain at least 32 bytes")
    return hmac.new(key, _DOMAIN + context.digest().encode("ascii"), hashlib.sha256).digest()


def verify_provenance(context: ProvenanceContext, seal: bytes, key: bytes) -> bool:
    if not isinstance(seal, bytes) or len(seal) != 32 or not isinstance(key, bytes) or len(key) < 32:
        return False
    try:
        expected = seal_provenance(context, key)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(expected, seal)
