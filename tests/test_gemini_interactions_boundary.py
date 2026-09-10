import json

import pytest

from noryx7_runtime.model_adapters.gemini_interactions import GeminiInteractionsAdapter, GeminiPart


def _adapter(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return GeminiInteractionsAdapter(model="gemini-3.8-flash")


def test_function_tools_reject_non_function_provider_tools(monkeypatch):
    adapter = _adapter(monkeypatch)
    with pytest.raises(ValueError, match="only_noryx7_function_declarations_are_supported"):
        adapter._validate_tools(({"type": "google_search"},))


def test_interact_continuation_payload_binds_previous_interaction(monkeypatch):
    adapter = _adapter(monkeypatch)
    captured = {}

    def fake_post(payload):
        captured.update(payload)
        return {"id": "next", "steps": []}

    monkeypatch.setattr(adapter, "_post_json", fake_post)
    adapter.interact(
        (GeminiPart("text", "continue"),),
        previous_interaction_id="int_123",
    )

    assert captured["previous_interaction_id"] == "int_123"
    assert captured["input"] == [{"type": "text", "text": "continue"}]


def test_stream_function_results_emits_streaming_payload(monkeypatch):
    adapter = _adapter(monkeypatch)
    captured = {}

    def fake_stream(payload):
        captured.update(payload)
        yield {"event_type": "interaction.completed"}

    monkeypatch.setattr(adapter, "_stream", fake_stream)
    events = list(
        adapter.stream_function_results(
            "int_123",
            ({"name": "noryx_tool", "call_id": "call_1", "result": {"ok": True}},),
        )
    )

    assert events == [{"event_type": "interaction.completed"}]
    assert captured["stream"] is True
    assert captured["previous_interaction_id"] == "int_123"
    assert captured["input"] == [
        {
            "type": "function_result",
            "name": "noryx_tool",
            "call_id": "call_1",
            "result": {"ok": True},
        }
    ]


def test_stream_request_uses_sse_accept_header(monkeypatch):
    adapter = _adapter(monkeypatch)
    request = adapter._request({"stream": True}, stream=True)
    assert request.get_header("Accept") == "text/event-stream"
    assert json.loads(request.data.decode("utf-8"))["stream"] is True
