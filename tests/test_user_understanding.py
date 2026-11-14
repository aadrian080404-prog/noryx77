import pytest

from core.user_understanding import (
    UnderstandingConsent,
    SignalKind,
    UserContent,
    UserUnderstandingEngine,
)


def test_pre_interaction_profile_is_deterministic_and_contains_only_bounded_signals():
    contents = (
        UserContent("c1", "I prefer detailed step by step programming and research."),
        UserContent("c2", "I like direct technical explanations and verification."),
    )
    engine = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION)
    first = engine.build_profile(contents)
    second = engine.build_profile(contents)

    assert first.profile_id == second.profile_id
    assert first.signals == second.signals
    assert first.raw_content_retained is False
    assert any(s.kind is SignalKind.TOPIC and s.value == "programming" for s in first.signals)
    assert any(s.kind is SignalKind.FORMAT and s.value == "step_by_step" for s in first.signals)
    assert any(s.kind is SignalKind.TONE and s.value == "direct" for s in first.signals)


def test_denied_consent_fails_closed():
    engine = UserUnderstandingEngine(consent=UnderstandingConsent.DENIED)
    with pytest.raises(PermissionError):
        engine.build_profile((UserContent("c1", "programming"),))


def test_raw_content_is_not_retained_and_evidence_is_scoped_to_content_id():
    item = UserContent("private-1", "I prefer concise technical answers.")
    profile = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION).build_profile((item,))
    assert profile.raw_content_retained is False
    assert all(item.text not in signal.value for signal in profile.signals)
    assert all(len(signal.evidence_ids) == 1 for signal in profile.signals)


def test_profile_changes_when_supported_preferences_change():
    engine = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION)
    concise = engine.build_profile((UserContent("c1", "concise direct answers"),))
    detailed = engine.build_profile((UserContent("c1", "detailed exploratory answers"),))
    assert concise.profile_id != detailed.profile_id


def test_first_interaction_returns_profile_signals_without_raw_content():
    engine = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION)
    profile = engine.build_profile((UserContent("c1", "I prefer friendly technical explanations."),))
    signals = engine.prepare_first_interaction(profile)
    assert signals == profile.signals
    assert all(isinstance(signal.value, str) for signal in signals)


def test_duplicate_evidence_increases_confidence_without_unbounded_growth():
    engine = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION)
    profile = engine.build_profile((
        UserContent("c1", "programming programming"),
        UserContent("c2", "programming"),
    ))
    topic = next(signal for signal in profile.signals if signal.kind is SignalKind.TOPIC and signal.value == "programming")
    assert 0.70 <= topic.confidence <= 1.0
    assert len(topic.evidence_ids) == 2
