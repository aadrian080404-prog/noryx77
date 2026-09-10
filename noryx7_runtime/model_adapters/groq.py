from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Sequence

from noryx7_runtime.model_fabric import ModelAdapter


class GroqAdapter:
    """Provider adapter for Groq's OpenAI-compatible inference API."""

    def __init__(
        self,
        *,
        model: str = "openai/gpt-oss-120b",
        api_key: str | None = None,
        timeout_seconds: float = 90.0,
        app_name: str = "NORYX7",
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")

        key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY", "")
        if not isinstance(key, str) or not key.startswith("gsk_"):
            raise ValueError("GROQ_API_KEY is missing or invalid")

        self.name = model
        self.capabilities = frozenset({
            "text",
            "chat",
            "reasoning",
            "cloud",
            "groq",
            "tools",
            "json_mode",
            "structured_outputs",
        })
        self.cost_per_call = 0.0
        self.expected_latency_ms = 1000.0

        self._api_key = key
        self._model = model
        self._timeout_seconds = float(timeout_seconds)
        self._app_name = app_name

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
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self._app_name,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"groq_http_error:{exc.code}:{body[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"groq_connection_error:{exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("groq_timeout") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("groq_invalid_json_response") from exc
        if not isinstance(data, dict):
            raise RuntimeError("groq_invalid_response")
        if "error" in data:
            error = data["error"]
            if isinstance(error, dict):
                raise RuntimeError(
                    "groq_model_error:"
                    f"{error.get('code', 'unknown')}:"
                    f"{error.get('message', 'unknown_error')}"
                )
            raise RuntimeError("groq_model_error")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("groq_missing_choices")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise RuntimeError("groq_invalid_choice")
        message = choice.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("groq_missing_message")
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("groq_non_text_response")
        content = content.strip()
        if not content:
            raise RuntimeError("groq_empty_response")
        return content
