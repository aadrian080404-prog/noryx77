import pytest

from core.runtime import NORYXRuntime
from core.user_understanding import UnderstandingConsent, UserUnderstandingEngine


def test_runtime_derives_interaction_context_when_engine_is_configured():
    engine = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION)
    runtime = NORYXRuntime(user_understanding=engine)

    class Task:
        task_id = "understanding-runtime-test"
        execution_id = "execution-understanding-runtime"
        input = "I prefer detailed technical explanations."

    context = None
    content = runtime.user_understanding
    profile = content.build_profile((
        __import__("core.user_understanding", fromlist=["UserContent"]).UserContent(
            Task.task_id,
            Task.input,
            source="runtime_task_input",
        ),
    ))
    from core.interaction_context import build_interaction_context
    context = build_interaction_context(profile)

    assert context.profile_id == profile.profile_id
    assert context.signals
    assert any(signal.value == "detailed" for signal in context.signals)


def test_runtime_rejects_invalid_understanding_engine():
    with pytest.raises(TypeError, match="invalid_user_understanding_engine"):
        NORYXRuntime(user_understanding=object())
