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
            if not isinstance(self.data, str) or not self.data.strip():
                raise ValueError("empty_text_part")
            return {"type": "text", "text": self.data}
        if self.type in {"image", "audio", "video", "document"}:
            if not isinstance(self.data, str) or not self.data:
                raise ValueError("media_data_required")
            if not isinstance(self.mime_type, str) or not self.mime_type.strip():
                raise ValueError("mime_type_required")
            try:
                base64.b64decode(self.data, validate=True)
            except Exception as exc:
                raise ValueError("media_data_must_be_base64") from exc
            return {"type": self.type, "data": self.data, "mime_type": self.mime_type}
        raise ValueError("unsupported_gemini_part_type")


class GeminiInteractionsAdapter:
    """NORYX7 boundary for Gemini multimodal and agentic Interactions.

    Model tool declarations are data only. NORYX7 remains responsible for
    authorization, ActionGate execution, verification, provenance and audit.
    Google-hosted tools are intentionally not enabled through this adapter.
    """

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"

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
            if not isinstance(tool, dict) or tool.get("type", "function") != "function":
                raise ValueError("only_noryx7_function_declarations_are_supported")
            name = tool.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("function_name_required")
            validated.append(dict(tool))
        return validated

    def _request(self, payload: dict[str, Any], *, stream: bool) -> urllib.request.Request:
        return urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json",
            },
            method="POST",
        )

    @staticmethod
    def _validate_parts(parts: Sequence[GeminiPart]) -> tuple[GeminiPart, ...]:
        if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)) or not parts:
            raise ValueError("at_least_one_gemini_part_required")
        validated = tuple(parts)
        if any(not isinstance(part, GeminiPart) for part in validated):
            raise ValueError("invalid_gemini_part")
        return validated

    @staticmethod
    def extract_function_calls(result: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        if not isinstance(result, dict):
            raise ValueError("invalid_gemini_interaction")
        calls: list[dict[str, Any]] = []
        for step in result.get("steps", ()):
            if not isinstance(step, dict) or step.get("type") != "function_call":
                continue
            name = step.get("name")
            call_id = step.get("id") or step.get("call_id")
            arguments = step.get("arguments", {})
            if not isinstance(name, str) or not name.strip() or not isinstance(call_id, str) or not call_id.strip() or not isinstance(arguments, dict):
                raise ValueError("invalid_gemini_function_call")
            calls.append({"name": name, "call_id": call_id, "arguments": dict(arguments)})
        return tuple(calls)

    @staticmethod
    def extract_text(result: dict[str, Any]) -> str:
        if not isinstance(result, dict):
            raise ValueError("invalid_gemini_interaction")
        chunks: list[str] = []
        for step in result.get("steps", ()):
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            content = step.get("content", ())
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        chunks.append(part["text"])
        text = "".join(chunks).strip()
        if not text:
            raise ValueError("gemini_interaction_empty_text")
        return text

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
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

    def interact(self, parts: Sequence[GeminiPart], *, tools: Sequence[dict[str, Any]] = (), previous_interaction_id: str | None = None) -> dict[str, Any]:
        validated_parts = self._validate_parts(parts)
        payload: dict[str, Any] = {"model": self._model, "input": [part.as_payload() for part in validated_parts]}
        if previous_interaction_id is not None:
            if not isinstance(previous_interaction_id, str) or not previous_interaction_id.strip():
                raise ValueError("previous_interaction_id_required")
            payload["previous_interaction_id"] = previous_interaction_id.strip()
        if tools:
            payload["tools"] = self._validate_tools(tools)
        return self._post_json(payload)

    def continue_interaction(self, previous_interaction_id: str, function_results: Sequence[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(previous_interaction_id, str) or not previous_interaction_id.strip():
            raise ValueError("previous_interaction_id_required")
        if not isinstance(function_results, Sequence) or isinstance(function_results, (str, bytes)) or not function_results:
            raise ValueError("function_results_required")
        input_items: list[dict[str, Any]] = []
        for item in function_results:
            if not isinstance(item, dict):
                raise ValueError("invalid_function_result")
            call_id = item.get("call_id")
            name = item.get("name")
            result = item.get("result")
            if not isinstance(call_id, str) or not call_id.strip() or not isinstance(name, str) or not name.strip():
                raise ValueError("function_result_identity_required")
            input_items.append({"type": "function_result", "name": name, "call_id": call_id, "result": result})
        return self._post_json({"model": self._model, "previous_interaction_id": previous_interaction_id.strip(), "input": input_items})

    def _stream(self, payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
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

    def stream(self, parts: Sequence[GeminiPart], *, tools: Sequence[dict[str, Any]] = (), previous_interaction_id: str | None = None) -> Iterator[dict[str, Any]]:
        validated_parts = self._validate_parts(parts)
        payload: dict[str, Any] = {"model": self._model, "input": [part.as_payload() for part in validated_parts], "stream": True}
        if previous_interaction_id is not None:
            if not isinstance(previous_interaction_id, str) or not previous_interaction_id.strip():
                raise ValueError("previous_interaction_id_required")
            payload["previous_interaction_id"] = previous_interaction_id.strip()
        if tools:
            payload["tools"] = self._validate_tools(tools)
        yield from self._stream(payload)

    def stream_function_results(self, previous_interaction_id: str, function_results: Sequence[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        if not isinstance(previous_interaction_id, str) or not previous_interaction_id.strip():
            raise ValueError("previous_interaction_id_required")
        if not isinstance(function_results, Sequence) or isinstance(function_results, (str, bytes)) or not function_results:
            raise ValueError("function_results_required")
        input_items: list[dict[str, Any]] = []
        for item in function_results:
            if not isinstance(item, dict):
                raise ValueError("invalid_function_result")
            call_id = item.get("call_id")
            name = item.get("name")
            result = item.get("result")
            if not isinstance(call_id, str) or not call_id.strip() or not isinstance(name, str) or not name.strip():
                raise ValueError("function_result_identity_required")
            input_items.append({"type": "function_result", "name": name, "call_id": call_id, "result": result})
        yield from self._stream({"model": self._model, "previous_interaction_id": previous_interaction_id.strip(), "input": input_items, "stream": True})
