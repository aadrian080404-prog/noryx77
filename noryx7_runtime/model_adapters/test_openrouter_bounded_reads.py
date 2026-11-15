import io
import json
import urllib.error

import pytest

from noryx7_runtime.model_adapters import openrouter


class FakeResponse:
    def __init__(self, body, headers=None):
        self.body = io.BytesIO(body)
        self.headers = headers or {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.body.read(size)


def _adapter(max_response_bytes=1024):
    return openrouter.OpenRouterAdapter(
        api_key="sk-or-v1-test",
        max_response_bytes=max_response_bytes,
    )


def _body(text="verified answer"):
    return json.dumps({"choices": [{"message": {"content": text}}]}).encode()


def test_valid_bounded_json_response_is_accepted(monkeypatch):
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *_a, **_k: FakeResponse(_body()))
    assert _adapter().generate("hello") == "verified answer"


def test_oversized_success_body_is_rejected(monkeypatch):
    body = _body("x" * 2048)
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *_a, **_k: FakeResponse(body))
    with pytest.raises(RuntimeError, match="openrouter_response_too_large"):
        _adapter(256).generate("hello")


def test_declared_oversized_content_length_is_rejected_before_read(monkeypatch):
    class NoRead(FakeResponse):
        def read(self, size=-1):
            raise AssertionError("body must not be read")

    monkeypatch.setattr(
        openrouter.urllib.request,
        "urlopen",
        lambda *_a, **_k: NoRead(b"", {"Content-Type": "application/json", "Content-Length": "9999"}),
    )
    with pytest.raises(RuntimeError, match="openrouter_response_too_large"):
        _adapter(128).generate("hello")


def test_non_json_content_type_is_rejected(monkeypatch):
    monkeypatch.setattr(
        openrouter.urllib.request,
        "urlopen",
        lambda *_a, **_k: FakeResponse(_body(), {"Content-Type": "text/plain"}),
    )
    with pytest.raises(RuntimeError, match="openrouter_invalid_content_type"):
        _adapter().generate("hello")


def test_malformed_json_is_rejected(monkeypatch):
    monkeypatch.setattr(
        openrouter.urllib.request,
        "urlopen",
        lambda *_a, **_k: FakeResponse(b"{", {"Content-Type": "application/json"}),
    )
    with pytest.raises(RuntimeError, match="openrouter_invalid_json_response"):
        _adapter().generate("hello")


def test_oversized_http_error_body_is_bounded(monkeypatch):
    error = urllib.error.HTTPError(
        "https://openrouter.ai/api/v1/chat/completions",
        502,
        "bad gateway",
        {"Content-Length": "4096"},
        io.BytesIO(b"x" * 4096),
    )
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(error))
    with pytest.raises(RuntimeError, match="openrouter_http_error:502:openrouter_response_too_large"):
        _adapter(128).generate("hello")


def test_invalid_response_limit_is_rejected():
    with pytest.raises(ValueError, match="max_response_bytes"):
        openrouter.OpenRouterAdapter(api_key="sk-or-v1-test", max_response_bytes=True)
