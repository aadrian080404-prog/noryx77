from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterator, Sequence


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
            try:
                base64.b64decode(self.data, validate=True)
            except Exception as exc:
                raise ValueError("media_data_must_be_base64") from exc
            return {"type": self.type, "data": self.data, "mime_type": self.mime_type}
        raise ValueError("unsupported_gemini_part_type")


class GeminiInteractionsAdapter:
    """Explicit NORYX7 boundary for Gemini multimodal Interactions.

    Function declarations are data only: NORYX7 must execute the selected
    function through its own authorization/action-gate boundary. Google-hosted
    tools are intentionally not enabled here yet, so they cannot bypass that
    policy boundary.
    """

    def __init__(self, *, model: str = "gemini-3.8-flash", api_key: str | None = None, timeout_seconds: float = 120.0) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("GEMINI_API_KEY is missing or invalid")
        self.name = f"gemini-interactions/{model}"
        self.capabilities = frozenset({"text", "chat", "reasoning", "cloud", "gemini", "multimodal", "vision", "audio", "video", "documents", "function_calling", "streaming"})
        self.cost_per_call = float(os.environ.get("NORYX7_GEMINI_COST_PER_CALL", "0.0"))
        self.expected_latency_ms = float(os.environ.get("NORYX7_GEMINI_LATENCY_MS", "4000"))
        if self.cost_per_call < 0 or self.expected_latency_ms <= 0:
            raise ValueError("invalid Gemini economics")
        self._model = model.strip()
        self._api_key = key.strip()
        self._timeout_seconds = float(timeout_seconds)

    @staticmethod
    def _validate_tools(tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        validated: list[dict[str, Any]] = []
        for tool in tools:
            if not isinstance(tool, dict) or tool.get("type", "function") != "function" or not isinstance(tool.get("name"), str) or not tool["name"].strip():
                raise ValueError("only_authorized_function_declarations_are_supported")
            validated.append(dict(tool))
        return validated

    def _request(self, payload: dict[str, Any], *, stream: bool) -> urllib.request.Request:
        return urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json", "Accept": "text/event-stream" if stream else "application/json"},
            method="POST",
        )

    def interact(self, parts: Sequence[GeminiPart], *, tools: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
        if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)) or not parts:
            raise ValueError("at_least_one_gemini_part_required")
        payload: dict[str, Any] = {"model": self._model, "input": [part.as_payload() for part in parts]}
        if tools:
            payload["tools"] = self._validate_tools(tools)
        request = self._request(payload, stream=False)
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

    def stream(self, parts: Sequence[GeminiPart], *, tools: Sequence[dict[str, Any]] = ()) -> Iterator[dict[str, Any]]:
        if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)) or not parts:
            raise ValueError("at_least_one_gemini_part_required")
        payload: dict[str, Any] = {"model": self._model, "input": [part.as_payload() for part in parts], "stream": True}
        if tools:
            payload["tools"] = self._validate_tools(tools)
        request = self._request(payload, stream=True)
        try:
            response = urllib.request.urlopen(request, timeout=self._timeout_seconds)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"gemini_interactions_http_error:{exc.code}:{body[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"gemini_interactions_connection_error:{exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("gemini_interactions_timeout") from exc
        try:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise RuntimeError("gemini_interactions_invalid_stream_event") from exc
                if isinstance(event, dict):
                    if isinstance(event.get("error"), dict):
                        error = event["error"]
                        raise RuntimeError(f"gemini_interactions_model_error:{error.get('code', 'unknown')}:{error.get('message', 'unknown_error')}")
                    yield event
        finally:
            response.close()
