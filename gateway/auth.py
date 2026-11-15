from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time


class SessionError(PermissionError):
    pass


class SessionAuthority:
    """Fail-closed bootstrap + revocable, short-lived browser sessions.

    Active nonce state is process-local. Restarting the authority invalidates
    every previously issued session, which is intentionally fail-closed.
    """

    MIN_SECRET_BYTES = 32
    MAX_TOKEN_BYTES = 4096
    MAX_CLIENT_ID_BYTES = 256

    def __init__(
        self,
        *,
        bootstrap_token: str,
        signing_secret: str,
        ttl_seconds: int = 3600,
        max_sessions: int = 10000,
    ):
        if not isinstance(bootstrap_token, str) or not isinstance(signing_secret, str):
            raise ValueError("gateway_auth_secrets_required")
        if len(bootstrap_token.encode("utf-8")) < self.MIN_SECRET_BYTES:
            raise ValueError("bootstrap_token_too_weak")
        if len(signing_secret.encode("utf-8")) < self.MIN_SECRET_BYTES:
            raise ValueError("signing_secret_too_weak")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 0 < ttl_seconds <= 86400:
            raise ValueError("invalid_session_ttl")
        if isinstance(max_sessions, bool) or not isinstance(max_sessions, int) or max_sessions < 1:
            raise ValueError("invalid_session_capacity")
        self._bootstrap = bootstrap_token
        self._secret = signing_secret.encode("utf-8")
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._active_nonces: dict[str, tuple[str, int]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _unb64(value: str) -> bytes:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("invalid_base64url")
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        if SessionAuthority._b64(decoded) != value:
            raise ValueError("non_canonical_base64url")
        return decoded

    def _sign(self, payload: str) -> str:
        return self._b64(hmac.new(self._secret, payload.encode("ascii"), hashlib.sha256).digest())

    def _prune_expired(self, now: int) -> None:
        expired = [nonce for nonce, (_, exp) in self._active_nonces.items() if exp <= now]
        for nonce in expired:
            self._active_nonces.pop(nonce, None)

    def issue(self, presented_bootstrap: str, client_id: str) -> str:
        if not isinstance(presented_bootstrap, str) or not hmac.compare_digest(presented_bootstrap, self._bootstrap):
            raise SessionError("bootstrap_auth_failed")
        if not isinstance(client_id, str) or not client_id.strip():
            raise SessionError("client_identity_required")
        if len(client_id.encode("utf-8")) > self.MAX_CLIENT_ID_BYTES:
            raise SessionError("client_identity_too_large")

        now = int(time.time())
        payload = {
            "client_id": client_id,
            "exp": now + self._ttl,
            "nonce": secrets.token_urlsafe(24),
        }
        encoded = self._b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        token = encoded + "." + self._sign(encoded)
        with self._lock:
            self._prune_expired(now)
            if len(self._active_nonces) >= self._max_sessions:
                raise SessionError("session_capacity_reached")
            self._active_nonces[payload["nonce"]] = (client_id, payload["exp"])
        return token

    def verify(self, token: str) -> dict:
        if not isinstance(token, str) or len(token.encode("utf-8")) > self.MAX_TOKEN_BYTES or token.count(".") != 1:
            raise SessionError("session_token_required")
        encoded, signature = token.split(".", 1)
        if not encoded or not signature or not re.fullmatch(r"[A-Za-z0-9_-]+", signature):
            raise SessionError("session_token_invalid")
        try:
            if not hmac.compare_digest(signature, self._sign(encoded)):
                raise SessionError("session_token_invalid")
            payload = json.loads(self._unb64(encoded).decode("utf-8"))
        except SessionError:
            raise
        except Exception as exc:
            raise SessionError("session_token_malformed") from exc

        if not isinstance(payload, dict) or set(payload) != {"client_id", "exp", "nonce"}:
            raise SessionError("session_token_malformed")
        exp = payload.get("exp")
        client_id = payload.get("client_id")
        nonce = payload.get("nonce")
        if isinstance(exp, bool) or not isinstance(exp, int):
            raise SessionError("session_token_malformed")
        if exp <= int(time.time()):
            raise SessionError("session_token_expired")
        if not isinstance(client_id, str) or not client_id.strip() or len(client_id.encode("utf-8")) > self.MAX_CLIENT_ID_BYTES:
            raise SessionError("session_identity_invalid")
        if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128:
            raise SessionError("session_token_malformed")

        with self._lock:
            self._prune_expired(int(time.time()))
            active = self._active_nonces.get(nonce)
            if active != (client_id, exp):
                raise SessionError("session_token_revoked")
        return payload

    def revoke(self, token: str) -> None:
        payload = self.verify(token)
        with self._lock:
            self._active_nonces.pop(payload["nonce"], None)

    def revoke_client(self, client_id: str) -> int:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("client_identity_required")
        with self._lock:
            matching = [nonce for nonce, (owner, _) in self._active_nonces.items() if owner == client_id]
            for nonce in matching:
                self._active_nonces.pop(nonce, None)
            return len(matching)

    def rotate_signing_secret(self, new_secret: str) -> None:
        if not isinstance(new_secret, str) or len(new_secret.encode("utf-8")) < self.MIN_SECRET_BYTES:
            raise ValueError("signing_secret_too_weak")
        with self._lock:
            self._secret = new_secret.encode("utf-8")
            self._active_nonces.clear()

    def rotate_bootstrap_token(self, new_token: str) -> None:
        if not isinstance(new_token, str) or len(new_token.encode("utf-8")) < self.MIN_SECRET_BYTES:
            raise ValueError("bootstrap_token_too_weak")
        with self._lock:
            self._bootstrap = new_token
