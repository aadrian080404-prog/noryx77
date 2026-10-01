"""Bounded JSON-over-HTTP provider adapter for the NORYX7 provider boundary."""
from __future__ import annotations

import json
import os
import ssl
from dataclasses import dataclass
from typing import Any, Mapping
from urllib import error as urlerror
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from core.provider_router import Provider


@dataclass(frozen=True)
class HttpProviderConfig:
    endpoint: str
    timeout_seconds: float = 10.0
    max_response_bytes: int = 1_048_576
    api_key_env: str | None = None
    authorization_scheme: str = "Bearer"
    allow_insecure_http: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("http_provider_endpoint_invalid")
        if parsed.scheme == "http" and not self.allow_insecure_http:
            raise ValueError("http_provider_insecure_transport")
        if parsed.username or parsed.password:
            raise ValueError("http_provider_credentials_must_not_be_in_url")
        if self.timeout_seconds <= 0:
            raise ValueError("http_provider_timeout_invalid")
        if self.max_response_bytes < 1:
            raise ValueError("http_provider_response_limit_invalid")
        if self.api_key_env is not None and not self.api_key_env.strip():
            raise ValueError("http_provider_api_key_env_invalid")


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("http_provider_redirect_rejected")


class HttpJsonProvider:
    """POST bounded JSON and require a bounded JSON response.

    Secrets are read only from the process environment and are never returned
    in exceptions or provider results. Retry/failover stays in the resilience
    layer so policy and provenance remain centralized.
    """

    def __init__(
        self,
        config: HttpProviderConfig,
        *,
        headers: Mapping[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self.config = config
        self._headers = dict(headers or {})
        self._ssl_context = ssl_context
        self._opener = build_opener(_NoRedirectHandler())

    def __call__(self, parameters: Any) -> Any:
        if not isinstance(parameters, Mapping):
            raise ValueError("http_provider_parameters_invalid")
        payload = parameters.get("payload")
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("http_provider_payload_not_json") from exc

        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "NORYX7-provider/1",
            **self._headers,
        }
        if self.config.api_key_env:
            secret = os.environ.get(self.config.api_key_env)
            if not secret:
                raise RuntimeError("http_provider_credentials_unavailable")
            request_headers["Authorization"] = f"{self.config.authorization_scheme} {secret}"

        request = Request(self.config.endpoint, data=body, headers=request_headers, method="POST")
        try:
            with self._opener.open(
                request,
                timeout=self.config.timeout_seconds,
                context=self._ssl_context,
            ) as response:
                raw = response.read(self.config.max_response_bytes + 1)
                status = getattr(response, "status", 200)
        except urlerror.HTTPError as exc:
            raise RuntimeError(f"http_provider_http_status:{exc.code}") from exc
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("http_provider_transport_failure") from exc

        if status < 200 or status >= 300:
            raise RuntimeError(f"http_provider_http_status:{status}")
        if len(raw) > self.config.max_response_bytes:
            raise RuntimeError("http_provider_response_too_large")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("http_provider_invalid_json_response") from exc


def build_http_provider(
    *,
    name: str,
    capabilities: frozenset[str],
    config: HttpProviderConfig,
    headers: Mapping[str, str] | None = None,
) -> Provider:
    if not name.strip() or not capabilities:
        raise ValueError("provider_contract_invalid")
    return Provider(
        name=name,
        capabilities=capabilities,
        handler=HttpJsonProvider(config, headers=headers),
    )
