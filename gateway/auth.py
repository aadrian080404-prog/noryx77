from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


class SessionError(PermissionError):
    pass


class SessionAuthority:
    """Fail-closed bootstrap + short-lived browser session authority."""

    def __init__(
        self,
        *,
        bootstrap_token: str,
        signing_secret: str,
        browser_pairing_code: str = "",
        ttl_seconds: int = 3600,
    ):
        if not bootstrap_token or not signing_secret:
            raise ValueError("gateway_auth_secrets_required")
        if not isinstance(browser_pairing_code, str):
            raise ValueError("invalid_browser_pairing_code")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            raise ValueError("invalid_session_ttl")
        if ttl_seconds <= 0:
            raise ValueError("invalid_session_ttl")
        self._bootstrap = bootstrap_token
        self._browser_pairing_code = browser_pairing_code
        self._secret = signing_secret.encode("utf-8")
        self._ttl = ttl_seconds

    @staticmethod
    def _b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _unb64(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def _sign(self, payload: str) -> str:
        return self._b64(
            hmac.new(
                self._secret,
                payload.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        )

    @staticmethod
    def _validate_client_id(client_id: str) -> str:
        if not isinstance(client_id, str) or not client_id.strip() or len(client_id.encode("utf-8")) > 128:
            raise SessionError("client_identity_required")
        return client_id.strip()

    def _issue(self, client_id: str) -> str:
        payload = {
            "client_id": self._validate_client_id(client_id),
            "exp": int(time.time()) + self._ttl,
            "nonce": secrets.token_urlsafe(18),
        }
        encoded = self._b64(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        return encoded + "." + self._sign(encoded)

    def issue(self, presented_bootstrap: str, client_id: str) -> str:
        if not hmac.compare_digest(str(presented_bootstrap), self._bootstrap):
            raise SessionError("bootstrap_auth_failed")
        return self._issue(client_id)

    def issue_browser_pairing(self, presented_code: str, client_id: str) -> str:
        """Issue a normal session from a dedicated browser pairing secret.

        The pairing secret is server-side only and is never embedded in the APK.
        """
        if not self._browser_pairing_code:
            raise SessionError("browser_pairing_disabled")
        if not hmac.compare_digest(str(presented_code), self._browser_pairing_code):
            raise SessionError("browser_pairing_failed")
        return self._issue(client_id)

    def verify(self, token: str) -> dict:
        if not isinstance(token, str) or "." not in token:
            raise SessionError("session_token_required")
        encoded, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, self._sign(encoded)):
            raise SessionError("session_token_invalid")
        try:
            payload = json.loads(self._unb64(encoded).decode("utf-8"))
        except Exception as exc:
            raise SessionError("session_token_malformed") from exc
        if not isinstance(payload, dict):
            raise SessionError("session_token_malformed")
        try:
            exp = int(payload.get("exp", 0))
        except (TypeError, ValueError) as exc:
            raise SessionError("session_token_malformed") from exc
        if exp <= int(time.time()):
            raise SessionError("session_token_expired")
        client_id = payload.get("client_id")
        if not isinstance(client_id, str) or not client_id.strip():
            raise SessionError("session_identity_invalid")
        return payload
