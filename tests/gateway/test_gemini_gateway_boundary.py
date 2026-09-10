from __future__ import annotations

import pytest

from noryx7_runtime.model_adapters.gemini_interactions import GeminiInteractionsAdapter, GeminiPart
from web.app import app


def test_gemini_gateway_routes_are_registered() -> None:
    routes = {getattr(route, "path", "") for route in app.routes}
    assert "/v1/gemini/interaction" in routes
    assert "/v1/gemini/stream" in routes
    assert "/v1/gemini/stream/function-results" in routes


def test_gemini_part_rejects_invalid_media() -> None:
    with pytest.raises(ValueError, match="media_data_must_be_base64"):
        GeminiPart(type="image", data="not-base64", mime_type="image/png").as_payload()


def test_gemini_tools_are_noryx7_function_only() -> None:
    with pytest.raises(ValueError, match="only_noryx7_function_declarations_are_supported"):
        GeminiInteractionsAdapter._validate_tools([{"type": "google_search"}])


def test_gemini_function_result_requires_identity() -> None:
    adapter = object.__new__(GeminiInteractionsAdapter)
    with pytest.raises(ValueError, match="function_result_identity_required"):
        adapter.continue_interaction("interaction-1", [{"name": "tool", "result": {}}])
