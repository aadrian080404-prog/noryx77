from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Sequence

from noryx7_runtime.model_fabric import ModelAdapter


class OpenRouterAdapter:
    """Provider adapter for OpenRouter."""

    def __init__(
        self,
        *,
        model: str = "openrouter/free",
        api_key: str | None = None,
        timeout_seconds: float = 90.0,
        app_name: str = "NORYX7",
        max_response_bytes: int = 1_048_576,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")

        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")

        key = (
            api_key
            if api_key is not None
            else os.environ.get("OPENROUTER_API_KEY", "")
        )

        if not isinstance(key, str) or not key.startswith("sk-or-v1-"):
            raise ValueError(
                "OPENROUTER_API_KEY is missing or invalid"
            )

        self.name = model
        self.capabilities = frozenset({
            "text",
            "chat",
            "reasoning",
            "cloud",
            "openrouter",
        })
        self.cost_per_call = 0.0
        self.expected_latency_ms = 5000.0

        self._api_key = key
        self._model = model
        self._timeout_seconds = float(timeout_seconds)
        if isinstance(max_response_bytes, bool) or not isinstance(max_response_bytes, int) or not 1 <= max_response_bytes <= 16_777_216:
            raise ValueError("max_response_bytes must be between 1 and 16777216")

        self._app_name = app_name
        self._max_response_bytes = max_response_bytes

    def _read_bounded(self, response) -> bytes:
        """Read at most max_response_bytes plus one sentinel byte."""
        headers = getattr(response, "headers", None)
        content_length = None
        if headers is not None:
            try:
                raw_length = headers.get("Content-Length")
                if raw_length is not None:
                    content_length = int(raw_length)
            except (TypeError, ValueError):
                raise RuntimeError("openrouter_invalid_content_length")
        if content_length is not None and (content_length < 0 or content_length > self._max_response_bytes):
            raise RuntimeError("openrouter_response_too_large")

        chunks = []
        total = 0
        while total <= self._max_response_bytes:
            chunk = response.read(min(65536, self._max_response_bytes + 1 - total))
            if not isinstance(chunk, bytes):
                raise RuntimeError("openrouter_invalid_response_body")
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > self._max_response_bytes:
                raise RuntimeError("openrouter_response_too_large")
        return b"".join(chunks)

    def generate(
        self,
        prompt: str,
        *,
        tools: Sequence[str] = (),
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt is required")

        if tools:
            raise ValueError(
                "tools are not enabled through the current "
                "string-only ModelAdapter contract"
            )

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
        }

        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-OpenRouter-Title": self._app_name,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                content_type = response.headers.get("Content-Type", "") if getattr(response, "headers", None) is not None else ""
                media_type = content_type.split(";", 1)[0].strip().lower()
                if media_type != "application/json" and not media_type.endswith("+json"):
                    raise RuntimeError("openrouter_invalid_content_type")
                raw = self._read_bounded(response).decode("utf-8")

        except urllib.error.HTTPError as exc:
            try:
                body = self._read_bounded(exc).decode("utf-8", errors="replace")
            except RuntimeError as read_error:
                body = str(read_error)
            raise RuntimeError(
                f"openrouter_http_error:{exc.code}:{body[:1000]}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"openrouter_connection_error:{exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError("openrouter_timeout") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "openrouter_invalid_json_response"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError("openrouter_invalid_response")

        if "error" in data:
            error = data["error"]

            if isinstance(error, dict):
                raise RuntimeError(
                    "openrouter_model_error:"
                    f"{error.get('code', 'unknown')}:"
                    f"{error.get('message', 'unknown_error')}"
                )

            raise RuntimeError("openrouter_model_error")

        choices = data.get("choices")

        if not isinstance(choices, list) or not choices:
            raise RuntimeError("openrouter_missing_choices")

        choice = choices[0]

        if not isinstance(choice, dict):
            raise RuntimeError("openrouter_invalid_choice")

        message = choice.get("message")

        if not isinstance(message, dict):
            raise RuntimeError("openrouter_missing_message")

        content = message.get("content")

        if not isinstance(content, str):
            raise RuntimeError("openrouter_non_text_response")

        content = content.strip()

        if not content:
            raise RuntimeError("openrouter_empty_response")

        return content
