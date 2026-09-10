from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class GeminiPart:
    """One explicit multimodal input part accepted by NORYX7's Gemini boundary."""

    type: str
    data: str
    mime_type: str = ""

    def as_payload(self) -> dict[str, Any]:
        if self.type == "text":
            if not self.data.strip():
                raise ValueError("empty_text_part")
            return {"type": "text", "text": self.data}
        if self.type in {"image", "audio", "video", "document"}:
            if not self.mime_type.strip():
                raise ValueError("mime_type_required")
            encoded = self.data
            try:
                base64.b64decode(encoded, validate=True)
            except Exception as exc:
                raise ValueError("media_data_must_be_base64") from exc
            return {
                "type": self.type,
                "data": encoded,
                "mime_type": self.mime_type,
            }
        raise ValueError("unsupported_gemini_part_type")


class GeminiInteractionsAdapter:
    """Explicit NORYX7 boundary for Gemini Interactions API capabilities.

    This boundary is deliberately separate from the string-only ModelAdapter.
    It supports multimodal input and server/client tool declarations without
    allowing arbitrary tool execution to bypass NORYX7 authorization gates.
    """

    def __init__(
        self,
        *,
        model: str = "gemini-3.8-flash",
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("GEMINI_API_KEY is missing or invalid")
        self.name = f"gemini-interactions/{model}"
        self.capabilities = frozenset({
            "text", "chat", "reasoning", "cloud", "gemini",
            "multimodal", "vision", "audio", "video", "documents",
            "function_calling", "streaming",
        })
        self.cost_per_call = float(os.environ.get("NORYX7_GEMINI_COST_PER_CALL", "0.0"))
        self.expected_latency_ms = float(os.environ.get("NORYX7_GEMINI_LATENCY_MS", "4000"))
        if self.cost_per_call < 0 or self.expected_latency_ms <= 0:
            raise ValueError("invalid Gemini economics")
        self._model = model.strip()
        self._api_key = key.strip()
        self._timeout_seconds = float(timeout_seconds)

    def interact(
        self,
        parts: Sequence[GeminiPart],
        *,
        tools: Sequence[dict[str, Any]] = (),
        stream: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)) or not parts:
            raise ValueError("at_least_one_gemini_part_required")
        payload: dict[str, Any] = {
            "model": self._model,
            "input": [part.as_payload() for part in parts],
        }
        if tools:
            validated_tools: list[dict[str, Any]] = []
            for tool in tools:
                if not isinstance(tool, dict) or not tool.get("name"):
                    raise ValueError("invalid_gemini_function_declaration")
                validated_tools.append(dict(tool))
            payload["tools"] = validated_tools
        if stream:
            payload["stream"] = True

        request = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
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
            raise RuntimeError(f"gemini_interactions_http_error:{exc.code}:{body[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"gemini_interactions_connection_error:{exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("gemini_interactions_timeout") from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("gemini_interactions_invalid_json") from exc
        if not isinstance(result, dict):
            raise RuntimeError("gemini_interactions_invalid_response")
        if isinstance(result.get("error"), dict):
            error = result["error"]
            raise RuntimeError(f"gemini_interactions_model_error:{error.get('code', 'unknown')}:{error.get('message', 'unknown_error')}")
        return result
