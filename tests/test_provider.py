import pytest

from models.provider import MockModelProvider, ModelProvider


def test_model_provider_is_abstract():
    with pytest.raises(TypeError):
        ModelProvider()


def test_mock_provider_returns_deterministic_response():
    provider = MockModelProvider("hello")

    result = provider.generate("plan a trip")

    assert result == "hello :: prompt=plan a trip"


def test_mock_provider_uses_default_response_when_not_specified():
    provider = MockModelProvider()

    assert provider.generate("test prompt") == "Mock model response :: prompt=test prompt"
