import pytest

from core.interaction_context import InteractionContext
from core.orchestration import OrchestrationCoordinator, OrchestrationEnvelope, OrchestrationStage
from core.user_understanding import SignalKind, UserSignal


def _envelope(metadata=()):
    signal = UserSignal(SignalKind.FORMAT, "detailed", 0.8, ("evidence-test",))
    context = InteractionContext(
        profile_id="profile-test",
        signals=(signal,),
        context_id="ctx-test",
    )
    return OrchestrationEnvelope(
        request_id="req-test",
        principal_id="exec-test",
        operation="compute",
        interaction_context=context,
        metadata=metadata,
    )


def test_reject_from_every_non_terminal_stage():
    stage_order = (
        OrchestrationStage.RECEIVED,
        OrchestrationStage.UNDERSTOOD,
        OrchestrationStage.REPRESENTED,
        OrchestrationStage.ROUTED,
        OrchestrationStage.PLANNED,
        OrchestrationStage.EXECUTING,
        OrchestrationStage.VERIFYING,
    )
    for target in stage_order:
        envelope = _envelope()
        target_index = stage_order.index(target)
        for next_stage in stage_order[1:target_index + 1]:
            envelope, _ = OrchestrationCoordinator.transition(envelope, next_stage)
        rejected, transition = OrchestrationCoordinator.reject(envelope)
        assert rejected.stage is OrchestrationStage.REJECTED
        assert transition.previous is target
        assert transition.current is OrchestrationStage.REJECTED


def test_rejected_and_committed_are_terminal():
    rejected, _ = OrchestrationCoordinator.reject(_envelope())
    with pytest.raises(ValueError, match="terminal_orchestration_stage"):
        OrchestrationCoordinator.reject(rejected)

    envelope = _envelope()
    for target in (
        OrchestrationStage.UNDERSTOOD,
        OrchestrationStage.REPRESENTED,
        OrchestrationStage.ROUTED,
        OrchestrationStage.PLANNED,
        OrchestrationStage.EXECUTING,
        OrchestrationStage.VERIFYING,
    ):
        envelope, _ = OrchestrationCoordinator.transition(envelope, target)
    committed, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.COMMITTED)
    with pytest.raises(ValueError, match="terminal_orchestration_stage"):
        OrchestrationCoordinator.reject(committed)


def test_metadata_rejects_duplicate_keys():
    with pytest.raises(ValueError, match="duplicate_metadata_key"):
        _envelope((("mode", "safe"), ("mode", "other")))


def test_metadata_rejects_blank_keys():
    with pytest.raises(ValueError, match="invalid_metadata_key"):
        _envelope(((" ", "value"),))


def test_metadata_accepts_unique_bounded_keys():
    envelope = _envelope((("mode", "safe"), ("source", "verified")))
    assert len(OrchestrationCoordinator.digest(envelope)) == 64
