import pytest

from ecosystem.boundaries import Front, make_intent


def test_all_four_fronts_are_explicit_and_distinct():
    assert {front.value for front in Front} == {"jarvis", "browser", "hypersynth", "orchestration"}


def test_intent_is_deterministic_and_payload_is_only_digest():
    first = make_intent(Front.JARVIS, "execute", b"secret payload")
    second = make_intent(Front.JARVIS, "execute", b"secret payload")
    assert first == second
    assert len(first.payload_digest) == 64
    assert "secret payload" not in first.payload_digest


def test_payload_changes_intent_identity():
    first = make_intent(Front.BROWSER, "navigate", b"one")
    second = make_intent(Front.BROWSER, "navigate", b"two")
    assert first.intent_id != second.intent_id


def test_invalid_payload_type_fails_closed():
    with pytest.raises(TypeError, match="payload_bytes_required"):
        make_intent(Front.HYPERSYNTH, "plan", "raw")


def test_operation_size_is_bounded():
    with pytest.raises(ValueError, match="operation_size_exceeded"):
        make_intent(Front.ORCHESTRATION, "x" * 4097, b"")
