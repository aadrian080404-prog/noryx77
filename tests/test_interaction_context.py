import pytest

from core.interaction_context import build_interaction_context
from core.user_understanding import (
    SignalKind,
    UnderstandingConsent,
    UserContent,
    UserSignal,
    UserUnderstandingEngine,
    UserUnderstandingProfile,
)


def _profile():
    return UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION).build_profile(
        (UserContent("c1", "I prefer direct technical programming answers."),)
    )


def test_context_is_deterministic_and_contains_only_derived_signals():
    profile = _profile()
    first = build_interaction_context(profile)
    second = build_interaction_context(profile)

    assert first == second
    rendered = first.as_prompt_context()
    assert "direct" in rendered
    assert "programming" in rendered
    assert "c1" not in rendered
    assert "I prefer" not in rendered


def test_context_rejects_raw_content_profiles():
    profile = _profile()
    object.__setattr__(profile, "raw_content_retained", True)
    with pytest.raises(ValueError, match="raw_content_not_allowed"):
        build_interaction_context(profile)


def test_context_requires_a_profile():
    with pytest.raises(TypeError, match="understanding_profile_required"):
        build_interaction_context(None)


def test_context_has_stable_nonempty_identifier():
    context = build_interaction_context(_profile())
    assert len(context.context_id) == 64
    assert all(char in "0123456789abcdef" for char in context.context_id)


def test_context_fails_closed_on_signal_overflow():
    evidence = ("evidence",)
    signals = tuple(
        UserSignal(SignalKind.TOPIC, f"topic-{index}", 0.7, evidence)
        for index in range(33)
    )
    profile = UserUnderstandingProfile("profile", signals, 1)
    with pytest.raises(ValueError, match="interaction_signal_capacity_exceeded"):
        build_interaction_context(profile)
