"""Adapters that bind the generic offline runtime to NORYX7 security primitives."""
from __future__ import annotations

from .contracts import ActionSpec
from .crypto import AuthenticatedCipher, EncryptedEnvelope
from .policy import PolicyEngine
from .verification import VerificationEngine


class PolicyOfflineAdapter:
    """Expose the central policy engine through the offline admission contract."""

    def __init__(self, policy: PolicyEngine):
        if not isinstance(policy, PolicyEngine):
            raise TypeError("policy_engine_required")
        self._policy = policy

    def authorize(self, *, principal_id: str, operation: str, offline: bool) -> bool:
        if offline is not True or not isinstance(operation, str) or not operation.strip():
            return False
        action = ActionSpec(
            action_id=f"offline:{principal_id}:{operation}",
            action_type="compute",
            target=operation,
            risk_class="normal",
            execution_id=principal_id,
        )
        return self._policy.allows(action)


class VerificationOfflineAdapter:
    """Require the canonical runtime-result verifier before an offline commit."""

    def __init__(self, verifier: VerificationEngine):
        if not isinstance(verifier, VerificationEngine):
            raise TypeError("verification_engine_required")
        self._verifier = verifier

    def verify(self, result: object) -> bool:
        check = self._verifier.verify_output(result, stage="runtime_result")
        return bool(check.is_well_formed() and check.valid and check.stage == "runtime_result")


class BoundAuthenticatedCipher:
    """Bind an AuthenticatedCipher to one approved key id for the offline outbox."""

    def __init__(self, cipher: AuthenticatedCipher, *, key_id: str):
        if not isinstance(cipher, AuthenticatedCipher):
            raise TypeError("authenticated_cipher_required")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("offline_key_id_required")
        self._cipher = cipher
        self._key_id = key_id

    def encrypt(self, plaintext: bytes, *, aad: bytes) -> bytes:
        envelope = self._cipher.encrypt(plaintext, key_id=self._key_id, aad=aad)
        return self._pack(envelope)

    def decrypt(self, ciphertext: bytes, *, aad: bytes) -> bytes:
        envelope = self._unpack(ciphertext, aad=aad)
        return self._cipher.decrypt(envelope)

    @staticmethod
    def _pack(envelope: EncryptedEnvelope) -> bytes:
        import base64
        import json

        body = {
            "key_id": envelope.key_id,
            "nonce": base64.b64encode(envelope.nonce).decode("ascii"),
            "ciphertext": base64.b64encode(envelope.ciphertext).decode("ascii"),
            "aad": base64.b64encode(envelope.aad).decode("ascii"),
            "version": envelope.version,
            "algorithm": envelope.algorithm,
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _unpack(blob: bytes, *, aad: bytes) -> EncryptedEnvelope:
        import base64
        import json

        if not isinstance(blob, bytes) or not blob:
            raise ValueError("invalid_offline_ciphertext")
        try:
            body = json.loads(blob.decode("utf-8"))
            envelope = EncryptedEnvelope(
                key_id=body["key_id"],
                nonce=base64.b64decode(body["nonce"], validate=True),
                ciphertext=base64.b64decode(body["ciphertext"], validate=True),
                aad=base64.b64decode(body["aad"], validate=True),
                version=body["version"],
                algorithm=body["algorithm"],
            )
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid_offline_ciphertext") from exc
        if envelope.aad != aad or not envelope.is_well_formed():
            raise ValueError("offline_envelope_invalid")
        return envelope
