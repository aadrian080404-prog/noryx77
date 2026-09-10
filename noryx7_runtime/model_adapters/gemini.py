from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Sequence


class GeminiAdapter:
    """NORYX7 provider adapter for Google's Gemini API.

    The adapter intentionally implements the current NORYX7 string ModelAdapter
    contract. Multimodal payloads, tool calls and live sessions stay behind their
    own explicit contracts instead of being faked through a text-only boundary.
    """

    def __init__(
        self,
        *,
        model: str = "gemini-3.8-flash",
        api_key: str | None = None,
        timeout_seconds: float = 90.0,
        system_instruction: str = "",
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")

        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("GEMINI_API_KEY is missing or invalid")

        self.name = f"gemini/{model}"
        self.capabilities = frozenset({
            "text",
            "chat",
            "reasoning",
            "cloud",
            "gemini",
        })
        self.cost_per_call = float(os.environ.get("NORYX7_GEMINI_COST_PER_CALL", "0.0"))
        self.expected_latency_ms = float(os.environ.get("NORYX7_GEMINI_LATENCY_MS", "4000"))
        if self.cost_per_call < 0 or self.expected_latency_ms <= 0:
            raise ValueError("invalid Gemini economics")

        self._api_key = key.strip()
        self._model = model.strip()
        self._timeout_seconds = float(timeout_seconds)
        self._system_instruction = system_instruction.strip()

    def generate(self, prompt: str, *, tools: Sequence[str] = ()) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt is required")
        if tools:
            raise ValueError(
                "tools are not enabled through the current string-only ModelAdapter contract"
            )

        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        if self._system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": self._system_instruction}]
            }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"gemini_http_error:{exc.code}:{body[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"gemini_connection_error:{exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("gemini_timeout") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("gemini_invalid_json_response") from exc
        if not isinstance(data, dict):
            raise RuntimeError("gemini_invalid_response")
        if "error" in data:
            error = data["error"]
            if isinstance(error, dict):
                raise RuntimeError(
                    "gemini_model_error:"
                    f"{error.get('code', 'unknown')}:"
                    f"{error.get('message', 'unknown_error')}"
                )
            raise RuntimeError("gemini_model_error")

        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeError("gemini_missing_candidates")
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            raise RuntimeError("gemini_invalid_candidate")
        content = candidate.get("content")
        if not isinstance(content, dict):
            raise RuntimeError("gemini_missing_content")
        parts = content.get("parts")
        if not isinstance(parts, list):
            raise RuntimeError("gemini_missing_parts")

        text_parts: list[str] = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        result = "".join(text_parts).strip()
        if not result:
            raise RuntimeError("gemini_empty_response")
        return result
